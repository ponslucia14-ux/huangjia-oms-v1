from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .schemas import ExecutionAction, new_id, now_iso
from .scheduling_approval import APPROVAL_APPROVED


EXECUTION_ENGINE_SCHEMA_VERSION = "oms.v1.execution_engine"

EXECUTION_COMPLETED = "completed"
EXECUTION_FAILED = "failed"


@dataclass(frozen=True)
class ExecutionRequest:
    """P15 request to execute an approved scheduling decision in simulation mode."""

    decision_result: dict[str, Any]
    approval_workflow: dict[str, Any]
    requester_emp_id: str
    reason: str
    request_id: str = field(default_factory=lambda: new_id("execreq"))
    command_type: str = "simulate_scheduling_execution"
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=now_iso)
    schema_version: str = EXECUTION_ENGINE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.decision_result:
            raise ValueError("decision_result is required.")
        if not self.approval_workflow:
            raise ValueError("approval_workflow is required.")
        if not self.requester_emp_id.strip():
            raise ValueError("requester_emp_id is required.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        if not self.command_type.strip():
            raise ValueError("command_type is required.")
        object.__setattr__(self, "decision_result", dict(self.decision_result))
        object.__setattr__(self, "approval_workflow", dict(self.approval_workflow))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionCommand:
    """Simulation command produced after approval authorization checks."""

    request_id: str
    decision_id: str
    approval_id: str
    command_type: str
    target_type: str = "scheduling"
    command_id: str = field(default_factory=lambda: new_id("execcmd"))
    payload: dict[str, Any] = field(default_factory=dict)
    simulation_only: bool = True
    mutates_business_state: bool = False
    timestamp: str = field(default_factory=now_iso)
    schema_version: str = EXECUTION_ENGINE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id is required.")
        if not self.decision_id.strip():
            raise ValueError("decision_id is required.")
        if not self.approval_id.strip():
            raise ValueError("approval_id is required.")
        if not self.command_type.strip():
            raise ValueError("command_type is required.")
        if not self.simulation_only:
            raise ValueError("P15 ExecutionCommand must be simulation_only.")
        if self.mutates_business_state:
            raise ValueError("P15 ExecutionCommand cannot mutate business state.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionResult:
    """P15 execution result. It records simulation outcome without resource mutation."""

    request: dict[str, Any]
    status: str
    execution_authorized: bool
    command: dict[str, Any] | None = None
    result_id: str = field(default_factory=lambda: new_id("execres"))
    simulated_actions: tuple[dict[str, Any], ...] = ()
    failure_reasons: tuple[dict[str, Any], ...] = ()
    warnings: tuple[dict[str, Any], ...] = ()
    mutates_business_state: bool = False
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = EXECUTION_ENGINE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.status not in {EXECUTION_COMPLETED, EXECUTION_FAILED}:
            raise ValueError("status must be completed or failed.")
        if self.mutates_business_state:
            raise ValueError("ExecutionResult cannot mutate business state in P15.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["simulated_actions"] = [dict(item) for item in self.simulated_actions]
        payload["failure_reasons"] = [dict(item) for item in self.failure_reasons]
        payload["warnings"] = [dict(item) for item in self.warnings]
        payload["audit_records"] = [dict(item) for item in self.audit_records]
        payload["events"] = [dict(item) for item in self.events]
        return payload


class ExecutionEngine:
    """Convert decisions into reversible actions and simulate approved scheduling execution."""

    def __init__(
        self,
        master_data: OMSMasterData | None = None,
        *,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
    ):
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self._execution_results: dict[str, ExecutionResult] = {}

    def build_execution_stream(self, decision_stream: dict[str, Any]) -> dict[str, Any]:
        actions = self._legacy_execute(decision_stream)
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

    def execute(self, payload: ExecutionRequest | dict[str, Any]) -> dict[str, Any] | list[ExecutionAction]:
        if self._is_p15_execution_request(payload):
            return self._execute_authorized(payload)
        if isinstance(payload, ExecutionRequest):
            return self._execute_authorized(payload)
        return self._legacy_execute(payload)

    def _legacy_execute(self, decision_stream: dict[str, Any]) -> list[ExecutionAction]:
        decisions = decision_stream.get("decisions")
        if decisions is None:
            raise ValueError("ExecutionEngine requires a DecisionEngine decision stream")

        actions: list[ExecutionAction] = []
        for decision in decisions:
            actions.append(self._action_for_decision(decision))
        return actions

    def _execute_authorized(self, request: ExecutionRequest | dict[str, Any]) -> dict[str, Any]:
        execution_request = request if isinstance(request, ExecutionRequest) else ExecutionRequest(**request)
        actor = self.master_data.employee_by_emp(execution_request.requester_emp_id)
        audit_records: list[dict[str, Any]] = [
            self._audit(
                action="execution.request",
                request=execution_request,
                actor_name=actor.name,
                result="PENDING",
                metadata={
                    "execution_authorized": False,
                    "simulation_only": True,
                },
            )
        ]
        events: list[dict[str, Any]] = [
            self._event(
                event_type="execution.requested",
                request=execution_request,
                actor_name=actor.name,
                payload={
                    "request_id": execution_request.request_id,
                    "execution_authorized": False,
                    "simulation_only": True,
                },
            )
        ]

        failure_reasons = tuple(self._authorization_failures(execution_request))
        if failure_reasons:
            audit_records.append(
                self._audit(
                    action="execution.fail",
                    request=execution_request,
                    actor_name=actor.name,
                    result=EXECUTION_FAILED,
                    metadata={
                        "execution_authorized": False,
                        "failure_reason_count": len(failure_reasons),
                        "simulation_only": True,
                    },
                )
            )
            events.append(
                self._event(
                    event_type="execution.failed",
                    request=execution_request,
                    actor_name=actor.name,
                    payload={
                        "request_id": execution_request.request_id,
                        "status": EXECUTION_FAILED,
                        "execution_authorized": False,
                        "failure_reasons": list(failure_reasons),
                        "simulation_only": True,
                    },
                )
            )
            result = ExecutionResult(
                request=execution_request.to_dict(),
                status=EXECUTION_FAILED,
                execution_authorized=False,
                failure_reasons=failure_reasons,
                mutates_business_state=False,
                audit_records=tuple(audit_records),
                events=tuple(events),
            )
            self._execution_results[result.result_id] = result
            return result.to_dict()

        decision_id = _decision_id(execution_request.decision_result)
        approval_id = str(execution_request.approval_workflow.get("approval_id") or "")
        command = ExecutionCommand(
            request_id=execution_request.request_id,
            decision_id=decision_id,
            approval_id=approval_id,
            command_type=execution_request.command_type,
            payload={
                "decision_result": dict(execution_request.decision_result),
                "approval_workflow": dict(execution_request.approval_workflow),
                "recommendations": list(execution_request.decision_result.get("ranked_recommendations") or []),
                "simulation_only": True,
            },
            simulation_only=True,
            mutates_business_state=False,
        )
        simulated_actions = tuple(self._simulated_actions(execution_request, command))
        audit_records.append(
            self._audit(
                action="execution.complete",
                request=execution_request,
                actor_name=actor.name,
                result=EXECUTION_COMPLETED,
                metadata={
                    "execution_authorized": True,
                    "command_id": command.command_id,
                    "simulated_action_count": len(simulated_actions),
                    "simulation_only": True,
                },
            )
        )
        events.append(
            self._event(
                event_type="execution.completed",
                request=execution_request,
                actor_name=actor.name,
                payload={
                    "request_id": execution_request.request_id,
                    "status": EXECUTION_COMPLETED,
                    "execution_authorized": True,
                    "command_id": command.command_id,
                    "simulated_actions": list(simulated_actions),
                    "simulation_only": True,
                },
            )
        )
        result = ExecutionResult(
            request=execution_request.to_dict(),
            status=EXECUTION_COMPLETED,
            execution_authorized=True,
            command=command.to_dict(),
            simulated_actions=simulated_actions,
            warnings=(
                {
                    "code": "simulation_only",
                    "message": "P15 records authorized simulation only; no Room, Stay, or Caregiver state is modified.",
                    "severity": "info",
                },
            ),
            mutates_business_state=False,
            audit_records=tuple(audit_records),
            events=tuple(events),
        )
        self._execution_results[result.result_id] = result
        return result.to_dict()

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
        final_authority = self.master_data.final_authority_name()
        room_owner = self.master_data.module_owner("room_status_module")
        finance_owner = self.master_data.module_owner("finance_module")
        service_owner = self.master_data.module_owner("service_module")
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
                "result": f"已生成排房/入住计划草案，等待{room_owner}或{final_authority}终审后写入正式房态。",
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
                "result": f"已生成调房/倒房期调整任务，等待{room_owner}确认。",
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
                "result": f"已生成收款对账任务，等待{finance_owner}核对合同、客户和到账记录。",
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
                "result": f"已生成服务金额拆分复核任务，等待{finance_owner}按凰家口径确认。",
                "rollback": "撤销服务金额拆分任务，不写入正式财务口径。",
            },
            "finance_risk": {
                "action_type": "flag_financial_risk",
                "target_module": "finance_module",
                "status": "success",
                "result": f"已标记财务风险，付款或入账前需要{finance_owner}/{final_authority}复核。",
                "rollback": "解除财务风险标记，保留解除审计记录。",
            },
            "service_preparation": {
                "action_type": "create_checkin_preparation_task",
                "target_module": "service_module",
                "status": "success",
                "result": f"已生成入住准备任务，提醒{service_owner}协调管家、产护和厨房。",
                "rollback": "取消入住准备任务，恢复服务事项为待判断。",
            },
            "service_risk": {
                "action_type": "create_service_risk_task",
                "target_module": "service_module",
                "status": "pending",
                "result": f"已生成服务异常/延迟风险处理任务，等待{service_owner}或{final_authority}确认。",
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
                "result": f"已生成服务备注跟进任务，等待{service_owner}复核。",
                "rollback": "取消服务跟进任务，恢复为未跟进备注。",
            },
            "support_admin_procurement": {
                "action_type": "create_admin_procurement_task",
                "target_module": "support_layer",
                "status": "success",
                "result": "已生成行政采购支撑任务，覆盖采购申请、物资补给和消耗品补充。",
                "rollback": "取消行政采购支撑任务，并撤回物资补给提醒。",
            },
            "support_maternity_care": {
                "action_type": "create_maternity_care_support_task",
                "target_module": "support_layer",
                "status": "success",
                "result": "已生成产护支持任务，覆盖人员调度、护理资源分配和临时支援。",
                "rollback": "取消产护支持任务，并撤回护理资源调度提醒。",
            },
            "support_kitchen": {
                "action_type": "create_kitchen_support_task",
                "target_module": "support_layer",
                "status": "success",
                "result": "已生成餐饮/厨房支撑任务，覆盖餐食准备、特殊餐需求和备餐计划。",
                "rollback": "取消餐饮/厨房支撑任务，并撤回备餐提醒。",
            },
            "support_logistics": {
                "action_type": "create_logistics_support_task",
                "target_module": "support_layer",
                "status": "success",
                "result": "已生成后勤保障任务，覆盖房间清理、设备维护和物资配送。",
                "rollback": "取消后勤保障任务，并撤回房间/设备/配送提醒。",
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
        for role in self.master_data.names_for_roles(["ROLE_OWNER", "ROLE_STORE_MANAGER", "ROLE_CASHIER", "ROLE_BUTLER"]):
            if role not in roles:
                roles.append(role)
        return roles

    @staticmethod
    def _is_p15_execution_request(payload: Any) -> bool:
        if isinstance(payload, ExecutionRequest):
            return True
        if not isinstance(payload, dict):
            return False
        return "decision_result" in payload or "approval_workflow" in payload

    @staticmethod
    def _authorization_failures(request: ExecutionRequest) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []
        decision_id = _decision_id(request.decision_result)
        approval_decision_id = _approval_decision_id(request.approval_workflow)
        approval_status = str(request.approval_workflow.get("current_status") or request.approval_workflow.get("decision_status") or "")
        execution_authorized = bool(request.approval_workflow.get("execution_authorized"))

        if not decision_id:
            failures.append(
                {
                    "code": "missing_decision_result",
                    "message": "Decision Result is required before execution.",
                    "severity": "error",
                }
            )
        if approval_status != APPROVAL_APPROVED:
            failures.append(
                {
                    "code": "approval_not_approved",
                    "message": f"Approval Status must be APPROVED; current status is {approval_status or 'UNKNOWN'}.",
                    "severity": "error",
                }
            )
        if not execution_authorized:
            failures.append(
                {
                    "code": "execution_not_authorized",
                    "message": "execution_authorized must be true before execution.",
                    "severity": "error",
                }
            )
        if decision_id and approval_decision_id and decision_id != approval_decision_id:
            failures.append(
                {
                    "code": "decision_approval_mismatch",
                    "message": "Decision Result and Approval Workflow refer to different decision IDs.",
                    "severity": "error",
                    "decision_id": decision_id,
                    "approval_decision_id": approval_decision_id,
                }
            )
        return failures

    @staticmethod
    def _simulated_actions(request: ExecutionRequest, command: ExecutionCommand) -> list[dict[str, Any]]:
        recommendations = list(request.decision_result.get("ranked_recommendations") or [])
        if not recommendations:
            return [
                {
                    "command_id": command.command_id,
                    "action_type": command.command_type,
                    "status": "simulated",
                    "target_type": "scheduling",
                    "target_id": "",
                    "mutates_business_state": False,
                    "result": "Execution authorization was recorded without concrete recommendation payload.",
                }
            ]
        actions: list[dict[str, Any]] = []
        for recommendation in recommendations:
            actions.append(
                {
                    "command_id": command.command_id,
                    "action_type": command.command_type,
                    "status": "simulated",
                    "target_type": "scheduling_recommendation",
                    "target_id": str(recommendation.get("recommendation_id") or recommendation.get("option_id") or ""),
                    "room_id": str(recommendation.get("room_id") or ""),
                    "caregiver_id": str(recommendation.get("caregiver_id") or ""),
                    "mutates_business_state": False,
                    "result": "Authorized scheduling recommendation was simulated; execution is reserved for a future phase.",
                }
            )
        return actions

    def _audit(
        self,
        *,
        action: str,
        request: ExecutionRequest,
        actor_name: str,
        result: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=request.requester_emp_id,
            actor_name=actor_name,
            module="execution",
            action=action,
            action_type=action,
            reason=request.reason,
            result=result,
            target_type="scheduling_decision",
            target_id=_decision_id(request.decision_result),
            correlation_id=request.correlation_id or request.request_id,
            metadata={
                "request_id": request.request_id,
                "decision_id": _decision_id(request.decision_result),
                "approval_id": str(request.approval_workflow.get("approval_id") or ""),
                "mutates_business_state": False,
                **metadata,
            },
        )

    def _event(
        self,
        *,
        event_type: str,
        request: ExecutionRequest,
        actor_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="execution",
                subject="execution",
                action=event_type.removeprefix("execution."),
                emp_id=request.requester_emp_id,
                actor_name=actor_name,
                payload={
                    "mutates_business_state": False,
                    **payload,
                },
                correlation_id=request.correlation_id or request.request_id,
                metadata={
                    "request_id": request.request_id,
                    "decision_id": _decision_id(request.decision_result),
                    "approval_id": str(request.approval_workflow.get("approval_id") or ""),
                    "reason": request.reason,
                    "mutates_business_state": False,
                },
            )
        )


def _decision_id(decision_result: dict[str, Any]) -> str:
    return str(decision_result.get("result_id") or decision_result.get("decision_id") or "")


def _approval_decision_id(approval_workflow: dict[str, Any]) -> str:
    decision_id = str(approval_workflow.get("decision_id") or "")
    if decision_id:
        return decision_id
    request = approval_workflow.get("request")
    if isinstance(request, dict):
        return str(request.get("decision_id") or "")
    return ""
