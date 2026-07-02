from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import OperationalWorkItem, now_iso


OPERATING_MODE = "daily_operating_mode"
LEGACY_POLICY = {
    "Excel": "read_only_history",
    "微信": "input_source_only",
    "OMS": "default_work_entry",
}


class OMSOperationalCore:
    """Turn OMS pipeline output into Huangjia daily operating work queues."""

    def __init__(self, operating_root: str | Path | None = None):
        self.operating_root = Path(operating_root or DEFAULT_LIVE_ROOT / "operational_core")

    def build_operating_stream(
        self,
        execution_stream: dict[str, Any],
        governance_stream: dict[str, Any],
        live_stream: dict[str, Any],
    ) -> dict[str, Any]:
        work_items = self.to_work_items(execution_stream, governance_stream, live_stream)
        self._persist_work_items(work_items)
        return {
            "schema_version": "oms.v1.operational_stream",
            "input_id": execution_stream.get("input_id") or governance_stream.get("input_id") or live_stream.get("input_id"),
            "operating_mode": OPERATING_MODE,
            "mode_change": "Tool Mode -> Operating Mode",
            "flow": [
                "input",
                "parsed_json",
                "business_events",
                "recommendations",
                "execution_actions",
                "governance_decisions",
                "live_sync",
                "daily_operations",
            ],
            "default_entry_policy": {
                "default_entry": "OMS",
                "human_role": "确认、审批、覆盖",
                "excel_role": "只读历史和迁移来源",
                "wechat_role": "输入来源和人工确认回写来源",
                "bypass_policy": "人不绕过系统，系统也不绕过人。",
            },
            "work_items": [item.to_dict() for item in work_items],
            "role_views": self._role_views(work_items),
            "operational_readiness": self._readiness(work_items, live_stream),
            "audit": {
                "created_at": now_iso(),
                "work_item_count": len(work_items),
                "operating_root": str(self.operating_root),
                "legacy_policy": LEGACY_POLICY,
            },
        }

    def to_work_items(
        self,
        execution_stream: dict[str, Any],
        governance_stream: dict[str, Any],
        live_stream: dict[str, Any],
    ) -> list[OperationalWorkItem]:
        actions = execution_stream.get("actions")
        governance = governance_stream.get("governance")
        sync_results = live_stream.get("sync_results")
        if actions is None:
            raise ValueError("OMSOperationalCore requires an ExecutionEngine execution stream")
        if governance is None:
            raise ValueError("OMSOperationalCore requires a GovernanceEngine governance stream")
        if sync_results is None:
            raise ValueError("OMSOperationalCore requires a LiveConnector live stream")

        governance_by_action = {item.get("action_id"): item for item in governance}
        syncs_by_action: dict[str, list[dict[str, Any]]] = {}
        for result in sync_results:
            syncs_by_action.setdefault(result.get("action_id"), []).append(result)

        work_items: list[OperationalWorkItem] = []
        for action in actions:
            action_id = action.get("action_id", "")
            gov = governance_by_action.get(action_id, {})
            syncs = syncs_by_action.get(action_id, [])
            work_items.append(self._work_item(action, gov, syncs))
        if work_items:
            work_items.append(self._boss_view(work_items, live_stream))
        return work_items

    def _work_item(
        self, action: dict[str, Any], governance: dict[str, Any], syncs: list[dict[str, Any]]
    ) -> OperationalWorkItem:
        role, workspace, process, next_action = self._route(action, governance)
        approval_required = bool(governance.get("approval_required"))
        status = self._status(governance, syncs)
        return OperationalWorkItem(
            role=role,
            workspace=workspace,
            daily_process=process,
            primary_entry="OMS",
            legacy_policy=LEGACY_POLICY,
            action_id=action.get("action_id", ""),
            action_type=action.get("action_type", ""),
            status=status,
            confirmation_required=approval_required,
            next_operator_action=next_action if approval_required else "在 OMS 中确认同步结果；不要回到 Excel/微信群重复操作。",
            source_sync_targets=[sync.get("sync_target", "") for sync in syncs],
        )

    def _boss_view(self, work_items: list[OperationalWorkItem], live_stream: dict[str, Any]) -> OperationalWorkItem:
        pending_count = sum(1 for item in work_items if item.status != "ready")
        return OperationalWorkItem(
            role="BOSS",
            workspace="经营总览",
            daily_process="每日经营判断",
            primary_entry="OMS",
            legacy_policy=LEGACY_POLICY,
            action_id=live_stream.get("input_id") or "daily_summary",
            action_type="boss_daily_operating_view",
            status="attention_required" if pending_count else "ready",
            confirmation_required=bool(pending_count),
            next_operator_action="在 OMS 中查看房态、财务、销售、服务的待确认事项和同步状态。",
            source_sync_targets=["OMS经营总览"],
        )

    def _route(self, action: dict[str, Any], governance: dict[str, Any]) -> tuple[str, str, str, str]:
        action_type = action.get("action_type", "")
        target_module = action.get("target_module", "")
        required_roles = governance.get("required_roles") or []

        if target_module == "room_status_module":
            return "六月", "房态工作台", "每日排房", "在 OMS 中确认排房、调房、冲突或超卖处理。"
        if target_module == "finance_module":
            return "刘姐", "财务工作台", "每日日结", "在 OMS 中确认日结、对账、待付款或服务金额拆分。"
        if target_module == "service_module":
            return "娜娜", "服务工作台", "每日入住/服务", "在 OMS 中确认入住准备、服务安排或异常处理。"
        if target_module == "sales_module" or action_type == "create_sales_operation_followup":
            return "销售", "销售提报入口", "每日签约提报", "在 OMS 中确认签约、收款和客户结构化结果。"
        if "BOSS" in required_roles:
            return "BOSS", "经营总览", "每日经营判断", "在 OMS 中进行终审或覆盖。"
        return "运营中心", "运营中心", "每日运营协同", "在 OMS 中分配岗位负责人。"

    def _status(self, governance: dict[str, Any], syncs: list[dict[str, Any]]) -> str:
        if governance.get("approval_required"):
            return "waiting_confirmation"
        if not syncs:
            return "waiting_live_sync"
        if any(sync.get("status") == "failed" for sync in syncs):
            return "blocked"
        if any(sync.get("status") == "pending" for sync in syncs):
            return "ready_with_pending_sync"
        return "ready"

    def _role_views(self, work_items: list[OperationalWorkItem]) -> dict[str, list[str]]:
        views: dict[str, list[str]] = {}
        for item in work_items:
            views.setdefault(item.role, []).append(item.work_item_id)
        return views

    def _readiness(self, work_items: list[OperationalWorkItem], live_stream: dict[str, Any]) -> dict[str, Any]:
        sync_results = live_stream.get("sync_results", [])
        pending_sync = sum(1 for result in sync_results if result.get("status") == "pending")
        failed_sync = sum(1 for result in sync_results if result.get("status") == "failed")
        return {
            "operating_mode_ready": failed_sync == 0,
            "production_adoption_status": "ready_not_enforced",
            "pending_external_sync_count": pending_sync,
            "failed_sync_count": failed_sync,
            "completion_criteria": {
                "六月不再用Excel排房": "requires_management_cutover",
                "刘姐不再手工做日结": "requires_management_cutover",
                "销售不再群里报数据": "requires_management_cutover",
                "BOSS直接看OMS": "requires_management_cutover",
            },
        }

    def _persist_work_items(self, work_items: list[OperationalWorkItem]) -> None:
        self.operating_root.mkdir(parents=True, exist_ok=True)
        path = self.operating_root / "daily_work_items.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            for item in work_items:
                handle.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
