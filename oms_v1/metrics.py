from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from .audit_log import AuditEngine
from .schemas import new_id, now_iso


METRICS_SCHEMA_VERSION = "oms.v1.metrics"

METRIC_SALES = "sales"
METRIC_FUNDS = "funds"
METRIC_OPERATIONS = "operations"

MetricCalculator = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class MetricDefinition:
    """Business metric definition for P18 dashboard foundation."""

    metric_id: str
    name: str
    category: str
    source_domain: str
    calculation_method: str
    unit: str
    calculator: MetricCalculator
    description: str = ""
    schema_version: str = METRICS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.metric_id.strip():
            raise ValueError("metric_id is required.")
        if not self.name.strip():
            raise ValueError("name is required.")
        if not self.category.strip():
            raise ValueError("category is required.")
        if not self.source_domain.strip():
            raise ValueError("source_domain is required.")
        if not self.calculation_method.strip():
            raise ValueError("calculation_method is required.")

    def evaluate(self, data: dict[str, Any]) -> "MetricSnapshot":
        value = self.calculator(data)
        return MetricSnapshot(
            metric_id=self.metric_id,
            name=self.name,
            category=self.category,
            source_domain=self.source_domain,
            calculation_method=self.calculation_method,
            value=value,
            unit=self.unit,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("calculator", None)
        return payload


@dataclass(frozen=True)
class MetricSnapshot:
    metric_id: str
    name: str
    category: str
    source_domain: str
    calculation_method: str
    value: Any
    unit: str
    snapshot_id: str = field(default_factory=lambda: new_id("metric"))
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = METRICS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["value"] = _json_safe_metric_value(self.value)
        return payload


@dataclass(frozen=True)
class DashboardDataset:
    """Dataset foundation for a future owner dashboard. This is not UI."""

    snapshots: tuple[MetricSnapshot, ...]
    source_summary: dict[str, Any]
    dataset_id: str = field(default_factory=lambda: new_id("dashboard"))
    audit_record: dict[str, Any] | None = None
    mutates_business_state: bool = False
    generated_at: str = field(default_factory=now_iso)
    schema_version: str = METRICS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshots", tuple(self.snapshots))
        if self.mutates_business_state:
            raise ValueError("DashboardDataset cannot mutate business state in P18.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "generated_at": self.generated_at,
            "mutates_business_state": self.mutates_business_state,
            "source_summary": dict(self.source_summary),
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "audit_record": dict(self.audit_record) if self.audit_record else None,
        }


class MetricsEngine:
    """Compute read-only business metric snapshots from provided domain data."""

    def __init__(
        self,
        *,
        definitions: list[MetricDefinition] | None = None,
        audit: AuditEngine | None = None,
    ):
        self.definitions = definitions or default_metric_definitions()
        self.audit = audit or AuditEngine()

    def definitions_payload(self) -> list[dict[str, Any]]:
        return [definition.to_dict() for definition in self.definitions]

    def snapshot(
        self,
        data: dict[str, Any],
        *,
        actor_emp_id: str,
        actor_name: str,
        reason: str,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required.")
        snapshots = tuple(definition.evaluate(data) for definition in self.definitions)
        audit_record = self.audit.record(
            emp_id=actor_emp_id,
            actor_name=actor_name,
            module="metrics",
            action="metrics.snapshot",
            action_type="metrics.snapshot",
            reason=reason,
            result="generated",
            target_type="dashboard_dataset",
            target_id="metrics",
            correlation_id=correlation_id,
            metadata={
                "metric_count": len(snapshots),
                "source_summary": _source_summary(data),
                "mutates_business_state": False,
            },
        )
        dataset = DashboardDataset(
            snapshots=snapshots,
            source_summary=_source_summary(data),
            audit_record=audit_record,
            mutates_business_state=False,
        )
        return dataset.to_dict()


def default_metric_definitions() -> list[MetricDefinition]:
    return [
        MetricDefinition(
            metric_id="sales.today_receptions",
            name="今日接待数",
            category=METRIC_SALES,
            source_domain="Customer",
            calculation_method="count sales_records where event_type is reception and date is today",
            unit="count",
            calculator=lambda data: _count_where(data.get("sales_records"), event_type="reception"),
        ),
        MetricDefinition(
            metric_id="sales.today_contracts",
            name="今日签约数",
            category=METRIC_SALES,
            source_domain="Contract",
            calculation_method="count sales_records where event_type is contract_signed and date is today",
            unit="count",
            calculator=lambda data: _count_where(data.get("sales_records"), event_type="contract_signed"),
        ),
        MetricDefinition(
            metric_id="sales.deal_amount",
            name="成交金额",
            category=METRIC_SALES,
            source_domain="Contract",
            calculation_method="sum amount of signed sales_records",
            unit="currency",
            calculator=lambda data: _sum_amount_where(data.get("sales_records"), event_type="contract_signed"),
        ),
        MetricDefinition(
            metric_id="sales.conversion_rate",
            name="转化率",
            category=METRIC_SALES,
            source_domain="Customer",
            calculation_method="today_contracts / today_receptions",
            unit="ratio",
            calculator=lambda data: _ratio(
                _count_where(data.get("sales_records"), event_type="contract_signed"),
                _count_where(data.get("sales_records"), event_type="reception"),
            ),
        ),
        MetricDefinition(
            metric_id="funds.today_received",
            name="今日收款",
            category=METRIC_FUNDS,
            source_domain="Payment",
            calculation_method="sum amount of finance_records where type is received",
            unit="currency",
            calculator=lambda data: _sum_amount_where(data.get("finance_records"), type="received"),
        ),
        MetricDefinition(
            metric_id="funds.receivable_amount",
            name="待收金额",
            category=METRIC_FUNDS,
            source_domain="Payment",
            calculation_method="sum amount of finance_records where type is receivable",
            unit="currency",
            calculator=lambda data: _sum_amount_where(data.get("finance_records"), type="receivable"),
        ),
        MetricDefinition(
            metric_id="funds.payable_amount",
            name="待付款金额",
            category=METRIC_FUNDS,
            source_domain="Expense",
            calculation_method="sum amount of finance_records where type is payable",
            unit="currency",
            calculator=lambda data: _sum_amount_where(data.get("finance_records"), type="payable"),
        ),
        MetricDefinition(
            metric_id="operations.current_stays",
            name="在住人数",
            category=METRIC_OPERATIONS,
            source_domain="Stay",
            calculation_method="count stay_records where status is in_house",
            unit="count",
            calculator=lambda data: _count_where(data.get("stay_records"), status="in_house"),
        ),
        MetricDefinition(
            metric_id="operations.room_utilization_rate",
            name="房间利用率",
            category=METRIC_OPERATIONS,
            source_domain="Room",
            calculation_method="occupied rooms / total enabled rooms",
            unit="ratio",
            calculator=lambda data: _room_utilization(data.get("room_records")),
        ),
        MetricDefinition(
            metric_id="operations.caregiver_status_counts",
            name="照护师状态数量",
            category=METRIC_OPERATIONS,
            source_domain="Caregiver",
            calculation_method="group caregiver_records by status",
            unit="mapping",
            calculator=lambda data: _status_counts(data.get("caregiver_records")),
        ),
    ]


def _source_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "sales_records": len(data.get("sales_records") or []),
        "finance_records": len(data.get("finance_records") or []),
        "stay_records": len(data.get("stay_records") or []),
        "room_records": len(data.get("room_records") or []),
        "caregiver_records": len(data.get("caregiver_records") or []),
    }


def _count_where(records: Any, **expected: Any) -> int:
    return sum(1 for record in _records(records) if _matches(record, expected))


def _sum_amount_where(records: Any, **expected: Any) -> str:
    total = Decimal("0")
    for record in _records(records):
        if _matches(record, expected):
            total += _decimal(record.get("amount"))
    return str(total)


def _ratio(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0"
    return str((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001")))


def _room_utilization(records: Any) -> str:
    rooms = _records(records)
    enabled_rooms = [room for room in rooms if room.get("status") != "DISABLED"]
    if not enabled_rooms:
        return "0"
    occupied = [room for room in enabled_rooms if room.get("status") == "OCCUPIED"]
    return str((Decimal(len(occupied)) / Decimal(len(enabled_rooms))).quantize(Decimal("0.0001")))


def _status_counts(records: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in _records(records):
        status = str(record.get("status") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("Metric source records must be a list.")
    return [dict(item) for item in value]


def _matches(record: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(record.get(key) == value for key, value in expected.items())


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _json_safe_metric_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe_metric_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_metric_value(item) for item in value]
    return value
