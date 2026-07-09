from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


AI_MEMORY_SCHEMA_VERSION = "oms.v1.ai_memory"

OUTCOME_SUCCESS = "SUCCESS"
OUTCOME_FAILURE = "FAILURE"
OUTCOME_HISTORICAL_CASE = "HISTORICAL_CASE"
SUPPORTED_OUTCOME_TYPES = {
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_HISTORICAL_CASE,
}


@dataclass(frozen=True)
class AIExperienceRecord:
    """Recommendation experience record for later AI context. It is not model training."""

    recommendation_id: str
    context: dict[str, Any]
    reasoning_source: dict[str, Any]
    decision_result: dict[str, Any]
    memory_id: str = field(default_factory=lambda: new_id("aimem"))
    related_domain: str = ""
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AI_MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.memory_id.strip():
            raise ValueError("memory_id is required.")
        if not self.recommendation_id.strip():
            raise ValueError("recommendation_id is required.")
        if not isinstance(self.context, dict) or not self.context:
            raise ValueError("context is required.")
        if not isinstance(self.reasoning_source, dict) or not self.reasoning_source:
            raise ValueError("reasoning_source is required.")
        if not isinstance(self.decision_result, dict) or not self.decision_result:
            raise ValueError("decision_result is required.")
        object.__setattr__(self, "context", copy.deepcopy(dict(self.context)))
        object.__setattr__(self, "reasoning_source", copy.deepcopy(dict(self.reasoning_source)))
        object.__setattr__(self, "decision_result", copy.deepcopy(dict(self.decision_result)))
        object.__setattr__(self, "metadata", copy.deepcopy(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["context"] = copy.deepcopy(self.context)
        payload["reasoning_source"] = copy.deepcopy(self.reasoning_source)
        payload["decision_result"] = copy.deepcopy(self.decision_result)
        payload["metadata"] = copy.deepcopy(self.metadata)
        return payload


@dataclass(frozen=True)
class AILearningFeedback:
    """Human feedback on whether an AI recommendation was adopted or rejected."""

    recommendation_id: str
    actor_emp_id: str
    adopted: bool
    rejected: bool
    outcome: str
    impact: str
    feedback_id: str = field(default_factory=lambda: new_id("aifb"))
    evidence_sources: tuple[str, ...] = ()
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AI_MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.feedback_id.strip():
            raise ValueError("feedback_id is required.")
        if not self.recommendation_id.strip():
            raise ValueError("recommendation_id is required.")
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if self.adopted == self.rejected:
            raise ValueError("Exactly one of adopted or rejected must be true.")
        if not self.outcome.strip():
            raise ValueError("outcome is required.")
        if not self.impact.strip():
            raise ValueError("impact is required.")
        object.__setattr__(self, "evidence_sources", tuple(dict.fromkeys(self.evidence_sources)))
        object.__setattr__(self, "metadata", copy.deepcopy(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_sources"] = list(self.evidence_sources)
        payload["metadata"] = copy.deepcopy(self.metadata)
        return payload


@dataclass(frozen=True)
class AIOutcomeRecord:
    """Settled memory item: success, failure, or historical case."""

    recommendation_id: str
    outcome_type: str
    outcome: str
    impact: str
    lessons: tuple[str, ...]
    outcome_id: str = field(default_factory=lambda: new_id("aiout"))
    feedback_id: str = ""
    evidence_sources: tuple[str, ...] = ()
    recorded_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AI_MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.outcome_id.strip():
            raise ValueError("outcome_id is required.")
        if not self.recommendation_id.strip():
            raise ValueError("recommendation_id is required.")
        if self.outcome_type not in SUPPORTED_OUTCOME_TYPES:
            raise ValueError(f"Unsupported outcome_type: {self.outcome_type}")
        if not self.outcome.strip():
            raise ValueError("outcome is required.")
        if not self.impact.strip():
            raise ValueError("impact is required.")
        lessons = tuple(dict.fromkeys(self.lessons))
        if not lessons:
            raise ValueError("lessons is required.")
        object.__setattr__(self, "lessons", lessons)
        object.__setattr__(self, "evidence_sources", tuple(dict.fromkeys(self.evidence_sources)))
        object.__setattr__(self, "metadata", copy.deepcopy(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lessons"] = list(self.lessons)
        payload["evidence_sources"] = list(self.evidence_sources)
        payload["metadata"] = copy.deepcopy(self.metadata)
        return payload


@dataclass(frozen=True)
class AIMemoryCase:
    """Current memory case snapshot for one recommendation."""

    experience: dict[str, Any]
    feedback_records: tuple[dict[str, Any], ...] = ()
    outcome_records: tuple[dict[str, Any], ...] = ()
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    updated_at: str = field(default_factory=now_iso)
    mutates_business_state: bool = False
    trains_model: bool = False
    auto_optimizes_rules: bool = False
    auto_executes: bool = False
    external_ai_called: bool = False
    schema_version: str = AI_MEMORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.mutates_business_state:
            raise ValueError("AI memory cannot mutate business state.")
        if self.trains_model:
            raise ValueError("AI memory cannot train models.")
        if self.auto_optimizes_rules:
            raise ValueError("AI memory cannot auto optimize rules.")
        if self.auto_executes:
            raise ValueError("AI memory cannot auto execute.")
        if self.external_ai_called:
            raise ValueError("AI memory cannot call external AI.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["experience"] = copy.deepcopy(self.experience)
        payload["feedback_records"] = [copy.deepcopy(item) for item in self.feedback_records]
        payload["outcome_records"] = [copy.deepcopy(item) for item in self.outcome_records]
        payload["audit_records"] = [copy.deepcopy(item) for item in self.audit_records]
        payload["events"] = [copy.deepcopy(item) for item in self.events]
        return payload


class AIMemoryEngine:
    """Record recommendation experience and feedback without training or execution."""

    def __init__(
        self,
        *,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
    ):
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.master_data = master_data or OMSMasterData()
        self._cases: dict[str, AIMemoryCase] = {}

    def create_experience(
        self,
        record: AIExperienceRecord | dict[str, Any],
        *,
        actor_emp_id: str,
        reason: str,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        experience = record if isinstance(record, AIExperienceRecord) else AIExperienceRecord(**record)
        if not reason.strip():
            raise ValueError("reason is required.")
        actor = self.master_data.employee_by_emp(actor_emp_id)
        if experience.recommendation_id in self._cases:
            raise ValueError(f"Duplicate recommendation memory: {experience.recommendation_id}")
        audit_record = self._audit(
            action="ai.memory.created",
            actor=actor,
            reason=reason,
            recommendation_id=experience.recommendation_id,
            memory_id=experience.memory_id,
            correlation_id=correlation_id or str(experience.metadata.get("correlation_id") or ""),
            metadata={
                "feedback_id": "",
                "outcome_id": "",
                "outcome_type": "",
            },
        )
        event = self._event(
            actor=actor,
            action="created",
            reason=reason,
            case=None,
            recommendation_id=experience.recommendation_id,
            memory_id=experience.memory_id,
            correlation_id=correlation_id or str(experience.metadata.get("correlation_id") or ""),
        )
        case = AIMemoryCase(
            experience=experience.to_dict(),
            audit_records=(audit_record,),
            events=(event,),
        )
        self._cases[experience.recommendation_id] = case
        return case.to_dict()

    def record_feedback(
        self,
        feedback: AILearningFeedback | dict[str, Any],
        *,
        actor_emp_id: str,
        reason: str,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        learning_feedback = feedback if isinstance(feedback, AILearningFeedback) else AILearningFeedback(**feedback)
        if actor_emp_id != learning_feedback.actor_emp_id:
            raise PermissionError("actor_emp_id must match feedback actor_emp_id.")
        actor = self.master_data.employee_by_emp(actor_emp_id)
        case = self._case(learning_feedback.recommendation_id)
        audit_record = self._audit(
            action="ai.memory.updated",
            actor=actor,
            reason=reason,
            recommendation_id=learning_feedback.recommendation_id,
            memory_id=str(case.experience["memory_id"]),
            correlation_id=correlation_id or str(learning_feedback.metadata.get("correlation_id") or ""),
            metadata={
                "feedback_id": learning_feedback.feedback_id,
                "outcome_id": "",
                "outcome_type": "",
                "adopted": learning_feedback.adopted,
                "rejected": learning_feedback.rejected,
            },
        )
        updated = AIMemoryCase(
            experience=copy.deepcopy(case.experience),
            feedback_records=(*case.feedback_records, learning_feedback.to_dict()),
            outcome_records=case.outcome_records,
            audit_records=(*case.audit_records, audit_record),
            events=case.events,
        )
        self._cases[learning_feedback.recommendation_id] = updated
        return updated.to_dict()

    def record_outcome(
        self,
        outcome: AIOutcomeRecord | dict[str, Any],
        *,
        actor_emp_id: str,
        reason: str,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        outcome_record = outcome if isinstance(outcome, AIOutcomeRecord) else AIOutcomeRecord(**outcome)
        actor = self.master_data.employee_by_emp(actor_emp_id)
        case = self._case(outcome_record.recommendation_id)
        audit_record = self._audit(
            action="ai.memory.updated",
            actor=actor,
            reason=reason,
            recommendation_id=outcome_record.recommendation_id,
            memory_id=str(case.experience["memory_id"]),
            correlation_id=correlation_id or str(outcome_record.metadata.get("correlation_id") or ""),
            metadata={
                "feedback_id": outcome_record.feedback_id,
                "outcome_id": outcome_record.outcome_id,
                "outcome_type": outcome_record.outcome_type,
            },
        )
        updated_case = AIMemoryCase(
            experience=copy.deepcopy(case.experience),
            feedback_records=case.feedback_records,
            outcome_records=(*case.outcome_records, outcome_record.to_dict()),
            audit_records=(*case.audit_records, audit_record),
            events=case.events,
        )
        event = self._event(
            actor=actor,
            action="outcome_recorded",
            reason=reason,
            case=updated_case,
            recommendation_id=outcome_record.recommendation_id,
            memory_id=str(case.experience["memory_id"]),
            correlation_id=correlation_id or str(outcome_record.metadata.get("correlation_id") or ""),
        )
        final_case = AIMemoryCase(
            experience=copy.deepcopy(updated_case.experience),
            feedback_records=updated_case.feedback_records,
            outcome_records=updated_case.outcome_records,
            audit_records=updated_case.audit_records,
            events=(*updated_case.events, event),
        )
        self._cases[outcome_record.recommendation_id] = final_case
        return final_case.to_dict()

    def memory_case(self, recommendation_id: str) -> dict[str, Any]:
        return self._case(recommendation_id).to_dict()

    def build_context(
        self,
        *,
        related_domain: str | None = None,
        outcome_type: str | None = None,
    ) -> dict[str, Any]:
        if outcome_type is not None and outcome_type not in SUPPORTED_OUTCOME_TYPES:
            raise ValueError(f"Unsupported outcome_type: {outcome_type}")
        cases = list(self._cases.values())
        if related_domain is not None:
            cases = [case for case in cases if str(case.experience.get("related_domain") or "") == related_domain]

        experience_records = [copy.deepcopy(case.experience) for case in cases]
        feedback_records = [copy.deepcopy(feedback) for case in cases for feedback in case.feedback_records]
        outcome_records = [copy.deepcopy(outcome) for case in cases for outcome in case.outcome_records]
        if outcome_type is not None:
            outcome_records = [outcome for outcome in outcome_records if outcome.get("outcome_type") == outcome_type]

        return {
            "schema_version": AI_MEMORY_SCHEMA_VERSION,
            "context_type": "ai_memory",
            "experience_records": experience_records,
            "feedback_records": feedback_records,
            "outcome_records": outcome_records,
            "success_cases": [item for item in outcome_records if item.get("outcome_type") == OUTCOME_SUCCESS],
            "failure_cases": [item for item in outcome_records if item.get("outcome_type") == OUTCOME_FAILURE],
            "historical_cases": [item for item in outcome_records if item.get("outcome_type") == OUTCOME_HISTORICAL_CASE],
            "mutates_business_state": False,
            "trains_model": False,
            "auto_optimizes_rules": False,
            "auto_executes": False,
            "external_ai_called": False,
        }

    def _case(self, recommendation_id: str) -> AIMemoryCase:
        if recommendation_id not in self._cases:
            raise KeyError(f"Unknown recommendation_id: {recommendation_id}")
        return self._cases[recommendation_id]

    def _audit(
        self,
        *,
        action: str,
        actor: Employee,
        reason: str,
        recommendation_id: str,
        memory_id: str,
        correlation_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required.")
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="ai_memory",
            action=action,
            action_type=action,
            reason=reason,
            result="success",
            target_type="ai_memory",
            target_id=memory_id,
            correlation_id=correlation_id or recommendation_id,
            metadata={
                "memory_id": memory_id,
                "recommendation_id": recommendation_id,
                "mutates_business_state": False,
                "trains_model": False,
                "auto_optimizes_rules": False,
                "auto_executes": False,
                "external_ai_called": False,
                **metadata,
            },
        )

    def _event(
        self,
        *,
        actor: Employee,
        action: str,
        reason: str,
        case: AIMemoryCase | None,
        recommendation_id: str,
        memory_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        feedback_count = len(case.feedback_records) if case else 0
        outcome_count = len(case.outcome_records) if case else 0
        event = OMSEvent(
            event_type="ai.memory.available",
            source_module="ai_memory",
            subject=memory_id,
            action=action,
            emp_id=actor.emp,
            actor_name=actor.name,
            correlation_id=correlation_id or recommendation_id,
            payload={
                "memory_id": memory_id,
                "recommendation_id": recommendation_id,
                "action": action,
                "feedback_count": feedback_count,
                "outcome_count": outcome_count,
                "mutates_business_state": False,
                "trains_model": False,
                "auto_optimizes_rules": False,
                "auto_executes": False,
                "external_ai_called": False,
            },
            metadata={"reason": reason},
        )
        return self.event_bus.publish(event)
