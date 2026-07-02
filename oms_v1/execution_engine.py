from __future__ import annotations

from typing import Any

from .schemas import ExecutionAction, now_iso


FINAL_REVIEW_ROLES = ["BOSS", "六月", "刘姐", "娜娜"]


class ExecutionEngine:
    """Convert decisions into reversible execution actions."""

    def build_execution_stream(self, decision_stream: dict[str, Any]) -> dict[str, Any]:
        actions = self.execute(decision_stream)
        return {
            "schema_version": "oms.v1.execution_stream",
            "input_id": decision_stream.get("input_id"),
            "flow": ["input", "parsed_json", "business_events", "recommendations", "execution_actions"],
            "actions": [action.to_dict() for action in actions],
            "audit": {
                "created_at": now_iso(),
                "action_count": len(actions),
                "requires_decision_stream": True,
                "direct_event_execution_allowed": False,
                "human_final_review_required": True,
                "execution_scope": "生成可回滚动作记录；不直接修改真实业务源表。",
            },
        }

    def execute(self, decision_stream: dict[str, Any]) -> list[ExecutionAction]:
        decisions = decision_stream.get("decisions")
        if decisions is None:
            raise ValueError("ExecutionEngine requires a DecisionEngine decision stream")

        actions: list[ExecutionAction] = []
        for decision in decisions:
            actions.append(self._action_for_decision(decision))
        return actions

    def _action_for_decision(self, decision: dict[str, Any]) -> ExecutionAction:
        decision_type = decision.get("decision_type", "")
        mapping = self._mapping(decision_type)
        status = self._status(decision, mapping["status"])
        result = self._result(decision, mapping["result"], status)
        return ExecutionAction(
            action_type=mapping["action_type"],
            target_module=mapping["target_module"],
            execution_result=result,
            status=status,
            timestamp=now_iso(),
            rollback_supported=True,
            decision_id=decision.get("decision_id"),
            source_decision_type=decision_type,
            rollback_plan={
                "method": mapping["rollback"],
                "requires_operator": True,
                "allowed_roles": self._override_roles(decision),
            },
            override_roles=self._override_roles(decision),
            execution_payload={
                "source_event_id": decision.get("event_id"),
                "recommended_action": decision.get("recommended_action"),
                "priority": decision.get("priority"),
                "risk_level": decision.get("risk_level"),
                "reason": decision.get("reason"),
            },
        )

    def _mapping(self, decision_type: str) -> dict[str, str]:
        mappings = {
            "sales_to_operations": {
                "action_type": "create_sales_operation_followup",
                "target_module": "sales_module",
                "status": "success",
                "result": "已生成销售转运营闭环跟进记录，等待财务、房态、服务岗位确认。",
                "rollback": "删除销售转运营跟进记录，并恢复对应事件为未执行状态。",
            },
            "room_assignment": {
                "action_type": "generate_room_assignment_plan",
                "target_module": "room_status_module",
                "status": "pending",
                "result": "已生成排房/入住计划草案，等待六月或BOSS终审后写入正式房态。",
                "rollback": "撤销排房计划草案，释放预占房态，不影响正式房态。",
            },
            "room_risk": {
                "action_type": "mark_oversell_risk",
                "target_module": "room_status_module",
                "status": "success",
                "result": "已生成超卖/满房风险标记和提醒记录。",
                "rollback": "关闭风险标记，保留撤销审计记录。",
            },
            "room_scheduling": {
                "action_type": "generate_room_adjustment_task",
                "target_module": "room_status_module",
                "status": "pending",
                "result": "已生成调房/倒房期调整任务，等待六月确认。",
                "rollback": "取消调房/倒房任务，恢复原计划状态。",
            },
            "room_exception": {
                "action_type": "generate_room_exception_task",
                "target_module": "room_status_module",
                "status": "pending",
                "result": "已生成劝退/居家服务异常处理任务，等待跨岗位终审。",
                "rollback": "取消异常处理任务，并解除相关岗位待办。",
            },
            "finance_reconciliation": {
                "action_type": "generate_reconciliation_task",
                "target_module": "finance_module",
                "status": "success",
                "result": "已生成收款对账任务，等待刘姐核对合同、客户和到账记录。",
                "rollback": "关闭对账任务，恢复为未生成对账状态。",
            },
            "payment_required": {
                "action_type": "create_payment_todo",
                "target_module": "finance_module",
                "status": "pending",
                "result": "已生成待付款/待报销复核项，付款前必须人工确认。",
                "rollback": "取消待付款/待报销复核项，保留取消原因。",
            },
            "service_amount_split": {
                "action_type": "generate_service_amount_split_task",
                "target_module": "finance_module",
                "status": "pending",
                "result": "已生成服务金额拆分复核任务，等待刘姐按凰家口径确认。",
                "rollback": "撤销服务金额拆分任务，不写入正式财务口径。",
            },
            "finance_risk": {
                "action_type": "flag_financial_risk",
                "target_module": "finance_module",
                "status": "success",
                "result": "已标记财务风险，付款或入账前需要刘姐/BOSS复核。",
                "rollback": "解除财务风险标记，保留解除审计记录。",
            },
            "service_preparation": {
                "action_type": "create_checkin_preparation_task",
                "target_module": "service_module",
                "status": "success",
                "result": "已生成入住准备任务，提醒娜娜协调管家、产护和厨房。",
                "rollback": "取消入住准备任务，恢复服务事项为待判断。",
            },
            "service_risk": {
                "action_type": "create_service_risk_task",
                "target_module": "service_module",
                "status": "pending",
                "result": "已生成服务异常/延迟风险处理任务，等待娜娜或BOSS确认。",
                "rollback": "取消服务风险任务，解除相关提醒。",
            },
            "service_coordination": {
                "action_type": "create_service_coordination_task",
                "target_module": "service_module",
                "status": "success",
                "result": "已生成产护/厨房/服务协同任务。",
                "rollback": "取消服务协同任务，并撤回岗位提醒。",
            },
            "service_followup": {
                "action_type": "create_service_followup_task",
                "target_module": "service_module",
                "status": "success",
                "result": "已生成服务备注跟进任务，等待娜娜复核。",
                "rollback": "取消服务跟进任务，恢复为未跟进备注。",
            },
        }
        return mappings.get(
            decision_type,
            {
                "action_type": "create_manual_review_task",
                "target_module": "operations_module",
                "status": "pending",
                "result": "已生成通用人工复核任务，当前决策类型尚未绑定专用执行动作。",
                "rollback": "取消通用人工复核任务。",
            },
        )

    def _status(self, decision: dict[str, Any], default_status: str) -> str:
        if decision.get("risk_level") == "high" and default_status == "success":
            return "pending"
        return default_status

    def _result(self, decision: dict[str, Any], result: str, status: str) -> str:
        if status == "pending":
            return f"{result} 当前状态为待人工终审。"
        return result

    def _override_roles(self, decision: dict[str, Any]) -> list[str]:
        roles = list(decision.get("override_roles") or [])
        for role in FINAL_REVIEW_ROLES:
            if role not in roles:
                roles.append(role)
        return roles
