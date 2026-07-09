from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from .ai_assistant import CONFIDENCE_HIGH, CONFIDENCE_INSUFFICIENT, CONFIDENCE_LOW, CONFIDENCE_MEDIUM
from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


AI_REASONING_SCHEMA_VERSION = "oms.v1.ai_reasoning"
SUPPORTED_REASONING_CONFIDENCE = {
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_INSUFFICIENT,
}


@dataclass(frozen=True)
class ReasoningContext:
    """Read-only reasoning input assembled from AI, knowledge, metrics, alerts, and domain data."""

    actor_emp_id: str
    question: str
    ai_context: dict[str, Any] = field(default_factory=dict)
    knowledge_retrieval_result: dict[str, Any] = field(default_factory=dict)
    metrics: tuple[dict[str, Any], ...] = ()
    alerts: tuple[dict[str, Any], ...] = ()
    domain_data: tuple[dict[str, Any], ...] = ()
    context_id: str = field(default_factory=lambda: new_id("rctx"))
    correlation_id: str = ""
    created_at: str = field(default_factory=now_iso)
    schema_version: str = AI_REASONING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.context_id.strip():
            raise ValueError("context_id is required.")
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if not self.question.strip():
            raise ValueError("question is required.")
        object.__setattr__(self, "ai_context", _to_dict(self.ai_context))
        object.__setattr__(self, "knowledge_retrieval_result", _to_dict(self.knowledge_retrieval_result))
        object.__setattr__(self, "metrics", _freeze_records(self.metrics))
        object.__setattr__(self, "alerts", _freeze_records(self.alerts))
        object.__setattr__(self, "domain_data", _freeze_records(self.domain_data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "context_id": self.context_id,
            "actor_emp_id": self.actor_emp_id,
            "question": self.question,
            "ai_context": copy.deepcopy(self.ai_context),
            "knowledge_retrieval_result": copy.deepcopy(self.knowledge_retrieval_result),
            "metrics": [copy.deepcopy(item) for item in self.metrics],
            "alerts": [copy.deepcopy(item) for item in self.alerts],
            "domain_data": [copy.deepcopy(item) for item in self.domain_data],
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ReasoningStep:
    """A single explainable reasoning step."""

    order: int
    description: str
    input_sources: tuple[str, ...]
    output: str
    confidence: str = CONFIDENCE_MEDIUM
    step_id: str = field(default_factory=lambda: new_id("rstep"))
    schema_version: str = AI_REASONING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.step_id.strip():
            raise ValueError("step_id is required.")
        if self.order <= 0:
            raise ValueError("order must be positive.")
        if not self.description.strip():
            raise ValueError("description is required.")
        if not self.output.strip():
            raise ValueError("output is required.")
        if self.confidence not in SUPPORTED_REASONING_CONFIDENCE:
            raise ValueError(f"Unsupported confidence: {self.confidence}")
        object.__setattr__(self, "input_sources", tuple(dict.fromkeys(self.input_sources)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["input_sources"] = list(self.input_sources)
        return payload


@dataclass(frozen=True)
class ReasoningChain:
    """Replayable reasoning chain with source references."""

    context_id: str
    steps: tuple[ReasoningStep | dict[str, Any], ...]
    evidence_sources: tuple[dict[str, Any], ...]
    chain_id: str = field(default_factory=lambda: new_id("rchain"))
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = AI_REASONING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.chain_id.strip():
            raise ValueError("chain_id is required.")
        if not self.context_id.strip():
            raise ValueError("context_id is required.")
        steps = tuple(_coerce_step(item) for item in self.steps)
        if not steps:
            raise ValueError("steps is required.")
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "evidence_sources", _freeze_records(self.evidence_sources))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "chain_id": self.chain_id,
            "context_id": self.context_id,
            "steps": [step.to_dict() for step in self.steps],
            "evidence_sources": [copy.deepcopy(item) for item in self.evidence_sources],
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class ReasoningResult:
    """Traceable AI reasoning output."""

    reasoning_chain: ReasoningChain | dict[str, Any]
    conclusions: tuple[dict[str, Any], ...]
    evidence_sources: tuple[dict[str, Any], ...]
    confidence: str
    uncertainty: tuple[str, ...]
    result_id: str = field(default_factory=lambda: new_id("rres"))
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = AI_REASONING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.result_id.strip():
            raise ValueError("result_id is required.")
        if self.confidence not in SUPPORTED_REASONING_CONFIDENCE:
            raise ValueError(f"Unsupported confidence: {self.confidence}")
        chain = self.reasoning_chain if isinstance(self.reasoning_chain, ReasoningChain) else _chain_from_dict(self.reasoning_chain)
        conclusions = tuple(copy.deepcopy(dict(item)) for item in self.conclusions)
        if not conclusions:
            raise ValueError("conclusions is required.")
        for item in conclusions:
            if not str(item.get("statement") or "").strip():
                raise ValueError("conclusion statement is required.")
            if not item.get("source_ids"):
                raise ValueError("conclusion source_ids is required.")
            if not item.get("reasoning_step_ids"):
                raise ValueError("conclusion reasoning_step_ids is required.")
        object.__setattr__(self, "reasoning_chain", chain)
        object.__setattr__(self, "conclusions", conclusions)
        object.__setattr__(self, "evidence_sources", _freeze_records(self.evidence_sources))
        object.__setattr__(self, "uncertainty", tuple(dict.fromkeys(self.uncertainty)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "result_id": self.result_id,
            "reasoning_chain": self.reasoning_chain.to_dict(),
            "conclusions": [copy.deepcopy(item) for item in self.conclusions],
            "evidence_sources": [copy.deepcopy(item) for item in self.evidence_sources],
            "confidence": self.confidence,
            "uncertainty": list(self.uncertainty),
            "generated_at": self.generated_at,
        }


class AIReasoningEngine:
    """P24 explainable reasoning foundation. It is rule-based and read-only."""

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

    def reason(self, context: ReasoningContext | dict[str, Any]) -> dict[str, Any]:
        reasoning_context = context if isinstance(context, ReasoningContext) else ReasoningContext(**context)
        actor = self.master_data.employee_by_emp(reasoning_context.actor_emp_id)
        context_snapshot = reasoning_context.to_dict()

        request_audit = self._audit_request(reasoning_context, actor)
        result = self._build_result(reasoning_context)
        completed_audit = self._audit_completed(reasoning_context, actor, result)
        event = self._event_completed(reasoning_context, actor, result)

        if context_snapshot != reasoning_context.to_dict():
            raise RuntimeError("AI reasoning attempted to mutate source context.")

        return {
            "schema_version": AI_REASONING_SCHEMA_VERSION,
            "context": reasoning_context.to_dict(),
            "reasoning_chain": result.reasoning_chain.to_dict(),
            "result": result.to_dict(),
            "audit_records": [request_audit, completed_audit],
            "event": event,
            "mutates_business_state": False,
            "auto_executes": False,
            "auto_approves": False,
            "external_ai_called": False,
        }

    def _build_result(self, context: ReasoningContext) -> ReasoningResult:
        evidence = collect_evidence_sources(context)
        evidence_ids = tuple(item["source_id"] for item in evidence)
        confidence = _confidence_for(evidence)
        uncertainty = _uncertainty_for(context, evidence)
        steps = _build_steps(context, evidence, confidence)
        chain = ReasoningChain(context_id=context.context_id, steps=tuple(steps), evidence_sources=tuple(evidence))
        conclusions = _build_conclusions(context, evidence, steps, confidence)
        return ReasoningResult(
            reasoning_chain=chain,
            conclusions=tuple(conclusions),
            evidence_sources=tuple(evidence),
            confidence=confidence,
            uncertainty=tuple(uncertainty),
        )

    def _audit_request(self, context: ReasoningContext, actor: Employee) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="ai_reasoning",
            action="ai.reasoning.request",
            action_type="ai.reasoning.request",
            reason="AI reasoning requested.",
            result="success",
            target_type="ai_reasoning",
            target_id=context.context_id,
            correlation_id=context.correlation_id,
            metadata={
                "context_id": context.context_id,
                "question": context.question,
                "external_ai_called": False,
                "mutates_business_state": False,
            },
        )

    def _audit_completed(
        self,
        context: ReasoningContext,
        actor: Employee,
        result: ReasoningResult,
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="ai_reasoning",
            action="ai.reasoning.completed",
            action_type="ai.reasoning.completed",
            reason="AI reasoning completed.",
            result="success",
            target_type="ai_reasoning_result",
            target_id=result.result_id,
            correlation_id=context.correlation_id,
            metadata={
                "context_id": context.context_id,
                "result_id": result.result_id,
                "evidence_count": len(result.evidence_sources),
                "conclusion_count": len(result.conclusions),
                "confidence": result.confidence,
                "external_ai_called": False,
                "mutates_business_state": False,
            },
        )

    def _event_completed(
        self,
        context: ReasoningContext,
        actor: Employee,
        result: ReasoningResult,
    ) -> dict[str, Any]:
        event = OMSEvent(
            event_type="ai.reasoning.completed",
            source_module="ai_reasoning",
            subject=result.result_id,
            action="reason",
            emp_id=actor.emp,
            actor_name=actor.name,
            correlation_id=context.correlation_id,
            payload={
                "context_id": context.context_id,
                "result_id": result.result_id,
                "confidence": result.confidence,
                "evidence_count": len(result.evidence_sources),
                "conclusion_count": len(result.conclusions),
                "external_ai_called": False,
                "mutates_business_state": False,
                "auto_executes": False,
                "auto_approves": False,
            },
        )
        return self.event_bus.publish(event)


def collect_evidence_sources(context: ReasoningContext) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    sources.extend(_knowledge_sources(context.knowledge_retrieval_result))
    sources.extend(_metric_sources(context.metrics))
    sources.extend(_metric_sources(_records(context.ai_context.get("metrics"))))
    sources.extend(_alert_sources(context.alerts))
    sources.extend(_alert_sources(_records(context.ai_context.get("alerts"))))
    sources.extend(_domain_sources(context.domain_data))
    if not sources:
        sources.append(
            {
                "source_id": context.context_id,
                "source_type": "reasoning_context",
                "domain": "",
                "version": context.schema_version,
                "title": "No evidence available",
            }
        )
    return _dedupe_sources(sources)


def _build_steps(context: ReasoningContext, evidence: list[dict[str, Any]], confidence: str) -> list[ReasoningStep]:
    source_ids = tuple(item["source_id"] for item in evidence)
    steps = [
        ReasoningStep(
            order=1,
            description="Collect available evidence.",
            input_sources=source_ids,
            output=f"Collected {len(evidence)} evidence source(s).",
            confidence=confidence,
        )
    ]
    knowledge_ids = tuple(item["source_id"] for item in evidence if item["source_type"] == "knowledge")
    if knowledge_ids:
        steps.append(
            ReasoningStep(
                order=2,
                description="Evaluate retrieved knowledge evidence.",
                input_sources=knowledge_ids,
                output=f"Knowledge evidence supports the reasoning with {len(knowledge_ids)} matched item(s).",
                confidence=confidence,
            )
        )
    operational_ids = tuple(item["source_id"] for item in evidence if item["source_type"] in {"metric", "alert", "domain_data"})
    if operational_ids:
        steps.append(
            ReasoningStep(
                order=len(steps) + 1,
                description="Evaluate operating evidence.",
                input_sources=operational_ids,
                output=f"Operating evidence contains {len(operational_ids)} metric, alert, or domain source(s).",
                confidence=confidence,
            )
        )
    return steps


def _build_conclusions(
    context: ReasoningContext,
    evidence: list[dict[str, Any]],
    steps: list[ReasoningStep],
    confidence: str,
) -> list[dict[str, Any]]:
    step_ids = [step.step_id for step in steps]
    conclusions: list[dict[str, Any]] = []
    knowledge_ids = [item["source_id"] for item in evidence if item["source_type"] == "knowledge"]
    metric_ids = [item["source_id"] for item in evidence if item["source_type"] == "metric"]
    alert_ids = [item["source_id"] for item in evidence if item["source_type"] == "alert"]
    domain_ids = [item["source_id"] for item in evidence if item["source_type"] == "domain_data"]
    fallback_ids = [item["source_id"] for item in evidence]

    if knowledge_ids:
        conclusions.append(_conclusion("Relevant knowledge evidence is available for this reasoning request.", knowledge_ids, step_ids, confidence))
    if metric_ids:
        conclusions.append(_conclusion("Metric evidence is available and can support quantitative analysis.", metric_ids, step_ids, confidence))
    if alert_ids:
        conclusions.append(_conclusion("Active alert evidence should be considered before operational action.", alert_ids, step_ids, confidence))
    if domain_ids:
        conclusions.append(_conclusion("Domain data evidence is available for business context grounding.", domain_ids, step_ids, confidence))
    if not conclusions:
        conclusions.append(_conclusion("Insufficient evidence for reliable reasoning.", fallback_ids, step_ids, CONFIDENCE_INSUFFICIENT))
    return conclusions


def _conclusion(statement: str, source_ids: list[str], step_ids: list[str], confidence: str) -> dict[str, Any]:
    return {
        "conclusion_id": new_id("rconc"),
        "statement": statement,
        "source_ids": list(dict.fromkeys(source_ids)),
        "reasoning_step_ids": list(dict.fromkeys(step_ids)),
        "confidence": confidence,
    }


def _knowledge_sources(retrieval_result: dict[str, Any]) -> list[dict[str, Any]]:
    matches = _records(retrieval_result.get("matched_knowledge"))
    if not matches:
        matches = _records(_to_dict(retrieval_result.get("ai_context_reference")).get("knowledge_entries"))
    sources: list[dict[str, Any]] = []
    for item in matches:
        knowledge_id = str(item.get("knowledge_id") or "")
        if not knowledge_id:
            continue
        domains = item.get("related_domains") or [item.get("related_domain")]
        domain = str(domains[0] if isinstance(domains, list) and domains else "")
        sources.append(
            {
                "source_id": knowledge_id,
                "source_type": "knowledge",
                "domain": domain,
                "version": str(item.get("version") or ""),
                "title": str(item.get("title") or knowledge_id),
            }
        )
    return sources


def _metric_sources(metrics: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for index, item in enumerate(_records(metrics), start=1):
        metric_id = str(item.get("metric_id") or item.get("id") or f"metric_{index}")
        sources.append(
            {
                "source_id": metric_id,
                "source_type": "metric",
                "domain": str(item.get("source_domain") or item.get("category") or item.get("domain") or ""),
                "version": str(item.get("schema_version") or ""),
                "title": str(item.get("name") or metric_id),
            }
        )
    return sources


def _alert_sources(alerts: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for index, item in enumerate(_records(alerts), start=1):
        alert_id = str(item.get("alert_id") or item.get("id") or f"alert_{index}")
        sources.append(
            {
                "source_id": alert_id,
                "source_type": "alert",
                "domain": str(item.get("domain") or ""),
                "version": str(item.get("schema_version") or ""),
                "title": str(item.get("name") or item.get("alert_code") or alert_id),
                "severity": str(item.get("severity") or ""),
                "status": str(item.get("status") or ""),
            }
        )
    return sources


def _domain_sources(domain_data: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for index, item in enumerate(_records(domain_data), start=1):
        source_id = str(
            item.get("entity_id")
            or item.get("domain_id")
            or item.get("id")
            or item.get("room_id")
            or item.get("stay_id")
            or item.get("contract_id")
            or item.get("tx_id")
            or f"domain_data_{index}"
        )
        sources.append(
            {
                "source_id": source_id,
                "source_type": "domain_data",
                "domain": str(item.get("domain") or item.get("entity") or ""),
                "version": str(item.get("schema_version") or ""),
                "title": str(item.get("title") or item.get("name") or source_id),
            }
        )
    return sources


def _confidence_for(evidence: list[dict[str, Any]]) -> str:
    real_sources = [item for item in evidence if item.get("source_type") != "reasoning_context"]
    if len(real_sources) >= 4:
        return CONFIDENCE_HIGH
    if len(real_sources) >= 2:
        return CONFIDENCE_MEDIUM
    if len(real_sources) == 1:
        return CONFIDENCE_LOW
    return CONFIDENCE_INSUFFICIENT


def _uncertainty_for(context: ReasoningContext, evidence: list[dict[str, Any]]) -> list[str]:
    real_sources = [item for item in evidence if item.get("source_type") != "reasoning_context"]
    if not real_sources:
        return ["No evidence sources were provided."]
    uncertainty: list[str] = []
    source_types = {item.get("source_type") for item in real_sources}
    if "knowledge" not in source_types:
        uncertainty.append("No knowledge retrieval evidence was provided.")
    if "metric" not in source_types:
        uncertainty.append("No metric evidence was provided.")
    if "domain_data" not in source_types:
        uncertainty.append("No domain data evidence was provided.")
    return uncertainty


def _coerce_step(item: ReasoningStep | dict[str, Any]) -> ReasoningStep:
    if isinstance(item, ReasoningStep):
        return item
    return ReasoningStep(**dict(item))


def _chain_from_dict(payload: dict[str, Any]) -> ReasoningChain:
    data = dict(payload)
    return ReasoningChain(
        chain_id=data.get("chain_id", new_id("rchain")),
        context_id=data["context_id"],
        steps=tuple(data.get("steps", ())),
        evidence_sources=tuple(data.get("evidence_sources", ())),
        generated_at=data.get("generated_at", now_iso()),
        schema_version=data.get("schema_version", AI_REASONING_SCHEMA_VERSION),
    )


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in sources:
        source_id = str(item.get("source_id") or "")
        if not source_id:
            continue
        deduped.setdefault(source_id, copy.deepcopy(item))
    return list(deduped.values())


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, tuple):
        value = list(value)
    if not isinstance(value, list):
        return []
    return [copy.deepcopy(dict(item)) for item in value if isinstance(item, dict)]


def _freeze_records(records: Any) -> tuple[dict[str, Any], ...]:
    return tuple(copy.deepcopy(dict(item)) for item in records)


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return copy.deepcopy(value.to_dict())
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return {}
