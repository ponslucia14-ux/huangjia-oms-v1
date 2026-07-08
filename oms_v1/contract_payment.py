from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from .audit_log import AuditEngine
from .domain import DomainRegistry, default_domain_registry
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .schemas import new_id, now_iso


CONTRACT_PAYMENT_SCHEMA_VERSION = "oms.v1.contract_payment"


@dataclass
class ContractRecord:
    customer_id: str
    customer_name: str
    contract_number: str
    amount: str
    package_name: str
    created_by_emp: str
    contract_id: str = field(default_factory=lambda: new_id("contract"))
    status: str = "active"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaymentRecord:
    contract_id: str
    amount: str
    payment_method: str
    recorded_by_emp: str
    payment_id: str = field(default_factory=lambda: new_id("payment"))
    status: str = "pending"
    recorded_at: str = field(default_factory=now_iso)
    confirmed_by_emp: str = ""
    confirmed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContractPaymentStore:
    """In-memory store for the P7 minimum business loop."""

    def __init__(self):
        self.contracts: dict[str, ContractRecord] = {}
        self.payments: dict[str, PaymentRecord] = {}

    def add_contract(self, contract: ContractRecord) -> ContractRecord:
        self.contracts[contract.contract_id] = contract
        return contract

    def add_payment(self, payment: PaymentRecord) -> PaymentRecord:
        self.payments[payment.payment_id] = payment
        return payment

    def contract(self, contract_id: str) -> ContractRecord:
        if contract_id not in self.contracts:
            raise KeyError(f"Unknown contract_id: {contract_id}")
        return self.contracts[contract_id]

    def payment(self, payment_id: str) -> PaymentRecord:
        if payment_id not in self.payments:
            raise KeyError(f"Unknown payment_id: {payment_id}")
        return self.payments[payment_id]


class ActorResolver:
    def __init__(self, master_data: OMSMasterData | None = None):
        self.master_data = master_data or OMSMasterData()

    def resolve(self, emp_id: str, allowed_roles: tuple[str, ...]) -> dict[str, str]:
        employee = self.master_data.employee_by_emp(emp_id)
        if employee.role_code not in allowed_roles:
            raise PermissionError(f"{emp_id} is not allowed to modify this domain.")
        return {"emp_id": employee.emp, "name": employee.name, "role_code": employee.role_code}


class ContractService:
    def __init__(
        self,
        *,
        store: ContractPaymentStore | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
        domains: DomainRegistry | None = None,
    ):
        self.store = store or ContractPaymentStore()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.domains = domains or default_domain_registry()
        self.actor_resolver = ActorResolver(master_data)

    def create_contract(
        self,
        *,
        actor_emp_id: str,
        customer_id: str,
        customer_name: str,
        contract_number: str,
        amount: str | int | float | Decimal,
        package_name: str,
        reason: str,
    ) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self.actor_resolver.resolve(actor_emp_id, self.domains.get("Contract").mutable_by_roles)
        contract = ContractRecord(
            customer_id=customer_id,
            customer_name=customer_name,
            contract_number=contract_number,
            amount=self._amount_text(amount),
            package_name=package_name,
            created_by_emp=actor["emp_id"],
        )
        self.store.add_contract(contract)
        audit = self.audit.record(
            emp_id=actor["emp_id"],
            actor_name=actor["name"],
            module="contract",
            action="create_contract",
            reason=reason,
            result="created",
            target_type="contract",
            target_id=contract.contract_id,
            metadata={"contract_number": contract_number, "customer_id": customer_id},
        )
        event = self.event_bus.publish(
            OMSEvent(
                event_type="contract.created",
                source_module="contract",
                subject="contract",
                action="created",
                emp_id=actor["emp_id"],
                actor_name=actor["name"],
                payload=contract.to_dict(),
                correlation_id=contract.contract_id,
            )
        )
        return {"contract": contract.to_dict(), "audit": audit, "event": event}

    @staticmethod
    def _require_reason(reason: str) -> None:
        if not reason or not reason.strip():
            raise ValueError("reason is required.")

    @staticmethod
    def _amount_text(amount: str | int | float | Decimal) -> str:
        value = Decimal(str(amount))
        if value <= 0:
            raise ValueError("amount must be greater than zero.")
        return str(value)


class PaymentService:
    def __init__(
        self,
        *,
        store: ContractPaymentStore,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
        domains: DomainRegistry | None = None,
    ):
        self.store = store
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.domains = domains or default_domain_registry()
        self.actor_resolver = ActorResolver(master_data)

    def record_payment(
        self,
        *,
        actor_emp_id: str,
        contract_id: str,
        amount: str | int | float | Decimal,
        payment_method: str,
        reason: str,
    ) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self.actor_resolver.resolve(actor_emp_id, self.domains.get("Payment").mutable_by_roles)
        self.store.contract(contract_id)
        payment = PaymentRecord(
            contract_id=contract_id,
            amount=self._amount_text(amount),
            payment_method=payment_method,
            recorded_by_emp=actor["emp_id"],
        )
        self.store.add_payment(payment)
        audit = self.audit.record(
            emp_id=actor["emp_id"],
            actor_name=actor["name"],
            module="payment",
            action="record_payment",
            reason=reason,
            result="recorded",
            target_type="payment",
            target_id=payment.payment_id,
            metadata={"contract_id": contract_id, "payment_method": payment_method},
        )
        event = self.event_bus.publish(
            OMSEvent(
                event_type="payment.recorded",
                source_module="payment",
                subject="payment",
                action="recorded",
                emp_id=actor["emp_id"],
                actor_name=actor["name"],
                payload=payment.to_dict(),
                correlation_id=contract_id,
            )
        )
        return {"payment": payment.to_dict(), "audit": audit, "event": event}

    def confirm_payment(self, *, actor_emp_id: str, payment_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self.actor_resolver.resolve(actor_emp_id, self.domains.get("Payment").mutable_by_roles)
        payment = self.store.payment(payment_id)
        if payment.status == "confirmed":
            raise ValueError("payment is already confirmed.")
        payment.status = "confirmed"
        payment.confirmed_by_emp = actor["emp_id"]
        payment.confirmed_at = now_iso()
        audit = self.audit.record(
            emp_id=actor["emp_id"],
            actor_name=actor["name"],
            module="payment",
            action="confirm_payment",
            reason=reason,
            result="confirmed",
            target_type="payment",
            target_id=payment.payment_id,
            metadata={"contract_id": payment.contract_id},
        )
        event = self.event_bus.publish(
            OMSEvent(
                event_type="payment.confirmed",
                source_module="payment",
                subject="payment",
                action="confirmed",
                emp_id=actor["emp_id"],
                actor_name=actor["name"],
                payload=payment.to_dict(),
                correlation_id=payment.contract_id,
            )
        )
        return {"payment": payment.to_dict(), "audit": audit, "event": event}

    @staticmethod
    def _require_reason(reason: str) -> None:
        if not reason or not reason.strip():
            raise ValueError("reason is required.")

    @staticmethod
    def _amount_text(amount: str | int | float | Decimal) -> str:
        value = Decimal(str(amount))
        if value <= 0:
            raise ValueError("amount must be greater than zero.")
        return str(value)
