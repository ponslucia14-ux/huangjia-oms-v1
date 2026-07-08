from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


ALERT_SCHEMA_VERSION = "oms.v1.alert_engine"

ALERT_OPEN = "OPEN"
ALERT_ACKNOWLEDGED = "ACKNOWLEDGED"
ALERT_RESOLVED = "RESOLVED"
ALERT_IGNORED = "IGNORED"
ALERT_STATUSES = {ALERT_OPEN, ALERT_ACKNOWLEDGED, ALERT_RESOLVED, ALERT_IGNORED}
TERMINAL_ALERT_STATUSES = {ALERT_RESOLVED, ALERT_IGNORED}

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"
ALERT_SEVERITIES = {SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL}

DOMAIN_OPERATIONS = "operations"
DOMAIN_FINANCE = "finance"
DOMAIN_APPROVAL = "approval"
DOMAIN_SYSTEM = "system"

ALERT_ROOM_RESOURCE_SHORTAGE = "ALERT_ROOM_RESOURCE_SHORTAGE"
ALERT_STAY_CONFLICT = "ALERT_STAY_CONFLICT"
ALERT_RECEIVABLE_EXCEPTION = "ALERT_RECEIVABLE_EXCEPTION"
ALERT_PAYABLE_EXCEPTION = "ALERT_PAYABLE_EXCEPTION"
ALERT_APPROVAL_TIMEOUT = "ALERT_APPROVAL_TIMEOUT"
ALERT_HEALTH_CHECK_WARNING = "ALERT_HEALTH_CHECK_WARNING"

AlertEvaluator = Callable[["AlertContext"], list[dict[str, Any]]]


@dataclass(frozen=True)
class AlertDefinition:
    """A read-only alert rule definition."""

    alert_code: str
    name: str
    domain: str
    severity: str
    description: str
    evaluator: AlertEvaluator
    schema_version: str = ALERT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.alert_code.strip():
            raise ValueError("alert_code is required.")
        if not self.name.strip():
            raise ValueError("name is required.")
        if not self.domain.strip():
            raise ValueError("domain is required.")
        if self.severity not in ALERT_SEVERITIES:
            raise ValueError(f"Unknown alert severity: {self.severity}")
        if not self.description.strip():
            raise ValueError("description is required.")

    def evaluate(self, context: "AlertContext") -> list[dict[str, Any]]:
        return [dict(item) for item in self.evaluator(context)]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("evaluator", None)
        return payload


@dataclass(frozen=True)
class AlertContext:
    """Read-only evaluation context for alert discovery."""

    actor_emp_id: str
    reason: str
    room_records: tuple[dict[str, Any], ...] = ()
    stay_records: tuple[dict[str, Any], ...] = ()
    finance_records: tuple[dict[str, Any], ...] = ()
    approval_records: tuple[dict[str, Any], ...] = ()
    health_items: tuple[dict[str, Any], ...] = ()
    thresholds: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    context_id: str = field(default_factory=lambda: new_id("alertctx"))
    created_at: str = field(default_factory=now_iso)
    schema_version: str = ALERT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        object.__setattr__(self, "room_records", _freeze_records(self.room_records))
        object.__setattr__(self, "stay_records", _freeze_records(self.stay_records))
        object.__setattr__(self, "finance_records", _freeze_records(self.finance_records))
        object.__setattr__(self, "approval_records", _freeze_records(self.approval_records))
        object.__setattr__(self, "health_items", _freeze_records(self.health_items))
        object.__setattr__(self, "thresholds", dict(self.thresholds))

    def threshold(self, key: str, default: Any) -> Any:
        return self.thresholds.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "context_id": self.context_id,
            "actor_emp_id": self.actor_emp_id,
            "reason": self.reason,
            "room_records": [dict(item) for item in self.room_records],
            "stay_records": [dict(item) for item in self.stay_records],
            "finance_records": [dict(item) for item in self.finance_records],
            "approval_records": [dict(item) for item in self.approval_records],
            "health_items": [dict(item) for item in self.health_items],
            "thresholds": dict(self.thresholds),
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class AlertResult:
    """Alert lifecycle record produced by ExceptionEngine."""

    alert_code: str
    name: str
    domain: str
    severity: str
    status: str
    reason: str
    evidence: dict[str, Any]
    source_context: dict[str, Any]
    receiver_emp_ids: tuple[str, ...]
    alert_id: str = field(default_factory=lambda: new_id("alert"))
    created_at: str = field(default_factory=now_iso)
    acknowledged_at: str = ""
    resolved_at: str = ""
    ignored_at: str = ""
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    mutates_business_state: bool = False
    schema_version: str = ALERT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.alert_code.strip():
            raise ValueError("alert_code is required.")
        if not self.name.strip():
            raise ValueError("name is required.")
        if not self.domain.strip():
            raise ValueError("domain is required.")
        if self.severity not in ALERT_SEVERITIES:
            raise ValueError(f"Unknown alert severity: {self.severity}")
        if self.status not in ALERT_STATUSES:
            raise ValueError(f"Unknown alert status: {self.status}")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        if self.mutates_business_state:
            raise ValueError("AlertResult cannot mutate business state in P20.")
        object.__setattr__(self, "evidence", copy.deepcopy(self.evidence))
        object.__setattr__(self, "source_context", copy.deepcopy(self.source_context))
        object.__setattr__(self, "receiver_emp_ids", tuple(self.receiver_emp_ids))
        object.__setattr__(self, "audit_records", tuple(copy.deepcopy(list(self.audit_records))))
        object.__setattr__(self, "events", tuple(copy.deepcopy(list(self.events))))

    def with_lifecycle_update(
        self,
        *,
        status: str,
        audit_record: dict[str, Any],
        event: dict[str, Any] | None = None,
    ) -> "AlertResult":
        if status not in ALERT_STATUSES:
            raise ValueError(f"Unknown alert status: {status}")
        if self.status in TERMINAL_ALERT_STATUSES:
            raise ValueError(f"Alert {self.alert_id} is terminal and cannot be updated.")
        now = now_iso()
        return AlertResult(
            alert_id=self.alert_id,
            alert_code=self.alert_code,
            name=self.name,
            domain=self.domain,
            severity=self.severity,
            status=status,
            reason=self.reason,
            evidence=self.evidence,
            source_context=self.source_context,
            receiver_emp_ids=self.receiver_emp_ids,
            created_at=self.created_at,
            acknowledged_at=now if status == ALERT_ACKNOWLEDGED else self.acknowledged_at,
            resolved_at=now if status == ALERT_RESOLVED else self.resolved_at,
            ignored_at=now if status == ALERT_IGNORED else self.ignored_at,
            audit_records=(*self.audit_records, audit_record),
            events=(*self.events, event) if event else self.events,
            mutates_business_state=False,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "alert_id": self.alert_id,
            "alert_code": self.alert_code,
            "name": self.name,
            "domain": self.domain,
            "severity": self.severity,
            "status": self.status,
            "reason": self.reason,
            "evidence": copy.deepcopy(self.evidence),
            "source_context": copy.deepcopy(self.source_context),
            "receiver_emp_ids": list(self.receiver_emp_ids),
            "created_at": self.created_at,
            "acknowledged_at": self.acknowledged_at,
            "resolved_at": self.resolved_at,
            "ignored_at": self.ignored_at,
            "audit_records": [dict(item) for item in self.audit_records],
            "events": [dict(item) for item in self.events],
            "mutates_business_state": self.mutates_business_state,
        }


class ExceptionEngine:
    """Evaluate alert rules and maintain in-memory alert lifecycle state."""

    def __init__(
        self,
        *,
        definitions: list[AlertDefinition] | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
    ):
        self.definitions = definitions or default_alert_definitions()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.master_data = master_data or OMSMasterData()
        self._alerts: dict[str, AlertResult] = {}

    def definitions_payload(self) -> list[dict[str, Any]]:
        return [definition.to_dict() for definition in self.definitions]

    def evaluate(self, context: AlertContext | dict[str, Any]) -> dict[str, Any]:
        alert_context = context if isinstance(context, AlertContext) else AlertContext(**context)
        actor = self.master_data.employee_by_emp(alert_context.actor_emp_id)
        context_before = alert_context.to_dict()
        created_alerts: list[dict[str, Any]] = []

        for definition in self.definitions:
            for finding in definition.evaluate(alert_context):
                alert = self._create_alert(
                    definition=definition,
                    finding=finding,
                    context=alert_context,
                    actor=actor,
                )
                self._alerts[alert.alert_id] = alert
                created_alerts.append(alert.to_dict())

        if alert_context.to_dict() != context_before:
            raise RuntimeError("Alert evaluation attempted to mutate context.")

        return {
            "schema_version": ALERT_SCHEMA_VERSION,
            "context": alert_context.to_dict(),
            "alert_count": len(created_alerts),
            "alerts": created_alerts,
            "mutates_business_state": False,
        }

    def acknowledge(self, alert_id: str, *, actor_emp_id: str, reason: str, correlation_id: str = "") -> dict[str, Any]:
        return self._transition(
            alert_id,
            actor_emp_id=actor_emp_id,
            reason=reason,
            correlation_id=correlation_id,
            status=ALERT_ACKNOWLEDGED,
            audit_action="alert.acknowledge",
            event_type="alert.acknowledged",
        )

    def resolve(self, alert_id: str, *, actor_emp_id: str, reason: str, correlation_id: str = "") -> dict[str, Any]:
        return self._transition(
            alert_id,
            actor_emp_id=actor_emp_id,
            reason=reason,
            correlation_id=correlation_id,
            status=ALERT_RESOLVED,
            audit_action="alert.resolve",
            event_type="alert.resolved",
        )

    def ignore(self, alert_id: str, *, actor_emp_id: str, reason: str, correlation_id: str = "") -> dict[str, Any]:
        return self._transition(
            alert_id,
            actor_emp_id=actor_emp_id,
            reason=reason,
            correlation_id=correlation_id,
            status=ALERT_IGNORED,
            audit_action="alert.ignore",
            event_type="",
        )

    def get_alert(self, alert_id: str) -> dict[str, Any]:
        return self._alert(alert_id).to_dict()

    def alerts(self) -> list[dict[str, Any]]:
        return [alert.to_dict() for alert in self._alerts.values()]

    def _create_alert(
        self,
        *,
        definition: AlertDefinition,
        finding: dict[str, Any],
        context: AlertContext,
        actor: Employee,
    ) -> AlertResult:
        receiver_emp_ids = tuple(finding.get("receiver_emp_ids") or _receiver_emp_ids(self.master_data, definition.domain))
        reason = str(finding.get("reason") or definition.description)
        evidence = dict(finding.get("evidence") or {})
        base_alert = AlertResult(
            alert_code=definition.alert_code,
            name=definition.name,
            domain=definition.domain,
            severity=str(finding.get("severity") or definition.severity),
            status=ALERT_OPEN,
            reason=reason,
            evidence=evidence,
            source_context={
                "context_id": context.context_id,
                "correlation_id": context.correlation_id,
            },
            receiver_emp_ids=receiver_emp_ids,
            mutates_business_state=False,
        )
        audit_record = self._audit(
            action="alert.create",
            alert=base_alert,
            actor=actor,
            reason=context.reason,
            correlation_id=context.correlation_id or base_alert.alert_id,
        )
        event = self._event(
            event_type="alert.created",
            alert=base_alert,
            actor=actor,
            correlation_id=context.correlation_id or base_alert.alert_id,
        )
        return AlertResult(
            alert_id=base_alert.alert_id,
            alert_code=base_alert.alert_code,
            name=base_alert.name,
            domain=base_alert.domain,
            severity=base_alert.severity,
            status=base_alert.status,
            reason=base_alert.reason,
            evidence=base_alert.evidence,
            source_context=base_alert.source_context,
            receiver_emp_ids=base_alert.receiver_emp_ids,
            created_at=base_alert.created_at,
            audit_records=(audit_record,),
            events=(event,),
            mutates_business_state=False,
        )

    def _transition(
        self,
        alert_id: str,
        *,
        actor_emp_id: str,
        reason: str,
        correlation_id: str,
        status: str,
        audit_action: str,
        event_type: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required.")
        alert = self._alert(alert_id)
        actor = self.master_data.employee_by_emp(actor_emp_id)
        audit_record = self._audit(
            action=audit_action,
            alert=alert,
            actor=actor,
            reason=reason,
            correlation_id=correlation_id or alert.alert_id,
            status_override=status,
        )
        event = None
        if event_type:
            event = self._event(
                event_type=event_type,
                alert=alert,
                actor=actor,
                correlation_id=correlation_id or alert.alert_id,
                status_override=status,
            )
        updated = alert.with_lifecycle_update(status=status, audit_record=audit_record, event=event)
        self._alerts[alert_id] = updated
        return updated.to_dict()

    def _alert(self, alert_id: str) -> AlertResult:
        try:
            return self._alerts[alert_id]
        except KeyError as exc:
            raise KeyError(f"Unknown alert_id: {alert_id}") from exc

    def _audit(
        self,
        *,
        action: str,
        alert: AlertResult,
        actor: Employee,
        reason: str,
        correlation_id: str,
        status_override: str | None = None,
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="alert_engine",
            action=action,
            action_type=action,
            reason=reason,
            result=status_override or alert.status,
            target_type="alert",
            target_id=alert.alert_id,
            correlation_id=correlation_id,
            metadata={
                "alert_id": alert.alert_id,
                "alert_code": alert.alert_code,
                "domain": alert.domain,
                "severity": alert.severity,
                "status": status_override or alert.status,
                "receiver_emp_ids": list(alert.receiver_emp_ids),
                "notification_consumable": True,
                "mutates_business_state": False,
            },
        )

    def _event(
        self,
        *,
        event_type: str,
        alert: AlertResult,
        actor: Employee,
        correlation_id: str,
        status_override: str | None = None,
    ) -> dict[str, Any]:
        status = status_override or alert.status
        return self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="alert_engine",
                subject="alert",
                action=event_type.removeprefix("alert."),
                emp_id=actor.emp,
                actor_name=actor.name,
                payload={
                    "alert_id": alert.alert_id,
                    "alert_code": alert.alert_code,
                    "name": alert.name,
                    "domain": alert.domain,
                    "severity": alert.severity,
                    "status": status,
                    "reason": alert.reason,
                    "evidence": copy.deepcopy(alert.evidence),
                    "receiver_emp_ids": list(alert.receiver_emp_ids),
                    "notification_consumable": True,
                    "mutates_business_state": False,
                },
                correlation_id=correlation_id,
                metadata={
                    "alert_id": alert.alert_id,
                    "alert_code": alert.alert_code,
                    "notification_consumable": True,
                    "mutates_business_state": False,
                },
            )
        )


def default_alert_definitions() -> list[AlertDefinition]:
    return [
        AlertDefinition(
            alert_code=ALERT_ROOM_RESOURCE_SHORTAGE,
            name="room_resource_shortage",
            domain=DOMAIN_OPERATIONS,
            severity=SEVERITY_HIGH,
            description="Available room resources are below the required threshold.",
            evaluator=_evaluate_room_resource_shortage,
        ),
        AlertDefinition(
            alert_code=ALERT_STAY_CONFLICT,
            name="stay_conflict",
            domain=DOMAIN_OPERATIONS,
            severity=SEVERITY_CRITICAL,
            description="Multiple active stays are assigned to the same room.",
            evaluator=_evaluate_stay_conflict,
        ),
        AlertDefinition(
            alert_code=ALERT_RECEIVABLE_EXCEPTION,
            name="receivable_exception",
            domain=DOMAIN_FINANCE,
            severity=SEVERITY_HIGH,
            description="Receivable amount is above the configured threshold.",
            evaluator=_evaluate_receivable_exception,
        ),
        AlertDefinition(
            alert_code=ALERT_PAYABLE_EXCEPTION,
            name="payable_exception",
            domain=DOMAIN_FINANCE,
            severity=SEVERITY_MEDIUM,
            description="Payable amount is above the configured threshold.",
            evaluator=_evaluate_payable_exception,
        ),
        AlertDefinition(
            alert_code=ALERT_APPROVAL_TIMEOUT,
            name="approval_timeout",
            domain=DOMAIN_APPROVAL,
            severity=SEVERITY_HIGH,
            description="Pending approval has exceeded the configured timeout.",
            evaluator=_evaluate_approval_timeout,
        ),
        AlertDefinition(
            alert_code=ALERT_HEALTH_CHECK_WARNING,
            name="health_check_warning",
            domain=DOMAIN_SYSTEM,
            severity=SEVERITY_WARNING,
            description="Health check reported warning or failed items.",
            evaluator=_evaluate_health_check_warning,
        ),
    ]


def _evaluate_room_resource_shortage(context: AlertContext) -> list[dict[str, Any]]:
    required = int(context.threshold("required_available_rooms", 1))
    available_rooms = [room for room in context.room_records if str(room.get("status") or "") == "AVAILABLE"]
    if len(available_rooms) >= required:
        return []
    return [
        {
            "reason": f"Available rooms {len(available_rooms)} below required {required}.",
            "evidence": {
                "available_room_count": len(available_rooms),
                "required_available_rooms": required,
            },
        }
    ]


def _evaluate_stay_conflict(context: AlertContext) -> list[dict[str, Any]]:
    active_statuses = {"in_house", "checked_in", "OCCUPIED", "ACTIVE"}
    by_room: dict[str, list[dict[str, Any]]] = {}
    for stay in context.stay_records:
        room_id = str(stay.get("room_id") or "")
        if not room_id:
            continue
        status = str(stay.get("status") or "")
        if status not in active_statuses:
            continue
        by_room.setdefault(room_id, []).append(dict(stay))
    return [
        {
            "reason": f"Room {room_id} has {len(stays)} active stays.",
            "evidence": {
                "room_id": room_id,
                "stay_ids": [str(stay.get("stay_id") or "") for stay in stays],
                "active_stay_count": len(stays),
            },
        }
        for room_id, stays in by_room.items()
        if len(stays) > 1
    ]


def _evaluate_receivable_exception(context: AlertContext) -> list[dict[str, Any]]:
    threshold = _decimal(context.threshold("receivable_threshold", "0"))
    total = _sum_finance(context.finance_records, "receivable")
    if total < threshold or total <= Decimal("0"):
        return []
    return [
        {
            "reason": f"Receivable amount {total} reached threshold {threshold}.",
            "evidence": {
                "receivable_amount": str(total),
                "receivable_threshold": str(threshold),
            },
        }
    ]


def _evaluate_payable_exception(context: AlertContext) -> list[dict[str, Any]]:
    threshold = _decimal(context.threshold("payable_threshold", "0"))
    total = _sum_finance(context.finance_records, "payable")
    if total < threshold or total <= Decimal("0"):
        return []
    return [
        {
            "reason": f"Payable amount {total} reached threshold {threshold}.",
            "evidence": {
                "payable_amount": str(total),
                "payable_threshold": str(threshold),
            },
        }
    ]


def _evaluate_approval_timeout(context: AlertContext) -> list[dict[str, Any]]:
    threshold = int(context.threshold("approval_timeout_hours", 24))
    findings: list[dict[str, Any]] = []
    for approval in context.approval_records:
        status = str(approval.get("status") or "")
        age_hours = int(approval.get("age_hours") or 0)
        if status != "PENDING" or age_hours < threshold:
            continue
        findings.append(
            {
                "reason": f"Approval {approval.get('approval_id') or ''} pending for {age_hours} hours.",
                "evidence": {
                    "approval_id": str(approval.get("approval_id") or ""),
                    "age_hours": age_hours,
                    "approval_timeout_hours": threshold,
                },
            }
        )
    return findings


def _evaluate_health_check_warning(context: AlertContext) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in context.health_items:
        status = str(item.get("status") or "")
        if status not in {"warning", "fail"}:
            continue
        findings.append(
            {
                "reason": f"Health check item {item.get('code') or ''} is {status}.",
                "severity": SEVERITY_WARNING if status == "warning" else SEVERITY_HIGH,
                "evidence": {
                    "code": str(item.get("code") or ""),
                    "status": status,
                    "message": str(item.get("message") or item.get("detail") or ""),
                },
            }
        )
    return findings


def _receiver_emp_ids(master_data: OMSMasterData, domain: str) -> tuple[str, ...]:
    roles_by_domain = {
        DOMAIN_OPERATIONS: ("ROLE_OWNER", "ROLE_STORE_MANAGER"),
        DOMAIN_FINANCE: ("ROLE_OWNER", "ROLE_ACCOUNTANT", "ROLE_CASHIER"),
        DOMAIN_APPROVAL: ("ROLE_OWNER", "ROLE_ACCOUNTANT"),
        DOMAIN_SYSTEM: ("ROLE_OWNER", "ROLE_HR"),
    }
    emp_ids: list[str] = []
    for role_code in roles_by_domain.get(domain, ("ROLE_OWNER",)):
        for employee in master_data.employees_by_role(role_code):
            emp_ids.append(employee.emp)
    return tuple(dict.fromkeys(emp_ids))


def _freeze_records(records: Any) -> tuple[dict[str, Any], ...]:
    if records is None:
        return ()
    if not isinstance(records, (list, tuple)):
        raise TypeError("Alert context records must be a list or tuple.")
    return tuple(copy.deepcopy([dict(item) for item in records]))


def _sum_finance(records: tuple[dict[str, Any], ...], record_type: str) -> Decimal:
    total = Decimal("0")
    for record in records:
        if str(record.get("type") or "") != record_type:
            continue
        total += _decimal(record.get("amount"))
    return total


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")
