from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .business_rules import BusinessRulesEngine, RuleContext, RULE_PASS, RULE_REJECT, RULE_WARNING
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .schemas import new_id, now_iso


SCHEDULER_SCHEMA_VERSION = "oms.v1.scheduler"

SCHEDULING_PASS = "PASS"
SCHEDULING_WARNING = "WARNING"
SCHEDULING_REJECT = "REJECT"
SCHEDULING_RESULT_ORDER = {SCHEDULING_PASS: 0, SCHEDULING_WARNING: 1, SCHEDULING_REJECT: 2}

SCHEDULING_COMPLETED = "completed"
SCHEDULING_FAILED = "failed"

DECISION_PENDING = "PENDING"
DECISION_RECOMMENDED = "RECOMMENDED"
DECISION_APPROVED = "APPROVED"
DECISION_REJECTED = "REJECTED"
DECISION_EXECUTED = "EXECUTED"
DECISION_STATUSES = {
    DECISION_PENDING,
    DECISION_RECOMMENDED,
    DECISION_APPROVED,
    DECISION_REJECTED,
    DECISION_EXECUTED,
}

REQUEST_TYPES = {"room", "caregiver", "combined"}
PRIORITIES = {"normal", "urgent", "critical"}


@dataclass(frozen=True)
class SchedulingRequest:
    """P12 scheduling request. It is a request for analysis, not execution."""

    actor_emp_id: str
    reason: str
    stay_id: str
    source_module: str
    request_id: str = field(default_factory=lambda: new_id("schedreq"))
    request_type: str = "combined"
    requirements: dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"
    correlation_id: str = ""
    created_at: str = field(default_factory=now_iso)
    schema_version: str = SCHEDULER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id is required.")
        if self.request_type not in REQUEST_TYPES:
            raise ValueError(f"request_type must be one of: {', '.join(sorted(REQUEST_TYPES))}.")
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        if not self.stay_id.strip():
            raise ValueError("stay_id is required.")
        if not self.source_module.strip():
            raise ValueError("source_module is required.")
        if self.priority not in PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(sorted(PRIORITIES))}.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SchedulingContext:
    """Read-only scheduling context built from Stay, Room, Caregiver, and Business Rules."""

    stay_context: dict[str, Any]
    room_candidates: tuple[dict[str, Any], ...] = ()
    caregiver_candidates: tuple[dict[str, Any], ...] = ()
    business_rule_results: tuple[dict[str, Any], ...] = ()
    business_rules: BusinessRulesEngine | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEDULER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.stay_context:
            raise ValueError("stay_context is required.")
        object.__setattr__(self, "room_candidates", tuple(self.room_candidates))
        object.__setattr__(self, "caregiver_candidates", tuple(self.caregiver_candidates))
        object.__setattr__(self, "business_rule_results", tuple(self.business_rule_results))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stay_context": dict(self.stay_context),
            "room_candidates": [dict(item) for item in self.room_candidates],
            "caregiver_candidates": [dict(item) for item in self.caregiver_candidates],
            "business_rule_results": [dict(item) for item in self.business_rule_results],
            "has_business_rules": self.business_rules is not None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SchedulingCandidate:
    resource_type: str
    resource_id: str
    status: str
    reason: str
    rule_status: str = SCHEDULING_PASS
    rule_reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEDULER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.status not in SCHEDULING_RESULT_ORDER:
            raise ValueError(f"Unknown candidate status: {self.status}")
        if not self.reason.strip():
            raise ValueError("candidate reason is required.")
        object.__setattr__(self, "rule_reasons", tuple(self.rule_reasons))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["rule_reasons"] = list(self.rule_reasons)
        return payload


@dataclass(frozen=True)
class SchedulingResult:
    request: dict[str, Any]
    status: str
    decision_status: str
    recommendations: tuple[dict[str, Any], ...]
    room_candidates: tuple[SchedulingCandidate, ...]
    caregiver_candidates: tuple[SchedulingCandidate, ...]
    failure_reasons: tuple[dict[str, Any], ...]
    warnings: tuple[dict[str, Any], ...]
    business_rule_trace: tuple[dict[str, Any], ...]
    result_id: str = field(default_factory=lambda: new_id("schedres"))
    mutates_business_state: bool = False
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = SCHEDULER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.status not in {SCHEDULING_COMPLETED, SCHEDULING_FAILED}:
            raise ValueError("status must be completed or failed.")
        if self.decision_status not in DECISION_STATUSES:
            raise ValueError(f"Unknown decision_status: {self.decision_status}")
        if self.mutates_business_state:
            raise ValueError("SchedulingResult cannot mutate business state in P12.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["recommendations"] = [dict(item) for item in self.recommendations]
        payload["room_candidates"] = [candidate.to_dict() for candidate in self.room_candidates]
        payload["caregiver_candidates"] = [candidate.to_dict() for candidate in self.caregiver_candidates]
        payload["failure_reasons"] = [dict(item) for item in self.failure_reasons]
        payload["warnings"] = [dict(item) for item in self.warnings]
        payload["business_rule_trace"] = [dict(item) for item in self.business_rule_trace]
        payload["audit_records"] = [dict(item) for item in self.audit_records]
        payload["events"] = [dict(item) for item in self.events]
        return payload


class SchedulerEngine:
    """Analyze scheduling context and return suggestions without mutating resources."""

    def __init__(
        self,
        *,
        business_rules: BusinessRulesEngine | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
    ):
        self.business_rules = business_rules
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.master_data = master_data or getattr(business_rules, "master_data", None) or OMSMasterData()

    def schedule(self, request: SchedulingRequest | dict[str, Any], context: SchedulingContext | dict[str, Any]) -> dict[str, Any]:
        scheduling_request = request if isinstance(request, SchedulingRequest) else SchedulingRequest(**request)
        scheduling_context = context if isinstance(context, SchedulingContext) else SchedulingContext(**context)
        actor = self.master_data.employee_by_emp(scheduling_request.actor_emp_id)

        audit_records: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        audit_records.append(
            self._audit(
                action="scheduling.request",
                request=scheduling_request,
                actor_name=actor.name,
                result=DECISION_PENDING,
                metadata={"decision_status": DECISION_PENDING},
            )
        )
        events.append(
            self._event(
                event_type="scheduling.requested",
                request=scheduling_request,
                actor_name=actor.name,
                payload={
                    "request_id": scheduling_request.request_id,
                    "actor_emp_id": scheduling_request.actor_emp_id,
                    "stay_id": scheduling_request.stay_id,
                    "reason": scheduling_request.reason,
                    "decision_status": DECISION_PENDING,
                },
            )
        )
        audit_records.append(
            self._audit(
                action="scheduling.context_built",
                request=scheduling_request,
                actor_name=actor.name,
                result=DECISION_PENDING,
                metadata={
                    "stay_id": scheduling_request.stay_id,
                    "room_candidate_count": len(scheduling_context.room_candidates),
                    "caregiver_candidate_count": len(scheduling_context.caregiver_candidates),
                    "business_rule_result_count": len(scheduling_context.business_rule_results),
                    "decision_status": DECISION_PENDING,
                },
            )
        )

        room_candidates, room_rule_trace = self._room_candidates(scheduling_request, scheduling_context)
        caregiver_candidates = tuple(
            self._caregiver_candidate(caregiver, scheduling_request=scheduling_request)
            for caregiver in scheduling_context.caregiver_candidates
        )
        business_rule_trace = tuple([*scheduling_context.business_rule_results, *room_rule_trace])
        warnings = tuple(self._warnings(room_candidates, caregiver_candidates, business_rule_trace))
        failure_reasons = tuple(self._failure_reasons(room_candidates, caregiver_candidates, business_rule_trace))
        recommendations = tuple(self._recommendations(scheduling_request, room_candidates, caregiver_candidates))

        if recommendations:
            result_status = SCHEDULING_COMPLETED
            decision_status = DECISION_RECOMMENDED
            terminal_action = "scheduling.complete"
            terminal_event = "scheduling.completed"
        else:
            result_status = SCHEDULING_FAILED
            decision_status = DECISION_REJECTED
            terminal_action = "scheduling.fail"
            terminal_event = "scheduling.failed"
            if not failure_reasons:
                failure_reasons = (
                    {
                        "code": "no_schedulable_candidate",
                        "message": "No schedulable room or caregiver candidate was available.",
                        "severity": "error",
                        "affected_resource": "",
                    },
                )

        terminal_audit = self._audit(
            action=terminal_action,
            request=scheduling_request,
            actor_name=actor.name,
            result=decision_status,
            metadata={
                "decision_status": decision_status,
                "recommendation_count": len(recommendations),
                "failure_reason_count": len(failure_reasons),
                "warning_count": len(warnings),
            },
        )
        audit_records.append(terminal_audit)
        terminal_dispatch = self._event(
            event_type=terminal_event,
            request=scheduling_request,
            actor_name=actor.name,
            payload={
                "request_id": scheduling_request.request_id,
                "result_status": result_status,
                "decision_status": decision_status,
                "recommendations": list(recommendations),
                "failure_reasons": list(failure_reasons),
                "warnings": list(warnings),
            },
        )
        events.append(terminal_dispatch)

        return SchedulingResult(
            request=scheduling_request.to_dict(),
            status=result_status,
            decision_status=decision_status,
            recommendations=recommendations,
            room_candidates=room_candidates,
            caregiver_candidates=caregiver_candidates,
            failure_reasons=failure_reasons,
            warnings=warnings,
            business_rule_trace=business_rule_trace,
            mutates_business_state=False,
            audit_records=tuple(audit_records),
            events=tuple(events),
        ).to_dict()

    def _room_candidates(
        self,
        scheduling_request: SchedulingRequest,
        scheduling_context: SchedulingContext,
    ) -> tuple[tuple[SchedulingCandidate, ...], tuple[dict[str, Any], ...]]:
        rules = scheduling_context.business_rules or self.business_rules
        candidates: list[SchedulingCandidate] = []
        traces: list[dict[str, Any]] = []
        for room in scheduling_context.room_candidates:
            candidate, trace = self._room_candidate(room, scheduling_request=scheduling_request, rules=rules)
            candidates.append(candidate)
            if trace:
                traces.append(trace)
        return tuple(candidates), tuple(traces)

    @staticmethod
    def _room_candidate(
        room: dict[str, Any],
        *,
        scheduling_request: SchedulingRequest,
        rules: BusinessRulesEngine | None,
    ) -> tuple[SchedulingCandidate, dict[str, Any] | None]:
        room_id = str(room.get("room_id") or "")
        status = str(room.get("room_status") or room.get("status") or "")
        if status != "AVAILABLE":
            base_status = SCHEDULING_WARNING if status == "RESERVED" else SCHEDULING_REJECT
            base_reason = f"Room status is {status}; scheduler can only suggest AVAILABLE rooms."
        else:
            base_status = SCHEDULING_PASS
            base_reason = "Room is available for scheduling suggestion."

        rule_status = RULE_PASS
        rule_reasons: tuple[str, ...] = ()
        rule_trace: dict[str, Any] | None = None
        if rules is not None:
            normalized_room = {**room, "status": status}
            rule_result = rules.evaluate(
                RuleContext(
                    action="check_in_room",
                    actor_emp_id=scheduling_request.actor_emp_id,
                    domain="Room",
                    required_fields=("room_id",),
                    data={
                        "room_id": room_id,
                        "room": normalized_room,
                        "stay": {"stay_id": scheduling_request.stay_id, **scheduling_request.requirements},
                    },
                )
            )
            rule_status = str(rule_result["overall_status"])
            rule_reasons = tuple(rule_result["reject_reasons"] + rule_result["warning_reasons"])
            rule_trace = {
                "resource_type": "room",
                "resource_id": room_id,
                "rule_result": rule_result,
            }

        final_status = _max_status(base_status, _rule_to_schedule_status(rule_status))
        final_reason = "; ".join([base_reason, *rule_reasons]).strip("; ")
        return (
            SchedulingCandidate(
                resource_type="room",
                resource_id=room_id,
                status=final_status,
                reason=final_reason,
                rule_status=rule_status,
                rule_reasons=rule_reasons,
                metadata={"room_status": status},
            ),
            rule_trace,
        )

    @staticmethod
    def _caregiver_candidate(caregiver: dict[str, Any], *, scheduling_request: SchedulingRequest) -> SchedulingCandidate:
        caregiver_id = str(caregiver.get("caregiver_id") or caregiver.get("caregiver_emp_id") or "")
        status = str(caregiver.get("availability_status") or caregiver.get("status") or "")
        if status == "AVAILABLE":
            return SchedulingCandidate(
                resource_type="caregiver",
                resource_id=caregiver_id,
                status=SCHEDULING_PASS,
                reason="Caregiver is available for scheduling suggestion.",
                metadata={"caregiver_status": status},
            )
        if status == "RESERVED":
            return SchedulingCandidate(
                resource_type="caregiver",
                resource_id=caregiver_id,
                status=SCHEDULING_WARNING,
                reason="Caregiver is already reserved; scheduler will not auto-assign.",
                metadata={"caregiver_status": status},
            )
        return SchedulingCandidate(
            resource_type="caregiver",
            resource_id=caregiver_id,
            status=SCHEDULING_REJECT,
            reason=f"Caregiver status is {status}; scheduler can only suggest AVAILABLE caregivers.",
            metadata={"caregiver_status": status},
        )

    @staticmethod
    def _recommendations(
        request: SchedulingRequest,
        room_candidates: tuple[SchedulingCandidate, ...],
        caregiver_candidates: tuple[SchedulingCandidate, ...],
    ) -> list[dict[str, Any]]:
        available_rooms = [candidate for candidate in room_candidates if candidate.status == SCHEDULING_PASS]
        available_caregivers = [candidate for candidate in caregiver_candidates if candidate.status == SCHEDULING_PASS]
        if request.request_type in {"room", "combined"} and not available_rooms:
            return []
        if request.request_type in {"caregiver", "combined"} and not available_caregivers:
            return []
        room_id = available_rooms[0].resource_id if available_rooms else ""
        caregiver_id = available_caregivers[0].resource_id if available_caregivers else ""
        return [
            {
                "recommendation_id": new_id("schedrec"),
                "recommended_room_id": room_id,
                "recommended_caregiver_id": caregiver_id,
                "room_id": room_id,
                "caregiver_id": caregiver_id,
                "confidence": "basic",
                "reasons": ["First available resources are suggested; no allocation algorithm is applied in P12."],
                "warnings": [],
                "rejected_candidates": [
                    candidate.resource_id
                    for candidate in [*room_candidates, *caregiver_candidates]
                    if candidate.status == SCHEDULING_REJECT
                ],
                "auto_assigned": False,
            }
        ]

    @staticmethod
    def _warnings(
        room_candidates: tuple[SchedulingCandidate, ...],
        caregiver_candidates: tuple[SchedulingCandidate, ...],
        business_rule_trace: tuple[dict[str, Any], ...],
    ) -> list[dict[str, Any]]:
        warnings = [
            {
                "code": f"{candidate.resource_type}_warning",
                "message": candidate.reason,
                "severity": "warning",
                "affected_resource": candidate.resource_id,
            }
            for candidate in [*room_candidates, *caregiver_candidates]
            if candidate.status == SCHEDULING_WARNING
        ]
        for trace in business_rule_trace:
            rule_result = trace.get("rule_result", trace)
            for reason in rule_result.get("warning_reasons", []) or []:
                warnings.append(
                    {
                        "code": "business_rule_warning",
                        "message": reason,
                        "severity": "warning",
                        "affected_resource": str(trace.get("resource_id") or ""),
                    }
                )
        return warnings

    @staticmethod
    def _failure_reasons(
        room_candidates: tuple[SchedulingCandidate, ...],
        caregiver_candidates: tuple[SchedulingCandidate, ...],
        business_rule_trace: tuple[dict[str, Any], ...],
    ) -> list[dict[str, Any]]:
        failures = [
            {
                "code": f"{candidate.resource_type}_rejected",
                "message": candidate.reason,
                "severity": "error",
                "affected_resource": candidate.resource_id,
            }
            for candidate in [*room_candidates, *caregiver_candidates]
            if candidate.status == SCHEDULING_REJECT
        ]
        for trace in business_rule_trace:
            rule_result = trace.get("rule_result", trace)
            for reason in rule_result.get("reject_reasons", []) or []:
                failures.append(
                    {
                        "code": "business_rule_rejected",
                        "message": reason,
                        "severity": "error",
                        "affected_resource": str(trace.get("resource_id") or ""),
                    }
                )
        return failures

    def _audit(
        self,
        *,
        action: str,
        request: SchedulingRequest,
        actor_name: str,
        result: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=request.actor_emp_id,
            actor_name=actor_name,
            module="scheduling",
            action=action,
            action_type=action,
            reason=request.reason,
            result=result,
            target_type="stay",
            target_id=request.stay_id,
            correlation_id=request.correlation_id or request.request_id,
            metadata={
                "request_id": request.request_id,
                "request_type": request.request_type,
                "source_module": request.source_module,
                "priority": request.priority,
                "mutates_business_state": False,
                **metadata,
            },
        )

    def _event(
        self,
        *,
        event_type: str,
        request: SchedulingRequest,
        actor_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="scheduling",
                subject="scheduling",
                action=event_type.removeprefix("scheduling."),
                emp_id=request.actor_emp_id,
                actor_name=actor_name,
                payload={
                    "mutates_business_state": False,
                    **payload,
                },
                correlation_id=request.correlation_id or request.request_id,
                metadata={
                    "request_id": request.request_id,
                    "stay_id": request.stay_id,
                    "reason": request.reason,
                    "mutates_business_state": False,
                },
            )
        )


class Scheduler:
    """Small facade kept for callers that want a scheduler object instead of engine naming."""

    def __init__(self, *, engine: SchedulerEngine | None = None):
        self.engine = engine or SchedulerEngine()

    def schedule(self, request: SchedulingRequest | dict[str, Any], context: SchedulingContext | dict[str, Any]) -> dict[str, Any]:
        return self.engine.schedule(request, context)


def _rule_to_schedule_status(status: str) -> str:
    if status == RULE_REJECT:
        return SCHEDULING_REJECT
    if status == RULE_WARNING:
        return SCHEDULING_WARNING
    return SCHEDULING_PASS


def _max_status(left: str, right: str) -> str:
    return max([left, right], key=lambda status: SCHEDULING_RESULT_ORDER[status])
