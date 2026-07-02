from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import RealityLockStatus, now_iso


LOCK_STATES = ["LOCKED", "UNLOCKED", "READONLY", "MIGRATION"]
FINAL_ARCHITECTURE = [
    "InputHub",
    "DataParser",
    "EventEngine",
    "DecisionEngine",
    "ExecutionEngine",
    "GovernanceEngine",
    "LiveConnector",
    "OMS_OperationalCore",
    "AdoptionEngine",
    "SystemSwitchController",
    "RealityLock",
]
TRACE_REQUIREMENTS = [
    "event trace",
    "decision trace",
    "execution trace",
    "governance trace",
    "adoption trace",
    "switch trace",
]
LOCKED_PRINCIPLES = [
    "OMS不再是项目，OMS等于企业运行方式本身。",
    "Excel / 微信 / 飞书 = 外围接口。",
    "OMS = 唯一事实解释系统。",
    "人 = 执行节点，系统 = 决策与结构节点。",
    "BOSS = 最终现实定义者。",
    "禁止新增阶段，禁止新增核心架构层，禁止改变链路顺序。",
]


class RealityLock:
    """Lock the final OMS architecture and its relationship to Huangjia reality."""

    def __init__(self, lock_root: str | Path | None = None):
        self.lock_root = Path(lock_root or DEFAULT_LIVE_ROOT / "reality_lock")

    def build_lock_stream(
        self,
        switch_stream: dict[str, Any],
        *,
        requested_lock_state: str | None = None,
        debug_unlock: bool = False,
    ) -> dict[str, Any]:
        status = self.evaluate(switch_stream, requested_lock_state=requested_lock_state, debug_unlock=debug_unlock)
        self._persist(status)
        return {
            "schema_version": "oms.v1.reality_lock_stream",
            "input_id": switch_stream.get("input_id"),
            "phase": "operating_reality_lock",
            "lock": status.to_dict(),
            "audit": {
                "created_at": now_iso(),
                "lock_root": str(self.lock_root),
                "allowed_lock_states": LOCK_STATES,
                "main_architecture_closed": True,
            },
        }

    def evaluate(
        self,
        switch_stream: dict[str, Any],
        *,
        requested_lock_state: str | None,
        debug_unlock: bool,
    ) -> RealityLockStatus:
        switch = switch_stream.get("switch")
        if switch is None:
            raise ValueError("RealityLock requires a SystemSwitchController switch stream")
        switch_state = switch.get("switch_state")
        blockers = list(switch.get("blockers") or [])
        role_blockers = [
            f"{item.get('role')} 未达到切换完成：{'; '.join(item.get('blockers') or [])}"
            for item in switch.get("role_switches", [])
            if not item.get("switch_ready")
        ]
        blockers.extend([blocker for blocker in role_blockers if blocker.strip()])

        lock_state = self._lock_state(switch_state, blockers, requested_lock_state, debug_unlock)
        return RealityLockStatus(
            lock_state=lock_state,
            reality_binding={
                "现实（凰家）": "业务事实和最终管理判断",
                "OMS": "唯一事实解释系统" if lock_state == "LOCKED" else "目标事实解释系统",
                "执行层": "六月 / 刘姐 / 销售 / 娜娜 / BOSS",
            },
            fixed_architecture=FINAL_ARCHITECTURE,
            trace_requirements=TRACE_REQUIREMENTS,
            locked_principles=LOCKED_PRINCIPLES,
            allowed_change_scope="仅允许子模块扩展；禁止新增核心阶段、核心架构层或改变主链路顺序。",
            blockers=blockers,
            switch_state=switch_state,
            recommended_actions=self._recommended_actions(lock_state, switch_state, blockers),
        )

    def _lock_state(
        self,
        switch_state: str,
        blockers: list[str],
        requested_lock_state: str | None,
        debug_unlock: bool,
    ) -> str:
        if debug_unlock:
            return "UNLOCKED"
        if requested_lock_state and requested_lock_state not in LOCK_STATES:
            raise ValueError(f"Unknown lock state: {requested_lock_state}")
        if requested_lock_state == "READONLY":
            return "READONLY"
        if switch_state == "FULL_OPERATING" and not blockers:
            return "LOCKED"
        if switch_state in {"SOFT_SWITCH", "HARD_SWITCH"}:
            return "MIGRATION"
        return "READONLY"

    def _recommended_actions(self, lock_state: str, switch_state: str, blockers: list[str]) -> list[str]:
        if lock_state == "LOCKED":
            return ["保持主架构冻结；后续需求全部进入子模块设计。", "持续检查所有 trace 是否完整。"]
        if lock_state == "MIGRATION":
            return ["继续清除切换 blockers，直到 SystemSwitchController 达到 FULL_OPERATING。", "禁止新增核心阶段，迁移问题用子模块解决。"]
        if lock_state == "READONLY":
            return ["保持观察模式，等待 BOSS 授权切换。", "不允许以 READONLY 状态替代真实运营。"]
        return ["仅用于调试；调试结束后必须回到 READONLY/MIGRATION/LOCKED。"]

    def _persist(self, status: RealityLockStatus) -> None:
        self.lock_root.mkdir(parents=True, exist_ok=True)
        path = self.lock_root / "reality_lock_status.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(status.to_dict(), ensure_ascii=False) + "\n")
