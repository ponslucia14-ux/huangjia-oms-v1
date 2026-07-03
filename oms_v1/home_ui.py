from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .operating_center_source import IDENTITY_BINDING_ERROR
from .operational_core import OPERATING_CENTER_PEOPLE, PERSONAL_WORKSPACES
from .schemas import now_iso


ROLE_HOME_PANELS = {
    "boss": {"title": "经营总览", "empty": "暂无全局待处理事项"},
    "huanhuan": {"title": "我的客户", "empty": "暂无客户待处理事项"},
    "june": {"title": "我的经营事务", "empty": "暂无经营事务待处理事项"},
    "liujie": {"title": "我的财务", "empty": "暂无财务待处理事项"},
    "zhangjie": {"title": "我的财务复核", "empty": "暂无财务复核待处理事项"},
    "nana": {"title": "我的服务", "empty": "暂无服务待处理事项"},
    "chenchangyi": {"title": "我的产护", "empty": "暂无产护待处理事项"},
    "zhouchen": {"title": "我的料理", "empty": "暂无料理待处理事项"},
    "yaowei": {"title": "我的行政采购", "empty": "暂无行政采购待处理事项"},
    "songxue": {"title": "我的人事行政", "empty": "暂无人事行政待处理事项"},
    "yuchun": {"title": "我的食材采购", "empty": "暂无食材采购待处理事项"},
}

STATUS_LABELS = {
    "ready": "已就绪",
    "ready_with_pending_sync": "待外部同步",
    "waiting_confirmation": "待确认",
    "waiting_live_sync": "待同步",
    "blocked": "需处理",
    "attention_required": "需关注",
}


class OMSHomeUI:
    """Build the user-facing OMS home payload from operating data."""

    def __init__(self, live_root: str | Path | None = None, operating_root: str | Path | None = None):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")

    def build_home(self, operating_stream: dict[str, Any], *, user_id: str | None = None) -> dict[str, Any]:
        identity = self._resolve_identity(user_id, operating_stream)
        if identity.get("binding_status") == "error":
            return self._identity_binding_error(identity)
        workspace = self._workspace_for_identity(identity, operating_stream)
        role_panel = ROLE_HOME_PANELS.get(identity["workspace_key"], ROLE_HOME_PANELS["boss"])
        sections = {
            "my_todos": self._section("我的待办", workspace.get("my_todos", []), empty_text="暂无待办"),
            "my_tasks": self._section("我的任务", workspace.get("my_tasks", []), empty_text="暂无任务"),
            "my_approvals": self._section("我的审批", workspace.get("my_approvals", []), empty_text="暂无审批"),
            "role_home": self._section(role_panel["title"], workspace.get("all_visible_items", []), empty_text=role_panel["empty"]),
        }
        business_dashboard = self._business_dashboard(identity, workspace.get("all_visible_items", []))
        sync_status = self._sync_status_from_operating_stream(operating_stream)
        decision_assist = self._decision_assist(operating_stream, identity["workspace_key"])
        return {
            "schema_version": "oms.v1.home",
            "home_type": "user_centric_operating_interface",
            "entry": "personal_workspace",
            "opened_at": now_iso(),
            "current_user": {
                "user_id": identity["user_id"],
                "workspace_key": identity["workspace_key"],
                "name": identity["name"],
                "role": identity["role"],
                "home_title": identity["title"],
            },
            "home_title": identity["title"],
            "business_dashboard": business_dashboard,
            "sections": sections,
            "sync_status": sync_status,
            "decision_assist": decision_assist,
            "bottom_tabs": self._bottom_tabs(identity["workspace_key"]),
            "empty_state": self._empty_state(sections),
        }

    def build_home_from_saved_state(self, *, user_id: str | None = None) -> dict[str, Any]:
        identity = self._resolve_identity(user_id, None)
        if identity.get("binding_status") == "error":
            return self._identity_binding_error(identity)
        workspace = self._workspace_from_saved_items(identity)
        role_panel = ROLE_HOME_PANELS.get(identity["workspace_key"], ROLE_HOME_PANELS["boss"])
        sections = {
            "my_todos": self._section("我的待办", workspace["my_todos"], empty_text="暂无待办"),
            "my_tasks": self._section("我的任务", workspace["my_tasks"], empty_text="暂无任务"),
            "my_approvals": self._section("我的审批", workspace["my_approvals"], empty_text="暂无审批"),
            "role_home": self._section(role_panel["title"], workspace["all_visible_items"], empty_text=role_panel["empty"]),
        }
        business_dashboard = self._business_dashboard(identity, workspace["all_visible_items"])
        return {
            "schema_version": "oms.v1.home",
            "home_type": "user_centric_operating_interface",
            "entry": "personal_workspace",
            "opened_at": now_iso(),
            "current_user": {
                "user_id": identity["user_id"],
                "workspace_key": identity["workspace_key"],
                "name": identity["name"],
                "role": identity["role"],
                "home_title": identity["title"],
            },
            "home_title": identity["title"],
            "business_dashboard": business_dashboard,
            "sections": sections,
            "sync_status": self._sync_status_from_pending_outbox(),
            "decision_assist": self._decision_assist_from_saved_items(workspace["all_visible_items"]),
            "bottom_tabs": self._bottom_tabs(identity["workspace_key"]),
            "empty_state": self._empty_state(sections),
        }

    def _resolve_identity(self, user_id: str | None, operating_stream: dict[str, Any] | None) -> dict[str, str]:
        if operating_stream:
            current_user = (operating_stream.get("personal_workspace_system") or {}).get("current_user") or {}
            if user_id is None and current_user:
                workspace_key = str(current_user.get("workspace_key") or "")
                if current_user.get("binding_status") == "error" or workspace_key not in PERSONAL_WORKSPACES:
                    return self._binding_error_identity(
                        str(current_user.get("user_id") or ""),
                        str(current_user.get("identity_source") or "operating_stream"),
                    )
                canonical = PERSONAL_WORKSPACES[workspace_key]
                return {
                    "user_id": str(current_user.get("user_id") or ""),
                    "workspace_key": workspace_key,
                    "role": canonical["role"],
                    "name": canonical["name"],
                    "title": canonical["title"],
                    "identity_source": str(current_user.get("identity_source") or "operating_stream"),
                }
        raw_user_id = (user_id or os.getenv("OMS_CURRENT_USER_ID") or os.getenv("OMS_USER_ID") or "").strip()
        normalized = raw_user_id.lower()
        key, identity_source = self._workspace_key_from_user_id(raw_user_id, normalized)
        if key not in PERSONAL_WORKSPACES:
            return self._binding_error_identity(raw_user_id, identity_source)
        workspace = PERSONAL_WORKSPACES[key]
        return {
            "user_id": raw_user_id,
            "workspace_key": key,
            "role": workspace["role"],
            "name": workspace["name"],
            "title": workspace["title"],
            "identity_source": identity_source,
        }

    def _workspace_key_from_user_id(self, raw_user_id: str, normalized: str) -> tuple[str, str]:
        for key, person in OPERATING_CENTER_PEOPLE.items():
            feishu_user_id = os.getenv(person["feishu_env"], "").strip()
            if feishu_user_id and raw_user_id == feishu_user_id:
                return key, "feishu_user_id"
        if normalized in PERSONAL_WORKSPACES:
            return normalized, "workspace_key"
        return "", "identity_binding_required"

    def _binding_error_identity(self, user_id: str, identity_source: str) -> dict[str, str]:
        return {
            "user_id": user_id,
            "workspace_key": "",
            "role": "",
            "name": "",
            "title": IDENTITY_BINDING_ERROR["title"],
            "identity_source": identity_source,
            "binding_status": "error",
            "error_type": IDENTITY_BINDING_ERROR["error_type"],
        }

    def _identity_binding_error(self, identity: dict[str, str]) -> dict[str, Any]:
        error = dict(IDENTITY_BINDING_ERROR)
        error["user_id_present"] = bool(identity.get("user_id"))
        error["identity_source"] = identity.get("identity_source", "")
        return {
            "schema_version": "oms.v1.home",
            "home_type": "identity_binding_error",
            "entry": "login_required",
            "opened_at": now_iso(),
            "current_user": None,
            "home_title": error["title"],
            "error": error,
            "business_dashboard": None,
            "sections": {},
            "sync_status": {
                "title": "identity_binding",
                "state": "blocked",
                "pending_count": 0,
                "failed_count": 1,
                "message": error["message"],
            },
            "decision_assist": {"title": "identity_binding", "messages": [error["message"]]},
            "bottom_tabs": [],
            "empty_state": "",
        }
    def _workspace_for_identity(self, identity: dict[str, str], operating_stream: dict[str, Any]) -> dict[str, Any]:
        workspaces = (operating_stream.get("personal_workspace_system") or {}).get("workspaces") or {}
        return workspaces.get(identity["workspace_key"]) or {
            "my_todos": [],
            "my_tasks": [],
            "my_approvals": [],
            "all_visible_items": [],
        }

    def _workspace_from_saved_items(self, identity: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
        items = self._read_saved_work_items()
        role = identity["role"]
        title = identity["title"]
        visible = (
            items
            if identity["workspace_key"] == "boss"
            else [item for item in items if item.get("role") == role or item.get("workspace") == title]
        )
        approvals = [item for item in visible if item.get("confirmation_required") or item.get("status") == "waiting_confirmation"]
        todos = [item for item in visible if item.get("status") != "ready"]
        tasks = [item for item in visible if item.get("status") == "ready"]
        return {
            "my_todos": todos,
            "my_tasks": tasks,
            "my_approvals": approvals,
            "all_visible_items": visible,
        }

    def _read_saved_work_items(self) -> list[dict[str, Any]]:
        paths = [
            self.operating_root / "daily_work_items.jsonl",
            self.operating_root / "excel_work_items.jsonl",
            self.operating_root / "finance_work_items.jsonl",
        ]
        items: list[dict[str, Any]] = []
        for path in paths:
            items.extend(self._read_jsonl(path))
        return items

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        items: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                items.append(data)
        return items

    def _is_truth_verified_item(self, item: dict[str, Any]) -> bool:
        evidence = item.get("source_evidence")
        if not evidence and isinstance(item.get("excel_record"), dict):
            evidence = item["excel_record"].get("source_evidence")
        if not evidence and isinstance(item.get("finance_record"), dict):
            evidence = item["finance_record"].get("source_evidence")
        return self._is_valid_source_evidence(evidence)

    def _is_truth_verified_event(self, event: dict[str, Any]) -> bool:
        return self._is_valid_source_evidence(event.get("source_evidence"))

    def _is_valid_source_evidence(self, evidence: Any) -> bool:
        if not isinstance(evidence, dict):
            return False
        return bool(
            evidence.get("truth_source")
            and evidence.get("source_type")
            and evidence.get("source_file")
            and evidence.get("record_id")
            and evidence.get("row_number") not in {"", None}
        )

    def _business_dashboard(self, identity: dict[str, str], visible_items: list[dict[str, Any]]) -> dict[str, Any]:
        saved_items = self._read_saved_work_items()
        all_items = list(saved_items)
        verified_items = [item for item in saved_items if self._is_truth_verified_item(item)]
        uncalibrated_items = [item for item in saved_items if not self._is_truth_verified_item(item)]
        finance_events_all = self._read_jsonl(self.live_root / "finance" / "financial_events.jsonl")
        finance_events = list(finance_events_all)
        verified_finance_events = [event for event in finance_events_all if self._is_truth_verified_event(event)]
        uncalibrated_finance_events = [event for event in finance_events_all if not self._is_truth_verified_event(event)]
        excel_items = [item for item in all_items if item.get("excel_record")]
        finance_items = [item for item in all_items if item.get("finance_record")]
        resident_items = [item for item in excel_items if item["excel_record"].get("source_type") == "resident"]
        room_items = [item for item in excel_items if item["excel_record"].get("source_type") == "room_status"]
        contract_items = [item for item in excel_items if item["excel_record"].get("source_type") == "contracts"]
        service_items = [
            item
            for item in resident_items
            if item["excel_record"].get("assignment", {}).get("workspace_key") in {"nana", "chenchangyi"}
            or item.get("workspace") in {"管家工作台", "产护工作台"}
        ]
        today_tokens = self._today_tokens()
        today_checkins = [
            item
            for item in resident_items
            if self._contains_today(item["excel_record"].get("raw_row", {}).get("入住时间"), today_tokens)
            or self._contains_today(item["excel_record"].get("raw_row", {}).get("入住日期"), today_tokens)
        ]
        today_checkouts = [
            item
            for item in resident_items
            if self._contains_today(item["excel_record"].get("raw_row", {}).get("出馆时间"), today_tokens)
            or self._contains_today(item["excel_record"].get("raw_row", {}).get("出馆日期"), today_tokens)
        ]
        today_finance_events = [
            event for event in finance_events if self._contains_today(event.get("occurred_at"), today_tokens)
        ]
        today_collection = sum(self._number(event.get("income_amount") or event.get("amount")) for event in today_finance_events)
        visible_items_all = list(visible_items)
        pending_visible = [item for item in visible_items_all if item.get("status") != "ready"]
        risk_items = [
            item
            for item in all_items
            if item.get("status") in {"attention_required", "blocked", "waiting_confirmation"}
            or item.get("confirmation_required")
        ]
        role_focus = self._role_focus(identity["workspace_key"], resident_items, room_items, contract_items, finance_items, service_items)
        business_schema = self._business_schema(
            resident_items=resident_items,
            room_items=room_items,
            contract_items=contract_items,
            finance_items=finance_items,
            service_items=service_items,
            finance_events=finance_events,
            today_checkins=today_checkins,
            today_checkouts=today_checkouts,
            today_collection=today_collection,
            risk_items=risk_items,
            pending_visible=pending_visible,
        )
        source_evidence_verified_data = self._source_evidence_verified_data(
            resident_items=resident_items,
            room_items=room_items,
            contract_items=contract_items,
            finance_items=finance_items,
            service_items=service_items,
            finance_events=finance_events,
            visible_items=visible_items_all,
        )
        return {
            "title": "今日经营",
            "source": "real_business_source_of_truth",
            "schema_source": "business_schema",
            "data_truth_alignment": {
                "policy": "source_evidence_required_soft_label",
                "data_source": "source_evidence_available_data",
                "display_policy": "always_render_with_confidence_label",
                "verified_work_items": len(verified_items),
                "uncalibrated_work_items": len(uncalibrated_items),
                "visible_work_items": len(all_items),
                "verified_financial_events": len(verified_finance_events),
                "uncalibrated_financial_events": len(uncalibrated_finance_events),
                "visible_financial_events": len(finance_events),
                "status": "aligned" if not uncalibrated_items and not uncalibrated_finance_events else "partial_alignment",
            },
            "source_evidence_available_data": source_evidence_verified_data,
            "source_evidence_verified_data": source_evidence_verified_data,
            "business_schema": business_schema,
            "metrics": {
                "resident_count": business_schema["resident_flow_schema"]["resident_count"],
                "today_checkins": business_schema["resident_flow_schema"]["upcoming_checkins"],
                "today_checkouts": business_schema["resident_flow_schema"]["checkouts"],
                "today_collection": business_schema["finance_schema"]["collected"],
                "today_todos": len(pending_visible),
                "risk_alerts": len(risk_items),
                "sales_contracts": business_schema["sales_schema"]["contracts"],
                "service_progress": business_schema["service_schema"]["in_service"],
                "room_status_records": business_schema["resident_flow_schema"]["room_status_records"],
                "finance_records": business_schema["finance_schema"]["event_records"],
            },
            "role_focus": role_focus,
            "risk提示": self._risk_messages(risk_items),
        }

    def _business_schema(
        self,
        *,
        resident_items: list[dict[str, Any]],
        room_items: list[dict[str, Any]],
        contract_items: list[dict[str, Any]],
        finance_items: list[dict[str, Any]],
        service_items: list[dict[str, Any]],
        finance_events: list[dict[str, Any]],
        today_checkins: list[dict[str, Any]],
        today_checkouts: list[dict[str, Any]],
        today_collection: float,
        risk_items: list[dict[str, Any]],
        pending_visible: list[dict[str, Any]],
    ) -> dict[str, Any]:
        income = sum(self._number(event.get("income_amount") or event.get("amount")) for event in finance_events)
        expenses = sum(self._number(event.get("expense_amount") or event.get("cost_amount")) for event in finance_events)
        receivable = sum(1 for item in finance_items if item.get("status") != "ready")
        completed_service = sum(1 for item in service_items if item.get("status") == "ready")
        service_exceptions = sum(
            1 for item in service_items if item.get("status") in {"attention_required", "blocked", "waiting_confirmation"}
        )
        leads = len(contract_items)
        lost = sum(1 for item in contract_items if "流失" in str(item.get("daily_process") or ""))
        contracts = len(contract_items)
        conversion = round(contracts / leads, 4) if leads else 0
        return {
            "schema_version": "oms.business.v1",
            "resident_flow_schema": {
                "resident_count": len(resident_items),
                "active_stays": len(resident_items),
                "upcoming_checkins": len(today_checkins),
                "checkouts": len(today_checkouts),
                "room_status_records": len(room_items),
            },
            "finance_schema": {
                "income": round(income, 2),
                "receivable": receivable,
                "collected": round(today_collection, 2),
                "expenses": round(expenses, 2),
                "profit": round(income - expenses, 2),
                "event_records": len(finance_items),
            },
            "sales_schema": {
                "leads": leads,
                "contracts": contracts,
                "conversion": conversion,
                "lost": lost,
            },
            "service_schema": {
                "checkin_preparation": len(today_checkins),
                "in_service": len(service_items),
                "exceptions": service_exceptions,
                "completed": completed_service,
            },
            "hr_schema": {
                "on_duty_staff": 0,
                "scheduled_shifts": 0,
                "performance": 0,
                "attendance_rate": 0,
            },
            "semantic_status": {
                "pending_work_items": len(pending_visible),
                "risk_items": len(risk_items),
                "source": "verified_source_evidence",
            },
        }

    def _source_evidence_verified_data(
        self,
        *,
        resident_items: list[dict[str, Any]],
        room_items: list[dict[str, Any]],
        contract_items: list[dict[str, Any]],
        finance_items: list[dict[str, Any]],
        service_items: list[dict[str, Any]],
        finance_events: list[dict[str, Any]],
        visible_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "policy": "source_evidence_available_data",
            "flow": "Excel / 财务 / 销售数据 -> OMS ingestion -> business_schema -> UI renderer -> personal_workspace",
            "resident_data": [self._verified_item_record(item, "resident") for item in resident_items],
            "room_status_data": [self._verified_item_record(item, "room_status") for item in room_items],
            "sales_contract_data": [self._verified_item_record(item, "contracts") for item in contract_items],
            "finance_data": [self._verified_item_record(item, "finance") for item in finance_items],
            "service_data": [self._verified_item_record(item, "service") for item in service_items],
            "financial_events": [self._verified_event_record(event) for event in finance_events],
            "current_user_visible_data": [self._verified_item_record(item, "current_user") for item in visible_items],
        }

    def _verified_item_record(self, item: dict[str, Any], business_domain: str) -> dict[str, Any]:
        source_record = item.get("excel_record") if isinstance(item.get("excel_record"), dict) else item.get("finance_record")
        source_record = source_record if isinstance(source_record, dict) else {}
        evidence = self._source_evidence_from_item(item)
        raw_row = source_record.get("raw_row") if isinstance(source_record.get("raw_row"), dict) else {}
        normalized = source_record.get("normalized") if isinstance(source_record.get("normalized"), dict) else {}
        return {
            "business_domain": business_domain,
            "data_confidence": "source_verified" if evidence else "uncalibrated_warning",
            "work_item_id": item.get("work_item_id") or item.get("action_id") or "",
            "title": item.get("daily_process") or item.get("workspace") or "",
            "status": item.get("status") or "",
            "role": item.get("role") or "",
            "workspace": item.get("workspace") or "",
            "source_evidence": evidence,
            "raw_row": raw_row,
            "normalized": normalized,
            "display_fields": self._display_fields(raw_row or normalized),
        }

    def _verified_event_record(self, event: dict[str, Any]) -> dict[str, Any]:
        evidence = event.get("source_evidence") if isinstance(event.get("source_evidence"), dict) else {}
        return {
            "business_domain": "financial_event",
            "data_confidence": "source_verified" if evidence else "uncalibrated_warning",
            "event_id": event.get("event_id") or event.get("record_id") or "",
            "title": event.get("event_type") or event.get("daily_process") or "financial_event",
            "status": event.get("truth_status") or "source_verified",
            "source_evidence": evidence,
            "amount": event.get("income_amount") or event.get("expense_amount") or event.get("amount") or "",
            "occurred_at": event.get("occurred_at") or "",
            "display_fields": self._display_fields(event),
        }

    def _source_evidence_from_item(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence")
        if not evidence and isinstance(item.get("excel_record"), dict):
            evidence = item["excel_record"].get("source_evidence")
        if not evidence and isinstance(item.get("finance_record"), dict):
            evidence = item["finance_record"].get("source_evidence")
        return evidence if isinstance(evidence, dict) else {}

    def _display_fields(self, row: dict[str, Any], limit: int = 6) -> list[dict[str, str]]:
        fields: list[dict[str, str]] = []
        for key, value in row.items():
            if key.startswith("__") or isinstance(value, (dict, list, tuple, set)) or value in {"", None}:
                continue
            fields.append({"label": str(key), "value": str(value)})
            if len(fields) >= limit:
                break
        return fields

    def _role_focus(
        self,
        workspace_key: str,
        resident_items: list[dict[str, Any]],
        room_items: list[dict[str, Any]],
        contract_items: list[dict[str, Any]],
        finance_items: list[dict[str, Any]],
        service_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if workspace_key == "june":
            return {"房态": len(room_items), "在住": len(resident_items), "排房": len(room_items)}
        if workspace_key == "liujie":
            return {"财务": len(finance_items), "收款/对账": len(finance_items)}
        if workspace_key == "huanhuan":
            return {"签约": len(contract_items), "客户": len(contract_items), "销售结算": len(finance_items)}
        if workspace_key in {"nana", "chenchangyi"}:
            return {"服务": len(service_items), "入住": len(resident_items), "产护": len(service_items)}
        if workspace_key == "boss":
            return {"经营总览": len(resident_items) + len(contract_items) + len(finance_items), "风险": len(finance_items)}
        return {}

    def _risk_messages(self, risk_items: list[dict[str, Any]]) -> list[str]:
        if not risk_items:
            return ["当前没有新的风险提示。"]
        return [
            f"{len(risk_items)} 个事项需要确认或外部同步，已保留在 OMS/pending_outbox。",
            "飞书 user_id 未完全解析时，数据不丢失但需要完成身份绑定后分发。",
        ]

    def _today_tokens(self) -> set[str]:
        now = now_iso()
        date = now.split("T", 1)[0]
        month = int(date.split("-")[1])
        day = int(date.split("-")[2])
        return {date, f"{month}.{day}", f"{month}月{day}日", f"{month}/{day}"}

    def _contains_today(self, value: Any, today_tokens: set[str]) -> bool:
        text = str(value or "").strip()
        return bool(text and any(token in text for token in today_tokens))

    def _number(self, value: Any) -> float:
        if value in {"", None, "无"}:
            return 0.0
        try:
            return float(str(value).replace(",", "").strip())
        except ValueError:
            return 0.0

    def _section(self, title: str, items: list[dict[str, Any]], *, empty_text: str) -> dict[str, Any]:
        return {
            "title": title,
            "count": len(items),
            "items": [self._home_item(item) for item in items],
            "empty_text": empty_text if not items else "",
        }

    def _home_item(self, item: dict[str, Any]) -> dict[str, Any]:
        status = item.get("status", "")
        evidence = self._source_evidence_from_item(item)
        source_record = item.get("excel_record") if isinstance(item.get("excel_record"), dict) else item.get("finance_record")
        source_record = source_record if isinstance(source_record, dict) else {}
        raw_row = source_record.get("raw_row") if isinstance(source_record.get("raw_row"), dict) else {}
        normalized = source_record.get("normalized") if isinstance(source_record.get("normalized"), dict) else {}
        return {
            "id": item.get("work_item_id") or item.get("action_id") or "",
            "title": item.get("daily_process") or item.get("workspace") or "待处理事项",
            "action": item.get("next_operator_action") or "请在 OMS 中确认处理结果。",
            "status": STATUS_LABELS.get(status, status or "待处理"),
            "needs_confirmation": bool(item.get("confirmation_required")),
            "data_confidence": "source_verified" if evidence else "uncalibrated_warning",
            "source_evidence": evidence,
            "source_summary": self._source_summary(evidence),
            "display_fields": self._display_fields(raw_row or normalized),
        }

    def _source_summary(self, evidence: dict[str, Any]) -> str:
        if not evidence:
            return ""
        source_file = Path(str(evidence.get("source_file") or "")).name
        row_number = evidence.get("row_number")
        record_id = evidence.get("record_id") or ""
        return f"{evidence.get('truth_source')} / {evidence.get('source_type')} / {source_file} / row {row_number} / {record_id}"

    def _sync_status_from_operating_stream(self, operating_stream: dict[str, Any]) -> dict[str, Any]:
        readiness = operating_stream.get("operational_readiness") or {}
        pending = int(readiness.get("pending_external_sync_count") or 0)
        failed = int(readiness.get("failed_sync_count") or 0)
        return {
            "title": "外部同步",
            "state": "待同步" if pending else "正常",
            "pending_count": pending,
            "failed_count": failed,
            "message": "外部系统暂未完全同步，事项已进入待同步队列。" if pending else "外部同步暂无待处理事项。",
        }

    def _sync_status_from_pending_outbox(self) -> dict[str, Any]:
        outbox = self.live_root / "pending_outbox"
        pending_count = 0
        queues: list[dict[str, Any]] = []
        if outbox.exists():
            for path in sorted(outbox.glob("*.jsonl")):
                line_count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
                pending_count += line_count
                queues.append({"name": path.stem, "count": line_count})
        return {
            "title": "外部同步",
            "state": "待同步" if pending_count else "正常",
            "pending_count": pending_count,
            "failed_count": 0,
            "queues": queues,
            "message": "外部系统暂未完全同步，事项已进入待同步队列。" if pending_count else "外部同步暂无待处理事项。",
        }

    def _decision_assist(self, operating_stream: dict[str, Any], workspace_key: str) -> dict[str, Any]:
        support_status = operating_stream.get("support_layer_status") or {}
        readiness = operating_stream.get("operational_readiness") or {}
        messages: list[str] = []
        if support_status.get("active"):
            messages.append("协同事项已自动分发，请优先处理自己的待办。")
        if readiness.get("pending_external_sync_count"):
            messages.append("有事项正在等待外部同步，不影响继续处理。")
        if workspace_key == "boss":
            messages.append("请关注需确认事项、待同步事项和跨岗位协同。")
        return {"title": "系统提醒", "messages": messages or ["当前首页暂无系统提醒。"]}

    def _decision_assist_from_saved_items(self, visible_items: list[dict[str, Any]]) -> dict[str, Any]:
        waiting = sum(1 for item in visible_items if item.get("confirmation_required"))
        pending = sum(1 for item in visible_items if item.get("status") in {"ready_with_pending_sync", "waiting_live_sync"})
        messages: list[str] = []
        if waiting:
            messages.append(f"有 {waiting} 个事项需要确认。")
        if pending:
            messages.append(f"有 {pending} 个事项等待外部同步，不影响继续处理。")
        return {"title": "系统提醒", "messages": messages or ["当前首页暂无系统提醒。"]}

    def _bottom_tabs(self, workspace_key: str) -> list[dict[str, Any]]:
        role_panel = ROLE_HOME_PANELS.get(workspace_key, ROLE_HOME_PANELS["boss"])
        return [
            {"key": "home", "label": "首页", "active": True},
            {"key": "todos", "label": "待办", "active": False},
            {"key": "approvals", "label": "审批", "active": False},
            {"key": "role_home", "label": role_panel["title"].replace("我的", ""), "active": False},
        ]

    def _empty_state(self, sections: dict[str, dict[str, Any]]) -> str:
        if any(section["count"] for section in sections.values()):
            return ""
        return "当前没有新的待办、任务或审批。"
