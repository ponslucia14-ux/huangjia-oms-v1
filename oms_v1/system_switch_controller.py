from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adoption_engine import ADOPTION_ROLES, ROLE_TARGETS
from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import SystemSwitchStatus, now_iso


SWITCH_STATES = ["PRE_SWITCH", "SOFT_SWITCH", "HARD_SWITCH", "FULL_OPERATING"]

ROLE_SWITCH_ACTIONS = {
    "刘芳羽": {
        "target_mode": "OMS唯一排房系统",
        "hard_switch_actions": ["Excel停止作为排房工具", "OMS成为唯一排房入口", "所有房态决策进入系统"],
    },
    "刘晶": {
        "target_mode": "OMS唯一财务系统",
        "hard_switch_actions": ["日结只在OMS完成", "对账只在OMS完成", "待付款只在OMS生成", "Excel降级为历史档案"],
    },
    "销售": {
        "target_mode": "OMS唯一签约入口",
        "hard_switch_actions": ["微信群不再作为提报系统", "所有合同/收款必须进入OMS", "自动结构化客户数据"],
    },
    "尚丽娜": {
        "target_mode": "OMS唯一服务调度系统",
        "hard_switch_actions": ["入住任务自动进入OMS", "服务安排在OMS执行", "出馆流程系统化"],
    },
}


class SystemSwitchController:
    """Control OMS cutover from tool mode to the single operating system."""

    def __init__(self, switch_root: str | Path | None = None):
        self.switch_root = Path(switch_root or DEFAULT_LIVE_ROOT / "system_switch")

    def build_switch_stream(
        self,
        adoption_stream: dict[str, Any],
        *,
        requested_state: str = "SOFT_SWITCH",
        boss_authorized: bool = False,
        bypass_events: list[dict[str, Any]] | None = None,
        manual_overrides: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        status = self.evaluate(
            adoption_stream,
            requested_state=requested_state,
            boss_authorized=boss_authorized,
            bypass_events=bypass_events or [],
            manual_overrides=manual_overrides or [],
        )
        self._persist(status)
        return {
            "schema_version": "oms.v1.system_switch_stream",
            "input_id": adoption_stream.get("input_id"),
            "phase": "full_operational_switch",
            "requested_state": requested_state,
            "boss_authorized": boss_authorized,
            "switch": status.to_dict(),
            "audit": {
                "created_at": now_iso(),
                "switch_root": str(self.switch_root),
                "allowed_states": SWITCH_STATES,
            },
        }

    def evaluate(
        self,
        adoption_stream: dict[str, Any],
        *,
        requested_state: str,
        boss_authorized: bool,
        bypass_events: list[dict[str, Any]],
        manual_overrides: list[dict[str, Any]],
    ) -> SystemSwitchStatus:
        if requested_state not in SWITCH_STATES:
            raise ValueError(f"Unknown switch state: {requested_state}")
        adoption = adoption_stream.get("adoption")
        if adoption is None:
            raise ValueError("SystemSwitchController requires an AdoptionEngine adoption stream")

        adoption_by_role = {item.get("role"): item for item in adoption}
        role_switches = [self._role_switch(role, adoption_by_role.get(role)) for role in ADOPTION_ROLES]
        blockers = self._blockers(role_switches, requested_state, boss_authorized, bypass_events)
        switch_state = self._effective_state(requested_state, role_switches, blockers, boss_authorized)
        return SystemSwitchStatus(
            switch_state=switch_state,
            oms_truth_role="OMS = 现在" if switch_state in {"HARD_SWITCH", "FULL_OPERATING"} else "OMS = 默认迁移目标",
            legacy_system_role={
                "Excel": "历史" if switch_state in {"HARD_SWITCH", "FULL_OPERATING"} else "并行历史/迁移来源",
                "微信": "历史/输入源" if switch_state in {"HARD_SWITCH", "FULL_OPERATING"} else "输入源/并行沟通",
                "旧系统": "历史" if switch_state in {"HARD_SWITCH", "FULL_OPERATING"} else "迁移来源",
            },
            role_switches=role_switches,
            blockers=blockers,
            required_authorization=[] if boss_authorized else ["石磊"],
            bypass_log=bypass_events,
            manual_override_log=manual_overrides,
            success_criteria={role: ROLE_TARGETS[role]["success_criteria"] for role in ADOPTION_ROLES},
            recommended_actions=self._recommended_actions(switch_state, role_switches, blockers, boss_authorized),
        )

    def _role_switch(self, role: str, adoption: dict[str, Any] | None) -> dict[str, Any]:
        config = ROLE_SWITCH_ACTIONS[role]
        if adoption is None:
            adoption_status = "not_started"
            blockers = ["缺少该岗位 adoption 状态。"]
            risk_level = "high"
        else:
            adoption_status = adoption.get("adoption_status", "not_started")
            blockers = adoption.get("blockers", [])
            risk_level = adoption.get("risk_level", "high")
        return {
            "role": role,
            "target_mode": config["target_mode"],
            "adoption_status": adoption_status,
            "switch_ready": adoption_status == "full" and not blockers,
            "hard_switch_actions": config["hard_switch_actions"],
            "blockers": blockers,
            "risk_level": risk_level,
        }

    def _blockers(
        self,
        role_switches: list[dict[str, Any]],
        requested_state: str,
        boss_authorized: bool,
        bypass_events: list[dict[str, Any]],
    ) -> list[str]:
        blockers: list[str] = []
        if requested_state in {"HARD_SWITCH", "FULL_OPERATING"} and not boss_authorized:
            blockers.append("HARD_SWITCH/FULL_OPERATING 需要 石磊 明确授权。")
        not_ready = [item["role"] for item in role_switches if not item["switch_ready"]]
        if requested_state == "FULL_OPERATING" and not_ready:
            blockers.append(f"以下岗位尚未达到 full adoption：{', '.join(not_ready)}。")
        if bypass_events:
            blockers.append("存在绕行旧系统行为，不能判定为完全运行。")
        return blockers

    def _effective_state(
        self,
        requested_state: str,
        role_switches: list[dict[str, Any]],
        blockers: list[str],
        boss_authorized: bool,
    ) -> str:
        if requested_state == "PRE_SWITCH":
            return "PRE_SWITCH"
        if requested_state == "SOFT_SWITCH":
            return "SOFT_SWITCH"
        all_ready = all(item["switch_ready"] for item in role_switches)
        if requested_state == "HARD_SWITCH":
            return "HARD_SWITCH" if boss_authorized else "SOFT_SWITCH"
        if requested_state == "FULL_OPERATING":
            return "FULL_OPERATING" if boss_authorized and all_ready and not blockers else "HARD_SWITCH" if boss_authorized else "SOFT_SWITCH"
        return "PRE_SWITCH"

    def _recommended_actions(
        self,
        switch_state: str,
        role_switches: list[dict[str, Any]],
        blockers: list[str],
        boss_authorized: bool,
    ) -> list[str]:
        actions: list[str] = []
        if not boss_authorized:
            actions.append("由 石磊 明确是否进入 HARD_SWITCH 或 FULL_OPERATING。")
        if blockers:
            actions.append("先清除 blockers，再提升切换状态。")
        for item in role_switches:
            if not item["switch_ready"]:
                actions.append(f"{item['role']} 继续执行迁移任务，直到 adoption_status=full。")
        if switch_state == "HARD_SWITCH":
            actions.append("开始冻结 Excel/微信群业务入口，只保留历史和输入源。")
        if switch_state == "FULL_OPERATING":
            actions.append("每日运营以 OMS 为唯一运行系统，并持续监控 bypass_log。")
        return actions

    def _persist(self, status: SystemSwitchStatus) -> None:
        self.switch_root.mkdir(parents=True, exist_ok=True)
        path = self.switch_root / "system_switch_status.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(status.to_dict(), ensure_ascii=False) + "\n")
