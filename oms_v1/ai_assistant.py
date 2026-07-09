from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .dashboard_query import (
    DASHBOARD_FUNDS,
    DASHBOARD_OPERATIONS,
    DASHBOARD_PERMISSIONS,
    DASHBOARD_SALES,
)
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .metrics import METRIC_FUNDS, METRIC_OPERATIONS, METRIC_SALES
from .schemas import new_id, now_iso


AI_ASSISTANT_SCHEMA_VERSION = "oms.v1.ai_assistant"

CONTEXT_DOMAIN = "domain"
CONTEXT_METRICS = "metrics"
CONTEXT_DASHBOARD_QUERY = "dashboard_query"
CONTEXT_ALERT = "alert"
CONTEXT_AUDIT = "audit"
CONTEXT_EVENT = "event"
SUPPORTED_CONTEXT_SCOPES = {
    CONTEXT_DOMAIN,
    CONTEXT_METRICS,
    CONTEXT_DASHBOARD_QUERY,
    CONTEXT_ALERT,
    CONTEXT_AUDIT,
    CONTEXT_EVENT,
}

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_INSUFFICIENT = "insufficient_context"
SUPPORTED_CONFIDENCE = {
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_INSUFFICIENT,
}

ROLE_DOMAIN_ACCESS = {
    "ROLE_OWNER": {"*"},
    "ROLE_ACCOUNTANT": {"Payment", "Expense", "Finance", "finance", "funds", "approval"},
    "ROLE_CASHIER": {"Payment", "Expense", "Finance", "finance", "funds", "approval"},
    "ROLE_SALES": {"Customer", "Contract", "Sales", "sales"},
    "ROLE_STORE_MANAGER": {"Room", "Stay", "Caregiver", "operations", "room", "stay"},
    "ROLE_BUTLER": {"Stay", "Service", "operations", "service"},
    "ROLE_NURSING_DIRECTOR": {"Caregiver", "Service", "operations", "service"},
    "ROLE_HR": {"Employee", "Caregiver", "system", "operations", "hr"},
    "ROLE_ADMIN": {"system", "operations"},
    "ROLE_KITCHEN_DIRECTOR": {"Service", "operations", "kitchen"},
}

METRIC_CATEGORY_DOMAINS = {
    METRIC_SALES: "sales",
    METRIC_FUNDS: "funds",
    METRIC_OPERATIONS: "operations",
}


@dataclass(frozen=True)
class AIQuery:
    """Read-only AI assistant query request."""

    actor_emp_id: str
    question: str
    context_scope: tuple[str, ...]
    query_id: str = field(default_factory=lambda: new_id("aiqry"))
    correlation_id: str = ""
    requested_at: str = field(default_factory=now_iso)
    schema_version: str = AI_ASSISTANT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.query_id.strip():
            raise ValueError("query_id is required.")
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if not self.question.strip():
            raise ValueError("question is required.")
        scope = tuple(self.context_scope)
        if not scope:
            raise ValueError("context_scope is required.")
        unknown = sorted(set(scope) - SUPPORTED_CONTEXT_SCOPES)
        if unknown:
            raise ValueError(f"Unsupported context_scope: {', '.join(unknown)}")
        object.__setattr__(self, "context_scope", scope)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["context_scope"] = list(self.context_scope)
        return payload


@dataclass(frozen=True)
class AIContext:
    """Permission-trimmed context available for a single AI response."""

    source_domains: tuple[str, ...] = ()
    metrics: tuple[dict[str, Any], ...] = ()
    dashboard_data: tuple[dict[str, Any], ...] = ()
    alerts: tuple[dict[str, Any], ...] = ()
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    schema_version: str = AI_ASSISTANT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_domains", tuple(dict.fromkeys(self.source_domains)))
        object.__setattr__(self, "metrics", _freeze_records(self.metrics))
        object.__setattr__(self, "dashboard_data", _freeze_records(self.dashboard_data))
        object.__setattr__(self, "alerts", _freeze_records(self.alerts))
        object.__setattr__(self, "audit_records", _freeze_records(self.audit_records))
        object.__setattr__(self, "events", _freeze_records(self.events))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_domains": list(self.source_domains),
            "metrics": [dict(item) for item in self.metrics],
            "dashboard_data": [dict(item) for item in self.dashboard_data],
            "alerts": [dict(item) for item in self.alerts],
            "audit_records": [dict(item) for item in self.audit_records],
            "events": [dict(item) for item in self.events],
        }


@dataclass(frozen=True)
class AIResponse:
    """Rule-based response result for P21 foundation."""

    answer: str
    source_domains: tuple[str, ...]
    related_metrics: tuple[str, ...] = ()
    related_alerts: tuple[str, ...] = ()
    confidence: str = CONFIDENCE_MEDIUM
    response_id: str = field(default_factory=lambda: new_id("airesp"))
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = AI_ASSISTANT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.response_id.strip():
            raise ValueError("response_id is required.")
        if not self.answer.strip():
            raise ValueError("answer is required.")
        if self.confidence not in SUPPORTED_CONFIDENCE:
            raise ValueError(f"Unsupported confidence: {self.confidence}")
        object.__setattr__(self, "source_domains", tuple(dict.fromkeys(self.source_domains)))
        object.__setattr__(self, "related_metrics", tuple(dict.fromkeys(self.related_metrics)))
        object.__setattr__(self, "related_alerts", tuple(dict.fromkeys(self.related_alerts)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_domains"] = list(self.source_domains)
        payload["related_metrics"] = list(self.related_metrics)
        payload["related_alerts"] = list(self.related_alerts)
        return payload


class AIAssistantEngine:
    """P21 AI assistant foundation. It is read-only and uses rule-based responses."""

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

    def ask(self, query: AIQuery | dict[str, Any], context_sources: dict[str, Any] | None = None) -> dict[str, Any]:
        ai_query = query if isinstance(query, AIQuery) else AIQuery(**query)
        actor = self.master_data.employee_by_emp(ai_query.actor_emp_id)
        sources = copy.deepcopy(context_sources or {})
        context = self.build_context(ai_query, sources, actor=actor)
        response = self.generate_response(ai_query, context)

        query_audit = self._audit_query(ai_query, actor, context)
        response_audit = self._audit_response(ai_query, actor, response)
        query_event = self._event_query(ai_query, actor, context)
        response_event = self._event_response(ai_query, actor, response)

        if sources != copy.deepcopy(context_sources or {}):
            raise RuntimeError("AI assistant attempted to mutate source context.")

        return {
            "schema_version": AI_ASSISTANT_SCHEMA_VERSION,
            "query": ai_query.to_dict(),
            "context": context.to_dict(),
            "response": response.to_dict(),
            "audit_records": [query_audit, response_audit],
            "events": [query_event, response_event],
            "mutates_business_state": False,
            "external_ai_called": False,
        }

    def build_context(self, query: AIQuery, context_sources: dict[str, Any], *, actor: Employee | None = None) -> AIContext:
        employee = actor or self.master_data.employee_by_emp(query.actor_emp_id)
        metrics = _records(context_sources.get("metrics")) if CONTEXT_METRICS in query.context_scope else []
        dashboard_data = _records(context_sources.get("dashboard_data")) if CONTEXT_DASHBOARD_QUERY in query.context_scope else []
        alerts = _records(context_sources.get("alerts")) if CONTEXT_ALERT in query.context_scope else []
        audit_records = _records(context_sources.get("audit_records")) if CONTEXT_AUDIT in query.context_scope else []
        events = _records(context_sources.get("events")) if CONTEXT_EVENT in query.context_scope else []

        permitted_metrics = [item for item in metrics if self._can_access_metric(employee, item)]
        permitted_dashboard = [item for item in dashboard_data if self._can_access_dashboard(employee, item)]
        permitted_alerts = [item for item in alerts if self._can_access_domain(employee, str(item.get("domain") or ""))]
        permitted_audits = [item for item in audit_records if self._can_access_audit(employee, item)]
        permitted_events = [item for item in events if self._can_access_event(employee, item)]
        source_domains = self._source_domains(
            metrics=permitted_metrics,
            dashboard_data=permitted_dashboard,
            alerts=permitted_alerts,
            audit_records=permitted_audits,
            events=permitted_events,
        )
        return AIContext(
            source_domains=tuple(source_domains),
            metrics=tuple(permitted_metrics),
            dashboard_data=tuple(permitted_dashboard),
            alerts=tuple(permitted_alerts),
            audit_records=tuple(permitted_audits),
            events=tuple(permitted_events),
        )

    @staticmethod
    def generate_response(query: AIQuery, context: AIContext) -> AIResponse:
        related_metrics = tuple(
            metric_id
            for metric_id in [str(item.get("metric_id") or "") for item in context.metrics]
            if metric_id
        )
        for dashboard in context.dashboard_data:
            for metric in _records(dashboard.get("metrics")):
                metric_id = str(metric.get("metric_id") or "")
                if metric_id:
                    related_metrics = (*related_metrics, metric_id)
        related_alerts = tuple(
            alert_id
            for alert_id in [str(item.get("alert_id") or "") for item in context.alerts]
            if alert_id
        )

        evidence_count = (
            len(context.metrics)
            + len(context.dashboard_data)
            + len(context.alerts)
            + len(context.audit_records)
            + len(context.events)
        )
        if evidence_count <= 0:
            return AIResponse(
                answer="Insufficient authorized OMS context to answer this question.",
                source_domains=(),
                related_metrics=(),
                related_alerts=(),
                confidence=CONFIDENCE_INSUFFICIENT,
            )

        answer = (
            f"Read-only OMS answer for query {query.query_id}: "
            f"{len(context.metrics)} metrics, "
            f"{len(context.dashboard_data)} dashboard views, "
            f"{len(context.alerts)} alerts, "
            f"{len(context.audit_records)} audit records, "
            f"{len(context.events)} events were available after permission trimming."
        )
        confidence = CONFIDENCE_HIGH if (context.metrics or context.dashboard_data or context.alerts) else CONFIDENCE_MEDIUM
        return AIResponse(
            answer=answer,
            source_domains=context.source_domains,
            related_metrics=related_metrics,
            related_alerts=related_alerts,
            confidence=confidence,
        )

    @staticmethod
    def _can_access_all(employee: Employee) -> bool:
        return employee.role_code == "ROLE_OWNER"

    def _can_access_metric(self, employee: Employee, metric: dict[str, Any]) -> bool:
        if self._can_access_all(employee):
            return True
        category_domain = METRIC_CATEGORY_DOMAINS.get(str(metric.get("category") or ""), "")
        return self._can_access_domain(employee, category_domain) or self._can_access_domain(
            employee, str(metric.get("source_domain") or "")
        )

    def _can_access_dashboard(self, employee: Employee, dashboard: dict[str, Any]) -> bool:
        if self._can_access_all(employee):
            return True
        category = str(dashboard.get("dashboard_category") or "")
        allowed_roles = DASHBOARD_PERMISSIONS.get(category, set())
        return employee.role_code in allowed_roles

    def _can_access_audit(self, employee: Employee, record: dict[str, Any]) -> bool:
        if self._can_access_all(employee):
            return True
        if record.get("emp_id") == employee.emp:
            return True
        return self._can_access_domain(employee, _record_domain(record))

    def _can_access_event(self, employee: Employee, event: dict[str, Any]) -> bool:
        if self._can_access_all(employee):
            return True
        if event.get("emp_id") == employee.emp:
            return True
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        domain = str(payload.get("domain") or payload.get("source_domain") or payload.get("dashboard_category") or "")
        return self._can_access_domain(employee, _domain_from_dashboard_or_metric(domain))

    def _can_access_domain(self, employee: Employee, domain: str) -> bool:
        if self._can_access_all(employee):
            return True
        allowed = ROLE_DOMAIN_ACCESS.get(employee.role_code, set())
        if "*" in allowed:
            return True
        normalized = _domain_from_dashboard_or_metric(domain)
        return normalized in allowed or domain in allowed

    def _source_domains(
        self,
        *,
        metrics: list[dict[str, Any]],
        dashboard_data: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
        audit_records: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> list[str]:
        domains: list[str] = []
        for metric in metrics:
            domains.append(str(metric.get("source_domain") or metric.get("category") or ""))
        for dashboard in dashboard_data:
            for metric in _records(dashboard.get("metrics")):
                domains.append(str(metric.get("source_domain") or metric.get("category") or ""))
        for alert in alerts:
            domains.append(str(alert.get("domain") or ""))
        for record in audit_records:
            domains.append(_record_domain(record))
        for event in events:
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            domains.append(
                _domain_from_dashboard_or_metric(
                    str(payload.get("domain") or payload.get("source_domain") or payload.get("dashboard_category") or "")
                )
            )
        return [domain for domain in dict.fromkeys(domains) if domain]

    def _audit_query(self, query: AIQuery, actor: Employee, context: AIContext) -> dict[str, Any]:
        return self.audit.record(
            emp_id=query.actor_emp_id,
            actor_name=actor.name,
            module="ai_assistant",
            action="ai.query",
            action_type="ai.query",
            reason=query.question,
            result="accepted",
            target_type="ai_query",
            target_id=query.query_id,
            correlation_id=query.correlation_id or query.query_id,
            metadata={
                "query_id": query.query_id,
                "actor_emp_id": query.actor_emp_id,
                "question": query.question,
                "context_scope": list(query.context_scope),
                "permission_result": "trimmed",
                "source_domains": list(context.source_domains),
                "mutates_business_state": False,
                "external_ai_called": False,
            },
        )

    def _audit_response(self, query: AIQuery, actor: Employee, response: AIResponse) -> dict[str, Any]:
        return self.audit.record(
            emp_id=query.actor_emp_id,
            actor_name=actor.name,
            module="ai_assistant",
            action="ai.response",
            action_type="ai.response",
            reason=query.question,
            result=response.confidence,
            target_type="ai_response",
            target_id=response.response_id,
            correlation_id=query.correlation_id or query.query_id,
            metadata={
                "query_id": query.query_id,
                "response_id": response.response_id,
                "source_domains": list(response.source_domains),
                "related_metrics": list(response.related_metrics),
                "related_alerts": list(response.related_alerts),
                "confidence": response.confidence,
                "mutates_business_state": False,
                "external_ai_called": False,
            },
        )

    def _event_query(self, query: AIQuery, actor: Employee, context: AIContext) -> dict[str, Any]:
        return self.event_bus.publish(
            OMSEvent(
                event_type="ai.query.requested",
                source_module="ai_assistant",
                subject="ai_query",
                action="requested",
                emp_id=query.actor_emp_id,
                actor_name=actor.name,
                payload={
                    "query_id": query.query_id,
                    "actor_emp_id": query.actor_emp_id,
                    "context_scope": list(query.context_scope),
                    "source_domains": list(context.source_domains),
                    "mutates_business_state": False,
                    "external_ai_called": False,
                },
                correlation_id=query.correlation_id or query.query_id,
                metadata={
                    "query_id": query.query_id,
                    "mutates_business_state": False,
                    "external_ai_called": False,
                },
            )
        )

    def _event_response(self, query: AIQuery, actor: Employee, response: AIResponse) -> dict[str, Any]:
        return self.event_bus.publish(
            OMSEvent(
                event_type="ai.response.generated",
                source_module="ai_assistant",
                subject="ai_response",
                action="generated",
                emp_id=query.actor_emp_id,
                actor_name=actor.name,
                payload={
                    "query_id": query.query_id,
                    "response_id": response.response_id,
                    "source_domains": list(response.source_domains),
                    "related_metrics": list(response.related_metrics),
                    "related_alerts": list(response.related_alerts),
                    "confidence": response.confidence,
                    "mutates_business_state": False,
                    "external_ai_called": False,
                },
                correlation_id=query.correlation_id or query.query_id,
                metadata={
                    "query_id": query.query_id,
                    "response_id": response.response_id,
                    "mutates_business_state": False,
                    "external_ai_called": False,
                },
            )
        )


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict) and "snapshots" in value:
        return [dict(item) for item in value.get("snapshots") or []]
    if isinstance(value, dict):
        return [dict(value)]
    if not isinstance(value, (list, tuple)):
        raise TypeError("AI context source records must be a dict, list, or tuple.")
    return [dict(item) for item in value]


def _freeze_records(records: Any) -> tuple[dict[str, Any], ...]:
    return tuple(copy.deepcopy(_records(records)))


def _domain_from_dashboard_or_metric(value: str) -> str:
    mapping = {
        DASHBOARD_SALES: "sales",
        DASHBOARD_FUNDS: "funds",
        DASHBOARD_OPERATIONS: "operations",
        METRIC_SALES: "sales",
        METRIC_FUNDS: "funds",
        METRIC_OPERATIONS: "operations",
    }
    return mapping.get(value, value)


def _record_domain(record: dict[str, Any]) -> str:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    return _domain_from_dashboard_or_metric(
        str(
            metadata.get("domain")
            or metadata.get("source_domain")
            or metadata.get("dashboard_category")
            or record.get("module")
            or record.get("target_type")
            or ""
        )
    )
