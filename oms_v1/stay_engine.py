from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .domain import DomainRegistry, default_domain_registry
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .schemas import new_id, now_iso


STAY_SCHEMA_VERSION = "oms.v1.stay"
STAY_LIFECYCLE = (
    "CONTRACTED",
    "WAITING_CHECKIN",
    "CHECKED_IN",
    "IN_STAY",
    "CHECKED_OUT",
    "EXTENDED",
    "CANCELLED",
)


@dataclass
class StayTransition:
    from_status: str
    to_status: str
    action: str
    actor_emp_id: str
    reason: str
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StayRecord:
    customer_id: str
    customer_name: str
    contract_id: str
    planned_checkin_date: str
    planned_checkout_date: str
    created_by_emp: str
    stay_id: str = field(default_factory=lambda: new_id("stay"))
    schema_version: str = STAY_SCHEMA_VERSION
    status: str = "WAITING_CHECKIN"
    created_at: str = field(default_factory=now_iso)
    checked_in_by_emp: str = ""
    checked_in_at: str = ""
    extended_by_emp: str = ""
    extended_at: str = ""
    extended_until: str = ""
    checked_out_by_emp: str = ""
    checked_out_at: str = ""
    cancelled_by_emp: str = ""
    cancelled_at: str = ""
    transitions: list[StayTransition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["transitions"] = [transition.to_dict() for transition in self.transitions]
        return payload


class StayStore:
    """In-memory store for the P8 Stay lifecycle engine."""

    def __init__(self):
        self.stays: dict[str, StayRecord] = {}

    def add_stay(self, stay: StayRecord) -> StayRecord:
        self.stays[stay.stay_id] = stay
        return stay

    def stay(self, stay_id: str) -> StayRecord:
        if stay_id not in self.stays:
            raise KeyError(f"Unknown stay_id: {stay_id}")
        return self.stays[stay_id]


class StayActorResolver:
    def __init__(self, master_data: OMSMasterData | None = None):
        self.master_data = master_data or OMSMasterData()

    def resolve(self, emp_id: str, allowed_roles: tuple[str, ...]) -> dict[str, str]:
        employee = self.master_data.employee_by_emp(emp_id)
        if employee.role_code not in allowed_roles:
            raise PermissionError(f"{emp_id} is not allowed to modify Stay.")
        return {"emp_id": employee.emp, "name": employee.name, "role_code": employee.role_code}


class StayService:
    """Manage Stay lifecycle transitions without room, caregiver, UI, or database coupling."""

    def __init__(
        self,
        *,
        store: StayStore | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
        domains: DomainRegistry | None = None,
    ):
        self.store = store or StayStore()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.domains = domains or default_domain_registry()
        self.actor_resolver = StayActorResolver(master_data)

    def create_stay(
        self,
        *,
        actor_emp_id: str,
        customer_id: str,
        customer_name: str,
        contract_id: str,
        planned_checkin_date: str,
        planned_checkout_date: str,
        reason: str,
    ) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        stay = StayRecord(
            customer_id=customer_id,
            customer_name=customer_name,
            contract_id=contract_id,
            planned_checkin_date=planned_checkin_date,
            planned_checkout_date=planned_checkout_date,
            created_by_emp=actor["emp_id"],
        )
        stay.transitions.append(
            StayTransition(
                from_status="CONTRACTED",
                to_status="WAITING_CHECKIN",
                action="create_stay",
                actor_emp_id=actor["emp_id"],
                reason=reason,
            )
        )
        self.store.add_stay(stay)
        return self._record_and_publish(
            stay=stay,
            actor=actor,
            action="create_stay",
            audit_action="stay.create",
            event_type="stay.created",
            event_action="created",
            reason=reason,
            result="WAITING_CHECKIN",
            metadata={"from_status": "CONTRACTED", "to_status": "WAITING_CHECKIN"},
        )

    def check_in(self, *, actor_emp_id: str, stay_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        stay = self.store.stay(stay_id)
        self._require_status(stay, {"WAITING_CHECKIN"}, "check_in")
        self._transition(
            stay=stay,
            actor=actor,
            action="check_in",
            reason=reason,
            from_status=stay.status,
            to_status="IN_STAY",
            event_status="CHECKED_IN",
        )
        stay.checked_in_by_emp = actor["emp_id"]
        stay.checked_in_at = now_iso()
        return self._record_and_publish(
            stay=stay,
            actor=actor,
            action="check_in",
            audit_action="stay.check_in",
            event_type="stay.checked_in",
            event_action="checked_in",
            reason=reason,
            result="IN_STAY",
            metadata={"from_status": "WAITING_CHECKIN", "event_status": "CHECKED_IN", "to_status": "IN_STAY"},
        )

    def extend_stay(self, *, actor_emp_id: str, stay_id: str, extended_until: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        if not extended_until or not extended_until.strip():
            raise ValueError("extended_until is required.")
        actor = self._actor(actor_emp_id)
        stay = self.store.stay(stay_id)
        previous_status = stay.status
        self._require_status(stay, {"IN_STAY", "EXTENDED"}, "extend_stay")
        self._transition(
            stay=stay,
            actor=actor,
            action="extend_stay",
            reason=reason,
            from_status=previous_status,
            to_status="EXTENDED",
        )
        stay.status = "EXTENDED"
        stay.extended_by_emp = actor["emp_id"]
        stay.extended_at = now_iso()
        stay.extended_until = extended_until
        stay.planned_checkout_date = extended_until
        return self._record_and_publish(
            stay=stay,
            actor=actor,
            action="extend_stay",
            audit_action="stay.extend",
            event_type="stay.extended",
            event_action="extended",
            reason=reason,
            result="EXTENDED",
            metadata={"from_status": previous_status, "to_status": "EXTENDED", "extended_until": extended_until},
        )

    def check_out(self, *, actor_emp_id: str, stay_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        stay = self.store.stay(stay_id)
        previous_status = stay.status
        self._require_status(stay, {"IN_STAY", "EXTENDED"}, "check_out")
        self._transition(
            stay=stay,
            actor=actor,
            action="check_out",
            reason=reason,
            from_status=previous_status,
            to_status="CHECKED_OUT",
        )
        stay.status = "CHECKED_OUT"
        stay.checked_out_by_emp = actor["emp_id"]
        stay.checked_out_at = now_iso()
        return self._record_and_publish(
            stay=stay,
            actor=actor,
            action="check_out",
            audit_action="stay.check_out",
            event_type="stay.checked_out",
            event_action="checked_out",
            reason=reason,
            result="CHECKED_OUT",
            metadata={"from_status": previous_status, "to_status": "CHECKED_OUT"},
        )

    def cancel_stay(self, *, actor_emp_id: str, stay_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        stay = self.store.stay(stay_id)
        previous_status = stay.status
        self._require_status(stay, {"WAITING_CHECKIN"}, "cancel_stay")
        self._transition(
            stay=stay,
            actor=actor,
            action="cancel_stay",
            reason=reason,
            from_status=previous_status,
            to_status="CANCELLED",
        )
        stay.status = "CANCELLED"
        stay.cancelled_by_emp = actor["emp_id"]
        stay.cancelled_at = now_iso()
        return self._record_and_publish(
            stay=stay,
            actor=actor,
            action="cancel_stay",
            audit_action="stay.cancel",
            event_type="stay.cancelled",
            event_action="cancelled",
            reason=reason,
            result="CANCELLED",
            metadata={"from_status": previous_status, "to_status": "CANCELLED"},
        )

    def _actor(self, actor_emp_id: str) -> dict[str, str]:
        return self.actor_resolver.resolve(actor_emp_id, self.domains.get("Stay").mutable_by_roles)

    @staticmethod
    def _require_reason(reason: str) -> None:
        if not reason or not reason.strip():
            raise ValueError("reason is required.")

    @staticmethod
    def _require_status(stay: StayRecord, allowed_statuses: set[str], action: str) -> None:
        if stay.status not in allowed_statuses:
            allowed = ", ".join(sorted(allowed_statuses))
            raise ValueError(f"{action} is not allowed when stay status is {stay.status}; expected one of: {allowed}.")

    @staticmethod
    def _transition(
        *,
        stay: StayRecord,
        actor: dict[str, str],
        action: str,
        reason: str,
        from_status: str,
        to_status: str,
        event_status: str = "",
    ) -> None:
        stay.transitions.append(
            StayTransition(
                from_status=from_status,
                to_status=event_status or to_status,
                action=action,
                actor_emp_id=actor["emp_id"],
                reason=reason,
            )
        )
        if event_status:
            stay.transitions.append(
                StayTransition(
                    from_status=event_status,
                    to_status=to_status,
                    action=f"{action}_ready",
                    actor_emp_id=actor["emp_id"],
                    reason=reason,
                )
            )
        stay.status = to_status

    def _record_and_publish(
        self,
        *,
        stay: StayRecord,
        actor: dict[str, str],
        action: str,
        audit_action: str,
        event_type: str,
        event_action: str,
        reason: str,
        result: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        audit = self.audit.record(
            emp_id=actor["emp_id"],
            actor_name=actor["name"],
            module="stay",
            action=action,
            action_type=audit_action,
            reason=reason,
            result=result,
            target_type="stay",
            target_id=stay.stay_id,
            metadata={
                "customer_id": stay.customer_id,
                "contract_id": stay.contract_id,
                **metadata,
            },
        )
        event = self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="stay",
                subject="stay",
                action=event_action,
                emp_id=actor["emp_id"],
                actor_name=actor["name"],
                payload=stay.to_dict(),
                correlation_id=stay.stay_id,
                metadata=metadata,
            )
        )
        return {"stay": stay.to_dict(), "audit": audit, "event": event}
