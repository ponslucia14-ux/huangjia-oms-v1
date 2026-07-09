from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from .ai_assistant import CONFIDENCE_HIGH, CONFIDENCE_INSUFFICIENT, CONFIDENCE_LOW, CONFIDENCE_MEDIUM
from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


AI_GOVERNANCE_SCHEMA_VERSION = "oms.v1.ai_governance"

GOVERNANCE_PENDING_REVIEW = "PENDING_REVIEW"
GOVERNANCE_APPROVED = "APPROVED"
GOVERNANCE_REJECTED = "REJECTED"
GOVERNANCE_EXPIRED = "EXPIRED"

SUPPORTED_GOVERNANCE_STATUSES = {
    GOVERNANCE_PENDING_REVIEW,
    GOVERNANCE_APPROVED,
    GOVERNANCE_REJECTED,
    GOVERNANCE_EXPIRED,
}

TERMINAL_GOVERNANCE_STATUSES = {
    GOVERNANCE_APPROVED,
    GOVERNANCE_REJECTED,
    GOVERNANCE_EXPIRED,
}

SUPPORTED_GOVERNANCE_CONFIDENCE = {
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_INSUFFICIENT,
}


@dataclass(frozen=True)
class AIRecommendationRecord:
    """Governance record for one AI recommendation. It does not execute the recommendation."""

    recommendation_id: str
    proposer_emp_id: str
    source_reasoning: dict[str, Any]
    evidence_sources: tuple[str, ...]
    confidence: str
    generated_at: str
    recommendation_text: str = ""
    record_id: str = field(default_factory=lambda: new_id("aigovrec"))
    status: str = GOVERNANCE_PENDING_REVIEW
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AI_GOVERNANCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.record_id.strip():
            raise ValueError("record_id is required.")
        if not self.recommendation_id.strip():
            raise ValueError("recommendation_id is required.")
        if not self.proposer_emp_id.strip():
            raise ValueError("proposer_emp_id is required.")
        if not isinstance(self.source_reasoning, dict) or not self.source_reasoning:
            raise ValueError("source_reasoning is required.")
        evidence_sources = tuple(dict.fromkeys(self.evidence_sources))
        if not evidence_sources:
            raise ValueError("evidence_sources is required.")
        if self.confidence not in SUPPORTED_GOVERNANCE_CONFIDENCE:
            raise ValueError(f"Unsupported confidence: {self.confidence}")
        if not self.generated_at.strip():
            raise ValueError("generated_at is required.")
        if self.status != GOVERNANCE_PENDING_REVIEW:
            raise ValueError("AIRecommendationRecord status must start as PENDING_REVIEW.")
        object.__setattr__(self, "source_reasoning", copy.deepcopy(dict(self.source_reasoning)))
        object.__setattr__(self, "evidence_sources", evidence_sources)
        object.__setattr__(self, "metadata", copy.deepcopy(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_reasoning"] = copy.deepcopy(self.source_reasoning)
        payload["evidence_sources"] = list(self.evidence_sources)
        payload["metadata"] = copy.deepcopy(self.metadata)
        return payload


@dataclass(frozen=True)
class AIReview:
    """Human review result for a governed recommendation."""

    recommendation_id: str
    reviewer_emp_id: str
    review_status: str
    reason: str
    review_id: str = field(default_factory=lambda: new_id("aigovrev"))
    reviewed_at: str = field(default_factory=now_iso)
    execution_flow_allowed: bool = False
    policy_id: str = ""
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AI_GOVERNANCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.review_id.strip():
            raise ValueError("review_id is required.")
        if not self.recommendation_id.strip():
            raise ValueError("recommendation_id is required.")
        if not self.reviewer_emp_id.strip():
            raise ValueError("reviewer_emp_id is required.")
        if self.review_status not in TERMINAL_GOVERNANCE_STATUSES:
            raise ValueError("AIReview review_status must be APPROVED, REJECTED, or EXPIRED.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        if self.execution_flow_allowed and self.review_status != GOVERNANCE_APPROVED:
            raise ValueError("Only APPROVED reviews can allow execution flow.")
        object.__setattr__(self, "metadata", copy.deepcopy(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["metadata"] = copy.deepcopy(self.metadata)
        return payload


@dataclass(frozen=True)
class AIGovernancePolicy:
    """Policy that defines who reviews AI recommendations and whether approved items can enter execution flow."""

    name: str
    allowed_reviewer_emp_ids: tuple[str, ...]
    requires_human_review: bool = True
    allow_execution_flow: bool = False
    expires_after_hours: int | None = None
    policy_id: str = field(default_factory=lambda: new_id("aigovpol"))
    schema_version: str = AI_GOVERNANCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id is required.")
        if not self.name.strip():
            raise ValueError("name is required.")
        reviewers = tuple(dict.fromkeys(self.allowed_reviewer_emp_ids))
        if not reviewers:
            raise ValueError("allowed_reviewer_emp_ids is required.")
        if self.expires_after_hours is not None and self.expires_after_hours <= 0:
            raise ValueError("expires_after_hours must be positive when provided.")
        object.__setattr__(self, "allowed_reviewer_emp_ids", reviewers)

    def can_review(self, emp_id: str) -> bool:
        return emp_id in self.allowed_reviewer_emp_ids

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_reviewer_emp_ids"] = list(self.allowed_reviewer_emp_ids)
        return payload


@dataclass(frozen=True)
class AIGovernanceCase:
    """Lifecycle snapshot for a governed recommendation."""

    record: dict[str, Any]
    policy: dict[str, Any]
    current_status: str
    reviews: tuple[dict[str, Any], ...] = ()
    responsibility_chain: tuple[dict[str, Any], ...] = ()
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    execution_flow_allowed: bool = False
    mutates_business_state: bool = False
    auto_executes: bool = False
    auto_approves: bool = False
    external_ai_called: bool = False
    updated_at: str = field(default_factory=now_iso)
    schema_version: str = AI_GOVERNANCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.current_status not in SUPPORTED_GOVERNANCE_STATUSES:
            raise ValueError(f"Unknown governance status: {self.current_status}")
        if self.mutates_business_state:
            raise ValueError("AI governance cannot mutate business state.")
        if self.auto_executes:
            raise ValueError("AI governance cannot auto execute.")
        if self.auto_approves:
            raise ValueError("AI governance cannot auto approve.")
        if self.external_ai_called:
            raise ValueError("AI governance cannot call external AI.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["record"] = copy.deepcopy(self.record)
        payload["policy"] = copy.deepcopy(self.policy)
        payload["reviews"] = [copy.deepcopy(item) for item in self.reviews]
        payload["responsibility_chain"] = [copy.deepcopy(item) for item in self.responsibility_chain]
        payload["audit_records"] = [copy.deepcopy(item) for item in self.audit_records]
        payload["events"] = [copy.deepcopy(item) for item in self.events]
        return payload


class AIGovernanceEngine:
    """Manage the lifecycle of AI recommendations without approval automation or execution."""

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
        self._cases: dict[str, AIGovernanceCase] = {}

    def request_review(
        self,
        record: AIRecommendationRecord | dict[str, Any],
        policy: AIGovernancePolicy | dict[str, Any],
        *,
        requester_emp_id: str,
        reason: str,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        recommendation_record = record if isinstance(record, AIRecommendationRecord) else AIRecommendationRecord(**record)
        governance_policy = policy if isinstance(policy, AIGovernancePolicy) else AIGovernancePolicy(**policy)
        if not reason.strip():
            raise ValueError("reason is required.")
        requester = self.master_data.employee_by_emp(requester_emp_id)
        proposer = self.master_data.employee_by_emp(recommendation_record.proposer_emp_id)
        for reviewer_emp_id in governance_policy.allowed_reviewer_emp_ids:
            self.master_data.employee_by_emp(reviewer_emp_id)
        if recommendation_record.recommendation_id in self._cases:
            raise ValueError(f"Recommendation already under governance: {recommendation_record.recommendation_id}")

        audit_record = self._audit_request(
            record=recommendation_record,
            policy=governance_policy,
            requester=requester,
            proposer=proposer,
            reason=reason,
            correlation_id=correlation_id,
        )
        case = AIGovernanceCase(
            record=recommendation_record.to_dict(),
            policy=governance_policy.to_dict(),
            current_status=GOVERNANCE_PENDING_REVIEW,
            responsibility_chain=(
                {
                    "step": "ai_recommendation_generated",
                    "emp_id": recommendation_record.proposer_emp_id,
                    "actor_name": proposer.name,
                    "timestamp": recommendation_record.generated_at,
                    "result": "GENERATED",
                },
                {
                    "step": "ai_governance_review_requested",
                    "emp_id": requester.emp,
                    "actor_name": requester.name,
                    "timestamp": now_iso(),
                    "result": GOVERNANCE_PENDING_REVIEW,
                },
            ),
            audit_records=(audit_record,),
            execution_flow_allowed=False,
        )
        self._cases[recommendation_record.recommendation_id] = case
        return case.to_dict()

    def approve(self, *, recommendation_id: str, reviewer_emp_id: str, reason: str) -> dict[str, Any]:
        return self._complete_review(
            recommendation_id=recommendation_id,
            reviewer_emp_id=reviewer_emp_id,
            reason=reason,
            review_status=GOVERNANCE_APPROVED,
        )

    def reject(self, *, recommendation_id: str, reviewer_emp_id: str, reason: str) -> dict[str, Any]:
        return self._complete_review(
            recommendation_id=recommendation_id,
            reviewer_emp_id=reviewer_emp_id,
            reason=reason,
            review_status=GOVERNANCE_REJECTED,
        )

    def expire(self, *, recommendation_id: str, reviewer_emp_id: str, reason: str) -> dict[str, Any]:
        return self._complete_review(
            recommendation_id=recommendation_id,
            reviewer_emp_id=reviewer_emp_id,
            reason=reason,
            review_status=GOVERNANCE_EXPIRED,
        )

    def governance_case(self, recommendation_id: str) -> dict[str, Any]:
        return self._case(recommendation_id).to_dict()

    def _complete_review(
        self,
        *,
        recommendation_id: str,
        reviewer_emp_id: str,
        reason: str,
        review_status: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required.")
        case = self._case(recommendation_id)
        if case.current_status != GOVERNANCE_PENDING_REVIEW:
            raise ValueError(f"Recommendation {recommendation_id} is already {case.current_status}.")
        policy = AIGovernancePolicy(**case.policy)
        if not policy.can_review(reviewer_emp_id):
            raise PermissionError(f"{reviewer_emp_id} is not allowed to review recommendation {recommendation_id}.")
        reviewer = self.master_data.employee_by_emp(reviewer_emp_id)
        execution_flow_allowed = bool(policy.allow_execution_flow and review_status == GOVERNANCE_APPROVED)
        review = AIReview(
            recommendation_id=recommendation_id,
            reviewer_emp_id=reviewer_emp_id,
            review_status=review_status,
            reason=reason,
            execution_flow_allowed=execution_flow_allowed,
            policy_id=policy.policy_id,
            correlation_id=str(case.record.get("metadata", {}).get("correlation_id") or ""),
        )
        audit_record = self._audit_completed(
            case=case,
            policy=policy,
            review=review,
            reviewer=reviewer,
            reason=reason,
        )
        event = self._event_completed(
            case=case,
            policy=policy,
            review=review,
            reviewer=reviewer,
            reason=reason,
        )
        updated = AIGovernanceCase(
            record=copy.deepcopy(case.record),
            policy=copy.deepcopy(case.policy),
            current_status=review_status,
            reviews=(*case.reviews, review.to_dict()),
            responsibility_chain=(
                *case.responsibility_chain,
                {
                    "step": "ai_governance_review_completed",
                    "emp_id": reviewer.emp,
                    "actor_name": reviewer.name,
                    "timestamp": review.reviewed_at,
                    "result": review_status,
                },
            ),
            audit_records=(*case.audit_records, audit_record),
            events=(*case.events, event),
            execution_flow_allowed=execution_flow_allowed,
        )
        self._cases[recommendation_id] = updated
        return updated.to_dict()

    def _case(self, recommendation_id: str) -> AIGovernanceCase:
        if recommendation_id not in self._cases:
            raise KeyError(f"Unknown recommendation_id: {recommendation_id}")
        return self._cases[recommendation_id]

    def _audit_request(
        self,
        *,
        record: AIRecommendationRecord,
        policy: AIGovernancePolicy,
        requester: Employee,
        proposer: Employee,
        reason: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=requester.emp,
            actor_name=requester.name,
            module="ai_governance",
            action="ai.governance.review.request",
            action_type="ai.governance.review.request",
            reason=reason,
            result=GOVERNANCE_PENDING_REVIEW,
            target_type="ai_recommendation",
            target_id=record.recommendation_id,
            correlation_id=correlation_id or record.recommendation_id,
            metadata={
                "record_id": record.record_id,
                "recommendation_id": record.recommendation_id,
                "proposer_emp_id": proposer.emp,
                "policy_id": policy.policy_id,
                "review_status": GOVERNANCE_PENDING_REVIEW,
                "reviewer_emp_id": "",
                "requires_human_review": policy.requires_human_review,
                "execution_flow_allowed": False,
                "mutates_business_state": False,
                "auto_executes": False,
                "auto_approves": False,
                "external_ai_called": False,
            },
        )

    def _audit_completed(
        self,
        *,
        case: AIGovernanceCase,
        policy: AIGovernancePolicy,
        review: AIReview,
        reviewer: Employee,
        reason: str,
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=reviewer.emp,
            actor_name=reviewer.name,
            module="ai_governance",
            action="ai.governance.review.completed",
            action_type="ai.governance.review.completed",
            reason=reason,
            result=review.review_status,
            target_type="ai_recommendation",
            target_id=review.recommendation_id,
            correlation_id=review.correlation_id or review.recommendation_id,
            metadata={
                "record_id": case.record["record_id"],
                "recommendation_id": review.recommendation_id,
                "review_id": review.review_id,
                "policy_id": policy.policy_id,
                "review_status": review.review_status,
                "reviewer_emp_id": reviewer.emp,
                "execution_flow_allowed": review.execution_flow_allowed,
                "mutates_business_state": False,
                "auto_executes": False,
                "auto_approves": False,
                "external_ai_called": False,
            },
        )

    def _event_completed(
        self,
        *,
        case: AIGovernanceCase,
        policy: AIGovernancePolicy,
        review: AIReview,
        reviewer: Employee,
        reason: str,
    ) -> dict[str, Any]:
        event = OMSEvent(
            event_type="ai.governance.review.completed",
            source_module="ai_governance",
            subject=review.recommendation_id,
            action="review",
            emp_id=reviewer.emp,
            actor_name=reviewer.name,
            correlation_id=review.correlation_id or review.recommendation_id,
            payload={
                "record_id": case.record["record_id"],
                "recommendation_id": review.recommendation_id,
                "review_id": review.review_id,
                "policy_id": policy.policy_id,
                "review_status": review.review_status,
                "reviewer_emp_id": reviewer.emp,
                "execution_flow_allowed": review.execution_flow_allowed,
                "mutates_business_state": False,
                "auto_executes": False,
                "auto_approves": False,
                "external_ai_called": False,
            },
            metadata={
                "reason": reason,
                "responsibility_chain": "ai_recommendation -> governance_review -> execution_flow_flag",
            },
        )
        return self.event_bus.publish(event)
