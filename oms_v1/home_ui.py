from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .business_state_writeback import BusinessStateWritebackLayer
from .core_fusion import OWNER_MASTER_CONTROL_ENTRY_TYPE, CoreFusionLayer
from .lifecycle_engine import LifecycleEngine
from .live_connector import DEFAULT_LIVE_ROOT
from .operating_center_source import IDENTITY_BINDING_ERROR, workspace_key_for_feishu_identity
from .operational_core import OPERATING_CENTER_PEOPLE, PERSONAL_WORKSPACES
from .production_data_adapter import (
    CAREGIVER_ADAPTER_ID,
    FINANCE_ADAPTER_ID,
    PRODUCTION_ADAPTER_SCHEMA_VERSION,
    ROOM_ADAPTER_ID,
    SALES_ADAPTER_ID,
    STAY_ADAPTER_ID,
    ProductionDataAdapter,
)
from .schemas import now_iso
from .truth_source import TruthSourceStore

HOME_UI_ITEM_LIMIT = 80
HOME_UI_SOURCE_LIMIT = 500


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
        self.truth_store = TruthSourceStore(self.live_root, self.operating_root)
        self.business_state = BusinessStateWritebackLayer(self.live_root, self.operating_root)
        self.lifecycle_engine = LifecycleEngine(self.live_root, self.operating_root)
        self._core_fusion_state: dict[str, Any] | None = None

    def build_home(self, operating_stream: dict[str, Any], *, user_id: str | None = None) -> dict[str, Any]:
        identity = self._resolve_identity(user_id, operating_stream)
        if identity.get("binding_status") == "error":
            return self._identity_binding_error(identity)
        workspace = self._workspace_from_core_fusion(identity)
        hr_items = workspace["all_visible_items"]
        role_panel = ROLE_HOME_PANELS.get(identity["workspace_key"], ROLE_HOME_PANELS["boss"])
        sections = {
            "my_todos": self._section("我的待办", workspace.get("my_todos", []), empty_text="暂无待办"),
            "my_tasks": self._section("我的任务", workspace.get("my_tasks", []), empty_text="暂无任务"),
            "my_approvals": self._section("我的审批", workspace.get("my_approvals", []), empty_text="暂无审批"),
            "role_home": self._section(role_panel["title"], workspace.get("all_visible_items", []), empty_text=role_panel["empty"]),
            "event_execution_flow": self._section("事件执行流", hr_items, empty_text="暂无事件执行任务"),
        }
        business_dashboard = self._business_dashboard(identity, workspace.get("all_visible_items", []))
        sync_status = self._sync_status_from_operating_stream(operating_stream)
        decision_assist = self._decision_assist(operating_stream, identity["workspace_key"])
        master_control = self._boss_master_control(identity, workspace, business_dashboard)
        return {
            "schema_version": "oms.v1.home",
            "home_type": self._home_type(identity),
            "entry": self._home_entry(identity),
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
            "core_fusion": self._core_fusion_summary(),
            "master_control": master_control,
        }

    def build_home_from_saved_state(self, *, user_id: str | None = None) -> dict[str, Any]:
        identity = self._resolve_identity(user_id, None)
        if identity.get("binding_status") == "error":
            return self._identity_binding_error(identity)
        workspace = self._workspace_from_core_fusion(identity)
        hr_items = workspace["all_visible_items"]
        role_panel = ROLE_HOME_PANELS.get(identity["workspace_key"], ROLE_HOME_PANELS["boss"])
        sections = {
            "my_todos": self._section("我的待办", workspace["my_todos"], empty_text="暂无待办"),
            "my_tasks": self._section("我的任务", workspace["my_tasks"], empty_text="暂无任务"),
            "my_approvals": self._section("我的审批", workspace["my_approvals"], empty_text="暂无审批"),
            "role_home": self._section(role_panel["title"], workspace["all_visible_items"], empty_text=role_panel["empty"]),
            "event_execution_flow": self._section("事件执行流", hr_items, empty_text="暂无事件执行任务"),
        }
        business_dashboard = self._business_dashboard(identity, workspace["all_visible_items"])
        master_control = self._boss_master_control(identity, workspace, business_dashboard)
        return {
            "schema_version": "oms.v1.home",
            "home_type": self._home_type(identity),
            "entry": self._home_entry(identity),
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
            "core_fusion": self._core_fusion_summary(),
            "master_control": master_control,
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
        key, identity_source = workspace_key_for_feishu_identity({raw_user_id}, live_root=self.live_root)
        if key:
            return key, identity_source
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

    def _core_fusion(self) -> dict[str, Any]:
        if self._core_fusion_state is None:
            self._core_fusion_state = CoreFusionLayer(self.live_root, self.operating_root).rebuild_from_saved_state()
        return self._core_fusion_state

    def _core_fusion_summary(self) -> dict[str, Any]:
        state = self._core_fusion()
        return {
            "schema_version": state.get("schema_version"),
            "mode": state.get("mode"),
            "flow": state.get("flow"),
            "source_of_truth": state.get("source_of_truth"),
            "counts": state.get("counts") or {},
            "validation": state.get("validation") or {},
            "paths": state.get("paths") or {},
        }

    def _home_type(self, identity: dict[str, str]) -> str:
        if identity["workspace_key"] == "boss":
            return "boss_master_control_interface"
        return "user_centric_operating_interface"

    def _home_entry(self, identity: dict[str, str]) -> str:
        if identity["workspace_key"] == "boss":
            return OWNER_MASTER_CONTROL_ENTRY_TYPE
        return "personal_workspace"

    def _boss_master_control(
        self,
        identity: dict[str, str],
        workspace: dict[str, list[dict[str, Any]]],
        business_dashboard: dict[str, Any],
    ) -> dict[str, Any] | None:
        if identity["workspace_key"] != "boss":
            return None
        entry = CoreFusionLayer(self.live_root, self.operating_root).work_entry_for_user(identity["user_id"])
        tasks = workspace.get("all_visible_items", [])
        return {
            "schema_version": "oms.v1.master_control",
            "entry_type": OWNER_MASTER_CONTROL_ENTRY_TYPE,
            "title": "OMS Master Dashboard",
            "control_user": {
                "user_id": identity["user_id"],
                "workspace_key": identity["workspace_key"],
                "name": identity["name"],
                "role": identity["role"],
            },
            "hierarchy": entry.get("hierarchy") or {
                "layer_1": "Owner Master Control",
                "layer_2": "Business Workspaces",
                "layer_3": "Execution Layer",
            },
            "permissions": entry.get("permissions") or {},
            "global_view": {
                "business_flows": entry.get("business_flows") or {},
                "risk_register": entry.get("risk_register") or {},
                "execution_status": entry.get("execution_status") or {},
                "unfinished_task_count": entry.get("unfinished_task_count", 0),
                "task_count": entry.get("task_count", len(tasks)),
            },
            "business_workspaces": entry.get("workspace_matrix") or {},
            "execution_layer": {
                "all_tasks": self._limit_items(tasks),
                "all_task_count": len(tasks),
                "all_task_visible_count": min(len(tasks), HOME_UI_ITEM_LIMIT),
                "unfinished_tasks": self._limit_items(entry.get("unfinished_tasks") or []),
                "sections": {
                    "all_unfinished": self._limit_items(workspace.get("my_todos", [])),
                    "all_active_tasks": self._limit_items(workspace.get("my_tasks", [])),
                    "all_approvals": self._limit_items(workspace.get("my_approvals", [])),
                },
            },
            "business_dashboard": business_dashboard,
        }

    def _workspace_from_core_fusion(self, identity: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
        self._core_fusion()
        items = self._read_jsonl(self.live_root / "core_fusion" / "unified_task_stream.jsonl")
        visible = (
            items
            if identity["workspace_key"] == "boss"
            else [item for item in items if item.get("workspace_key") == identity["workspace_key"]]
        )
        approvals = [
            item
            for item in visible
            if item.get("confirmation_required")
            or item.get("status") == "waiting_confirmation"
            or item.get("execution_status") == "waiting_confirmation"
        ]
        todos = [
            item
            for item in visible
            if item.get("status") not in {"ready", "assigned", "source_verified"}
            or item.get("execution_status") not in {"assigned", ""}
        ]
        tasks = [
            item
            for item in visible
            if item.get("status") in {"ready", "assigned", "source_verified"}
            and item.get("execution_status") in {"assigned", ""}
        ]
        return {
            "my_todos": todos,
            "my_tasks": tasks,
            "my_approvals": approvals,
            "all_visible_items": visible,
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

    def _hr_items_for_identity(self, identity: dict[str, str]) -> list[dict[str, Any]]:
        self._core_fusion()
        items = self._read_jsonl(self.live_root / "core_fusion" / "unified_task_stream.jsonl")
        if identity["workspace_key"] == "boss":
            return items
        return [item for item in items if item.get("workspace_key") == identity["workspace_key"]]

    def _business_events(self) -> list[dict[str, Any]]:
        self._core_fusion()
        return self.truth_store.read_events()

    def _workflow_distribution(self) -> list[dict[str, Any]]:
        self._core_fusion()
        return self._read_jsonl(self.live_root / "core_fusion" / "unified_task_stream.jsonl")

    def _read_saved_work_items(self) -> list[dict[str, Any]]:
        return self.truth_store.read_work_items()

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
        production_adapter = ProductionDataAdapter(
            self.truth_store,
            operational_baseline_root=self.live_root / "operational_baseline",
        )
        operating_mode = production_adapter.operating_mode()
        current_initialized = operating_mode.get("current_status") != "NOT_INITIALIZED"
        production_sales_records = production_adapter.sales_records()
        production_finance_records = production_adapter.finance_records()
        production_financial_events = production_adapter.financial_event_records()
        production_stay_records = production_adapter.stay_records()
        production_room_records = production_adapter.room_records()
        production_caregiver_records = production_adapter.caregiver_records()
        production_sales_metrics = production_adapter.sales_metrics()
        production_finance_metrics = production_adapter.finance_metrics()
        production_operations_metrics = production_adapter.operations_metrics()
        saved_items = self._read_saved_work_items() if current_initialized else []
        all_items = list(saved_items)
        verified_items = [
            *production_stay_records,
            *production_room_records,
            *production_caregiver_records,
            *production_sales_records,
            *production_finance_records,
        ] if current_initialized else []
        uncalibrated_items: list[dict[str, Any]] = []
        finance_events_all = self.truth_store.read_financial_events() if current_initialized else []
        finance_events = list(production_financial_events)
        business_events = self._business_events() if current_initialized else []
        workflow_distribution = self._workflow_distribution() if current_initialized else []
        hr_items = workflow_distribution
        verified_finance_events = list(production_financial_events)
        uncalibrated_finance_events = [
            event for event in finance_events_all if not self._is_truth_verified_event(event)
        ]
        finance_items = list(production_finance_records)
        resident_items = production_adapter.resident_records()
        stay_items = production_adapter.stay_records()
        room_items = production_adapter.room_records()
        caregiver_items = production_adapter.caregiver_records()
        contract_items = list(production_sales_records)
        service_items = list(caregiver_items)
        today_tokens = self._today_tokens()
        today_checkins = [
            item
            for item in resident_items
            if self._contains_today(item.get("checkin_date"), today_tokens)
            or self._contains_today(item.get("planned_checkin_date"), today_tokens)
        ]
        today_checkouts = [
            item
            for item in resident_items
            if self._contains_today(item.get("checkout_date"), today_tokens)
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
            business_events=business_events,
            hr_items=hr_items,
            today_checkins=today_checkins,
            today_checkouts=today_checkouts,
            today_collection=today_collection,
            risk_items=risk_items,
            pending_visible=pending_visible,
            production_sales_metrics=production_sales_metrics,
            production_finance_metrics=production_finance_metrics,
            production_operations_metrics=production_operations_metrics,
        )
        source_evidence_verified_data = self._source_evidence_verified_data(
            resident_items=resident_items,
            room_items=room_items,
            contract_items=contract_items,
            finance_items=finance_items,
            service_items=service_items,
            finance_events=finance_events,
            business_events=business_events,
            workflow_distribution=workflow_distribution,
            hr_items=hr_items,
            visible_items=visible_items_all,
        )
        business_state_summary = self.business_state.read_state_summary()
        lifecycle_summary = self.lifecycle_engine.build_summary()
        return {
            "title": "今日经营",
            "source": "real_business_source_of_truth",
            "schema_source": "business_schema",
            "truth_source": self.truth_store.summary(),
            "operating_mode": operating_mode,
            "production_adapters": production_adapter.summary(),
            "data_truth_alignment": {
                "policy": "truth_source_contract_records_only",
                "data_source": "source_evidence_available_data",
                "production_data_source": "production_truth_adapter",
                "display_policy": "always_render_with_confidence_label",
                "verified_work_items": len(verified_items),
                "uncalibrated_work_items": len(uncalibrated_items),
                "visible_work_items": len(all_items),
                "verified_financial_events": len(verified_finance_events),
                "uncalibrated_financial_events": len(uncalibrated_finance_events),
                "visible_financial_events": len(finance_events),
                "production_sales_records": len(production_sales_records),
                "production_finance_records": len(production_finance_records),
                "production_room_records": len(room_items),
                "production_stay_records": len(stay_items),
                "production_resident_records": len(resident_items),
                "production_caregiver_records": len(caregiver_items),
                "visible_business_events": len(business_events),
                "visible_hr_execution_items": len(hr_items),
                "status": "aligned" if not uncalibrated_items and not uncalibrated_finance_events else "partial_alignment",
            },
            "source_evidence_available_data": source_evidence_verified_data,
            "source_evidence_verified_data": source_evidence_verified_data,
            "business_schema": business_schema,
            "business_state": business_state_summary,
            "lifecycle": lifecycle_summary,
            "metrics": {
                "resident_count": business_schema["resident_flow_schema"]["resident_count"],
                "today_checkins": business_schema["resident_flow_schema"]["upcoming_checkins"],
                "today_checkouts": business_schema["resident_flow_schema"]["checkouts"],
                "today_collection": business_schema["finance_schema"].get(
                    "today_income", business_schema["finance_schema"]["collected"]
                ),
                "today_todos": len(pending_visible),
                "risk_alerts": len(risk_items),
                "sales_contracts": business_schema["sales_schema"]["contracts"],
                "service_progress": business_schema["service_schema"]["in_service"],
                "room_status_records": business_schema["resident_flow_schema"]["room_status_records"],
                "finance_records": business_schema["finance_schema"]["event_records"],
                "business_events": len(business_events),
                "hr_execution_items": len(hr_items),
                "business_state_writebacks": sum(int(value or 0) for value in (business_state_summary.get("counts") or {}).values()),
                "open_lifecycles": int(lifecycle_summary.get("open_count") or 0),
                "closed_lifecycles": int(lifecycle_summary.get("closed_count") or 0),
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
        business_events: list[dict[str, Any]],
        hr_items: list[dict[str, Any]],
        today_checkins: list[dict[str, Any]],
        today_checkouts: list[dict[str, Any]],
        today_collection: float,
        risk_items: list[dict[str, Any]],
        pending_visible: list[dict[str, Any]],
        production_sales_metrics: dict[str, Any] | None = None,
        production_finance_metrics: dict[str, Any] | None = None,
        production_operations_metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        production_sales_metrics = production_sales_metrics or {}
        production_finance_metrics = production_finance_metrics or {}
        production_operations_metrics = production_operations_metrics or {}
        income = sum(self._number(event.get("income_amount") or event.get("amount")) for event in finance_events)
        expenses = sum(self._number(event.get("expense_amount") or event.get("cost_amount")) for event in finance_events)
        receivable = sum(self._number(item.get("receivable_amount")) for item in finance_items)
        if not receivable and finance_items:
            receivable = sum(1 for item in finance_items if item.get("status") != "ready")
        pending_payment_amount = sum(self._number(item.get("pending_payment_amount")) for item in finance_items)
        completed_service = sum(1 for item in service_items if item.get("status") == "ready")
        service_exceptions = sum(
            1 for item in service_items if item.get("status") in {"attention_required", "blocked", "waiting_confirmation"}
        )
        leads = len(contract_items)
        lost = sum(1 for item in contract_items if "流失" in str(item.get("daily_process") or ""))
        contracts = len(contract_items)
        conversion = round(contracts / leads, 4) if leads else 0
        hr_assigned = [item for item in hr_items if item.get("execution_status") == "assigned"]
        hr_executors = {
            item.get("workspace_key") or item.get("executor_user_id") or item.get("name")
            for item in hr_items
            if item.get("workspace_key") or item.get("executor_user_id") or item.get("name")
        }
        attendance_rate = round(len(hr_assigned) / len(hr_items), 4) if hr_items else 0
        return {
            "schema_version": "oms.business.v1",
            "resident_flow_schema": {
                "resident_count": int(production_operations_metrics.get("stay_records") or len(resident_items)),
                "active_stays": int(production_operations_metrics.get("active_stays") or len(resident_items)),
                "upcoming_checkins": int(production_operations_metrics.get("waiting_checkins") or len(today_checkins)),
                "checkouts": int(production_operations_metrics.get("checked_out") or len(today_checkouts)),
                "room_status_records": int(production_operations_metrics.get("room_records") or len(room_items)),
                "adapter_id": STAY_ADAPTER_ID,
                "room_adapter_id": ROOM_ADAPTER_ID,
                "mapping_version": production_operations_metrics.get("mapping_version") or "",
            },
            "finance_schema": {
                "income": round(self._number(production_finance_metrics.get("income")) or income, 2),
                "receivable": round(self._number(production_finance_metrics.get("receivable")) or receivable, 2),
                "today_income": round(today_collection, 2),
                "collected": round(self._number(production_finance_metrics.get("collected")) or today_collection, 2),
                "expenses": round(self._number(production_finance_metrics.get("expenses")) or expenses, 2),
                "pending_payment_amount": round(
                    self._number(production_finance_metrics.get("pending_payment_amount")) or pending_payment_amount,
                    2,
                ),
                "profit": round(self._number(production_finance_metrics.get("profit")) or (income - expenses), 2),
                "event_records": len(finance_items),
                "adapter_id": production_finance_metrics.get("adapter_id") or FINANCE_ADAPTER_ID,
                "mapping_version": production_finance_metrics.get("mapping_version") or "",
            },
            "sales_schema": {
                "leads": int(production_sales_metrics.get("leads") or leads),
                "contracts": int(production_sales_metrics.get("contracts") or contracts),
                "conversion": self._number(production_sales_metrics.get("conversion")) or conversion,
                "lost": int(production_sales_metrics.get("lost") or lost),
                "sales_amount": round(self._number(production_sales_metrics.get("sales_amount")), 2),
                "adapter_id": production_sales_metrics.get("adapter_id") or SALES_ADAPTER_ID,
                "mapping_version": production_sales_metrics.get("mapping_version") or "",
            },
            "service_schema": {
                "checkin_preparation": len(today_checkins),
                "in_service": int(production_operations_metrics.get("assigned_caregivers") or len(service_items)),
                "exceptions": service_exceptions,
                "completed": completed_service,
                "caregiver_records": int(production_operations_metrics.get("caregiver_records") or len(service_items)),
                "on_duty_caregivers": int(production_operations_metrics.get("on_duty_caregivers") or len(service_items)),
                "adapter_id": CAREGIVER_ADAPTER_ID,
                "mapping_version": production_operations_metrics.get("mapping_version") or "",
            },
            "hr_schema": {
                "on_duty_staff": len(hr_executors),
                "scheduled_shifts": len(hr_items),
                "performance": len(hr_assigned),
                "attendance_rate": attendance_rate,
            },
            "semantic_status": {
                "pending_work_items": len(pending_visible),
                "risk_items": len(risk_items),
                "business_events": len(business_events),
                "hr_execution_items": len(hr_items),
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
        business_events: list[dict[str, Any]],
        workflow_distribution: list[dict[str, Any]],
        hr_items: list[dict[str, Any]],
        visible_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "policy": "source_evidence_available_data",
            "adapter_schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "adapter_policy": "production_truth_source_contract_domain",
            "counts": {
                "resident_data": len(resident_items),
                "stay_data": len(resident_items),
                "room_status_data": len(room_items),
                "sales_contract_data": len(contract_items),
                "finance_data": len(finance_items),
                "service_data": len(service_items),
                "caregiver_data": len(service_items),
                "financial_events": len(finance_events),
                "business_event_flow": len(business_events),
                "workflow_distribution": len(workflow_distribution),
                "hr_execution_flow": len(hr_items),
                "current_user_visible_data": len(visible_items),
                "visible_limit": HOME_UI_SOURCE_LIMIT,
            },
            "flow": "OMS_TRUTH_SOURCE -> ProductionDataAdapter -> Domain -> /api/oms/home -> UI",
            "resident_data": [self._verified_item_record(item, "resident") for item in self._limit_items(resident_items, HOME_UI_SOURCE_LIMIT)],
            "stay_data": [self._verified_item_record(item, "stay") for item in self._limit_items(resident_items, HOME_UI_SOURCE_LIMIT)],
            "room_status_data": [self._verified_item_record(item, "room_status") for item in self._limit_items(room_items, HOME_UI_SOURCE_LIMIT)],
            "sales_contract_data": [self._verified_item_record(item, "contracts") for item in self._limit_items(contract_items, HOME_UI_SOURCE_LIMIT)],
            "finance_data": [self._verified_item_record(item, "finance") for item in self._limit_items(finance_items, HOME_UI_SOURCE_LIMIT)],
            "service_data": [self._verified_item_record(item, "service") for item in self._limit_items(service_items, HOME_UI_SOURCE_LIMIT)],
            "caregiver_data": [self._verified_item_record(item, "caregiver") for item in self._limit_items(service_items, HOME_UI_SOURCE_LIMIT)],
            "financial_events": [self._verified_event_record(event) for event in self._limit_items(finance_events, HOME_UI_SOURCE_LIMIT)],
            "business_event_flow": [self._business_event_record(event) for event in self._limit_items(business_events, HOME_UI_SOURCE_LIMIT)],
            "workflow_distribution": [self._workflow_task_record(task) for task in self._limit_items(workflow_distribution, HOME_UI_SOURCE_LIMIT)],
            "hr_execution_flow": [self._hr_execution_record(item) for item in self._limit_items(hr_items, HOME_UI_SOURCE_LIMIT)],
            "current_user_visible_data": [self._verified_item_record(item, "current_user") for item in self._limit_items(visible_items, HOME_UI_SOURCE_LIMIT)],
        }

    def _business_event_record(self, event: dict[str, Any]) -> dict[str, Any]:
        assignment = event.get("assignment") if isinstance(event.get("assignment"), dict) else {}
        return {
            "business_domain": event.get("event_type") or "business_event",
            "data_confidence": "source_verified" if event.get("source_evidence") else "uncalibrated_warning",
            "event_id": event.get("business_event_id") or "",
            "event_action": event.get("event_action") or "",
            "event_name": event.get("event_name") or "",
            "record_id": event.get("source_record_id") or "",
            "title": event.get("title") or event.get("event_name") or event.get("event_type") or "",
            "status": event.get("status") or "",
            "role": assignment.get("role") or "",
            "workspace": assignment.get("workspace") or "",
            "source_evidence": event.get("source_evidence") or {},
            "event_chain": event.get("event_chain") or {},
            "trace_chain": event.get("trace_chain") or event.get("event_chain") or {},
            "next_action": event.get("next_action") or "",
            "display_fields": self._display_fields(event.get("trace_chain") or event.get("event_chain") or event),
        }

    def _workflow_task_record(self, task: dict[str, Any]) -> dict[str, Any]:
        workflow = task.get("workflow") if isinstance(task.get("workflow"), dict) else {}
        identity = task.get("identity") if isinstance(task.get("identity"), dict) else {}
        return {
            "business_domain": "workflow_distribution",
            "data_confidence": "source_verified" if task.get("source_evidence") else "uncalibrated_warning",
            "event_id": task.get("business_event_id") or "",
            "event_action": task.get("event_action") or "",
            "event_name": task.get("event_name") or "",
            "work_item_id": workflow.get("workflow_task_id") or task.get("workflow_task_id") or task.get("task_id") or "",
            "title": task.get("event_name") or task.get("next_action") or task.get("event_type") or "",
            "status": task.get("status") or workflow.get("distribution_status") or "",
            "role": task.get("role") or identity.get("role") or "",
            "workspace": task.get("workspace") or identity.get("workspace") or "",
            "source_evidence": task.get("source_evidence") or {},
            "trace_chain": task.get("trace_chain") or workflow.get("trace_chain") or {},
            "display_fields": task.get("display_fields") or self._display_fields(task),
        }

    def _hr_execution_record(self, item: dict[str, Any]) -> dict[str, Any]:
        workflow = item.get("workflow") if isinstance(item.get("workflow"), dict) else {}
        identity = item.get("identity") if isinstance(item.get("identity"), dict) else {}
        return {
            "business_domain": "hr_execution_flow",
            "data_confidence": "source_verified" if item.get("source_evidence") else "uncalibrated_warning",
            "event_id": item.get("business_event_id") or "",
            "event_action": item.get("event_action") or "",
            "event_name": item.get("event_name") or "",
            "work_item_id": workflow.get("hr_execution_id") or item.get("hr_execution_id") or item.get("task_id") or "",
            "title": item.get("title") or item.get("event_name") or item.get("source_event_type") or "",
            "status": item.get("execution_status") or workflow.get("execution_status") or "",
            "role": item.get("role") or identity.get("role") or "",
            "workspace": item.get("workspace") or identity.get("workspace") or "",
            "source_evidence": item.get("source_evidence") or {},
            "event_chain": item.get("event_chain") or {},
            "trace_chain": item.get("trace_chain") or item.get("event_chain") or workflow.get("trace_chain") or {},
            "display_fields": item.get("display_fields") or self._display_fields(item.get("trace_chain") or item.get("event_chain") or item),
        }

    def _verified_item_record(self, item: dict[str, Any], business_domain: str) -> dict[str, Any]:
        if item.get("schema_version") == PRODUCTION_ADAPTER_SCHEMA_VERSION or item.get("adapter_id") in {
            SALES_ADAPTER_ID,
            FINANCE_ADAPTER_ID,
            ROOM_ADAPTER_ID,
            STAY_ADAPTER_ID,
            CAREGIVER_ADAPTER_ID,
        }:
            record = dict(item)
            record["business_domain"] = item.get("business_domain") or business_domain
            record["data_confidence"] = item.get("data_confidence") or "source_verified"
            record["source_evidence"] = item.get("source_evidence") or {}
            record["display_fields"] = item.get("display_fields") or self._display_fields(item)
            return record
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
        if event.get("schema_version") == PRODUCTION_ADAPTER_SCHEMA_VERSION or event.get("adapter_id") == FINANCE_ADAPTER_ID:
            record = dict(event)
            record["business_domain"] = event.get("business_domain") or "financial_event"
            record["data_confidence"] = event.get("data_confidence") or "source_verified"
            record["source_evidence"] = event.get("source_evidence") or {}
            record["display_fields"] = event.get("display_fields") or self._display_fields(event)
            return record
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
        visible_items = self._limit_items(items)
        return {
            "title": title,
            "count": len(items),
            "visible_count": len(visible_items),
            "visible_limit": HOME_UI_ITEM_LIMIT,
            "items": [self._home_item(item) for item in visible_items],
            "empty_text": empty_text if not items else "",
        }

    def _limit_items(self, items: list[dict[str, Any]], limit: int = HOME_UI_ITEM_LIMIT) -> list[dict[str, Any]]:
        if len(items) <= limit:
            return items
        return items[:limit]

    def _home_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if item.get("schema_version") in {"oms.v1.hr_execution_item", "oms.v1.unified_task"} or item.get("hr_source") == "business_event_flow":
            return self._event_execution_home_item(item)
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

    def _event_execution_home_item(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") if isinstance(item.get("source_evidence"), dict) else {}
        chain = item.get("trace_chain") if isinstance(item.get("trace_chain"), dict) else item.get("event_chain")
        chain = chain if isinstance(chain, dict) else {}
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        identity = item.get("identity") if isinstance(item.get("identity"), dict) else {}
        workflow = item.get("workflow") if isinstance(item.get("workflow"), dict) else {}
        event_type = str(item.get("source_event_type") or "business_event")
        event_name = str(item.get("event_name") or item.get("event_action") or event_type)
        workspace = str(item.get("workspace") or identity.get("workspace") or chain.get("workspace") or "")
        executor = str(item.get("name") or identity.get("name") or chain.get("executor") or "")
        source_file = Path(str(chain.get("source_file") or evidence.get("source_file") or data.get("source_file") or "")).name
        source_row = str(chain.get("source_row") or evidence.get("row_number") or data.get("source_row") or "")
        source_label = source_file or str(evidence.get("truth_source") or data.get("source_type") or "OMS_TRUTH_SOURCE")
        if source_row:
            source_label = f"{source_label} / row {source_row}"
        next_action = str(item.get("next_action") or "confirm_business_event")
        display_fields = item.get("display_fields") or [
            {"label": "Excel来源", "value": source_label},
            {"label": "业务事件", "value": event_name},
            {"label": "执行人", "value": executor or "user_id待绑定"},
            {"label": "工作台", "value": workspace},
            {"label": "下一步", "value": next_action},
        ]
        return {
            "id": workflow.get("hr_execution_id") or item.get("hr_execution_id") or item.get("task_id") or item.get("business_event_id") or "",
            "title": item.get("title") or event_name,
            "action": f"{event_name} -> {executor or 'unresolved_user'} -> {workspace or 'workspace_pending'}",
            "status": item.get("execution_status") or item.get("status") or "assigned",
            "needs_confirmation": (item.get("execution_status") or item.get("status")) not in {"assigned", "ready", "source_verified"},
            "data_confidence": "source_verified" if evidence else "uncalibrated_warning",
            "source_evidence": evidence,
            "source_summary": self._source_summary(evidence),
            "event_chain": chain,
            "trace_chain": chain,
            "display_fields": display_fields,
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
        if workspace_key == "boss":
            return [
                {"key": "master", "label": "主控", "active": True},
                {"key": "flows", "label": "业务", "active": False},
                {"key": "execution", "label": "执行", "active": False},
                {"key": "risk", "label": "风险", "active": False},
                {"key": "data", "label": "数据", "active": False},
            ]
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
