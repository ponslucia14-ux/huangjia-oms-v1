from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .business_rules import BusinessRulesEngine, RuleContext, RULE_PASS, RULE_REJECT, RULE_WARNING


SCHEDULER_SCHEMA_VERSION = "oms.v1.scheduler"
SCHEDULING_PASS = "PASS"
SCHEDULING_WARNING = "WARNING"
SCHEDULING_REJECT = "REJECT"
SCHEDULING_RESULT_ORDER = {SCHEDULING_PASS: 0, SCHEDULING_WARNING: 1, SCHEDULING_REJECT: 2}


@dataclass(frozen=True)
class SchedulingRequest:
    """Read-only scheduling input. Stay is the required scheduling subject."""

    stay: dict[str, Any]
    actor_emp_id: str
    requested_room_id: str = ""
    requested_caregiver_id: str = ""
    requirements: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    schema_version: str = SCHEDULER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.stay:
            raise ValueError("stay is required.")
        if not self.actor_emp_id:
            raise ValueError("actor_emp_id is required.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SchedulingContext:
    """Read-only resources and rule engine available to scheduler."""

    rooms: tuple[dict[str, Any], ...] = ()
    caregivers: tuple[dict[str, Any], ...] = ()
    business_rules: BusinessRulesEngine | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEDULER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "rooms": list(self.rooms),
            "caregivers": list(self.caregivers),
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SchedulingResult:
    request: dict[str, Any]
    status: str
    reason: str
    room_candidates: tuple[SchedulingCandidate, ...]
    caregiver_candidates: tuple[SchedulingCandidate, ...]
    recommendations: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    rejects: tuple[str, ...] = ()
    mutates_business_state: bool = False
    schema_version: str = SCHEDULER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.status not in SCHEDULING_RESULT_ORDER:
            raise ValueError(f"Unknown scheduling status: {self.status}")
        if not self.reason.strip():
            raise ValueError("scheduling result reason is required.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["room_candidates"] = [candidate.to_dict() for candidate in self.room_candidates]
        payload["caregiver_candidates"] = [candidate.to_dict() for candidate in self.caregiver_candidates]
        return payload


class SchedulerEngine:
    """Analyze scheduling context and return suggestions without mutating resources."""

    def __init__(self, *, business_rules: BusinessRulesEngine | None = None):
        self.business_rules = business_rules

    def schedule(self, request: SchedulingRequest | dict[str, Any], context: SchedulingContext | dict[str, Any]) -> dict[str, Any]:
        scheduling_request = request if isinstance(request, SchedulingRequest) else SchedulingRequest(**request)
        scheduling_context = context if isinstance(context, SchedulingContext) else SchedulingContext(**context)
        rules = scheduling_context.business_rules or self.business_rules

        room_candidates = tuple(
            self._room_candidate(room, scheduling_request=scheduling_request, rules=rules)
            for room in scheduling_context.rooms
        )
        caregiver_candidates = tuple(
            self._caregiver_candidate(caregiver, scheduling_request=scheduling_request)
            for caregiver in scheduling_context.caregivers
        )
        warnings = tuple(
            candidate.reason
            for candidate in [*room_candidates, *caregiver_candidates]
            if candidate.status == SCHEDULING_WARNING
        )
        rejects = tuple(
            candidate.reason
            for candidate in [*room_candidates, *caregiver_candidates]
            if candidate.status == SCHEDULING_REJECT
        )
        recommendations = self._recommendations(room_candidates, caregiver_candidates)
        status, reason = self._overall_status(
            room_candidates=room_candidates,
            caregiver_candidates=caregiver_candidates,
            recommendations=recommendations,
        )
        return SchedulingResult(
            request=scheduling_request.to_dict(),
            status=status,
            reason=reason,
            room_candidates=room_candidates,
            caregiver_candidates=caregiver_candidates,
            recommendations=tuple(recommendations),
            warnings=warnings,
            rejects=rejects,
            mutates_business_state=False,
        ).to_dict()

    @staticmethod
    def _room_candidate(
        room: dict[str, Any],
        *,
        scheduling_request: SchedulingRequest,
        rules: BusinessRulesEngine | None,
    ) -> SchedulingCandidate:
        room_id = str(room.get("room_id") or "")
        status = str(room.get("status") or "")
        if scheduling_request.requested_room_id and room_id != scheduling_request.requested_room_id:
            return SchedulingCandidate(
                resource_type="room",
                resource_id=room_id,
                status=SCHEDULING_WARNING,
                reason="Room does not match requested_room_id.",
                metadata={"room_status": status},
            )
        if status != "AVAILABLE":
            base_status = SCHEDULING_WARNING if status == "RESERVED" else SCHEDULING_REJECT
            base_reason = f"Room status is {status}; scheduler can only suggest AVAILABLE rooms."
        else:
            base_status = SCHEDULING_PASS
            base_reason = "Room is available for scheduling suggestion."

        rule_status = RULE_PASS
        rule_reasons: tuple[str, ...] = ()
        if rules is not None:
            rule_result = rules.evaluate(
                RuleContext(
                    action="check_in_room",
                    actor_emp_id=scheduling_request.actor_emp_id,
                    domain="Room",
                    required_fields=("room_id",),
                    data={
                        "room_id": room_id,
                        "room": room,
                        "stay": scheduling_request.stay,
                    },
                )
            )
            rule_status = str(rule_result["overall_status"])
            rule_reasons = tuple(rule_result["reject_reasons"] + rule_result["warning_reasons"])
        final_status = _max_status(base_status, _rule_to_schedule_status(rule_status))
        final_reason = "; ".join([base_reason, *rule_reasons]).strip("; ")
        return SchedulingCandidate(
            resource_type="room",
            resource_id=room_id,
            status=final_status,
            reason=final_reason,
            rule_status=rule_status,
            rule_reasons=rule_reasons,
            metadata={"room_status": status},
        )

    @staticmethod
    def _caregiver_candidate(caregiver: dict[str, Any], *, scheduling_request: SchedulingRequest) -> SchedulingCandidate:
        caregiver_id = str(caregiver.get("caregiver_id") or "")
        status = str(caregiver.get("status") or "")
        if scheduling_request.requested_caregiver_id and caregiver_id != scheduling_request.requested_caregiver_id:
            return SchedulingCandidate(
                resource_type="caregiver",
                resource_id=caregiver_id,
                status=SCHEDULING_WARNING,
                reason="Caregiver does not match requested_caregiver_id.",
                metadata={"caregiver_status": status},
            )
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
        room_candidates: tuple[SchedulingCandidate, ...],
        caregiver_candidates: tuple[SchedulingCandidate, ...],
    ) -> list[dict[str, Any]]:
        available_rooms = [candidate for candidate in room_candidates if candidate.status == SCHEDULING_PASS]
        available_caregivers = [candidate for candidate in caregiver_candidates if candidate.status == SCHEDULING_PASS]
        if not available_rooms and not available_caregivers:
            return []
        return [
            {
                "room_id": available_rooms[0].resource_id if available_rooms else "",
                "caregiver_id": available_caregivers[0].resource_id if available_caregivers else "",
                "reason": "First available resources are suggested; no optimal algorithm is applied in P12.",
                "auto_assigned": False,
            }
        ]

    @staticmethod
    def _overall_status(
        *,
        room_candidates: tuple[SchedulingCandidate, ...],
        caregiver_candidates: tuple[SchedulingCandidate, ...],
        recommendations: list[dict[str, Any]],
    ) -> tuple[str, str]:
        if not room_candidates:
            return SCHEDULING_WARNING, "No room resources were provided for scheduling analysis."
        if not caregiver_candidates:
            return SCHEDULING_WARNING, "No caregiver resources were provided for scheduling analysis."
        if recommendations:
            candidate_status = max(
                (candidate.status for candidate in [*room_candidates, *caregiver_candidates]),
                key=lambda status: SCHEDULING_RESULT_ORDER[status],
            )
            if candidate_status == SCHEDULING_REJECT:
                return SCHEDULING_WARNING, "Scheduling suggestions exist, but some resources were rejected."
            if candidate_status == SCHEDULING_WARNING:
                return SCHEDULING_WARNING, "Scheduling suggestions exist with non-blocking warnings."
            return SCHEDULING_PASS, "Scheduling suggestions generated without modifying resources."
        return SCHEDULING_REJECT, "No schedulable room or caregiver candidate was available."


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
