from __future__ import annotations

from typing import Any

from .schemas import GovernanceDecision, now_iso


ROLE_PERMISSIONS = {
    "BOSS": {
        "execute": ["all"],
        "approve": ["all"],
        "override": ["all"],
    },
    "六月": {
        "execute": ["room_status_module"],
        "approve": ["room_status_module"],
        "override": ["room_status_module"],
    },
    "刘姐": {
        "execute": ["finance_module"],
        "approve": ["finance_module"],
        "override": ["finance_module"],
    },
    "娜娜": {
        "execute": ["service_module"],
        "approve": ["service_module"],
        "override": ["service_module"],
    },
    "系统": {
        "execute": ["low_risk_automation"],
        "approve": [],
        "override": [],
    },
}


class GovernanceEngine:
    """Gate execution actions through Huangjia role and approval rules."""

    def build_governance_stream(self, execution_stream: dict[str, Any]) -> dict[str, Any]:
        decisions = self.review(execution_stream)
        return {
            "schema_version": "oms.v1.governance_stream",
            "input_id": execution_stream.get("input_id"),
            "flow": [
                "input",
                "parsed_json",
                "business_events",
                "recommendations",
                "execution_actions",
                "governance_decisions",
            ],
            "governance": [decision.to_dict() for decision in decisions],
            "roles": ROLE_PERMISSIONS,
            "audit": {
                "created_at": now_iso(),
                "governance_count": len(decisions),
                "requires_execution_stream": True,
                "direct_high_risk_execution_allowed": False,
                "boss_final_override": True,
                "controlled_autonomy": True,
            },
        }

    def review(self, execution_stream: dict[str, Any]) -> list[GovernanceDecision]:
        actions = execution_stream.get("actions")
        if actions is None:
            raise ValueError("GovernanceEngine requires an ExecutionEngine execution stream")

        decisions: list[GovernanceDecision] = []
        for action in actions:
            decisions.append(self._review_action(action))
        return decisions

    def _review_action(self, action: dict[str, Any]) -> GovernanceDecision:
        policy = self._policy(action)
        allowed = policy["risk_level"] == "low"
        approval_required = not allowed
        required_roles = policy["required_roles"] if approval_required else ["系统"]
        return GovernanceDecision(
            action_id=action.get("action_id", ""),
            allowed=allowed,
            approval_required=approval_required,
            required_roles=required_roles,
            risk_level=policy["risk_level"],
            reason=self._reason(action, policy, approval_required),
            override_policy=self._override_policy(policy),
            action_type=action.get("action_type"),
            target_module=action.get("target_module"),
            responsibility_chain={
                "approved_by": [] if approval_required else ["系统"],
                "executed_by": ["系统"] if allowed else [],
                "overridden_by": [],
                "final_override_role": "BOSS",
                "source_action_status": action.get("status"),
            },
        )

    def _policy(self, action: dict[str, Any]) -> dict[str, Any]:
        action_type = action.get("action_type", "")
        target_module = action.get("target_module", "")
        payload_risk = (action.get("execution_payload") or {}).get("risk_level")

        policies = {
            "create_sales_operation_followup": ("low", ["系统"]),
            "generate_room_assignment_plan": ("low", ["系统"]),
            "create_checkin_preparation_task": ("low", ["系统"]),
            "create_service_followup_task": ("low", ["系统"]),
            "create_service_coordination_task": ("medium", ["娜娜"]),
            "create_admin_procurement_task": ("low", ["系统"]),
            "create_maternity_care_support_task": ("low", ["系统"]),
            "create_kitchen_support_task": ("low", ["系统"]),
            "create_logistics_support_task": ("low", ["系统"]),
            "generate_reconciliation_task": ("medium", ["刘姐"]),
            "create_payment_todo": ("medium", ["刘姐"]),
            "generate_room_adjustment_task": ("medium", ["六月"]),
            "generate_service_amount_split_task": ("medium", ["刘姐"]),
            "create_service_risk_task": ("high", ["娜娜", "BOSS"]),
            "flag_financial_risk": ("high", ["刘姐", "BOSS"]),
            "mark_oversell_risk": ("high", ["六月", "BOSS"]),
            "generate_room_exception_task": ("critical", ["BOSS"]),
            "create_manual_review_task": ("medium", self._module_owner_roles(target_module)),
        }

        risk_level, roles = policies.get(action_type, ("medium", self._module_owner_roles(target_module)))
        if payload_risk == "high" and risk_level in {"low", "medium"}:
            risk_level = "high"
            roles = self._ensure_boss(roles)
        if "财务入账" in str(action.get("execution_result", "")):
            risk_level = "critical"
            roles = ["BOSS", "刘姐"]
        return {"risk_level": risk_level, "required_roles": roles}

    def _reason(self, action: dict[str, Any], policy: dict[str, Any], approval_required: bool) -> str:
        action_type = action.get("action_type", "")
        risk_level = policy["risk_level"]
        if not approval_required:
            return f"{action_type} 属于低风险任务/草稿/提醒类动作，系统可自动放行，但仍保留责任链和回滚记录。"
        return f"{action_type} 被判定为 {risk_level} 风险动作，系统不能直接执行，必须由 {', '.join(policy['required_roles'])} 审批。"

    def _override_policy(self, policy: dict[str, Any]) -> str:
        risk_level = policy["risk_level"]
        if risk_level == "low":
            return "系统可执行；岗位负责人和BOSS可覆盖。"
        if risk_level == "medium":
            return "岗位负责人审批后执行；BOSS可最终覆盖。"
        if risk_level == "high":
            return "岗位负责人和BOSS共同确认；系统不得直接执行。"
        return "BOSS终审；未获BOSS确认前系统不得执行。"

    def _module_owner_roles(self, target_module: str) -> list[str]:
        if target_module == "room_status_module":
            return ["六月"]
        if target_module == "finance_module":
            return ["刘姐"]
        if target_module == "service_module":
            return ["娜娜"]
        if target_module == "sales_module":
            return ["BOSS"]
        return ["BOSS"]

    def _ensure_boss(self, roles: list[str]) -> list[str]:
        next_roles = list(roles)
        if "BOSS" not in next_roles:
            next_roles.append("BOSS")
        return next_roles
