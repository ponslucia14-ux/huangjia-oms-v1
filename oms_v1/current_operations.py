from __future__ import annotations

import hashlib
import json
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


CURRENT_OPERATIONS_SCHEMA_VERSION = "oms.v1.current_operations"
ROOM_STATUSES = {"AVAILABLE", "RESERVED", "OCCUPIED", "CLEANING", "MAINTENANCE", "DISABLED"}
ACTIVE_STAY_STATUSES = {"CHECKED_IN", "IN_STAY", "EXTENDED"}


class CurrentOperationsService:
    """Persist authorized OMS Current facts without importing or overwriting Excel data."""

    def __init__(
        self,
        live_root: str | Path,
        *,
        master_data: OMSMasterData | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
    ):
        self.live_root = Path(live_root)
        self.current_root = self.live_root / "domain_current"
        self.event_path = self.live_root / "events" / "current_operations.jsonl"
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine(audit_root=self.live_root / "audit_center")
        self.event_bus = event_bus or EventBus()
        self._lock = threading.RLock()

    def record_finance_current(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, allowed_emp_ids={"EMP004"}, allowed_roles={"ROLE_CASHIER"})
        reason = self._reason(payload)
        effective_date = self._required(payload, "effective_date")
        amounts = {
            key: self._amount(payload, key)
            for key in ("income", "expense", "receivable", "payable", "cash_balance")
        }
        record = self._base_record("finance", actor, reason, effective_date)
        record.update(amounts)
        record.update({"status": "PENDING_REVIEW", "reviewer_emp_id": "EMP003", "reviewed_at": ""})
        self._append_version("finance", record)
        self._audit_event(actor, "finance.current.record", reason, record, "finance.current.recorded")
        return record

    def review_finance_current(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, allowed_emp_ids={"EMP003"}, allowed_roles={"ROLE_ACCOUNTANT"})
        reason = self._reason(payload)
        record_id = self._required(payload, "record_id")
        approved = payload.get("approved") is True
        with self._lock:
            ledger = self._read_ledger("finance")
            source = next((item for item in ledger["versions"] if item.get("record_id") == record_id), None)
            if source is None:
                raise KeyError(f"Unknown finance Current record: {record_id}")
            if source.get("status") != "PENDING_REVIEW":
                raise ValueError("Finance Current record is not pending review.")
            reviewed = dict(source)
            reviewed.update(
                {
                    "record_id": new_id("finance_current"),
                    "previous_record_id": source["record_id"],
                    "version": len(ledger["versions"]) + 1,
                    "status": "CURRENT" if approved else "REJECTED",
                    "reviewer_emp_id": actor.emp,
                    "reviewer_user_id": actor.user_id,
                    "reviewed_at": now_iso(),
                    "reason": reason,
                }
            )
            ledger["versions"].append(reviewed)
            if approved:
                ledger["active"] = reviewed
            self._write_ledger("finance", ledger)
        event_type = "finance.current.published" if approved else "finance.current.rejected"
        self._audit_event(actor, "finance.current.review", reason, reviewed, event_type)
        return reviewed

    def publish_room_current(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, allowed_emp_ids={"EMP008"}, allowed_roles={"ROLE_STORE_MANAGER"})
        reason = self._reason(payload)
        effective_time = self._required(payload, "effective_time")
        rooms = payload.get("rooms")
        if not isinstance(rooms, list) or len(rooms) != 42:
            raise ValueError("Room Current requires exactly 42 rooms.")
        normalized: list[dict[str, Any]] = []
        room_numbers: set[str] = set()
        for item in rooms:
            if not isinstance(item, dict):
                raise ValueError("Each room must be an object.")
            room_number = self._required(item, "room_number")
            status = self._required(item, "status").upper()
            if status not in ROOM_STATUSES:
                raise ValueError(f"Invalid room status: {status}")
            if room_number in room_numbers:
                raise ValueError(f"Duplicate room number: {room_number}")
            room_numbers.add(room_number)
            normalized.append(
                {
                    "room_number": room_number,
                    "status": status,
                    "customer_id": str(item.get("customer_id") or "").strip(),
                    "customer_name": str(item.get("customer_name") or "").strip(),
                    "exception": str(item.get("exception") or "").strip(),
                }
            )
        record = self._base_record("room", actor, reason, effective_time)
        record.update({"status": "CURRENT", "room_count": 42, "rooms": normalized})
        self._append_version("room", record, activate=True)
        self._audit_event(actor, "room.current.publish", reason, record, "room.current.published")
        return record

    def publish_actual_stay(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, allowed_emp_ids={"EMP008"}, allowed_roles={"ROLE_STORE_MANAGER"})
        reason = self._reason(payload)
        effective_time = self._required(payload, "effective_time")
        stays = payload.get("stays")
        if not isinstance(stays, list):
            raise ValueError("Actual Stay requires a stays list.")
        normalized: list[dict[str, Any]] = []
        stay_ids: set[str] = set()
        occupied_rooms: set[str] = set()
        for item in stays:
            if not isinstance(item, dict):
                raise ValueError("Each stay must be an object.")
            stay_id = self._required(item, "stay_id")
            customer_name = self._required(item, "customer_name")
            room_number = self._required(item, "room_number")
            checkin_time = self._required(item, "checkin_time")
            status = self._required(item, "status").upper()
            if status not in ACTIVE_STAY_STATUSES:
                raise ValueError(f"Invalid active stay status: {status}")
            if stay_id in stay_ids:
                raise ValueError(f"Duplicate stay_id: {stay_id}")
            if room_number in occupied_rooms:
                raise ValueError(f"Room has multiple active stays: {room_number}")
            stay_ids.add(stay_id)
            occupied_rooms.add(room_number)
            normalized.append(
                {
                    "stay_id": stay_id,
                    "customer_id": str(item.get("customer_id") or "").strip(),
                    "customer_name": customer_name,
                    "room_number": room_number,
                    "checkin_time": checkin_time,
                    "expected_checkout_time": str(item.get("expected_checkout_time") or "").strip(),
                    "status": status,
                }
            )
        self._assert_stays_match_room_current(normalized)
        record = self._base_record("actual_stay", actor, reason, effective_time)
        record.update(
            {
                "status": "CURRENT",
                "resident_count": len(normalized),
                "stays": normalized,
                "service_verification_status": "PENDING",
                "service_verifier_emp_id": "EMP009",
            }
        )
        self._append_version("actual_stay", record, activate=True)
        self._audit_event(actor, "stay.actual.publish", reason, record, "stay.actual.published")
        return record

    def verify_actual_stay(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, allowed_emp_ids={"EMP009"}, allowed_roles={"ROLE_BUTLER"})
        reason = self._reason(payload)
        record_id = self._required(payload, "record_id")
        with self._lock:
            ledger = self._read_ledger("actual_stay")
            active = ledger.get("active") or {}
            if active.get("record_id") != record_id:
                raise ValueError("Only the active Actual Stay Current can be verified.")
            verified = dict(active)
            verified.update(
                {
                    "record_id": new_id("actual_stay_current"),
                    "previous_record_id": active["record_id"],
                    "version": len(ledger["versions"]) + 1,
                    "service_verification_status": "VERIFIED",
                    "service_verifier_emp_id": actor.emp,
                    "service_verifier_user_id": actor.user_id,
                    "service_verified_at": now_iso(),
                    "reason": reason,
                }
            )
            ledger["versions"].append(verified)
            ledger["active"] = verified
            self._write_ledger("actual_stay", ledger)
        self._audit_event(actor, "stay.actual.verify", reason, verified, "stay.actual.verified")
        return verified

    def check_in(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, allowed_emp_ids={"EMP008"}, allowed_roles={"ROLE_STORE_MANAGER"})
        reason = self._reason(payload)
        stay_id = self._required(payload, "stay_id")
        customer_name = self._required(payload, "customer_name")
        room_number = self._required(payload, "room_number")
        checkin_time = self._required(payload, "checkin_time")
        with self._lock:
            room_ledger = self._read_ledger("room")
            stay_ledger = self._read_ledger("actual_stay")
            room_active = room_ledger.get("active") or {}
            rooms = [dict(item) for item in room_active.get("rooms") or []]
            room = next((item for item in rooms if str(item.get("room_number")) == room_number), None)
            if room is None:
                raise ValueError("Room Current must be initialized before check-in.")
            if room.get("status") not in {"AVAILABLE", "RESERVED"}:
                raise ValueError("The selected room is not available for check-in.")
            stays = [dict(item) for item in (stay_ledger.get("active") or {}).get("stays") or []]
            if any(item.get("stay_id") == stay_id for item in stays):
                raise ValueError("Duplicate active stay id.")
            if any(item.get("room_number") == room_number for item in stays):
                raise ValueError("The selected room already has an active stay.")
            stays.append(
                {
                    "stay_id": stay_id,
                    "customer_id": str(payload.get("customer_id") or "").strip(),
                    "customer_name": customer_name,
                    "room_number": room_number,
                    "checkin_time": checkin_time,
                    "expected_checkout_time": str(payload.get("expected_checkout_time") or "").strip(),
                    "status": "IN_STAY",
                }
            )
            room.update({"status": "OCCUPIED", "customer_name": customer_name, "customer_id": str(payload.get("customer_id") or "").strip()})
            stay_record = self._derived_current_record("actual_stay", stay_ledger, actor, reason, checkin_time, {"resident_count": len(stays), "stays": stays, "service_verification_status": "PENDING", "service_verifier_emp_id": "EMP009"})
            room_record = self._derived_current_record("room", room_ledger, actor, reason, checkin_time, {"room_count": 42, "rooms": rooms})
            self._activate_records(("actual_stay", stay_ledger, stay_record), ("room", room_ledger, room_record))
        self._audit_event(actor, "stay.actual.check_in", reason, stay_record, "stay.actual.checked_in")
        self._audit_event(actor, "room.current.occupy", reason, room_record, "room.current.occupied")
        return {"action": "CHECK_IN", "stay_current": stay_record, "room_current": room_record}

    def check_out(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, allowed_emp_ids={"EMP008"}, allowed_roles={"ROLE_STORE_MANAGER"})
        reason = self._reason(payload)
        stay_id = self._required(payload, "stay_id")
        checkout_time = self._required(payload, "checkout_time")
        with self._lock:
            room_ledger = self._read_ledger("room")
            stay_ledger = self._read_ledger("actual_stay")
            active_stays = [dict(item) for item in (stay_ledger.get("active") or {}).get("stays") or []]
            leaving = next((item for item in active_stays if item.get("stay_id") == stay_id), None)
            if leaving is None:
                raise KeyError(f"Unknown active stay: {stay_id}")
            stays = [item for item in active_stays if item.get("stay_id") != stay_id]
            rooms = [dict(item) for item in (room_ledger.get("active") or {}).get("rooms") or []]
            room = next((item for item in rooms if item.get("room_number") == leaving.get("room_number")), None)
            if room is None:
                raise ValueError("The occupied room is missing from Room Current.")
            room.update({"status": "CLEANING", "customer_name": "", "customer_id": ""})
            stay_record = self._derived_current_record("actual_stay", stay_ledger, actor, reason, checkout_time, {"resident_count": len(stays), "stays": stays, "service_verification_status": "PENDING", "service_verifier_emp_id": "EMP009", "last_checkout": {**leaving, "checkout_time": checkout_time}})
            room_record = self._derived_current_record("room", room_ledger, actor, reason, checkout_time, {"room_count": 42, "rooms": rooms})
            self._activate_records(("actual_stay", stay_ledger, stay_record), ("room", room_ledger, room_record))
        self._audit_event(actor, "stay.actual.check_out", reason, stay_record, "stay.actual.checked_out")
        self._audit_event(actor, "room.current.release", reason, room_record, "room.current.cleaning_requested")
        return {"action": "CHECK_OUT", "stay_current": stay_record, "room_current": room_record}

    def update_room_status(self, claims: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = self._actor(claims, allowed_emp_ids={"EMP008"}, allowed_roles={"ROLE_STORE_MANAGER"})
        reason = self._reason(payload)
        room_number = self._required(payload, "room_number")
        status = self._required(payload, "status").upper()
        effective_time = self._required(payload, "effective_time")
        if status not in ROOM_STATUSES:
            raise ValueError("Invalid room status.")
        with self._lock:
            room_ledger = self._read_ledger("room")
            rooms = [dict(item) for item in (room_ledger.get("active") or {}).get("rooms") or []]
            room = next((item for item in rooms if item.get("room_number") == room_number), None)
            if room is None:
                raise ValueError("Room Current must be initialized before changing a room.")
            active_stays = (self._read_ledger("actual_stay").get("active") or {}).get("stays") or []
            stay = next((item for item in active_stays if item.get("room_number") == room_number), None)
            if status == "OCCUPIED" and stay is None:
                raise ValueError("An occupied room must be linked to an active stay.")
            if status != "OCCUPIED" and stay is not None:
                raise ValueError("An active stay must be checked out or transferred before changing the room status.")
            room.update({"status": status, "exception": str(payload.get("exception") or "").strip()})
            if status != "OCCUPIED":
                room.update({"customer_name": "", "customer_id": ""})
            record = self._derived_current_record("room", room_ledger, actor, reason, effective_time, {"room_count": 42, "rooms": rooms})
            self._activate_records(("room", room_ledger, record))
        self._audit_event(actor, "room.current.update", reason, record, "room.current.updated")
        return record

    def current_summary(self) -> dict[str, Any]:
        finance = self._read_ledger("finance")
        room = self._read_ledger("room")
        actual_stay = self._read_ledger("actual_stay")
        return {
            "schema_version": CURRENT_OPERATIONS_SCHEMA_VERSION,
            "finance": finance.get("active"),
            "finance_pending": next(
                (item for item in reversed(finance["versions"]) if item.get("status") == "PENDING_REVIEW"),
                None,
            ),
            "room": room.get("active"),
            "actual_stay": actual_stay.get("active"),
            "source": "OMS_DOMAIN_CURRENT",
            "excel_current_allowed": False,
        }

    def _actor(self, claims: dict[str, Any], *, allowed_emp_ids: set[str], allowed_roles: set[str]) -> Employee:
        user_id = str(claims.get("user_id") or "").strip()
        workspace_key = str(claims.get("workspace_key") or "").strip()
        actor = next(
            (
                employee
                for employee in self.master_data.employees()
                if user_id and user_id in {employee.user_id, employee.open_id, employee.union_id}
            ),
            None,
        )
        if actor is None:
            raise PermissionError("session_identity_not_in_master_data")
        if actor.emp not in allowed_emp_ids or actor.role_code not in allowed_roles:
            raise PermissionError(f"{actor.emp} is not authorized for this Current operation.")
        expected_workspace = {
            "EMP003": "zhangjingdong",
            "EMP004": "liujie",
            "EMP008": "june",
            "EMP009": "nana",
        }.get(actor.emp)
        if expected_workspace and workspace_key != expected_workspace:
            raise PermissionError("session_workspace_mismatch")
        return actor

    def _assert_stays_match_room_current(self, stays: list[dict[str, Any]]) -> None:
        room_current = self._read_ledger("room").get("active") or {}
        rooms = {str(item.get("room_number")): item for item in room_current.get("rooms") or []}
        if len(rooms) != 42:
            raise ValueError("Room Current must be published before Actual Stay Current.")
        for stay in stays:
            room = rooms.get(stay["room_number"])
            if not room or room.get("status") != "OCCUPIED":
                raise ValueError(f"Actual Stay room is not OCCUPIED: {stay['room_number']}")
            room_customer = str(room.get("customer_name") or "").strip()
            if room_customer and room_customer != stay["customer_name"]:
                raise ValueError(f"Room customer mismatch: {stay['room_number']}")

    def _base_record(self, domain: str, actor: Employee, reason: str, effective_time: str) -> dict[str, Any]:
        ledger = self._read_ledger(domain)
        return {
            "schema_version": CURRENT_OPERATIONS_SCHEMA_VERSION,
            "record_id": new_id(f"{domain}_current"),
            "domain": domain,
            "version": len(ledger["versions"]) + 1,
            "effective_time": effective_time,
            "created_at": now_iso(),
            "actor_emp_id": actor.emp,
            "actor_user_id": actor.user_id,
            "actor_name": actor.name,
            "reason": reason,
            "source": "OMS_OPERATION",
            "is_current": True,
        }

    def _derived_current_record(self, domain: str, ledger: dict[str, Any], actor: Employee, reason: str, effective_time: str, values: dict[str, Any]) -> dict[str, Any]:
        record = self._base_record(domain, actor, reason, effective_time)
        active = ledger.get("active") or {}
        record.update({"status": "CURRENT", "previous_record_id": active.get("record_id", "")})
        record.update(values)
        return record

    def _activate_records(self, *entries: tuple[str, dict[str, Any], dict[str, Any]]) -> None:
        for domain, ledger, record in entries:
            ledger["versions"].append(record)
            ledger["active"] = record
            self._write_ledger(domain, ledger)

    def _append_version(self, domain: str, record: dict[str, Any], *, activate: bool = False) -> None:
        with self._lock:
            ledger = self._read_ledger(domain)
            ledger["versions"].append(record)
            if activate:
                ledger["active"] = record
            self._write_ledger(domain, ledger)

    def _read_ledger(self, domain: str) -> dict[str, Any]:
        path = self.current_root / f"{domain}.json"
        if not path.exists():
            return {
                "schema_version": CURRENT_OPERATIONS_SCHEMA_VERSION,
                "domain": domain,
                "active": None,
                "versions": [],
                "physical_delete_allowed": False,
                "excel_current_allowed": False,
            }
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("versions", [])
        data.setdefault("active", None)
        return data

    def _write_ledger(self, domain: str, ledger: dict[str, Any]) -> None:
        self.current_root.mkdir(parents=True, exist_ok=True)
        target = self.current_root / f"{domain}.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)

    def _audit_event(self, actor: Employee, action: str, reason: str, record: dict[str, Any], event_type: str) -> None:
        digest = hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        audit = self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="current_operations",
            action=action,
            action_type="write",
            target_type=record["domain"],
            target_id=record["record_id"],
            reason=reason,
            result=record.get("status", "CURRENT"),
            after_hash=digest,
            metadata={"version": record["version"], "source": "OMS_OPERATION"},
        )
        event = OMSEvent(
            event_type=event_type,
            source_module="current_operations",
            subject=record["record_id"],
            action=action,
            emp_id=actor.emp,
            actor_name=actor.name,
            correlation_id=audit["audit_id"],
            payload={"domain": record["domain"], "record_id": record["record_id"], "version": record["version"]},
        )
        dispatched = self.event_bus.publish(event)
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(dispatched["event"], ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _required(payload: dict[str, Any], field: str) -> str:
        value = str(payload.get(field) or "").strip()
        if not value:
            raise ValueError(f"{field} is required.")
        return value

    def _reason(self, payload: dict[str, Any]) -> str:
        return self._required(payload, "reason")

    @staticmethod
    def _amount(payload: dict[str, Any], field: str) -> float:
        try:
            value = Decimal(str(payload.get(field, "")))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"{field} must be a valid amount.") from exc
        if value < 0:
            raise ValueError(f"{field} cannot be negative.")
        return float(value.quantize(Decimal("0.01")))
