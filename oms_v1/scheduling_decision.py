from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .scheduler import (
    DECISION_PENDING,
    DECISION_RECOMMENDED,
    DECISION_REJECTED,
    DECISION_STATUSES,
    SchedulingContext,
)
from .schemas import new_id, now_iso


SCHEDULING_DECISION_SCHEMA_VERSION = "oms.v1.scheduling_decision"

DECISION_PASS = "PASS"
DECISION_WARNING = "WARNING"
DECISION_REJECT = "REJECT"
DECISION_RESULT_ORDER = {DECISION_PASS: 0, DECISION_WARNING: 1, DECISION_REJECT: 2}

SCHEDULING_DECISION_COMPLETED = "completed"
SCHEDULING_DECISION_FAILED = "failed"

ROOM_AVAILABLE_SCORE = 100
ROOM_RESERVED_SCORE = 40
CAREGIVER_AVAILABLE_SCORE = 60
CAREGIVER_RESERVED_SCORE = 20

ROOM_ALLOWED_WARNING_STATUSES = {"RESERVED"}
ROOM_BLOCKED_STATUSES = {"OCCUPIED", "CLEANING"}
ROOM_EXCLUDED_STATUSES = {"MAINTENANCE", "DISABLED"}

CAREGIVER_ALLOWED_WARNING_STATUSES = {"RESERVED"}
CAREGIVER_BLOCKED_STATUSES = {"ASSIGNED", "ON_LEAVE", "OFF_DUTY", "DISABLED"}

SCHEDULING_DECISION_ALLOWED_ROLES = {
    "ROLE_OWNER",
    "ROLE_STORE_MANAGER",
    "ROLE_NURSING_DIRECTOR",
    "ROLE_HR",
}


DecisionEvaluator = Callable[["DecisionContext", dict[str, Any]], "DecisionRuleOutcome"]


@dataclass(frozen=True)
class DecisionContext:
    """Read-only input for the P13 scheduling decision engine."""

    actor_emp_id: str
    reason: str
    scheduling_context: SchedulingContext | dict[str, Any]
    request_id: str = ""
    candidate_resources: tuple[dict[str, Any], ...] = ()
    business_rule_results: tuple[dict[str, Any], ...] = ()
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    schema_version: str = SCHEDULING_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        if not self.request_id.strip():
            object.__setattr__(self, "request_id", new_id("scheddec_req"))
        if isinstance(self.scheduling_context, SchedulingContext):
            object.__setattr__(self, "scheduling_context", self.scheduling_context.to_dict())
        elif not self.scheduling_context:
            raise ValueError("scheduling_context is required.")
        else:
            object.__setattr__(self, "scheduling_context", dict(self.scheduling_context))
        object.__setattr__(self, "candidate_resources", tuple(dict(item) for item in self.candidate_resources))
        object.__setattr__(self, "business_rule_results", tuple(dict(item) for item in self.business_rule_results))

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_emp_id": self.actor_emp_id,
            "reason": self.reason,
            "scheduling_context": dict(self.scheduling_context),
            "request_id": self.request_id,
            "candidate_resources": [dict(item) for item in self.candidate_resources],
            "business_rule_results": [dict(item) for item in self.business_rule_results],
            "correlation_id": self.correlation_id,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DecisionRuleOutcome:
    rule_id: str
    name: str
    status: str
    reason: str
    score_delta: int = 0
    severity: str = "info"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in DECISION_RESULT_ORDER:
            raise ValueError(f"Unknown decision rule status: {self.status}")
        if not self.reason.strip():
            raise ValueError("decision rule reason is required.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionRule:
    """A read-only rule used to rank or reject scheduling candidates."""

    rule_id: str
    name: str
    description: str
    priority: int
    evaluator: DecisionEvaluator
    enabled: bool = True
    schema_version: str = SCHEDULING_DECISION_SCHEMA_VERSION

    def evaluate(self, context: DecisionContext, option: dict[str, Any]) -> DecisionRuleOutcome:
        if not self.enabled:
            return DecisionRuleOutcome(
                rule_id=self.rule_id,
                name=self.name,
                status=DECISION_WARNING,
                reason="Decision rule is disabled.",
                severity="warning",
            )
        outcome = self.evaluator(context, option)
        if outcome.rule_id != self.rule_id:
            raise ValueError(f"Rule evaluator returned mismatched result for {self.rule_id}.")
        return outcome

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("evaluator", None)
        return payload


@dataclass(frozen=True)
class DecisionResult:
    """P13 decision output. It recommends only; it never executes allocation."""

    context: dict[str, Any]
    status: str
    decision_status: str
    decision_reason: str
    ranked_recommendations: tuple[dict[str, Any], ...]
    warnings: tuple[dict[str, Any], ...]
    rejected_options: tuple[dict[str, Any], ...]
    business_rule_trace: tuple[dict[str, Any], ...]
    result_id: str = field(default_factory=lambda: new_id("scheddec_res"))
    decision_chain: tuple[str, ...] = ("system_recommendation", "human_confirmation", "execution")
    mutates_business_state: bool = False
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = SCHEDULING_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.status not in {SCHEDULING_DECISION_COMPLETED, SCHEDULING_DECISION_FAILED}:
            raise ValueError("status must be completed or failed.")
        if self.decision_status not in DECISION_STATUSES:
            raise ValueError(f"Unknown decision_status: {self.decision_status}")
        if self.mutates_business_state:
            raise ValueError("DecisionResult cannot mutate business state in P13.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ranked_recommendations"] = [dict(item) for item in self.ranked_recommendations]
        payload["warnings"] = [dict(item) for item in self.warnings]
        payload["rejected_options"] = [dict(item) for item in self.rejected_options]
        payload["business_rule_trace"] = [dict(item) for item in self.business_rule_trace]
        payload["decision_chain"] = list(self.decision_chain)
        payload["audit_records"] = [dict(item) for item in self.audit_records]
        payload["events"] = [dict(item) for item in self.events]
        return payload


class SchedulingDecisionEngine:
    """Rank scheduling candidates without changing Room, Stay, or Caregiver state."""

    def __init__(
        self,
        *,
        rules: list[DecisionRule] | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
    ):
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.rules = sorted(rules or default_decision_rules(self.master_data), key=lambda rule: rule.priority)

    def decide(self, context: DecisionContext | dict[str, Any]) -> dict[str, Any]:
        decision_context = context if isinstance(context, DecisionContext) else DecisionContext(**context)
        actor = self.master_data.employee_by_emp(decision_context.actor_emp_id)
        options = _candidate_options(decision_context)

        audit_records: list[dict[str, Any]] = [
            self._audit(
                action="scheduling_decision.request",
                context=decision_context,
                actor_name=actor.name,
                result=DECISION_PENDING,
                metadata={
                    "decision_status": DECISION_PENDING,
                    "candidate_count": len(options),
                },
            )
        ]
        events: list[dict[str, Any]] = [
            self._event(
                event_type="scheduling.decision.requested",
                context=decision_context,
                actor_name=actor.name,
                payload={
                    "request_id": decision_context.request_id,
                    "decision_status": DECISION_PENDING,
                    "candidate_count": len(options),
                },
            )
        ]

        evaluated = [self._evaluate_option(decision_context, option) for option in options]
        recommendations = tuple(self._ranked_recommendations(evaluated))
        rejected_options = tuple(item["rejected_option"] for item in evaluated if item["rejected_option"])
        warnings = tuple(warning for item in evaluated for warning in item["warnings"])
        business_rule_trace = tuple(decision_context.business_rule_results)

        if recommendations:
            status = SCHEDULING_DECISION_COMPLETED
            decision_status = DECISION_RECOMMENDED
            decision_reason = "Candidates were ranked by P13 decision rules; human confirmation is required before execution."
            terminal_action = "scheduling_decision.complete"
            terminal_event = "scheduling.decision.completed"
        else:
            status = SCHEDULING_DECISION_FAILED
            decision_status = DECISION_REJECTED
            decision_reason = "No candidate passed P13 decision rules; no scheduling execution is allowed."
            terminal_action = "scheduling_decision.fail"
            terminal_event = "scheduling.decision.failed"
            if not rejected_options:
                rejected_options = (
                    {
                        "option_id": "",
                        "room_id": "",
                        "caregiver_id": "",
                        "rejected_by": ["SDR_NO_CANDIDATE"],
                        "reasons": ["No candidate resources were provided."],
                    },
                )

        audit_records.append(
            self._audit(
                action=terminal_action,
                context=decision_context,
                actor_name=actor.name,
                result=decision_status,
                metadata={
                    "decision_status": decision_status,
                    "recommendation_count": len(recommendations),
                    "rejected_option_count": len(rejected_options),
                    "warning_count": len(warnings),
                    "mutates_business_state": False,
                },
            )
        )
        events.append(
            self._event(
                event_type=terminal_event,
                context=decision_context,
                actor_name=actor.name,
                payload={
                    "request_id": decision_context.request_id,
                    "result_status": status,
                    "decision_status": decision_status,
                    "decision_reason": decision_reason,
                    "recommendation_count": len(recommendations),
                    "rejected_option_count": len(rejected_options),
                    "warnings": list(warnings),
                },
            )
        )

        return DecisionResult(
            context=decision_context.to_dict(),
            status=status,
            decision_status=decision_status,
            decision_reason=decision_reason,
            ranked_recommendations=recommendations,
            warnings=warnings,
            rejected_options=rejected_options,
            business_rule_trace=business_rule_trace,
            mutates_business_state=False,
            audit_records=tuple(audit_records),
            events=tuple(events),
        ).to_dict()

    def definitions(self) -> list[dict[str, Any]]:
        return [rule.to_dict() for rule in self.rules]

    def _evaluate_option(self, context: DecisionContext, option: dict[str, Any]) -> dict[str, Any]:
        score = int(option.get("score") or 0)
        rule_trace: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        reject_reasons: list[str] = []
        rejected_by: list[str] = []

        for rule in self.rules:
            outcome = rule.evaluate(context, option)
            rule_trace.append(outcome.to_dict())
            score += outcome.score_delta
            if outcome.status == DECISION_WARNING:
                warnings.append(
                    {
                        "code": outcome.rule_id,
                        "message": outcome.reason,
                        "severity": outcome.severity,
                        "option_id": _option_id(option),
                    }
                )
            elif outcome.status == DECISION_REJECT:
                rejected_by.append(outcome.rule_id)
                reject_reasons.append(outcome.reason)

        rejected_option = None
        if rejected_by:
            rejected_option = {
                "option_id": _option_id(option),
                "room_id": _room_id(option),
                "caregiver_id": _caregiver_id(option),
                "rejected_by": rejected_by,
                "reasons": reject_reasons,
                "rule_trace": rule_trace,
            }

        return {
            "option": dict(option),
            "score": score,
            "rule_trace": rule_trace,
            "warnings": warnings,
            "rejected_option": rejected_option,
        }

    @staticmethod
    def _ranked_recommendations(evaluated_options: list[dict[str, Any]]) -> list[dict[str, Any]]:
        accepted = [item for item in evaluated_options if not item["rejected_option"]]
        ranked = sorted(
            accepted,
            key=lambda item: (
                -int(item["score"]),
                _room_id(item["option"]),
                _caregiver_id(item["option"]),
                _option_id(item["option"]),
            ),
        )
        recommendations: list[dict[str, Any]] = []
        for index, item in enumerate(ranked, start=1):
            option = item["option"]
            recommendations.append(
                {
                    "recommendation_id": new_id("scheddec_rec"),
                    "rank": index,
                    "option_id": _option_id(option),
                    "score": item["score"],
                    "room_id": _room_id(option),
                    "room_status": _room_status(option),
                    "caregiver_id": _caregiver_id(option),
                    "caregiver_status": _caregiver_status(option),
                    "decision_status": DECISION_RECOMMENDED,
                    "decision_reason": "Recommended by scheduling decision rules; awaiting human confirmation.",
                    "requires_human_confirmation": True,
                    "auto_executed": False,
                    "rule_trace": item["rule_trace"],
                    "warnings": item["warnings"],
                }
            )
        return recommendations

    def _audit(
        self,
        *,
        action: str,
        context: DecisionContext,
        actor_name: str,
        result: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=context.actor_emp_id,
            actor_name=actor_name,
            module="scheduling_decision",
            action=action,
            action_type=action,
            reason=context.reason,
            result=result,
            target_type="scheduling_request",
            target_id=context.request_id,
            correlation_id=context.correlation_id or context.request_id,
            metadata={
                "request_id": context.request_id,
                "mutates_business_state": False,
                **metadata,
            },
        )

    def _event(
        self,
        *,
        event_type: str,
        context: DecisionContext,
        actor_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="scheduling_decision",
                subject="scheduling_decision",
                action=event_type.removeprefix("scheduling.decision."),
                emp_id=context.actor_emp_id,
                actor_name=actor_name,
                payload={
                    "mutates_business_state": False,
                    **payload,
                },
                correlation_id=context.correlation_id or context.request_id,
                metadata={
                    "request_id": context.request_id,
                    "reason": context.reason,
                    "mutates_business_state": False,
                },
            )
        )


def default_decision_rules(master_data: OMSMasterData | None = None) -> list[DecisionRule]:
    data = master_data or OMSMasterData()
    return [
        DecisionRule(
            rule_id="SDR_ROOM_AVAILABILITY_PRIORITY",
            name="Room availability priority",
            description="Rank AVAILABLE rooms first and keep RESERVED rooms as lower confidence warnings.",
            priority=10,
            evaluator=_room_availability_priority_rule,
        ),
        DecisionRule(
            rule_id="SDR_ROOM_STATUS_RESTRICTION",
            name="Room status restriction",
            description="Reject rooms whose state cannot be used for scheduling recommendation.",
            priority=20,
            evaluator=_room_status_restriction_rule,
        ),
        DecisionRule(
            rule_id="SDR_ROOM_MAINTENANCE_DISABLED_EXCLUSION",
            name="Maintenance and disabled room exclusion",
            description="Reject MAINTENANCE and DISABLED rooms.",
            priority=30,
            evaluator=_room_exclusion_rule,
        ),
        DecisionRule(
            rule_id="SDR_CAREGIVER_STATUS_RESTRICTION",
            name="Caregiver status restriction",
            description="Reject caregivers that are not available for scheduling recommendation.",
            priority=40,
            evaluator=_caregiver_status_rule,
        ),
        DecisionRule(
            rule_id="SDR_PERMISSION_AUTHORIZATION",
            name="Permission authorization",
            description="Reject recommendations when the actor is not authorized to request scheduling decisions.",
            priority=50,
            evaluator=_permission_rule(data),
        ),
    ]


def _room_availability_priority_rule(context: DecisionContext, option: dict[str, Any]) -> DecisionRuleOutcome:
    status = _room_status(option)
    if not _room_id(option):
        return DecisionRuleOutcome(
            rule_id="SDR_ROOM_AVAILABILITY_PRIORITY",
            name="Room availability priority",
            status=DECISION_PASS,
            reason="No room candidate was provided; room priority was not applied.",
        )
    if status == "AVAILABLE":
        return DecisionRuleOutcome(
            rule_id="SDR_ROOM_AVAILABILITY_PRIORITY",
            name="Room availability priority",
            status=DECISION_PASS,
            reason="Room is AVAILABLE and receives highest scheduling priority.",
            score_delta=ROOM_AVAILABLE_SCORE,
            metadata={"room_status": status},
        )
    if status in ROOM_ALLOWED_WARNING_STATUSES:
        return DecisionRuleOutcome(
            rule_id="SDR_ROOM_AVAILABILITY_PRIORITY",
            name="Room availability priority",
            status=DECISION_WARNING,
            reason=f"Room is {status}; keep as lower priority human-review option.",
            score_delta=ROOM_RESERVED_SCORE,
            severity="warning",
            metadata={"room_status": status},
        )
    return DecisionRuleOutcome(
        rule_id="SDR_ROOM_AVAILABILITY_PRIORITY",
        name="Room availability priority",
        status=DECISION_WARNING,
        reason=f"Room is {status or 'UNKNOWN'}; no availability score was added.",
        severity="warning",
        metadata={"room_status": status},
    )


def _room_status_restriction_rule(context: DecisionContext, option: dict[str, Any]) -> DecisionRuleOutcome:
    status = _room_status(option)
    if not _room_id(option):
        return DecisionRuleOutcome(
            rule_id="SDR_ROOM_STATUS_RESTRICTION",
            name="Room status restriction",
            status=DECISION_PASS,
            reason="No room candidate was provided; room status restriction was not applied.",
        )
    if status in {"AVAILABLE", *ROOM_ALLOWED_WARNING_STATUSES, *ROOM_EXCLUDED_STATUSES}:
        return DecisionRuleOutcome(
            rule_id="SDR_ROOM_STATUS_RESTRICTION",
            name="Room status restriction",
            status=DECISION_PASS,
            reason=f"Room status {status} is handled by scheduling decision rules.",
            metadata={"room_status": status},
        )
    return DecisionRuleOutcome(
        rule_id="SDR_ROOM_STATUS_RESTRICTION",
        name="Room status restriction",
        status=DECISION_REJECT,
        reason=f"Room status {status or 'UNKNOWN'} cannot be recommended for scheduling.",
        severity="error",
        metadata={"room_status": status},
    )


def _room_exclusion_rule(context: DecisionContext, option: dict[str, Any]) -> DecisionRuleOutcome:
    status = _room_status(option)
    if not _room_id(option):
        return DecisionRuleOutcome(
            rule_id="SDR_ROOM_MAINTENANCE_DISABLED_EXCLUSION",
            name="Maintenance and disabled room exclusion",
            status=DECISION_PASS,
            reason="No room candidate was provided; exclusion was not applied.",
        )
    if status in ROOM_EXCLUDED_STATUSES:
        return DecisionRuleOutcome(
            rule_id="SDR_ROOM_MAINTENANCE_DISABLED_EXCLUSION",
            name="Maintenance and disabled room exclusion",
            status=DECISION_REJECT,
            reason=f"Room status {status} is excluded from scheduling recommendation.",
            severity="error",
            metadata={"room_status": status},
        )
    return DecisionRuleOutcome(
        rule_id="SDR_ROOM_MAINTENANCE_DISABLED_EXCLUSION",
        name="Maintenance and disabled room exclusion",
        status=DECISION_PASS,
        reason=f"Room status {status or 'UNKNOWN'} is not MAINTENANCE or DISABLED.",
        metadata={"room_status": status},
    )


def _caregiver_status_rule(context: DecisionContext, option: dict[str, Any]) -> DecisionRuleOutcome:
    caregiver_id = _caregiver_id(option)
    status = _caregiver_status(option)
    if not caregiver_id:
        return DecisionRuleOutcome(
            rule_id="SDR_CAREGIVER_STATUS_RESTRICTION",
            name="Caregiver status restriction",
            status=DECISION_PASS,
            reason="No caregiver candidate was provided; caregiver restriction was not applied.",
        )
    if status == "AVAILABLE":
        return DecisionRuleOutcome(
            rule_id="SDR_CAREGIVER_STATUS_RESTRICTION",
            name="Caregiver status restriction",
            status=DECISION_PASS,
            reason="Caregiver is AVAILABLE and can be recommended for human confirmation.",
            score_delta=CAREGIVER_AVAILABLE_SCORE,
            metadata={"caregiver_status": status},
        )
    if status in CAREGIVER_ALLOWED_WARNING_STATUSES:
        return DecisionRuleOutcome(
            rule_id="SDR_CAREGIVER_STATUS_RESTRICTION",
            name="Caregiver status restriction",
            status=DECISION_WARNING,
            reason=f"Caregiver is {status}; keep as lower priority human-review option.",
            score_delta=CAREGIVER_RESERVED_SCORE,
            severity="warning",
            metadata={"caregiver_status": status},
        )
    if status in CAREGIVER_BLOCKED_STATUSES or not status:
        return DecisionRuleOutcome(
            rule_id="SDR_CAREGIVER_STATUS_RESTRICTION",
            name="Caregiver status restriction",
            status=DECISION_REJECT,
            reason=f"Caregiver status {status or 'UNKNOWN'} cannot be recommended for scheduling.",
            severity="error",
            metadata={"caregiver_status": status},
        )
    return DecisionRuleOutcome(
        rule_id="SDR_CAREGIVER_STATUS_RESTRICTION",
        name="Caregiver status restriction",
        status=DECISION_WARNING,
        reason=f"Caregiver status {status} is not recognized; human review is required.",
        severity="warning",
        metadata={"caregiver_status": status},
    )


def _permission_rule(master_data: OMSMasterData) -> DecisionEvaluator:
    def evaluate(context: DecisionContext, option: dict[str, Any]) -> DecisionRuleOutcome:
        employee = master_data.employee_by_emp(context.actor_emp_id)
        if employee.role_code not in SCHEDULING_DECISION_ALLOWED_ROLES:
            return DecisionRuleOutcome(
                rule_id="SDR_PERMISSION_AUTHORIZATION",
                name="Permission authorization",
                status=DECISION_REJECT,
                reason=f"{employee.emp} role {employee.role_code} is not allowed to make scheduling decisions.",
                severity="error",
                metadata={
                    "role_code": employee.role_code,
                    "allowed_roles": sorted(SCHEDULING_DECISION_ALLOWED_ROLES),
                },
            )
        return DecisionRuleOutcome(
            rule_id="SDR_PERMISSION_AUTHORIZATION",
            name="Permission authorization",
            status=DECISION_PASS,
            reason=f"{employee.emp} role {employee.role_code} can request scheduling recommendations.",
            metadata={"role_code": employee.role_code},
        )

    return evaluate


def _candidate_options(context: DecisionContext) -> list[dict[str, Any]]:
    if context.candidate_resources:
        return [dict(option) for option in context.candidate_resources]

    scheduling_context = context.scheduling_context
    rooms = [dict(item) for item in scheduling_context.get("room_candidates", [])]
    caregivers = [dict(item) for item in scheduling_context.get("caregiver_candidates", [])]
    if rooms and caregivers:
        return [
            _combine_room_and_caregiver(room, caregiver, index)
            for index, (room, caregiver) in enumerate((room, caregiver) for room in rooms for caregiver in caregivers)
        ]
    if rooms:
        return [_normalize_option(room, index=index) for index, room in enumerate(rooms)]
    if caregivers:
        return [_normalize_option(caregiver, index=index) for index, caregiver in enumerate(caregivers)]
    return []


def _combine_room_and_caregiver(room: dict[str, Any], caregiver: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "option_id": f"option_{index + 1:03d}",
        "room_id": _room_id(room),
        "room_status": _room_status(room),
        "caregiver_id": _caregiver_id(caregiver),
        "caregiver_status": _caregiver_status(caregiver),
        "room": dict(room),
        "caregiver": dict(caregiver),
    }


def _normalize_option(option: dict[str, Any], *, index: int) -> dict[str, Any]:
    normalized = dict(option)
    normalized.setdefault("option_id", f"option_{index + 1:03d}")
    normalized.setdefault("room_id", _room_id(option))
    normalized.setdefault("room_status", _room_status(option))
    normalized.setdefault("caregiver_id", _caregiver_id(option))
    normalized.setdefault("caregiver_status", _caregiver_status(option))
    return normalized


def _option_id(option: dict[str, Any]) -> str:
    return str(option.get("option_id") or option.get("recommendation_id") or "")


def _room_id(option: dict[str, Any]) -> str:
    room = option.get("room") if isinstance(option.get("room"), dict) else {}
    return str(
        option.get("room_id")
        or option.get("recommended_room_id")
        or option.get("resource_id")
        or room.get("room_id")
        or ""
    )


def _room_status(option: dict[str, Any]) -> str:
    room = option.get("room") if isinstance(option.get("room"), dict) else {}
    metadata = option.get("metadata") if isinstance(option.get("metadata"), dict) else {}
    return str(
        option.get("room_status")
        or option.get("status")
        or metadata.get("room_status")
        or room.get("room_status")
        or room.get("status")
        or ""
    )


def _caregiver_id(option: dict[str, Any]) -> str:
    caregiver = option.get("caregiver") if isinstance(option.get("caregiver"), dict) else {}
    return str(
        option.get("caregiver_id")
        or option.get("caregiver_emp_id")
        or option.get("recommended_caregiver_id")
        or caregiver.get("caregiver_id")
        or caregiver.get("caregiver_emp_id")
        or ""
    )


def _caregiver_status(option: dict[str, Any]) -> str:
    caregiver = option.get("caregiver") if isinstance(option.get("caregiver"), dict) else {}
    metadata = option.get("metadata") if isinstance(option.get("metadata"), dict) else {}
    return str(
        option.get("caregiver_status")
        or option.get("availability_status")
        or metadata.get("caregiver_status")
        or caregiver.get("caregiver_status")
        or caregiver.get("availability_status")
        or caregiver.get("status")
        or ""
    )
