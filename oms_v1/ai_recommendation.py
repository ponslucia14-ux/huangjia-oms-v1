from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from .ai_assistant import CONFIDENCE_HIGH, CONFIDENCE_INSUFFICIENT, CONFIDENCE_LOW, CONFIDENCE_MEDIUM
from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


AI_RECOMMENDATION_SCHEMA_VERSION = "oms.v1.ai_recommendation"

PRIORITY_LOW = "LOW"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_HIGH = "HIGH"
PRIORITY_CRITICAL = "CRITICAL"
SUPPORTED_PRIORITIES = {PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL}

SUPPORTED_RECOMMENDATION_CONFIDENCE = {
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_INSUFFICIENT,
}


@dataclass(frozen=True)
class RecommendationContext:
    """Read-only recommendation input built from reasoning, metrics, alerts, and knowledge."""

    actor_emp_id: str
    objective: str = "Generate operating recommendations."
    reasoning_result: dict[str, Any] = field(default_factory=dict)
    metrics: tuple[dict[str, Any], ...] = ()
    alerts: tuple[dict[str, Any], ...] = ()
    knowledge_context: dict[str, Any] = field(default_factory=dict)
    context_id: str = field(default_factory=lambda: new_id("recctx"))
    correlation_id: str = ""
    created_at: str = field(default_factory=now_iso)
    schema_version: str = AI_RECOMMENDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.context_id.strip():
            raise ValueError("context_id is required.")
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if not self.objective.strip():
            raise ValueError("objective is required.")
        object.__setattr__(self, "reasoning_result", _to_dict(self.reasoning_result))
        object.__setattr__(self, "metrics", _freeze_records(self.metrics))
        object.__setattr__(self, "alerts", _freeze_records(self.alerts))
        object.__setattr__(self, "knowledge_context", _to_dict(self.knowledge_context))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "context_id": self.context_id,
            "actor_emp_id": self.actor_emp_id,
            "objective": self.objective,
            "reasoning_result": copy.deepcopy(self.reasoning_result),
            "metrics": [copy.deepcopy(item) for item in self.metrics],
            "alerts": [copy.deepcopy(item) for item in self.alerts],
            "knowledge_context": copy.deepcopy(self.knowledge_context),
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RecommendationItem:
    """Single explainable recommendation that is not an executable command."""

    recommendation: str
    priority: str
    expected_impact: str
    evidence_sources: tuple[str, ...]
    confidence: str
    risks: tuple[str, ...]
    basis: str
    related_domain: str = ""
    recommendation_id: str = field(default_factory=lambda: new_id("rec"))
    created_at: str = field(default_factory=now_iso)
    schema_version: str = AI_RECOMMENDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.recommendation_id.strip():
            raise ValueError("recommendation_id is required.")
        if not self.recommendation.strip():
            raise ValueError("recommendation is required.")
        if self.priority not in SUPPORTED_PRIORITIES:
            raise ValueError(f"Unsupported priority: {self.priority}")
        if not self.expected_impact.strip():
            raise ValueError("expected_impact is required.")
        if not self.basis.strip():
            raise ValueError("basis is required.")
        if self.confidence not in SUPPORTED_RECOMMENDATION_CONFIDENCE:
            raise ValueError(f"Unsupported confidence: {self.confidence}")
        evidence_sources = tuple(dict.fromkeys(self.evidence_sources))
        risks = tuple(dict.fromkeys(self.risks))
        if not evidence_sources:
            raise ValueError("evidence_sources is required.")
        if not risks:
            raise ValueError("risks is required.")
        object.__setattr__(self, "evidence_sources", evidence_sources)
        object.__setattr__(self, "risks", risks)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_sources"] = list(self.evidence_sources)
        payload["risks"] = list(self.risks)
        return payload


@dataclass(frozen=True)
class RecommendationResult:
    """Traceable recommendation result."""

    context_id: str
    recommendations: tuple[RecommendationItem | dict[str, Any], ...]
    evidence_sources: tuple[dict[str, Any], ...]
    confidence: str
    result_id: str = field(default_factory=lambda: new_id("recres"))
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = AI_RECOMMENDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.result_id.strip():
            raise ValueError("result_id is required.")
        if not self.context_id.strip():
            raise ValueError("context_id is required.")
        if self.confidence not in SUPPORTED_RECOMMENDATION_CONFIDENCE:
            raise ValueError(f"Unsupported confidence: {self.confidence}")
        recommendations = tuple(_coerce_recommendation(item) for item in self.recommendations)
        if not recommendations:
            raise ValueError("recommendations is required.")
        object.__setattr__(self, "recommendations", recommendations)
        object.__setattr__(self, "evidence_sources", _freeze_records(self.evidence_sources))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "result_id": self.result_id,
            "context_id": self.context_id,
            "recommendations": [item.to_dict() for item in self.recommendations],
            "recommendation_count": len(self.recommendations),
            "evidence_sources": [copy.deepcopy(item) for item in self.evidence_sources],
            "confidence": self.confidence,
            "generated_at": self.generated_at,
        }


class AIRecommendationEngine:
    """P25 recommendation foundation. It is rule-based and non-executing."""

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

    def recommend(self, context: RecommendationContext | dict[str, Any]) -> dict[str, Any]:
        recommendation_context = context if isinstance(context, RecommendationContext) else RecommendationContext(**context)
        actor = self.master_data.employee_by_emp(recommendation_context.actor_emp_id)
        context_snapshot = recommendation_context.to_dict()

        request_audit = self._audit_request(recommendation_context, actor)
        result = self._build_result(recommendation_context)
        generated_audit = self._audit_generated(recommendation_context, actor, result)
        event = self._event_generated(recommendation_context, actor, result)

        if context_snapshot != recommendation_context.to_dict():
            raise RuntimeError("AI recommendation attempted to mutate source context.")

        return {
            "schema_version": AI_RECOMMENDATION_SCHEMA_VERSION,
            "context": recommendation_context.to_dict(),
            "result": result.to_dict(),
            "recommendations": [item.to_dict() for item in result.recommendations],
            "audit_records": [request_audit, generated_audit],
            "event": event,
            "mutates_business_state": False,
            "auto_executes": False,
            "auto_approves": False,
            "external_ai_called": False,
        }

    def _build_result(self, context: RecommendationContext) -> RecommendationResult:
        evidence = collect_recommendation_evidence(context)
        confidence = _confidence_for(context, evidence)
        recommendations = _generate_recommendations(context, evidence, confidence)
        return RecommendationResult(
            context_id=context.context_id,
            recommendations=tuple(recommendations),
            evidence_sources=tuple(evidence),
            confidence=confidence,
        )

    def _audit_request(self, context: RecommendationContext, actor: Employee) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="ai_recommendation",
            action="ai.recommendation.request",
            action_type="ai.recommendation.request",
            reason="AI recommendation requested.",
            result="success",
            target_type="ai_recommendation",
            target_id=context.context_id,
            correlation_id=context.correlation_id,
            metadata={
                "context_id": context.context_id,
                "objective": context.objective,
                "external_ai_called": False,
                "mutates_business_state": False,
                "auto_executes": False,
                "auto_approves": False,
            },
        )

    def _audit_generated(
        self,
        context: RecommendationContext,
        actor: Employee,
        result: RecommendationResult,
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="ai_recommendation",
            action="ai.recommendation.generated",
            action_type="ai.recommendation.generated",
            reason="AI recommendation generated.",
            result="success",
            target_type="ai_recommendation_result",
            target_id=result.result_id,
            correlation_id=context.correlation_id,
            metadata={
                "context_id": context.context_id,
                "result_id": result.result_id,
                "recommendation_count": len(result.recommendations),
                "evidence_count": len(result.evidence_sources),
                "confidence": result.confidence,
                "external_ai_called": False,
                "mutates_business_state": False,
                "auto_executes": False,
                "auto_approves": False,
            },
        )

    def _event_generated(
        self,
        context: RecommendationContext,
        actor: Employee,
        result: RecommendationResult,
    ) -> dict[str, Any]:
        event = OMSEvent(
            event_type="ai.recommendation.generated",
            source_module="ai_recommendation",
            subject=result.result_id,
            action="recommend",
            emp_id=actor.emp,
            actor_name=actor.name,
            correlation_id=context.correlation_id,
            payload={
                "context_id": context.context_id,
                "result_id": result.result_id,
                "recommendation_count": len(result.recommendations),
                "confidence": result.confidence,
                "external_ai_called": False,
                "mutates_business_state": False,
                "auto_executes": False,
                "auto_approves": False,
            },
        )
        return self.event_bus.publish(event)


def collect_recommendation_evidence(context: RecommendationContext) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    reasoning_payload = _reasoning_payload(context.reasoning_result)
    evidence.extend(_reasoning_sources(reasoning_payload))
    evidence.extend(_conclusion_sources(reasoning_payload))
    evidence.extend(_metric_sources(context.metrics))
    evidence.extend(_alert_sources(context.alerts))
    evidence.extend(_knowledge_sources(context.knowledge_context))
    if not evidence:
        evidence.append(
            {
                "source_id": context.context_id,
                "source_type": "recommendation_context",
                "domain": "",
                "version": context.schema_version,
                "title": "No evidence available",
            }
        )
    return _dedupe_sources(evidence)


def _generate_recommendations(
    context: RecommendationContext,
    evidence: list[dict[str, Any]],
    confidence: str,
) -> list[RecommendationItem]:
    evidence_by_id = {item["source_id"]: item for item in evidence}
    recommendations: list[RecommendationItem] = []
    alert_sources = [item for item in evidence if item.get("source_type") == "alert"]
    conclusion_sources = [item for item in evidence if item.get("source_type") == "reasoning_conclusion"]
    metric_sources = [item for item in evidence if item.get("source_type") == "metric"]
    knowledge_sources = [item for item in evidence if item.get("source_type") == "knowledge"]

    for alert in alert_sources[:3]:
        recommendations.append(_alert_recommendation(alert, confidence))
    for conclusion in conclusion_sources[:3]:
        source_ids = _linked_sources(conclusion, evidence_by_id) or [conclusion["source_id"]]
        recommendations.append(_conclusion_recommendation(conclusion, source_ids, evidence_by_id, confidence))
    if metric_sources:
        recommendations.append(_metric_recommendation(metric_sources[:3], confidence))
    if knowledge_sources and not recommendations:
        recommendations.append(_knowledge_recommendation(knowledge_sources[:3], confidence))
    if not recommendations:
        recommendations.append(
            RecommendationItem(
                recommendation="Collect more evidence before making an operating recommendation.",
                priority=PRIORITY_LOW,
                expected_impact="Avoid acting on insufficient context.",
                evidence_sources=(evidence[0]["source_id"],),
                confidence=CONFIDENCE_INSUFFICIENT,
                risks=("Insufficient evidence can lead to incorrect action.",),
                basis="No metric, alert, reasoning, or knowledge evidence was available.",
                related_domain=str(evidence[0].get("domain") or ""),
            )
        )
    return recommendations


def _alert_recommendation(alert: dict[str, Any], confidence: str) -> RecommendationItem:
    severity = str(alert.get("severity") or "").lower()
    status = str(alert.get("status") or "")
    priority = _priority_for_alert(severity)
    domain = str(alert.get("domain") or "")
    return RecommendationItem(
        recommendation=f"Review open alert: {alert.get('title') or alert['source_id']}.",
        priority=priority,
        expected_impact=f"Reduce operating risk in {domain or 'the related domain'}.",
        evidence_sources=(alert["source_id"],),
        confidence=confidence,
        risks=(f"Alert remains {status or 'unresolved'} if no owner reviews it.",),
        basis=f"Alert source {alert['source_id']} has severity {severity or 'unknown'} and status {status or 'unknown'}.",
        related_domain=domain,
    )


def _conclusion_recommendation(
    conclusion: dict[str, Any],
    source_ids: list[str],
    evidence_by_id: dict[str, dict[str, Any]],
    confidence: str,
) -> RecommendationItem:
    priority = _priority_for_sources(source_ids, evidence_by_id)
    domain = _first_domain(source_ids, evidence_by_id)
    return RecommendationItem(
        recommendation=f"Review reasoning conclusion: {conclusion.get('title') or conclusion['source_id']}.",
        priority=priority,
        expected_impact="Convert explainable analysis into a human-reviewed operating action.",
        evidence_sources=tuple(source_ids),
        confidence=str(conclusion.get("confidence") or confidence),
        risks=("Recommendation requires human review before execution.",),
        basis=f"Generated from reasoning conclusion {conclusion['source_id']}.",
        related_domain=domain,
    )


def _metric_recommendation(metric_sources: list[dict[str, Any]], confidence: str) -> RecommendationItem:
    ids = tuple(item["source_id"] for item in metric_sources)
    domain = str(metric_sources[0].get("domain") or "")
    return RecommendationItem(
        recommendation="Review the related operating metrics before deciding next action.",
        priority=PRIORITY_MEDIUM,
        expected_impact="Improve decision quality with current quantitative signals.",
        evidence_sources=ids,
        confidence=confidence,
        risks=("Metric evidence alone may not explain root cause.",),
        basis=f"Metric evidence includes {len(metric_sources)} source(s).",
        related_domain=domain,
    )


def _knowledge_recommendation(knowledge_sources: list[dict[str, Any]], confidence: str) -> RecommendationItem:
    ids = tuple(item["source_id"] for item in knowledge_sources)
    domain = str(knowledge_sources[0].get("domain") or "")
    return RecommendationItem(
        recommendation="Use the matched knowledge guidance as reference before acting.",
        priority=PRIORITY_LOW,
        expected_impact="Keep operating judgment aligned with approved knowledge assets.",
        evidence_sources=ids,
        confidence=confidence,
        risks=("Knowledge guidance may need current business evidence before execution.",),
        basis=f"Knowledge evidence includes {len(knowledge_sources)} matched source(s).",
        related_domain=domain,
    )


def _priority_for_alert(severity: str) -> str:
    if severity == "critical":
        return PRIORITY_CRITICAL
    if severity == "high":
        return PRIORITY_HIGH
    if severity in {"medium", "warning"}:
        return PRIORITY_MEDIUM
    return PRIORITY_LOW


def _priority_for_sources(source_ids: list[str], evidence_by_id: dict[str, dict[str, Any]]) -> str:
    priorities = [_priority_for_alert(str(evidence_by_id.get(source_id, {}).get("severity") or "").lower()) for source_id in source_ids]
    if PRIORITY_CRITICAL in priorities:
        return PRIORITY_CRITICAL
    if PRIORITY_HIGH in priorities:
        return PRIORITY_HIGH
    if PRIORITY_MEDIUM in priorities:
        return PRIORITY_MEDIUM
    return PRIORITY_LOW


def _linked_sources(conclusion: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]) -> list[str]:
    linked = [source_id for source_id in conclusion.get("linked_source_ids", []) if source_id in evidence_by_id]
    return linked


def _first_domain(source_ids: list[str], evidence_by_id: dict[str, dict[str, Any]]) -> str:
    for source_id in source_ids:
        domain = str(evidence_by_id.get(source_id, {}).get("domain") or "")
        if domain:
            return domain
    return ""


def _confidence_for(context: RecommendationContext, evidence: list[dict[str, Any]]) -> str:
    reasoning_payload = _reasoning_payload(context.reasoning_result)
    confidence = str(reasoning_payload.get("confidence") or "")
    if confidence in SUPPORTED_RECOMMENDATION_CONFIDENCE:
        return confidence
    real_sources = [item for item in evidence if item.get("source_type") != "recommendation_context"]
    if len(real_sources) >= 4:
        return CONFIDENCE_HIGH
    if len(real_sources) >= 2:
        return CONFIDENCE_MEDIUM
    if len(real_sources) == 1:
        return CONFIDENCE_LOW
    return CONFIDENCE_INSUFFICIENT


def _reasoning_payload(reasoning_result: dict[str, Any]) -> dict[str, Any]:
    payload = _to_dict(reasoning_result)
    if "result" in payload and isinstance(payload["result"], dict):
        return copy.deepcopy(payload["result"])
    return payload


def _reasoning_sources(reasoning_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [_normalize_source(item) for item in _records(reasoning_payload.get("evidence_sources"))]


def _conclusion_sources(reasoning_payload: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for item in _records(reasoning_payload.get("conclusions")):
        conclusion_id = str(item.get("conclusion_id") or "")
        if not conclusion_id:
            continue
        sources.append(
            {
                "source_id": conclusion_id,
                "source_type": "reasoning_conclusion",
                "domain": "",
                "version": str(item.get("schema_version") or ""),
                "title": str(item.get("statement") or conclusion_id),
                "confidence": str(item.get("confidence") or ""),
                "linked_source_ids": list(item.get("source_ids") or []),
            }
        )
    return sources


def _metric_sources(metrics: Any) -> list[dict[str, Any]]:
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


def _alert_sources(alerts: Any) -> list[dict[str, Any]]:
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


def _knowledge_sources(knowledge_context: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for item in _records(_to_dict(knowledge_context).get("knowledge_entries")):
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


def _normalize_source(item: dict[str, Any]) -> dict[str, Any]:
    source_id = str(item.get("source_id") or "")
    source_type = str(item.get("source_type") or "reasoning")
    return {
        "source_id": source_id,
        "source_type": source_type,
        "domain": str(item.get("domain") or ""),
        "version": str(item.get("version") or ""),
        "title": str(item.get("title") or source_id),
        **{key: copy.deepcopy(value) for key, value in item.items() if key not in {"source_id", "source_type", "domain", "version", "title"}},
    }


def _coerce_recommendation(item: RecommendationItem | dict[str, Any]) -> RecommendationItem:
    if isinstance(item, RecommendationItem):
        return item
    return RecommendationItem(**dict(item))


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
    if records is None:
        return ()
    return tuple(copy.deepcopy(dict(item)) for item in records)


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return copy.deepcopy(value.to_dict())
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return {}
