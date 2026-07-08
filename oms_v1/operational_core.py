from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .operating_center_source import (
    IDENTITY_BINDING_ERROR,
    IDENTITY_LOCK_POLICY,
    OPERATING_CENTER_PEOPLE,
    OPERATING_CENTER_VERSION,
    WORKSPACE_KEY_BY_ROLE,
    workspace_key_for_feishu_identity,
)
from .schemas import OperationalWorkItem, now_iso
from .truth_source import TruthSourceStore


OPERATING_MODE = "daily_operating_mode"
LEGACY_POLICY = {
    "Excel": "read_only_history",
    "微信": "input_source_only",
    "OMS": "default_work_entry",
}

PERSONAL_WORKSPACES = OPERATING_CENTER_PEOPLE

OPERATING_CENTER_STRUCTURE = {
    "business_layer": {
        "layer_name": "业务层",
        "purpose": "一线业务闭环，直接承接客户、房态、财务、服务和经营总览。",
        "units": [
            {
                "unit": "销售",
                "owner": "杨欢欢",
                "classification": {"人": ["杨欢欢", "销售"], "流程": ["签约提报", "客户结构化", "销售转运营"], "系统能力": ["InputHub", "CRM历史数据"]},
            },
            {
                "unit": "店长",
                "owner": "刘芳羽",
                "classification": {"人": ["刘芳羽"], "流程": ["排房", "调房", "房态冲突确认"], "系统能力": ["排房优化", "房态工作台"]},
            },
            {
                "unit": "财务",
                "owner": "刘晶",
                "classification": {"人": ["刘晶"], "流程": ["日结", "对账", "付款审批", "费用报销"], "系统能力": ["成本控制", "API-driven审批"]},
            },
            {
                "unit": "服务",
                "owner": "尚丽娜",
                "classification": {"人": ["尚丽娜"], "流程": ["入住准备", "服务安排", "异常处理", "出馆跟进"], "系统能力": ["服务工作台", "风险预警"]},
            },
            {
                "unit": "经营总览",
                "owner": "石磊",
                "classification": {"人": ["石磊"], "流程": ["终审", "经营判断", "跨部门协调"], "系统能力": ["经营指标中心", "数据分析中心"]},
            },
        ],
    },
    "support_layer": {
        "layer_name": "支撑层",
        "purpose": "保障业务层稳定运行，不拆主链路，只作为协同支撑入口。",
        "units": [
            {
                "unit": "行政采购",
                "owner": "运营中心",
                "classification": {"人": ["行政", "采购"], "流程": ["采购申请", "物品领用", "供应保障"], "系统能力": ["成本控制", "pending_outbox"]},
            },
            {
                "unit": "产护支持",
                "owner": "尚丽娜",
                "classification": {"人": ["产护"], "流程": ["产护排班", "护理协同", "入住支持"], "系统能力": ["服务工作台", "风险预警"]},
            },
            {
                "unit": "餐饮/厨房",
                "owner": "厨房",
                "classification": {"人": ["厨房", "餐饮"], "流程": ["月子餐协同", "餐饮异常", "厨房备餐"], "系统能力": ["服务工作台", "成本控制"]},
            },
            {
                "unit": "后勤保障",
                "owner": "后勤",
                "classification": {"人": ["后勤"], "流程": ["房间物资", "维修保洁", "运营保障"], "系统能力": ["风险预警", "pending_outbox"]},
            },
        ],
    },
    "system_capability_layer": {
        "layer_name": "系统能力层",
        "purpose": "沉淀 OMS 的复用能力，为业务层和支撑层提供判断、预警和指标。",
        "units": [
            {
                "unit": "数据分析中心",
                "owner": "OMS",
                "classification": {"人": ["石磊", "运营中心"], "流程": ["数据汇总", "趋势分析"], "系统能力": ["结构化事件流", "经营指标中心"]},
            },
            {
                "unit": "风险预警",
                "owner": "OMS",
                "classification": {"人": ["石磊", "岗位负责人"], "流程": ["风险识别", "审批触发", "pending兜底"], "系统能力": ["GovernanceEngine", "Feishu_Pending_Mode"]},
            },
            {
                "unit": "排房优化",
                "owner": "OMS",
                "classification": {"人": ["刘芳羽", "石磊"], "流程": ["排房建议", "冲突提示", "调房复核"], "系统能力": ["DecisionEngine", "房态工作台"]},
            },
            {
                "unit": "成本控制",
                "owner": "OMS",
                "classification": {"人": ["刘晶", "石磊"], "流程": ["费用归集", "付款控制", "采购成本观察"], "系统能力": ["API-driven审批", "Excel账本"]},
            },
            {
                "unit": "经营指标中心",
                "owner": "OMS",
                "classification": {"人": ["石磊"], "流程": ["每日总览", "异常追踪", "经营复盘"], "系统能力": ["经营总览", "operational_readiness"]},
            },
        ],
    },
}


class OMSOperationalCore:
    """Turn OMS pipeline output into Huangjia daily operating work queues."""

    def __init__(self, operating_root: str | Path | None = None):
        self.operating_root = Path(operating_root or DEFAULT_LIVE_ROOT / "operational_core")
        self.live_root = self._resolve_live_root(self.operating_root)
        self.truth_store = TruthSourceStore(self.live_root, self.operating_root)

    def _resolve_live_root(self, operating_root: Path) -> Path:
        configured = os.getenv("OMS_LIVE_ROOT")
        if configured:
            return Path(configured)
        if operating_root.name == "operational_core":
            return operating_root.parent
        sibling_live_root = operating_root.parent / "live"
        if sibling_live_root.exists() or operating_root.name == "operational":
            return sibling_live_root
        return DEFAULT_LIVE_ROOT

    def build_operating_stream(
        self,
        execution_stream: dict[str, Any],
        governance_stream: dict[str, Any],
        live_stream: dict[str, Any],
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        work_items = self.to_work_items(execution_stream, governance_stream, live_stream)
        support_work_items = self._support_layer_work_items(work_items)
        support_trigger_events = self._support_layer_trigger_events(execution_stream, live_stream)
        personal_workspace_system = self._personal_workspace_system(work_items, user_id)
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
                "default_entry": "personal_workspace",
                "identity_model": "feishu_user_id_first",
                "workspace_policy": "one_user_one_workspace",
                "source_of_truth": OPERATING_CENTER_VERSION,
                "human_role": "确认、审批、覆盖",
                "excel_role": "只读历史和迁移来源",
                "wechat_role": "输入来源和人工确认回写来源",
                "bypass_policy": "人不绕过系统，系统也不绕过人。",
            },
            "workspace_mode": "personal_workspace_system",
            "personal_workspace_system": personal_workspace_system,
            "default_workspace": personal_workspace_system["default_workspace"],
            "operating_center_structure": OPERATING_CENTER_STRUCTURE,
            "work_items": [item.to_dict() for item in work_items],
            "support_layer_work_items": [item.to_dict() for item in support_work_items],
            "support_layer_trigger_events": support_trigger_events,
            "support_layer_status": self._support_layer_status(support_work_items, support_trigger_events),
            "role_views": self._role_views(work_items),
            "structure_views": self._structure_views(work_items),
            "operational_readiness": self._readiness(work_items, live_stream),
            "audit": {
                "created_at": now_iso(),
                "work_item_count": len(work_items),
                "operating_root": str(self.operating_root),
                "legacy_policy": LEGACY_POLICY,
                "structure_layer_count": len(OPERATING_CENTER_STRUCTURE),
                "people_model_count": len(OPERATING_CENTER_PEOPLE),
                "people_model_source": OPERATING_CENTER_VERSION,
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
            role="石磊",
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
            return "刘芳羽", "房态工作台", "每日排房", "在 OMS 中确认排房、调房、冲突或超卖处理。"
        if target_module == "finance_module":
            return "刘晶", "财务工作台", "每日日结", "在 OMS 中确认日结、对账、待付款或服务金额拆分。"
        if target_module == "service_module":
            return "尚丽娜", "服务工作台", "每日入住/服务", "在 OMS 中确认入住准备、服务安排或异常处理。"
        if target_module == "support_layer":
            return self._support_route(action)
        if target_module == "sales_module" or action_type == "create_sales_operation_followup":
            return "销售", "销售提报入口", "每日签约提报", "在 OMS 中确认签约、收款和客户结构化结果。"
        if "石磊" in required_roles:
            return "石磊", "经营总览", "每日经营判断", "在 OMS 中进行终审或覆盖。"
        return "运营中心", "运营中心", "每日运营协同", "在 OMS 中分配岗位负责人。"

    def _support_route(self, action: dict[str, Any]) -> tuple[str, str, str, str]:
        action_type = action.get("action_type", "")
        routes = {
            "create_admin_procurement_task": (
                "行政采购",
                "行政采购",
                "采购与物资补给",
                "在 OMS 中确认采购申请、物资补给和消耗品补充。",
            ),
            "create_maternity_care_support_task": (
                "产护支持",
                "产护支持",
                "产护资源调度",
                "在 OMS 中确认人员调度、护理资源分配和临时支援任务。",
            ),
            "create_kitchen_support_task": (
                "餐饮/厨房",
                "餐饮/厨房",
                "餐食与备餐计划",
                "在 OMS 中确认餐食准备、特殊餐需求和备餐计划。",
            ),
            "create_logistics_support_task": (
                "后勤保障",
                "后勤保障",
                "后勤与房间保障",
                "在 OMS 中确认房间清理、设备维护和物资配送。",
            ),
        }
        return routes.get(
            action_type,
            (
                "运营中心",
                "支撑层协同",
                "支撑层任务分派",
                "在 OMS 中确认支撑层负责人和下一步处理。",
            ),
        )

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

    def _personal_workspace_system(self, work_items: list[OperationalWorkItem], user_id: str | None) -> dict[str, Any]:
        identity = self._resolve_identity(user_id)
        workspaces = {
            key: self._personal_workspace(key, config, work_items)
            for key, config in PERSONAL_WORKSPACES.items()
        }
        return {
            "mode": "wechat_style_personal_home",
            "login_behavior": "user_id -> personal_workspace",
            "identity_policy": "feishu_user_id_is_primary_entry",
            "identity_lock_policy": IDENTITY_LOCK_POLICY,
            "workspace_policy": "one_user_one_workspace",
            "source_of_truth": OPERATING_CENTER_VERSION,
            "person_count": len(OPERATING_CENTER_PEOPLE),
            "fallback_user_id": "",
            "current_user": identity,
            "default_workspace": workspaces.get(identity["workspace_key"]) if identity.get("binding_status") != "error" else self._identity_binding_workspace(identity),
            "workspaces": workspaces,
        }

    def _resolve_identity(self, user_id: str | None) -> dict[str, str]:
        raw_user_id = (user_id or os.getenv("OMS_CURRENT_USER_ID") or os.getenv("OMS_USER_ID") or "").strip()
        normalized = raw_user_id.lower()
        key, identity_source = self._workspace_key_from_user_id(raw_user_id, normalized)
        if key not in PERSONAL_WORKSPACES:
            return {
                "user_id": raw_user_id,
                "workspace_key": "",
                "role": "",
                "name": "",
                "title": IDENTITY_BINDING_ERROR["title"],
                "identity_source": identity_source,
                "binding_status": "error",
                "error_type": IDENTITY_BINDING_ERROR["error_type"],
                "layer": "",
                "unit": "",
            }
        workspace = PERSONAL_WORKSPACES[key]
        return {
            "user_id": raw_user_id,
            "workspace_key": key,
            "role": workspace["role"],
            "name": workspace["name"],
            "title": workspace["title"],
            "identity_source": identity_source,
            "layer": workspace["layer"],
            "unit": workspace["unit"],
        }
    def _workspace_key_from_user_id(self, raw_user_id: str, normalized: str) -> tuple[str, str]:
        key, identity_source = workspace_key_for_feishu_identity({raw_user_id}, live_root=self.operating_root.parent)
        if key:
            return key, identity_source
        return "", "identity_binding_required"

    def _personal_workspace(
        self, workspace_key: str, config: dict[str, Any], work_items: list[OperationalWorkItem]
    ) -> dict[str, Any]:
        visible_items = self._visible_items_for_workspace(workspace_key, config, work_items)
        item_dicts = [item.to_dict() for item in visible_items]
        approvals = [item.to_dict() for item in visible_items if item.confirmation_required or item.status == "waiting_confirmation"]
        todos = [item.to_dict() for item in visible_items if item.status != "ready"]
        tasks = [item.to_dict() for item in visible_items if item.status == "ready"]
        return {
            "workspace_key": workspace_key,
            "title": config["title"],
            "role": config["role"],
            "name": config["name"],
            "layer": config["layer"],
            "unit": config["unit"],
            "home": "我的任务流",
            "focus": config["focus"],
            "my_todos": todos,
            "my_approvals": approvals,
            "my_tasks": tasks,
            "all_visible_items": item_dicts,
            "counts": {
                "todos": len(todos),
                "approvals": len(approvals),
                "tasks": len(tasks),
                "visible_items": len(item_dicts),
            },
        }

    def _visible_items_for_workspace(
        self, workspace_key: str, config: dict[str, Any], work_items: list[OperationalWorkItem]
    ) -> list[OperationalWorkItem]:
        role = config["role"]
        if workspace_key == "boss":
            return list(work_items)
        unit = config.get("unit")
        canonical_match_terms = {role, unit or ""}
        return [
            item
            for item in work_items
            if item.role in canonical_match_terms
            or item.workspace == unit
            or WORKSPACE_KEY_BY_ROLE.get(item.role) == workspace_key
            or WORKSPACE_KEY_BY_ROLE.get(item.workspace) == workspace_key
        ]

    def _support_layer_work_items(self, work_items: list[OperationalWorkItem]) -> list[OperationalWorkItem]:
        support_roles = {"行政采购", "产护支持", "餐饮/厨房", "后勤保障"}
        support_workspaces = {"行政采购", "产护支持", "餐饮/厨房", "后勤保障"}
        return [item for item in work_items if item.role in support_roles or item.workspace in support_workspaces]

    def _empty_workspace(self, identity: dict[str, str]) -> dict[str, Any]:
        return {
            "workspace_key": identity["workspace_key"],
            "title": identity["title"],
            "role": identity["role"],
            "name": identity["name"],
            "layer": identity["layer"],
            "unit": identity["unit"],
            "home": "我的任务流",
            "focus": [],
            "my_todos": [],
            "my_approvals": [],
            "my_tasks": [],
            "all_visible_items": [],
            "counts": {"todos": 0, "approvals": 0, "tasks": 0, "visible_items": 0},
        }

    def _identity_binding_workspace(self, identity: dict[str, str]) -> dict[str, Any]:
        return {
            "workspace_key": "",
            "title": IDENTITY_BINDING_ERROR["title"],
            "role": "",
            "name": "",
            "layer": "",
            "unit": "",
            "home": "identity_binding_error",
            "focus": [],
            "my_todos": [],
            "my_approvals": [],
            "my_tasks": [],
            "all_visible_items": [],
            "counts": {"todos": 0, "approvals": 0, "tasks": 0, "visible_items": 0},
            "binding_status": "error",
            "error": IDENTITY_BINDING_ERROR,
        }

    def _support_layer_trigger_events(
        self, execution_stream: dict[str, Any], live_stream: dict[str, Any]
    ) -> list[dict[str, Any]]:
        support_actions = {
            "create_admin_procurement_task",
            "create_maternity_care_support_task",
            "create_kitchen_support_task",
            "create_logistics_support_task",
        }
        syncs_by_action: dict[str, list[dict[str, Any]]] = {}
        for result in live_stream.get("sync_results", []):
            syncs_by_action.setdefault(result.get("action_id"), []).append(result)

        triggers: list[dict[str, Any]] = []
        for action in execution_stream.get("actions", []):
            action_type = action.get("action_type", "")
            if action_type not in support_actions:
                continue
            payload = action.get("execution_payload") or {}
            triggers.append(
                {
                    "action_id": action.get("action_id", ""),
                    "action_type": action_type,
                    "source_decision_type": action.get("source_decision_type", ""),
                    "source_event_id": payload.get("source_event_id", ""),
                    "trigger_reason": payload.get("reason", ""),
                    "pending_targets": [
                        sync.get("sync_target", "") for sync in syncs_by_action.get(action.get("action_id"), []) if sync.get("status") == "pending"
                    ],
                }
            )
        return triggers

    def _support_layer_status(
        self, support_work_items: list[OperationalWorkItem], support_trigger_events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        pending_count = sum(1 for item in support_work_items if item.status in {"ready_with_pending_sync", "waiting_confirmation"})
        blocked_count = sum(1 for item in support_work_items if item.status == "blocked")
        return {
            "active": bool(support_work_items),
            "work_item_count": len(support_work_items),
            "trigger_event_count": len(support_trigger_events),
            "pending_count": pending_count,
            "blocked_count": blocked_count,
            "status": "blocked" if blocked_count else "active" if support_work_items else "idle",
            "pending_outbox_enabled": any(event.get("pending_targets") for event in support_trigger_events),
        }

    def _structure_views(self, work_items: list[OperationalWorkItem]) -> dict[str, Any]:
        work_item_counts = self._work_item_counts_by_layer(work_items)
        return {
            layer_key: {
                "layer_name": layer["layer_name"],
                "units": [unit["unit"] for unit in layer["units"]],
                "owners": [unit["owner"] for unit in layer["units"]],
                "work_item_count": work_item_counts.get(layer_key, 0),
                "classification_required": ["人", "流程", "系统能力"],
            }
            for layer_key, layer in OPERATING_CENTER_STRUCTURE.items()
        }

    def _work_item_counts_by_layer(self, work_items: list[OperationalWorkItem]) -> dict[str, int]:
        counts = {layer_key: 0 for layer_key in OPERATING_CENTER_STRUCTURE}
        business_roles = {"杨欢欢", "销售", "刘芳羽", "刘晶", "尚丽娜", "石磊"}
        support_workspaces = {"行政采购", "产护支持", "餐饮/厨房", "后勤保障"}
        for item in work_items:
            if item.role in business_roles:
                counts["business_layer"] += 1
            elif item.workspace in support_workspaces:
                counts["support_layer"] += 1
            else:
                counts["system_capability_layer"] += 1
        return counts

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
                "刘芳羽不再用Excel排房": "requires_management_cutover",
                "刘晶不再手工做日结": "requires_management_cutover",
                "销售不再群里报数据": "requires_management_cutover",
                "石磊直接看OMS": "requires_management_cutover",
            },
        }

    def _persist_work_items(self, work_items: list[OperationalWorkItem]) -> None:
        self.operating_root.mkdir(parents=True, exist_ok=True)
        path = self.operating_root / "daily_work_items.jsonl"
        rows = [item.to_dict() for item in work_items]
        with path.open("a", encoding="utf-8") as handle:
            for item in rows:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.truth_store.append_work_items(rows)
