from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


PROCUREMENT_SCHEMA_VERSION = "oms.v1.procurement"
ADMIN_PURCHASE = "ADMIN"
FOOD_PURCHASE = "FOOD"
PURCHASE_TYPES = {ADMIN_PURCHASE, FOOD_PURCHASE}
OWNER_BY_TYPE = {ADMIN_PURCHASE: "EMP005", FOOD_PURCHASE: "EMP007"}
WORKSPACE_BY_EMP = {
    "EMP001": "boss",
    "EMP003": "zhangjie",
    "EMP004": "liujie",
    "EMP005": "yaowei",
    "EMP007": "yuchun",
}
ALLOWED_MIME_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024


class ProcurementService:
    """V1 purchasing workflow with role separation and append-only trace records."""

    def __init__(
        self,
        live_root: str | Path,
        *,
        master_data: OMSMasterData | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
    ):
        self.live_root = Path(live_root)
        self.root = self.live_root / "procurement"
        self.records_path = self.root / "records.json"
        self.attachments_root = self.root / "attachments"
        self.event_path = self.live_root / "events" / "procurement.jsonl"
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine(audit_root=self.live_root / "audit_center")
        self.event_bus = event_bus or EventBus()
        self._lock = threading.RLock()

    def save_draft(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, {"EMP005", "EMP007"})
        purchase_type = ADMIN_PURCHASE if actor.emp == "EMP005" else FOOD_PURCHASE
        with self._lock:
            records = self._read_records()
            record_id = str(payload.get("record_id") or "").strip()
            existing = self._find(records, record_id) if record_id else None
            if existing:
                self._assert_owner(actor, existing)
                if existing.get("status") not in {"DRAFT", "RETURNED"}:
                    raise ValueError("Only draft or returned records can be changed.")
                before = dict(existing)
            else:
                before = {}
                existing = self._new_record(actor, purchase_type)
                records.append(existing)

            attachment = payload.get("attachment")
            if isinstance(attachment, dict) and attachment.get("data_url"):
                attachment_meta, recognized = self._save_and_recognize_attachment(existing["record_id"], attachment, purchase_type)
                existing.setdefault("attachments", []).append(attachment_meta)
                existing["recognition"] = recognized
                self._apply_recognition_defaults(existing, recognized)

            self._apply_editable_fields(existing, payload)
            existing["manual_changes"] = self._manual_changes(existing)
            existing["status"] = "DRAFT"
            existing["updated_at"] = now_iso()
            existing["updated_by_emp_id"] = actor.emp
            existing["returned_reason"] = "" if before.get("status") == "RETURNED" else existing.get("returned_reason", "")
            self._write_records(records)
        self._trace(actor, "procurement.draft.save", payload.get("reason") or "保存采购草稿", existing, "procurement.draft.saved", before)
        return self._public_record(existing, include_attachment_content=True)

    def submit(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, {"EMP005", "EMP007"})
        reason = self._required(payload, "reason")
        with self._lock:
            records = self._read_records()
            record = self._required_record(records, payload)
            self._assert_owner(actor, record)
            if record.get("status") not in {"DRAFT", "RETURNED"}:
                raise ValueError("Only draft or returned records can be submitted.")
            self._validate_submission(record)
            before = dict(record)
            record.update(
                {
                    "status": "PENDING_APPROVAL",
                    "submitted_at": now_iso(),
                    "submitted_by_emp_id": actor.emp,
                    "approval_status": "PENDING",
                    "approval_reason": "",
                    "returned_reason": "",
                    "updated_at": now_iso(),
                }
            )
            self._write_records(records)
        self._trace(actor, "procurement.submit", reason, record, "procurement.submitted", before)
        return self._public_record(record, include_attachment_content=True)

    def decide(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, {"EMP001"})
        reason = self._required(payload, "reason")
        approved = payload.get("approved") is True
        with self._lock:
            records = self._read_records()
            record = self._required_record(records, payload)
            if record.get("status") != "PENDING_APPROVAL":
                raise ValueError("The record is not pending approval.")
            before = dict(record)
            record.update(
                {
                    "status": "APPROVED" if approved else "RETURNED",
                    "approval_status": "APPROVED" if approved else "REJECTED",
                    "approval_reason": reason,
                    "returned_reason": "" if approved else reason,
                    "approved_by_emp_id": actor.emp,
                    "approved_at": now_iso(),
                    "payment_status": "PENDING" if approved else "NOT_READY",
                    "updated_at": now_iso(),
                }
            )
            self._write_records(records)
        action = "procurement.approve" if approved else "procurement.reject"
        event_type = "procurement.approved" if approved else "procurement.returned"
        self._trace(actor, action, reason, record, event_type, before)
        return self._public_record(record, include_attachment_content=True)

    def record_payment(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, {"EMP004"})
        reason = self._required(payload, "reason")
        with self._lock:
            records = self._read_records()
            record = self._required_record(records, payload)
            if record.get("status") != "APPROVED":
                raise ValueError("Only approved purchasing records can be paid.")
            before = dict(record)
            record.update(
                {
                    "status": "PAID",
                    "payment_status": "PAID",
                    "payment_reference": str(payload.get("payment_reference") or "").strip(),
                    "payment_note": str(payload.get("payment_note") or "").strip(),
                    "paid_by_emp_id": actor.emp,
                    "paid_at": now_iso(),
                    "accounting_status": "PENDING",
                    "updated_at": now_iso(),
                }
            )
            self._write_records(records)
        self._trace(actor, "procurement.payment", reason, record, "procurement.paid", before)
        return self._public_record(record, include_attachment_content=True)

    def record_accounting(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, {"EMP003"})
        reason = self._required(payload, "reason")
        with self._lock:
            records = self._read_records()
            record = self._required_record(records, payload)
            if record.get("status") != "PAID":
                raise ValueError("Only paid purchasing records can be accounted.")
            before = dict(record)
            record.update(
                {
                    "status": "ACCOUNTED",
                    "accounting_status": "COMPLETED",
                    "accounting_category": str(payload.get("accounting_category") or record.get("category") or "").strip(),
                    "accounting_note": str(payload.get("accounting_note") or "").strip(),
                    "accounted_by_emp_id": actor.emp,
                    "accounted_at": now_iso(),
                    "updated_at": now_iso(),
                }
            )
            self._write_records(records)
        self._trace(actor, "procurement.account", reason, record, "procurement.accounted", before)
        return self._public_record(record, include_attachment_content=True)

    def confirm_arrival(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, {"EMP007"})
        reason = self._required(payload, "reason")
        with self._lock:
            records = self._read_records()
            record = self._required_record(records, payload)
            self._assert_owner(actor, record)
            if record.get("purchase_type") != FOOD_PURCHASE:
                raise ValueError("Arrival confirmation is only available for food purchasing.")
            if record.get("status") not in {"DRAFT", "RETURNED"}:
                raise ValueError("Arrival can only be confirmed before submission.")
            before = dict(record)
            record.update({"arrival_status": "RECEIVED", "arrival_confirmed_at": now_iso(), "updated_at": now_iso()})
            self._write_records(records)
        self._trace(actor, "procurement.arrival.confirm", reason, record, "procurement.arrival.confirmed", before)
        return self._public_record(record, include_attachment_content=True)

    def list_records(self, claims: dict[str, Any], query: dict[str, Any] | None = None) -> dict[str, Any]:
        actor = self._actor(claims, set(WORKSPACE_BY_EMP))
        query = query or {}
        with self._lock:
            records = self._read_records()
        visible = [record for record in records if self._can_view(actor, record)]
        purchase_type = str(query.get("purchase_type") or "").upper()
        status = str(query.get("status") or "").upper()
        if purchase_type in PURCHASE_TYPES:
            visible = [record for record in visible if record.get("purchase_type") == purchase_type]
        if status:
            visible = [record for record in visible if record.get("status") == status]
        visible.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return {
            "records": [self._public_record(record) for record in visible],
            "total": len(visible),
            "scope": actor.emp,
            "source": "OMS_PROCUREMENT_V1",
        }

    def get_record(self, claims: dict[str, Any], record_id: str) -> dict[str, Any]:
        actor = self._actor(claims, set(WORKSPACE_BY_EMP))
        with self._lock:
            record = self._find(self._read_records(), record_id)
        if record is None:
            raise KeyError(f"Unknown procurement record: {record_id}")
        if not self._can_view(actor, record):
            raise PermissionError("procurement_record_not_visible")
        return self._public_record(record, include_attachment_content=True)

    def _new_record(self, actor: Employee, purchase_type: str) -> dict[str, Any]:
        timestamp = now_iso()
        return {
            "schema_version": PROCUREMENT_SCHEMA_VERSION,
            "record_id": new_id("purchase"),
            "purchase_type": purchase_type,
            "owner_emp_id": actor.emp,
            "owner_user_id": actor.user_id,
            "owner_name": actor.name,
            "status": "DRAFT",
            "approval_status": "NOT_SUBMITTED",
            "payment_status": "NOT_READY",
            "accounting_status": "NOT_READY",
            "arrival_status": "NOT_REQUIRED" if purchase_type == ADMIN_PURCHASE else "PENDING",
            "title": "",
            "amount": 0.0,
            "purchase_date": "",
            "supplier": "",
            "category": "",
            "quantity": "",
            "unit": "",
            "unit_price": "",
            "items": [],
            "remark": "",
            "attachments": [],
            "recognition": {"status": "NOT_STARTED", "fields": {}, "items": [], "raw_text": ""},
            "manual_changes": [],
            "created_at": timestamp,
            "updated_at": timestamp,
            "source": "OMS_OPERATION",
        }

    def _save_and_recognize_attachment(self, record_id: str, attachment: dict[str, Any], purchase_type: str) -> tuple[dict[str, Any], dict[str, Any]]:
        name = str(attachment.get("name") or "采购凭证").strip()
        data_url = str(attachment.get("data_url") or "")
        match = re.fullmatch(r"data:([^;,]+);base64,(.+)", data_url, flags=re.DOTALL)
        if not match or match.group(1) not in ALLOWED_MIME_TYPES:
            raise ValueError("Only JPG, PNG and WebP purchasing evidence is supported.")
        try:
            content = base64.b64decode(match.group(2), validate=True)
        except ValueError as exc:
            raise ValueError("Invalid purchasing evidence.") from exc
        if not content or len(content) > MAX_ATTACHMENT_BYTES:
            raise ValueError("Purchasing evidence must be between 1 byte and 8 MB.")
        attachment_id = new_id("purchase_attachment")
        suffix = ALLOWED_MIME_TYPES[match.group(1)]
        self.attachments_root.mkdir(parents=True, exist_ok=True)
        target = self.attachments_root / f"{attachment_id}{suffix}"
        target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        meta = {
            "attachment_id": attachment_id,
            "name": name,
            "mime_type": match.group(1),
            "size": len(content),
            "sha256": digest,
            "stored_name": target.name,
            "uploaded_at": now_iso(),
        }
        return meta, self._recognize(target, purchase_type)

    def _recognize(self, path: Path, purchase_type: str) -> dict[str, Any]:
        raw_text = ""
        engine = "人工核对"
        if shutil.which("tesseract"):
            try:
                result = subprocess.run(
                    ["tesseract", str(path), "stdout", "-l", "chi_sim+eng", "--psm", "6"],
                    capture_output=True,
                    text=True,
                    timeout=25,
                    check=False,
                )
                raw_text = (result.stdout or "").strip()
                engine = "中文凭证识别"
            except (OSError, subprocess.TimeoutExpired):
                raw_text = ""
        fields, items = self._parse_recognition(raw_text, purchase_type)
        return {
            "status": "RECOGNIZED" if raw_text else "NEEDS_MANUAL_REVIEW",
            "engine": engine,
            "fields": fields,
            "items": items,
            "raw_text": raw_text,
            "recognized_at": now_iso(),
            "manual_correction_allowed": True,
        }

    def _parse_recognition(self, raw_text: str, purchase_type: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        text = raw_text.replace("，", ",").replace("：", ":")
        amounts = [Decimal(value) for value in re.findall(r"(?:金额|合计|实付|支付|总计)\s*[:：]?\s*[¥￥]?\s*(\d+(?:\.\d{1,2})?)", text)]
        date_match = re.search(r"(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})", text)
        supplier_match = re.search(r"([^\n]{2,30}(?:公司|商贸|超市|市场|商店|门店|供应链))", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        ignored = ("金额", "合计", "实付", "支付", "订单", "日期", "微信", "交易")
        title = next((line[:80] for line in lines if not any(term in line for term in ignored)), "")
        fields: dict[str, Any] = {
            "title": title,
            "amount": float(max(amounts)) if amounts else 0.0,
            "purchase_date": "-".join([date_match.group(1), date_match.group(2).zfill(2), date_match.group(3).zfill(2)]) if date_match else "",
            "supplier": supplier_match.group(1).strip() if supplier_match else "",
            "category": self._suggest_category(text, purchase_type),
        }
        items: list[dict[str, Any]] = []
        if purchase_type == FOOD_PURCHASE:
            pattern = re.compile(r"([\u4e00-\u9fff]{1,12})\s+(\d+(?:\.\d+)?)\s*(斤|公斤|千克|克|袋|箱|瓶|个|盒)?(?:\s+[xX×]?\s*(\d+(?:\.\d{1,2})?))?(?:\s+(\d+(?:\.\d{1,2})?))?")
            for match in pattern.finditer(text):
                quantity = match.group(2)
                unit_price = match.group(4) or ""
                total = match.group(5) or ""
                items.append({"name": match.group(1), "quantity": quantity, "unit": match.group(3) or "", "unit_price": unit_price, "amount": total})
            if items and not fields["title"]:
                fields["title"] = items[0]["name"]
        return fields, items

    @staticmethod
    def _suggest_category(text: str, purchase_type: str) -> str:
        if purchase_type == FOOD_PURCHASE:
            groups = (("蔬菜", "蔬菜"), ("水果", "水果"), ("肉", "肉禽蛋"), ("蛋", "肉禽蛋"), ("奶", "乳制品"), ("米", "粮油调味"), ("油", "粮油调味"))
            return next((category for keyword, category in groups if keyword in text), "其他食材")
        groups = (("纸", "办公与耗材"), ("清洁", "清洁用品"), ("维修", "维修服务"), ("打印", "办公与耗材"), ("设备", "设备用品"))
        return next((category for keyword, category in groups if keyword in text), "其他行政采购")

    def _apply_recognition_defaults(self, record: dict[str, Any], recognized: dict[str, Any]) -> None:
        for key, value in (recognized.get("fields") or {}).items():
            if value not in (None, "", 0, 0.0) and record.get(key) in (None, "", 0, 0.0):
                record[key] = value
        if recognized.get("items") and not record.get("items"):
            record["items"] = recognized["items"]

    def _apply_editable_fields(self, record: dict[str, Any], payload: dict[str, Any]) -> None:
        for key in ("title", "purchase_date", "supplier", "category", "quantity", "unit", "unit_price", "remark"):
            if key in payload:
                record[key] = str(payload.get(key) or "").strip()
        if "amount" in payload and str(payload.get("amount") or "").strip():
            record["amount"] = self._amount(payload.get("amount"))
        if isinstance(payload.get("items"), list):
            record["items"] = [self._normalize_item(item) for item in payload["items"] if isinstance(item, dict)]

    def _manual_changes(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        recognized = record.get("recognition") or {}
        original = recognized.get("fields") or {}
        changes: list[dict[str, Any]] = []
        for key in ("title", "amount", "purchase_date", "supplier", "category"):
            if key in original and str(original.get(key) or "") != str(record.get(key) or ""):
                changes.append({"field": key, "recognized_value": original.get(key), "current_value": record.get(key)})
        if (recognized.get("items") or []) != (record.get("items") or []):
            changes.append({"field": "items", "recognized_value": recognized.get("items") or [], "current_value": record.get("items") or []})
        return changes

    @staticmethod
    def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
        return {key: str(item.get(key) or "").strip() for key in ("name", "quantity", "unit", "unit_price", "amount")}

    def _validate_submission(self, record: dict[str, Any]) -> None:
        if not record.get("attachments"):
            raise ValueError("At least one purchasing evidence image is required.")
        if not str(record.get("title") or "").strip():
            raise ValueError("Purchasing name is required.")
        if self._amount(record.get("amount")) <= 0:
            raise ValueError("Purchasing amount must be greater than zero.")
        if not str(record.get("purchase_date") or "").strip():
            raise ValueError("Purchasing date is required.")

    def _actor(self, claims: dict[str, Any], allowed_emp_ids: set[str]) -> Employee:
        user_id = str(claims.get("user_id") or "").strip()
        workspace_key = str(claims.get("workspace_key") or "").strip()
        actor = next((employee for employee in self.master_data.employees() if user_id and user_id in {employee.user_id, employee.open_id, employee.union_id}), None)
        if actor is None:
            raise PermissionError("session_identity_not_in_master_data")
        if actor.emp not in allowed_emp_ids:
            raise PermissionError("procurement_operation_not_authorized")
        if workspace_key != WORKSPACE_BY_EMP.get(actor.emp):
            raise PermissionError("session_workspace_mismatch")
        return actor

    @staticmethod
    def _assert_owner(actor: Employee, record: dict[str, Any]) -> None:
        if record.get("owner_emp_id") != actor.emp:
            raise PermissionError("procurement_record_not_owned")

    @staticmethod
    def _can_view(actor: Employee, record: dict[str, Any]) -> bool:
        if actor.emp == "EMP001":
            return True
        if actor.emp == "EMP004":
            return record.get("status") in {"APPROVED", "PAID", "ACCOUNTED"}
        if actor.emp == "EMP003":
            return record.get("status") in {"PAID", "ACCOUNTED"}
        return record.get("owner_emp_id") == actor.emp

    @staticmethod
    def _find(records: list[dict[str, Any]], record_id: str) -> dict[str, Any] | None:
        return next((record for record in records if record.get("record_id") == record_id), None)

    def _required_record(self, records: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
        record_id = self._required(payload, "record_id")
        record = self._find(records, record_id)
        if record is None:
            raise KeyError(f"Unknown procurement record: {record_id}")
        return record

    @staticmethod
    def _required(payload: dict[str, Any], field: str) -> str:
        value = str(payload.get(field) or "").strip()
        if not value:
            raise ValueError(f"{field} is required.")
        return value

    @staticmethod
    def _amount(value: Any) -> float:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("amount must be valid.") from exc
        if amount < 0:
            raise ValueError("amount cannot be negative.")
        return float(amount.quantize(Decimal("0.01")))

    def _read_records(self) -> list[dict[str, Any]]:
        if not self.records_path.exists():
            return []
        data = json.loads(self.records_path.read_text(encoding="utf-8"))
        return list(data.get("records") or [])

    def _write_records(self, records: list[dict[str, Any]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": PROCUREMENT_SCHEMA_VERSION, "updated_at": now_iso(), "records": records}
        temporary = self.records_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.records_path)

    def _public_record(self, record: dict[str, Any], *, include_attachment_content: bool = False) -> dict[str, Any]:
        result = json.loads(json.dumps(record, ensure_ascii=False))
        attachments = []
        for item in result.get("attachments") or []:
            meta = dict(item)
            stored_name = meta.pop("stored_name", "")
            if include_attachment_content and stored_name:
                path = self.attachments_root / stored_name
                if path.exists():
                    meta["data_url"] = f"data:{meta['mime_type']};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
            attachments.append(meta)
        result["attachments"] = attachments
        if not include_attachment_content:
            result.get("recognition", {}).pop("raw_text", None)
        return result

    def _trace(self, actor: Employee, action: str, reason: str, record: dict[str, Any], event_type: str, before: dict[str, Any]) -> None:
        before_hash = hashlib.sha256(json.dumps(before, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest() if before else ""
        after_hash = hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        audit = self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="procurement",
            action=action,
            action_type="write",
            target_type="procurement_record",
            target_id=record["record_id"],
            reason=str(reason or "采购流程操作"),
            result=str(record.get("status") or ""),
            before_hash=before_hash,
            after_hash=after_hash,
            metadata={"purchase_type": record.get("purchase_type"), "owner_emp_id": record.get("owner_emp_id")},
        )
        event = OMSEvent(
            event_type=event_type,
            source_module="procurement",
            subject=record["record_id"],
            action=action,
            emp_id=actor.emp,
            actor_name=actor.name,
            correlation_id=audit["audit_id"],
            payload={"record_id": record["record_id"], "status": record.get("status"), "purchase_type": record.get("purchase_type")},
        )
        dispatched = self.event_bus.publish(event)
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(dispatched["event"], ensure_ascii=False, sort_keys=True) + "\n")
