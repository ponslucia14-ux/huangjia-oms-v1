from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .metrics import METRIC_FUNDS, METRIC_OPERATIONS, METRIC_SALES
from .schemas import new_id, now_iso


DASHBOARD_QUERY_SCHEMA_VERSION = "oms.v1.dashboard_query"

TIME_TODAY = "today"
TIME_WEEK = "week"
TIME_MONTH = "month"
SUPPORTED_TIME_SCOPES = {TIME_TODAY, TIME_WEEK, TIME_MONTH}
TIME_SCOPE_ALIASES = {
    TIME_TODAY: TIME_TODAY,
    TIME_WEEK: TIME_WEEK,
    TIME_MONTH: TIME_MONTH,
    "今日": TIME_TODAY,
    "本周": TIME_WEEK,
    "本月": TIME_MONTH,
}

DASHBOARD_SALES = "sales_dashboard"
DASHBOARD_FUNDS = "funds_dashboard"
DASHBOARD_OPERATIONS = "operations_dashboard"
SUPPORTED_DASHBOARDS = {DASHBOARD_SALES, DASHBOARD_FUNDS, DASHBOARD_OPERATIONS}
DASHBOARD_CATEGORY_ALIASES = {
    DASHBOARD_SALES: DASHBOARD_SALES,
    DASHBOARD_FUNDS: DASHBOARD_FUNDS,
    DASHBOARD_OPERATIONS: DASHBOARD_OPERATIONS,
    "销售驾驶舱": DASHBOARD_SALES,
    "资金驾驶舱": DASHBOARD_FUNDS,
    "经营驾驶舱": DASHBOARD_OPERATIONS,
}
DASHBOARD_LABELS = {
    DASHBOARD_SALES: "销售驾驶舱",
    DASHBOARD_FUNDS: "资金驾驶舱",
    DASHBOARD_OPERATIONS: "经营驾驶舱",
}
DASHBOARD_METRIC_CATEGORIES = {
    DASHBOARD_SALES: {METRIC_SALES},
    DASHBOARD_FUNDS: {METRIC_FUNDS},
    DASHBOARD_OPERATIONS: {METRIC_OPERATIONS},
}
DASHBOARD_PERMISSIONS = {
    DASHBOARD_SALES: {"ROLE_OWNER", "ROLE_STORE_MANAGER", "ROLE_SALES"},
    DASHBOARD_FUNDS: {"ROLE_OWNER", "ROLE_ACCOUNTANT", "ROLE_CASHIER"},
    DASHBOARD_OPERATIONS: {
        "ROLE_OWNER",
        "ROLE_STORE_MANAGER",
        "ROLE_BUTLER",
        "ROLE_NURSING_DIRECTOR",
        "ROLE_HR",
    },
}

DATA_STATUS_READY = "READY"
DATA_STATUS_EMPTY = "EMPTY"


@dataclass(frozen=True)
class DashboardFilter:
    """Read-only dashboard filter for time and dashboard category."""

    time_scope: str = TIME_TODAY
    dashboard_category: str = DASHBOARD_SALES
    metric_ids: tuple[str, ...] = ()
    source_domains: tuple[str, ...] = ()
    schema_version: str = DASHBOARD_QUERY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        time_scope = _normalize_time_scope(self.time_scope)
        dashboard_category = _normalize_dashboard_category(self.dashboard_category)
        object.__setattr__(self, "time_scope", time_scope)
        object.__setattr__(self, "dashboard_category", dashboard_category)
        object.__setattr__(self, "metric_ids", tuple(self.metric_ids))
        object.__setattr__(self, "source_domains", tuple(self.source_domains))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["dashboard_label"] = DASHBOARD_LABELS[self.dashboard_category]
        payload["metric_ids"] = list(self.metric_ids)
        payload["source_domains"] = list(self.source_domains)
        return payload


@dataclass(frozen=True)
class DashboardQuery:
    """Query request for a dashboard dataset. This request is read-only."""

    actor_emp_id: str
    reason: str
    dataset: dict[str, Any]
    filter: DashboardFilter | dict[str, Any] = field(default_factory=DashboardFilter)
    query_id: str = field(default_factory=lambda: new_id("dashqry"))
    correlation_id: str = ""
    requested_at: str = field(default_factory=now_iso)
    schema_version: str = DASHBOARD_QUERY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        if not self.dataset:
            raise ValueError("dataset is required.")
        dashboard_filter = self.filter if isinstance(self.filter, DashboardFilter) else DashboardFilter(**self.filter)
        object.__setattr__(self, "filter", dashboard_filter)
        object.__setattr__(self, "dataset", copy.deepcopy(self.dataset))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "query_id": self.query_id,
            "actor_emp_id": self.actor_emp_id,
            "reason": self.reason,
            "filter": self.filter.to_dict(),
            "dataset_id": self.dataset.get("dataset_id", ""),
            "correlation_id": self.correlation_id,
            "requested_at": self.requested_at,
        }


@dataclass(frozen=True)
class DashboardView:
    """P19 read-only query result for a future dashboard surface. This is not UI."""

    query: dict[str, Any]
    dashboard_category: str
    time_scope: str
    metrics: tuple[dict[str, Any], ...]
    generated_time: str
    source_domains: tuple[str, ...]
    data_status: str
    audit_record: dict[str, Any]
    event: dict[str, Any]
    view_id: str = field(default_factory=lambda: new_id("dashview"))
    mutates_business_state: bool = False
    schema_version: str = DASHBOARD_QUERY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.dashboard_category not in SUPPORTED_DASHBOARDS:
            raise ValueError(f"Unsupported dashboard_category: {self.dashboard_category}")
        if self.time_scope not in SUPPORTED_TIME_SCOPES:
            raise ValueError(f"Unsupported time_scope: {self.time_scope}")
        if self.data_status not in {DATA_STATUS_READY, DATA_STATUS_EMPTY}:
            raise ValueError(f"Unsupported data_status: {self.data_status}")
        if self.mutates_business_state:
            raise ValueError("DashboardView cannot mutate business state in P19.")
        object.__setattr__(self, "metrics", tuple(copy.deepcopy(list(self.metrics))))
        object.__setattr__(self, "source_domains", tuple(self.source_domains))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "view_id": self.view_id,
            "query": dict(self.query),
            "dashboard_category": self.dashboard_category,
            "dashboard_label": DASHBOARD_LABELS[self.dashboard_category],
            "time_scope": self.time_scope,
            "metric_count": len(self.metrics),
            "metrics": [dict(metric) for metric in self.metrics],
            "generated_time": self.generated_time,
            "source_domains": list(self.source_domains),
            "data_status": self.data_status,
            "audit_record": dict(self.audit_record),
            "event": dict(self.event),
            "mutates_business_state": self.mutates_business_state,
        }


class DashboardQueryEngine:
    """Read-only dashboard query engine over MetricsEngine dashboard datasets."""

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

    def execute(self, query: DashboardQuery | dict[str, Any]) -> dict[str, Any]:
        dashboard_query = query if isinstance(query, DashboardQuery) else DashboardQuery(**query)
        actor = self.master_data.employee_by_emp(dashboard_query.actor_emp_id)
        self._assert_permission(actor, dashboard_query.filter)

        metrics = tuple(self._select_metrics(dashboard_query.dataset, dashboard_query.filter))
        source_domains = tuple(sorted({str(metric.get("source_domain") or "") for metric in metrics if metric.get("source_domain")}))
        data_status = DATA_STATUS_READY if metrics else DATA_STATUS_EMPTY
        generated_time = str(dashboard_query.dataset.get("generated_at") or now_iso())

        audit_record = self._audit(
            query=dashboard_query,
            actor=actor,
            metric_count=len(metrics),
            source_domains=source_domains,
            data_status=data_status,
        )
        event = self._event(
            query=dashboard_query,
            actor=actor,
            metric_count=len(metrics),
            source_domains=source_domains,
            data_status=data_status,
        )

        return DashboardView(
            query=dashboard_query.to_dict(),
            dashboard_category=dashboard_query.filter.dashboard_category,
            time_scope=dashboard_query.filter.time_scope,
            metrics=metrics,
            generated_time=generated_time,
            source_domains=source_domains,
            data_status=data_status,
            audit_record=audit_record,
            event=event,
            mutates_business_state=False,
        ).to_dict()

    def query(self, query: DashboardQuery | dict[str, Any]) -> dict[str, Any]:
        return self.execute(query)

    def _select_metrics(self, dataset: dict[str, Any], dashboard_filter: DashboardFilter) -> list[dict[str, Any]]:
        metric_categories = DASHBOARD_METRIC_CATEGORIES[dashboard_filter.dashboard_category]
        metric_ids = set(dashboard_filter.metric_ids)
        source_domains = set(dashboard_filter.source_domains)
        selected: list[dict[str, Any]] = []
        for snapshot in dataset.get("snapshots") or []:
            metric = copy.deepcopy(snapshot)
            if metric.get("category") not in metric_categories:
                continue
            if metric_ids and metric.get("metric_id") not in metric_ids:
                continue
            if source_domains and metric.get("source_domain") not in source_domains:
                continue
            metric["generated_time"] = metric.get("generated_at") or dataset.get("generated_at") or now_iso()
            metric["data_status"] = DATA_STATUS_READY
            selected.append(metric)
        return selected

    @staticmethod
    def _assert_permission(actor: Employee, dashboard_filter: DashboardFilter) -> None:
        allowed_roles = DASHBOARD_PERMISSIONS[dashboard_filter.dashboard_category]
        if actor.role_code not in allowed_roles:
            raise PermissionError(
                f"{actor.emp} with role {actor.role_code} cannot query {dashboard_filter.dashboard_category}."
            )

    def _audit(
        self,
        *,
        query: DashboardQuery,
        actor: Employee,
        metric_count: int,
        source_domains: tuple[str, ...],
        data_status: str,
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=query.actor_emp_id,
            actor_name=actor.name,
            module="dashboard_query",
            action="dashboard.query",
            action_type="dashboard.query",
            reason=query.reason,
            result="executed",
            target_type="dashboard_view",
            target_id=query.filter.dashboard_category,
            correlation_id=query.correlation_id or query.query_id,
            metadata={
                "query_id": query.query_id,
                "dataset_id": query.dataset.get("dataset_id", ""),
                "time_scope": query.filter.time_scope,
                "dashboard_category": query.filter.dashboard_category,
                "dashboard_label": DASHBOARD_LABELS[query.filter.dashboard_category],
                "metric_count": metric_count,
                "source_domains": list(source_domains),
                "data_status": data_status,
                "mutates_business_state": False,
            },
        )

    def _event(
        self,
        *,
        query: DashboardQuery,
        actor: Employee,
        metric_count: int,
        source_domains: tuple[str, ...],
        data_status: str,
    ) -> dict[str, Any]:
        return self.event_bus.publish(
            OMSEvent(
                event_type="dashboard.query.executed",
                source_module="dashboard_query",
                subject="dashboard_query",
                action="executed",
                emp_id=query.actor_emp_id,
                actor_name=actor.name,
                payload={
                    "query_id": query.query_id,
                    "dataset_id": query.dataset.get("dataset_id", ""),
                    "time_scope": query.filter.time_scope,
                    "dashboard_category": query.filter.dashboard_category,
                    "dashboard_label": DASHBOARD_LABELS[query.filter.dashboard_category],
                    "metric_count": metric_count,
                    "source_domains": list(source_domains),
                    "data_status": data_status,
                    "mutates_business_state": False,
                },
                correlation_id=query.correlation_id or query.query_id,
                metadata={
                    "query_id": query.query_id,
                    "dataset_id": query.dataset.get("dataset_id", ""),
                    "mutates_business_state": False,
                },
            )
        )


def _normalize_time_scope(value: str) -> str:
    try:
        normalized = TIME_SCOPE_ALIASES[value]
    except KeyError as exc:
        raise ValueError(f"Unsupported time_scope: {value}") from exc
    return normalized


def _normalize_dashboard_category(value: str) -> str:
    try:
        normalized = DASHBOARD_CATEGORY_ALIASES[value]
    except KeyError as exc:
        raise ValueError(f"Unsupported dashboard_category: {value}") from exc
    return normalized
