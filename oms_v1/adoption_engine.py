from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import AdoptionStatus, now_iso


ADOPTION_ROLES = ["刘芳羽", "刘晶", "销售", "尚丽娜"]

ROLE_TARGETS = {
    "刘芳羽": {
        "from": "Excel 排房",
        "to": "OMS 房态",
        "success_criteria": ["不再依赖 Excel 排房", "每天只看 OMS 房态", "排房决策只在 OMS 中完成"],
        "migration_tasks": ["确认 OMS 房态为默认入口", "将 Excel 排房表设为只读历史", "每日排房结果从 OMS 确认"],
    },
    "刘晶": {
        "from": "Excel 日结",
        "to": "OMS 财务流",
        "success_criteria": ["日结不再手工做", "待付款在 OMS 管理", "对账在 OMS 完成"],
        "migration_tasks": ["确认 OMS 财务工作台为默认入口", "将日结 Excel 设为只读历史", "在 OMS 内确认对账和待付款"],
    },
    "销售": {
        "from": "微信群提报",
        "to": "OMS 提报入口",
        "success_criteria": ["不再微信群报数据", "所有签约进 OMS", "合同、收款、客户自动结构化"],
        "migration_tasks": ["确认 OMS InputHub 为唯一提报入口", "微信群只保留提醒和异常沟通", "销售每天检查 OMS 提报状态"],
    },
    "尚丽娜": {
        "from": "人工安排",
        "to": "OMS 服务工作台",
        "success_criteria": ["入住流程自动进入 OMS", "服务排程在 OMS 内执行", "出馆流程系统化"],
        "migration_tasks": ["确认 OMS 服务工作台为默认入口", "入住任务从 OMS 接收", "服务安排和出馆流程在 OMS 内确认"],
    },
}


class AdoptionEngine:
    """Assess and guide organizational migration from old work habits to OMS."""

    def __init__(self, adoption_root: str | Path | None = None):
        self.adoption_root = Path(adoption_root or DEFAULT_LIVE_ROOT / "adoption")

    def build_adoption_stream(
        self,
        operational_stream: dict[str, Any],
        live_stream: dict[str, Any],
        governance_stream: dict[str, Any],
        *,
        bypass_events: list[dict[str, Any]] | None = None,
        manual_overrides: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        statuses = self.assess(operational_stream, live_stream, governance_stream, bypass_events or [], manual_overrides or [])
        self._persist(statuses)
        return {
            "schema_version": "oms.v1.adoption_stream",
            "input_id": operational_stream.get("input_id") or live_stream.get("input_id") or governance_stream.get("input_id"),
            "phase": "organizational_adoption",
            "goal": "从使用系统变成依赖系统",
            "flow": [
                "input",
                "parsed_json",
                "business_events",
                "recommendations",
                "execution_actions",
                "governance_decisions",
                "live_sync",
                "daily_operations",
                "organizational_adoption",
            ],
            "adoption": [status.to_dict() for status in statuses],
            "adoption_policy": {
                "replacement_mode": "默认迁移，不强制替代",
                "bypass_policy": "人可以绕开系统，但系统必须记录。",
                "manual_override_policy": "人工覆盖允许，但必须进入 manual_override_log。",
                "success_definition": "切换是行为变化，不是功能上线。",
            },
            "audit": {
                "created_at": now_iso(),
                "adoption_count": len(statuses),
                "adoption_root": str(self.adoption_root),
            },
        }

    def assess(
        self,
        operational_stream: dict[str, Any],
        live_stream: dict[str, Any],
        governance_stream: dict[str, Any],
        bypass_events: list[dict[str, Any]],
        manual_overrides: list[dict[str, Any]],
    ) -> list[AdoptionStatus]:
        work_items = operational_stream.get("work_items")
        sync_results = live_stream.get("sync_results")
        governance = governance_stream.get("governance")
        if work_items is None:
            raise ValueError("AdoptionEngine requires an OMSOperationalCore operational stream")
        if sync_results is None:
            raise ValueError("AdoptionEngine requires a LiveConnector live stream")
        if governance is None:
            raise ValueError("AdoptionEngine requires a GovernanceEngine governance stream")

        statuses: list[AdoptionStatus] = []
        for role in ADOPTION_ROLES:
            role_items = [item for item in work_items if item.get("role") == role]
            role_bypass = [event for event in bypass_events if event.get("role") == role]
            role_overrides = [event for event in manual_overrides if event.get("role") == role]
            statuses.append(self._status_for_role(role, role_items, sync_results, governance, role_bypass, role_overrides))
        return statuses

    def _status_for_role(
        self,
        role: str,
        work_items: list[dict[str, Any]],
        sync_results: list[dict[str, Any]],
        governance: list[dict[str, Any]],
        bypass_events: list[dict[str, Any]],
        manual_overrides: list[dict[str, Any]],
    ) -> AdoptionStatus:
        target = ROLE_TARGETS[role]
        blockers = self._blockers(role, work_items, sync_results, governance, bypass_events)
        adoption_status = self._adoption_status(work_items, blockers, bypass_events)
        risk_level = self._risk_level(adoption_status, blockers, bypass_events)
        return AdoptionStatus(
            role=role,
            adoption_status=adoption_status,
            blockers=blockers,
            migration_tasks=target["migration_tasks"],
            recommended_actions=self._recommended_actions(role, adoption_status, blockers),
            risk_level=risk_level,
            bypass_log=bypass_events,
            manual_override_log=manual_overrides,
            success_criteria=target["success_criteria"],
        )

    def _blockers(
        self,
        role: str,
        work_items: list[dict[str, Any]],
        sync_results: list[dict[str, Any]],
        governance: list[dict[str, Any]],
        bypass_events: list[dict[str, Any]],
    ) -> list[str]:
        blockers: list[str] = []
        if not work_items:
            blockers.append("当前输入未生成该岗位工作项，无法判断日常迁移状态。")
        if any(item.get("status") == "waiting_confirmation" for item in work_items):
            blockers.append("存在待人工确认事项，岗位尚未形成稳定闭环。")
        if any(item.get("status") == "ready_with_pending_sync" for item in work_items):
            blockers.append("存在外部系统 pending 同步，飞书/微信/API 授权或回写未完全打通。")
        if bypass_events:
            blockers.append("检测到绕过 OMS 的旧入口行为，需要记录并迁回默认路径。")
        if role == "刘晶" and any(item.get("confirmation_required") for item in work_items):
            blockers.append("财务对账/日结仍需人工确认，尚未达到全量依赖。")
        if role == "销售" and not any(item.get("workspace") == "销售提报入口" for item in work_items):
            blockers.append("本次未形成销售提报入口工作项。")
        return blockers

    def _adoption_status(self, work_items: list[dict[str, Any]], blockers: list[str], bypass_events: list[dict[str, Any]]) -> str:
        if not work_items:
            return "not_started"
        if bypass_events:
            return "partial"
        if not blockers and all(item.get("primary_entry") == "OMS" and item.get("status") == "ready" for item in work_items):
            return "full"
        if any(item.get("primary_entry") == "OMS" for item in work_items):
            return "active"
        return "partial"

    def _risk_level(self, adoption_status: str, blockers: list[str], bypass_events: list[dict[str, Any]]) -> str:
        if adoption_status == "not_started":
            return "high"
        if bypass_events:
            return "high"
        if len(blockers) >= 2:
            return "medium"
        if blockers:
            return "medium"
        return "low"

    def _recommended_actions(self, role: str, adoption_status: str, blockers: list[str]) -> list[str]:
        base = [f"由 石磊 明确 {role} 的 OMS 默认入口切换时间。"]
        if adoption_status in {"not_started", "partial"}:
            base.append(f"安排 {role} 用一日真实业务只走 OMS，旧入口只读或只输入。")
        if blockers:
            base.append("逐条处理 blockers，完成后再评估 full adoption。")
        if role == "销售":
            base.append("销售群只允许发提醒和异常，不再作为结构化提报入口。")
        if role == "刘芳羽":
            base.append("排房确认只在 OMS 房态工作台完成，Excel 作为历史备查。")
        if role == "刘晶":
            base.append("日结、待付款、对账统一在 OMS 财务工作台确认。")
        if role == "尚丽娜":
            base.append("入住、服务、出馆任务统一在 OMS 服务工作台确认。")
        return base

    def _persist(self, statuses: list[AdoptionStatus]) -> None:
        self.adoption_root.mkdir(parents=True, exist_ok=True)
        path = self.adoption_root / "adoption_status.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            for status in statuses:
                handle.write(json.dumps(status.to_dict(), ensure_ascii=False) + "\n")
