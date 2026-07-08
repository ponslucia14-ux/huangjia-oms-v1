from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .scheduler import DECISION_RECOMMENDED
from .schemas import new_id, now_iso


SCHEDULING_APPROVAL_SCHEMA_VERSION = "oms.v1.scheduling_approval"

APPROVAL_PENDING = "PENDING"
APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"
APPROVAL_EXPIRED = "EXPIRED"
APPROVAL_STATUSES = {
    APPROVAL_PENDING,
    APPROVAL_APPROVED,
    APPROVAL_REJECTED,
    APPROVAL_EXPIRED,
}

TERMINAL_APPROVAL_STATUSES = {
    APPROVAL_APPROVED,
    APPROVAL_REJECTED,
    APPROVAL_EXPIRED,
}

SCHEDULING_APPROVAL_CHAIN = (
    "system_recommendation",
    "approval_request",
    "approval_decision",
    "execution_authorization",
)


@dataclass(frozen=True)
class ApprovalRequest:
    """Request human approval for a scheduling decision recommendation."""

    decision_id: str
    requester_emp_id: str
    approver_emp_id: str
    reason: str
    approval_id: str = field(default_factory=lambda: new_id("schedappr"))
    decision_status: str = APPROVAL_PENDING
    source_decision_status: str = DECISION_RECOMMENDED
    correlation_id: str = ""
    timestamp: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEDULING_APPROVAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.approval_id.strip():
            raise ValueError("approval_id is required.")
        if not self.decision_id.strip():
            raise ValueError("decision_id is required.")
        if not self.requester_emp_id.strip():
            raise ValueError("requester_emp_id is required.")
        if not self.approver_emp_id.strip():
            raise ValueError("approver_emp_id is required.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        if self.decision_status != APPROVAL_PENDING:
            raise ValueError("ApprovalRequest decision_status must be PENDING.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovalDecision:
    """Human approval decision. It authorizes future execution but does not execute it."""

    approval_id: str
    decision_id: str
    requester_emp_id: str
    approver_emp_id: str
    reason: str
    decision_status: str
    correlation_id: str = ""
    timestamp: str = field(default_factory=now_iso)
    execution_authorized: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEDULING_APPROVAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.approval_id.strip():
            raise ValueError("approval_id is required.")
        if not self.decision_id.strip():
            raise ValueError("decision_id is required.")
        if not self.requester_emp_id.strip():
            raise ValueError("requester_emp_id is required.")
        if not self.approver_emp_id.strip():
            raise ValueError("approver_emp_id is required.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        if self.decision_status not in TERMINAL_APPROVAL_STATUSES:
            raise ValueError("ApprovalDecision decision_status must be APPROVED, REJECTED, or EXPIRED.")
        if self.execution_authorized and self.decision_status != APPROVAL_APPROVED:
            raise ValueError("Only APPROVED decisions can authorize execution.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovalWorkflow:
    """Approval workflow state for one scheduling decision."""

    request: dict[str, Any]
    current_status: str
    decisions: tuple[dict[str, Any], ...] = ()
    approval_id: str = ""
    decision_id: str = ""
    execution_authorized: bool = False
    decision_chain: tuple[str, ...] = SCHEDULING_APPROVAL_CHAIN
    mutates_business_state: bool = False
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    updated_at: str = field(default_factory=now_iso)
    schema_version: str = SCHEDULING_APPROVAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.current_status not in APPROVAL_STATUSES:
            raise ValueError(f"Unknown approval status: {self.current_status}")
        if self.mutates_business_state:
            raise ValueError("ApprovalWorkflow cannot mutate business state in P14.")
        if not self.approval_id:
            object.__setattr__(self, "approval_id", str(self.request.get("approval_id") or ""))
        if not self.decision_id:
            object.__setattr__(self, "decision_id", str(self.request.get("decision_id") or ""))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decisions"] = [dict(item) for item in self.decisions]
        payload["decision_chain"] = list(self.decision_chain)
        payload["audit_records"] = [dict(item) for item in self.audit_records]
        payload["events"] = [dict(item) for item in self.events]
        return payload


class SchedulingApprovalEngine:
    """Create and decide scheduling approvals without executing scheduling changes."""

    def __init__(
        self,
        *,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
    ):
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self._workflows: dict[str, ApprovalWorkflow] = {}

    def request_approval(self, request: ApprovalRequest | dict[str, Any]) -> dict[str, Any]:
        approval_request = request if isinstance(request, ApprovalRequest) else ApprovalRequest(**request)
        requester = self.master_data.employee_by_emp(approval_request.requester_emp_id)
        self.master_data.employee_by_emp(approval_request.approver_emp_id)

        audit_record = self._audit(
            action="approval.request",
            actor_emp_id=approval_request.requester_emp_id,
            actor_name=requester.name,
            reason=approval_request.reason,
            result=APPROVAL_PENDING,
            approval_id=approval_request.approval_id,
            decision_id=approval_request.decision_id,
            correlation_id=approval_request.correlation_id,
            metadata={
                "requester_emp_id": approval_request.requester_emp_id,
                "approver_emp_id": approval_request.approver_emp_id,
                "decision_status": APPROVAL_PENDING,
                "source_decision_status": approval_request.source_decision_status,
                "execution_authorized": False,
            },
        )
        event = self._event(
            event_type="scheduling.approval.requested",
            actor_emp_id=approval_request.requester_emp_id,
            actor_name=requester.name,
            approval_id=approval_request.approval_id,
            decision_id=approval_request.decision_id,
            reason=approval_request.reason,
            correlation_id=approval_request.correlation_id,
            payload={
                "approval_id": approval_request.approval_id,
                "decision_id": approval_request.decision_id,
                "requester_emp_id": approval_request.requester_emp_id,
                "approver_emp_id": approval_request.approver_emp_id,
                "decision_status": APPROVAL_PENDING,
                "execution_authorized": False,
            },
        )
        workflow = ApprovalWorkflow(
            request=approval_request.to_dict(),
            current_status=APPROVAL_PENDING,
            execution_authorized=False,
            audit_records=(audit_record,),
            events=(event,),
        )
        self._workflows[approval_request.approval_id] = workflow
        return workflow.to_dict()

    def approve(self, *, approval_id: str, approver_emp_id: str, reason: str) -> dict[str, Any]:
        return self._decide(
            approval_id=approval_id,
            approver_emp_id=approver_emp_id,
            reason=reason,
            decision_status=APPROVAL_APPROVED,
            audit_action="approval.approve",
            event_type="scheduling.approval.approved",
            execution_authorized=True,
        )

    def reject(self, *, approval_id: str, approver_emp_id: str, reason: str) -> dict[str, Any]:
        return self._decide(
            approval_id=approval_id,
            approver_emp_id=approver_emp_id,
            reason=reason,
            decision_status=APPROVAL_REJECTED,
            audit_action="approval.reject",
            event_type="scheduling.approval.rejected",
            execution_authorized=False,
        )

    def expire(self, *, approval_id: str, approver_emp_id: str, reason: str) -> dict[str, Any]:
        return self._decide(
            approval_id=approval_id,
            approver_emp_id=approver_emp_id,
            reason=reason,
            decision_status=APPROVAL_EXPIRED,
            audit_action="approval.expire",
            event_type="scheduling.approval.expired",
            execution_authorized=False,
        )

    def workflow(self, approval_id: str) -> dict[str, Any]:
        return self._workflow(approval_id).to_dict()

    def _decide(
        self,
        *,
        approval_id: str,
        approver_emp_id: str,
        reason: str,
        decision_status: str,
        audit_action: str,
        event_type: str,
        execution_authorized: bool,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required.")
        workflow = self._workflow(approval_id)
        if workflow.current_status != APPROVAL_PENDING:
            raise ValueError(f"Approval {approval_id} is already {workflow.current_status}.")
        request = workflow.request
        expected_approver = str(request.get("approver_emp_id") or "")
        if approver_emp_id != expected_approver:
            raise PermissionError(f"{approver_emp_id} is not the approver for approval {approval_id}.")
        approver = self.master_data.employee_by_emp(approver_emp_id)

        decision = ApprovalDecision(
            approval_id=approval_id,
            decision_id=str(request["decision_id"]),
            requester_emp_id=str(request["requester_emp_id"]),
            approver_emp_id=approver_emp_id,
            reason=reason,
            decision_status=decision_status,
            correlation_id=str(request.get("correlation_id") or ""),
            execution_authorized=execution_authorized,
        )
        audit_record = self._audit(
            action=audit_action,
            actor_emp_id=approver_emp_id,
            actor_name=approver.name,
            reason=reason,
            result=decision_status,
            approval_id=approval_id,
            decision_id=decision.decision_id,
            correlation_id=decision.correlation_id,
            metadata={
                "requester_emp_id": decision.requester_emp_id,
                "approver_emp_id": approver_emp_id,
                "decision_status": decision_status,
                "execution_authorized": execution_authorized,
            },
        )
        event = self._event(
            event_type=event_type,
            actor_emp_id=approver_emp_id,
            actor_name=approver.name,
            approval_id=approval_id,
            decision_id=decision.decision_id,
            reason=reason,
            correlation_id=decision.correlation_id,
            payload={
                "approval_id": approval_id,
                "decision_id": decision.decision_id,
                "requester_emp_id": decision.requester_emp_id,
                "approver_emp_id": approver_emp_id,
                "decision_status": decision_status,
                "execution_authorized": execution_authorized,
            },
        )
        updated = ApprovalWorkflow(
            request=dict(request),
            current_status=decision_status,
            decisions=(*workflow.decisions, decision.to_dict()),
            approval_id=workflow.approval_id,
            decision_id=workflow.decision_id,
            execution_authorized=execution_authorized,
            audit_records=(*workflow.audit_records, audit_record),
            events=(*workflow.events, event),
        )
        self._workflows[approval_id] = updated
        return updated.to_dict()

    def _workflow(self, approval_id: str) -> ApprovalWorkflow:
        if approval_id not in self._workflows:
            raise KeyError(f"Unknown approval_id: {approval_id}")
        return self._workflows[approval_id]

    def _audit(
        self,
        *,
        action: str,
        actor_emp_id: str,
        actor_name: str,
        reason: str,
        result: str,
        approval_id: str,
        decision_id: str,
        correlation_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor_emp_id,
            actor_name=actor_name,
            module="scheduling_approval",
            action=action,
            action_type=action,
            reason=reason,
            result=result,
            target_type="scheduling_decision",
            target_id=decision_id,
            correlation_id=correlation_id or approval_id,
            metadata={
                "approval_id": approval_id,
                "decision_id": decision_id,
                "mutates_business_state": False,
                **metadata,
            },
        )

    def _event(
        self,
        *,
        event_type: str,
        actor_emp_id: str,
        actor_name: str,
        approval_id: str,
        decision_id: str,
        reason: str,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="scheduling_approval",
                subject="scheduling_approval",
                action=event_type.removeprefix("scheduling.approval."),
                emp_id=actor_emp_id,
                actor_name=actor_name,
                payload={
                    "mutates_business_state": False,
                    **payload,
                },
                correlation_id=correlation_id or approval_id,
                metadata={
                    "approval_id": approval_id,
                    "decision_id": decision_id,
                    "reason": reason,
                    "decision_chain": list(SCHEDULING_APPROVAL_CHAIN),
                    "mutates_business_state": False,
                },
            )
        )
