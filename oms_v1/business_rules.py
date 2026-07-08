from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from .domain import DomainRegistry, default_domain_registry
from .master_data import OMSMasterData


BUSINESS_RULE_SCHEMA_VERSION = "oms.v1.business_rule"
RULE_PASS = "PASS"
RULE_WARNING = "WARNING"
RULE_REJECT = "REJECT"
RULE_RESULT_ORDER = {RULE_PASS: 0, RULE_WARNING: 1, RULE_REJECT: 2}

RuleEvaluator = Callable[["RuleContext"], "RuleResult"]


@dataclass(frozen=True)
class RuleContext:
    """Read-only input for business rule evaluation."""

    action: str
    actor_emp_id: str = ""
    domain: str = ""
    required_fields: tuple[str, ...] = ()
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuleResult:
    """Single business rule decision."""

    rule_id: str
    name: str
    status: str
    reason: str
    priority: int
    severity: str = "info"
    schema_version: str = BUSINESS_RULE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in RULE_RESULT_ORDER:
            raise ValueError(f"Unknown rule status: {self.status}")
        if not self.reason.strip():
            raise ValueError("Rule reason is required.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuleDefinition:
    """Business rule definition with priority and evaluator."""

    rule_id: str
    name: str
    description: str
    priority: int
    evaluator: RuleEvaluator
    enabled: bool = True
    schema_version: str = BUSINESS_RULE_SCHEMA_VERSION

    def evaluate(self, context: RuleContext) -> RuleResult:
        if not self.enabled:
            return RuleResult(
                rule_id=self.rule_id,
                name=self.name,
                status=RULE_WARNING,
                reason="Rule is disabled.",
                priority=self.priority,
                severity="warning",
            )
        result = self.evaluator(context)
        if result.rule_id != self.rule_id or result.priority != self.priority:
            raise ValueError(f"Rule evaluator returned mismatched result for {self.rule_id}.")
        return result

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("evaluator", None)
        return payload


class BusinessRulesEngine:
    """Evaluate OMS business rules without mutating business state."""

    def __init__(
        self,
        *,
        rules: list[RuleDefinition] | None = None,
        master_data: OMSMasterData | None = None,
        domains: DomainRegistry | None = None,
    ):
        self.master_data = master_data or OMSMasterData()
        self.domains = domains or default_domain_registry()
        self.rules = sorted(rules or default_business_rules(self.master_data, self.domains), key=lambda rule: rule.priority)

    def evaluate(self, context: RuleContext | dict[str, Any]) -> dict[str, Any]:
        rule_context = context if isinstance(context, RuleContext) else RuleContext(**context)
        results = [rule.evaluate(rule_context) for rule in self.rules]
        overall_status = max((result.status for result in results), key=lambda status: RULE_RESULT_ORDER[status])
        return {
            "schema_version": "oms.v1.business_rule_evaluation",
            "action": rule_context.action,
            "domain": rule_context.domain,
            "actor_emp_id": rule_context.actor_emp_id,
            "overall_status": overall_status,
            "results": [result.to_dict() for result in results],
            "reject_reasons": [result.reason for result in results if result.status == RULE_REJECT],
            "warning_reasons": [result.reason for result in results if result.status == RULE_WARNING],
            "mutates_business_state": False,
        }

    def definitions(self) -> list[dict[str, Any]]:
        return [rule.to_dict() for rule in self.rules]


def default_business_rules(master_data: OMSMasterData | None = None, domains: DomainRegistry | None = None) -> list[RuleDefinition]:
    data = master_data or OMSMasterData()
    registry = domains or default_domain_registry()
    return [
        RuleDefinition(
            rule_id="BR_REQUIRED_FIELDS",
            name="Required fields must exist",
            description="Reject when required fields are missing or blank.",
            priority=10,
            evaluator=_required_fields_rule,
        ),
        RuleDefinition(
            rule_id="BR_ROLE_PERMISSION",
            name="Actor must have domain permission",
            description="Reject when actor EMP is unknown or role cannot modify target domain.",
            priority=20,
            evaluator=_role_permission_rule(data, registry),
        ),
        RuleDefinition(
            rule_id="BR_CONTRACT_PAYMENT_CONFIRMED",
            name="Contract is effective only after confirmed payment",
            description="Reject contract effectiveness checks until at least one payment is confirmed.",
            priority=30,
            evaluator=_contract_payment_confirmed_rule,
        ),
        RuleDefinition(
            rule_id="BR_ROOM_MAINTENANCE_NOT_CHECKIN",
            name="Maintenance room cannot be checked in",
            description="Reject room check-in when room status is MAINTENANCE.",
            priority=40,
            evaluator=_room_status_rule("MAINTENANCE", "Room is under maintenance and cannot be checked in."),
        ),
        RuleDefinition(
            rule_id="BR_ROOM_DISABLED_NOT_CHECKIN",
            name="Disabled room cannot be checked in",
            description="Reject room check-in when room status is DISABLED.",
            priority=50,
            evaluator=_room_status_rule("DISABLED", "Room is disabled and cannot be checked in."),
        ),
    ]


def _required_fields_rule(context: RuleContext) -> RuleResult:
    missing = []
    for field_name in context.required_fields:
        value = context.data.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field_name)
    if missing:
        return RuleResult(
            rule_id="BR_REQUIRED_FIELDS",
            name="Required fields must exist",
            status=RULE_REJECT,
            reason=f"Missing required fields: {', '.join(missing)}.",
            priority=10,
            severity="error",
            metadata={"missing_fields": missing},
        )
    return RuleResult(
        rule_id="BR_REQUIRED_FIELDS",
        name="Required fields must exist",
        status=RULE_PASS,
        reason="All required fields are present.",
        priority=10,
    )


def _role_permission_rule(master_data: OMSMasterData, domains: DomainRegistry) -> RuleEvaluator:
    def evaluate(context: RuleContext) -> RuleResult:
        if not context.actor_emp_id or not context.domain:
            return RuleResult(
                rule_id="BR_ROLE_PERMISSION",
                name="Actor must have domain permission",
                status=RULE_WARNING,
                reason="Actor EMP or domain was not provided; role permission was not evaluated.",
                priority=20,
                severity="warning",
            )
        try:
            employee = master_data.employee_by_emp(context.actor_emp_id)
            domain = domains.get(context.domain)
        except KeyError as exc:
            return RuleResult(
                rule_id="BR_ROLE_PERMISSION",
                name="Actor must have domain permission",
                status=RULE_REJECT,
                reason=str(exc),
                priority=20,
                severity="error",
            )
        if employee.role_code not in domain.mutable_by_roles:
            return RuleResult(
                rule_id="BR_ROLE_PERMISSION",
                name="Actor must have domain permission",
                status=RULE_REJECT,
                reason=f"{employee.emp} role {employee.role_code} is not allowed to modify {domain.name}.",
                priority=20,
                severity="error",
                metadata={"role_code": employee.role_code, "allowed_roles": list(domain.mutable_by_roles)},
            )
        return RuleResult(
            rule_id="BR_ROLE_PERMISSION",
            name="Actor must have domain permission",
            status=RULE_PASS,
            reason=f"{employee.emp} role {employee.role_code} is allowed to modify {domain.name}.",
            priority=20,
            metadata={"role_code": employee.role_code},
        )

    return evaluate


def _contract_payment_confirmed_rule(context: RuleContext) -> RuleResult:
    if context.action not in {"activate_contract", "create_stay", "contract_effective"}:
        return RuleResult(
            rule_id="BR_CONTRACT_PAYMENT_CONFIRMED",
            name="Contract is effective only after confirmed payment",
            status=RULE_PASS,
            reason="Rule does not apply to this action.",
            priority=30,
        )
    payments = context.data.get("payments") or []
    if not payments:
        return RuleResult(
            rule_id="BR_CONTRACT_PAYMENT_CONFIRMED",
            name="Contract is effective only after confirmed payment",
            status=RULE_REJECT,
            reason="Contract cannot become effective before confirmed payment exists.",
            priority=30,
            severity="error",
        )
    confirmed_payments = [payment for payment in payments if _value(payment, "status") == "confirmed"]
    if not confirmed_payments:
        return RuleResult(
            rule_id="BR_CONTRACT_PAYMENT_CONFIRMED",
            name="Contract is effective only after confirmed payment",
            status=RULE_REJECT,
            reason="Contract has payment records but no confirmed payment.",
            priority=30,
            severity="error",
        )
    confirmed_amount = sum(_decimal(_value(payment, "amount")) for payment in confirmed_payments)
    return RuleResult(
        rule_id="BR_CONTRACT_PAYMENT_CONFIRMED",
        name="Contract is effective only after confirmed payment",
        status=RULE_PASS,
        reason="Contract has confirmed payment and can be treated as effective.",
        priority=30,
        metadata={"confirmed_payment_count": len(confirmed_payments), "confirmed_amount": str(confirmed_amount)},
    )


def _room_status_rule(blocked_status: str, blocked_reason: str) -> RuleEvaluator:
    def evaluate(context: RuleContext) -> RuleResult:
        if context.action not in {"check_in_room", "create_stay", "check_in"}:
            return RuleResult(
                rule_id=f"BR_ROOM_{blocked_status}_NOT_CHECKIN",
                name=f"{blocked_status.title()} room cannot be checked in",
                status=RULE_PASS,
                reason="Rule does not apply to this action.",
                priority=40 if blocked_status == "MAINTENANCE" else 50,
            )
        room = context.data.get("room") or {}
        status = _value(room, "status")
        if status == blocked_status:
            return RuleResult(
                rule_id=f"BR_ROOM_{blocked_status}_NOT_CHECKIN",
                name=f"{blocked_status.title()} room cannot be checked in",
                status=RULE_REJECT,
                reason=blocked_reason,
                priority=40 if blocked_status == "MAINTENANCE" else 50,
                severity="error",
                metadata={"room_status": status},
            )
        if not status:
            return RuleResult(
                rule_id=f"BR_ROOM_{blocked_status}_NOT_CHECKIN",
                name=f"{blocked_status.title()} room cannot be checked in",
                status=RULE_WARNING,
                reason="Room status was not provided; room status rule was not fully evaluated.",
                priority=40 if blocked_status == "MAINTENANCE" else 50,
                severity="warning",
            )
        return RuleResult(
            rule_id=f"BR_ROOM_{blocked_status}_NOT_CHECKIN",
            name=f"{blocked_status.title()} room cannot be checked in",
            status=RULE_PASS,
            reason=f"Room status is {status}; blocked status {blocked_status} was not found.",
            priority=40 if blocked_status == "MAINTENANCE" else 50,
            metadata={"room_status": status},
        )

    return evaluate


def _value(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(key)
    return getattr(payload, key, None)


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")
