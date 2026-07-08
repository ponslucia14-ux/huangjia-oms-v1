from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .domain import DomainRegistry, default_domain_registry
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .schemas import new_id, now_iso


CAREGIVER_SCHEMA_VERSION = "oms.v1.caregiver"
CAREGIVER_LIFECYCLE = (
    "AVAILABLE",
    "RESERVED",
    "ASSIGNED",
    "ON_LEAVE",
    "OFF_DUTY",
    "DISABLED",
)


@dataclass
class CaregiverTransition:
    from_status: str
    to_status: str
    action: str
    actor_emp_id: str
    reason: str
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CaregiverRecord:
    caregiver_name: str
    skill_level: str
    phone: str
    created_by_emp: str
    caregiver_id: str = field(default_factory=lambda: new_id("caregiver"))
    schema_version: str = CAREGIVER_SCHEMA_VERSION
    status: str = "AVAILABLE"
    created_at: str = field(default_factory=now_iso)
    reserved_by_emp: str = ""
    reserved_at: str = ""
    assigned_by_emp: str = ""
    assigned_at: str = ""
    released_by_emp: str = ""
    released_at: str = ""
    leave_by_emp: str = ""
    leave_at: str = ""
    enabled_by_emp: str = ""
    enabled_at: str = ""
    notes: str = ""
    transitions: list[CaregiverTransition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["transitions"] = [transition.to_dict() for transition in self.transitions]
        return payload


class CaregiverStore:
    """In-memory store for the P11 Caregiver resource engine."""

    def __init__(self):
        self.caregivers: dict[str, CaregiverRecord] = {}

    def add_caregiver(self, caregiver: CaregiverRecord) -> CaregiverRecord:
        self.caregivers[caregiver.caregiver_id] = caregiver
        return caregiver

    def caregiver(self, caregiver_id: str) -> CaregiverRecord:
        if caregiver_id not in self.caregivers:
            raise KeyError(f"Unknown caregiver_id: {caregiver_id}")
        return self.caregivers[caregiver_id]


class CaregiverActorResolver:
    def __init__(self, master_data: OMSMasterData | None = None):
        self.master_data = master_data or OMSMasterData()

    def resolve(self, emp_id: str, allowed_roles: tuple[str, ...]) -> dict[str, str]:
        employee = self.master_data.employee_by_emp(emp_id)
        if employee.role_code not in allowed_roles:
            raise PermissionError(f"{emp_id} is not allowed to modify Caregiver.")
        return {"emp_id": employee.emp, "name": employee.name, "role_code": employee.role_code}


class CaregiverService:
    """Manage caregiver resource states without Stay assignment, scheduling, payroll, attendance, UI, or database coupling."""

    def __init__(
        self,
        *,
        store: CaregiverStore | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
        domains: DomainRegistry | None = None,
    ):
        self.store = store or CaregiverStore()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.domains = domains or default_domain_registry()
        self.actor_resolver = CaregiverActorResolver(master_data)

    def create_caregiver(
        self,
        *,
        actor_emp_id: str,
        caregiver_name: str,
        skill_level: str,
        phone: str,
        reason: str,
        notes: str = "",
    ) -> dict[str, Any]:
        self._require_reason(reason)
        self._require_text(caregiver_name, "caregiver_name")
        actor = self._actor(actor_emp_id)
        caregiver = CaregiverRecord(
            caregiver_name=caregiver_name,
            skill_level=skill_level,
            phone=phone,
            created_by_emp=actor["emp_id"],
            notes=notes,
        )
        caregiver.transitions.append(
            CaregiverTransition(
                from_status="",
                to_status="AVAILABLE",
                action="create_caregiver",
                actor_emp_id=actor["emp_id"],
                reason=reason,
            )
        )
        self.store.add_caregiver(caregiver)
        return self._record_and_publish(
            caregiver=caregiver,
            actor=actor,
            action="create_caregiver",
            audit_action="caregiver.create",
            event_type="caregiver.created",
            event_action="created",
            reason=reason,
            result="AVAILABLE",
            metadata={"from_status": "", "to_status": "AVAILABLE"},
        )

    def reserve_caregiver(self, *, actor_emp_id: str, caregiver_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        caregiver = self.store.caregiver(caregiver_id)
        previous_status = caregiver.status
        self._require_status(caregiver, {"AVAILABLE"}, "reserve_caregiver")
        self._transition(
            caregiver=caregiver,
            actor=actor,
            action="reserve_caregiver",
            reason=reason,
            to_status="RESERVED",
        )
        caregiver.reserved_by_emp = actor["emp_id"]
        caregiver.reserved_at = now_iso()
        return self._record_and_publish(
            caregiver=caregiver,
            actor=actor,
            action="reserve_caregiver",
            audit_action="caregiver.reserve",
            event_type="caregiver.reserved",
            event_action="reserved",
            reason=reason,
            result="RESERVED",
            metadata={"from_status": previous_status, "to_status": "RESERVED"},
        )

    def assign_caregiver(self, *, actor_emp_id: str, caregiver_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        caregiver = self.store.caregiver(caregiver_id)
        previous_status = caregiver.status
        self._require_status(caregiver, {"RESERVED"}, "assign_caregiver")
        self._transition(
            caregiver=caregiver,
            actor=actor,
            action="assign_caregiver",
            reason=reason,
            to_status="ASSIGNED",
        )
        caregiver.assigned_by_emp = actor["emp_id"]
        caregiver.assigned_at = now_iso()
        return self._record_and_publish(
            caregiver=caregiver,
            actor=actor,
            action="assign_caregiver",
            audit_action="caregiver.assign",
            event_type="caregiver.assigned",
            event_action="assigned",
            reason=reason,
            result="ASSIGNED",
            metadata={"from_status": previous_status, "to_status": "ASSIGNED"},
        )

    def release_caregiver(self, *, actor_emp_id: str, caregiver_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        caregiver = self.store.caregiver(caregiver_id)
        previous_status = caregiver.status
        self._require_status(caregiver, {"RESERVED", "ASSIGNED"}, "release_caregiver")
        next_status = "AVAILABLE" if previous_status == "RESERVED" else "OFF_DUTY"
        self._transition(
            caregiver=caregiver,
            actor=actor,
            action="release_caregiver",
            reason=reason,
            to_status=next_status,
        )
        caregiver.released_by_emp = actor["emp_id"]
        caregiver.released_at = now_iso()
        return self._record_and_publish(
            caregiver=caregiver,
            actor=actor,
            action="release_caregiver",
            audit_action="caregiver.release",
            event_type="caregiver.released",
            event_action="released",
            reason=reason,
            result=next_status,
            metadata={"from_status": previous_status, "to_status": next_status},
        )

    def leave_caregiver(
        self,
        *,
        actor_emp_id: str,
        caregiver_id: str,
        reason: str,
        target_status: str = "ON_LEAVE",
    ) -> dict[str, Any]:
        self._require_reason(reason)
        if target_status not in {"ON_LEAVE", "DISABLED"}:
            raise ValueError("target_status must be ON_LEAVE or DISABLED.")
        actor = self._actor(actor_emp_id)
        caregiver = self.store.caregiver(caregiver_id)
        previous_status = caregiver.status
        self._require_status(caregiver, {"AVAILABLE", "RESERVED", "OFF_DUTY", "ON_LEAVE", "DISABLED"}, "leave_caregiver")
        self._transition(
            caregiver=caregiver,
            actor=actor,
            action="leave_caregiver",
            reason=reason,
            to_status=target_status,
        )
        caregiver.leave_by_emp = actor["emp_id"]
        caregiver.leave_at = now_iso()
        return self._record_and_publish(
            caregiver=caregiver,
            actor=actor,
            action="leave_caregiver",
            audit_action="caregiver.leave",
            event_type="caregiver.leave",
            event_action="leave",
            reason=reason,
            result=target_status,
            metadata={"from_status": previous_status, "to_status": target_status},
        )

    def enable_caregiver(self, *, actor_emp_id: str, caregiver_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        caregiver = self.store.caregiver(caregiver_id)
        previous_status = caregiver.status
        self._require_status(caregiver, {"ON_LEAVE", "OFF_DUTY", "DISABLED"}, "enable_caregiver")
        self._transition(
            caregiver=caregiver,
            actor=actor,
            action="enable_caregiver",
            reason=reason,
            to_status="AVAILABLE",
        )
        caregiver.enabled_by_emp = actor["emp_id"]
        caregiver.enabled_at = now_iso()
        return self._record_and_publish(
            caregiver=caregiver,
            actor=actor,
            action="enable_caregiver",
            audit_action="caregiver.enable",
            event_type="caregiver.enabled",
            event_action="enabled",
            reason=reason,
            result="AVAILABLE",
            metadata={"from_status": previous_status, "to_status": "AVAILABLE"},
        )

    def _actor(self, actor_emp_id: str) -> dict[str, str]:
        return self.actor_resolver.resolve(actor_emp_id, self.domains.get("Caregiver").mutable_by_roles)

    @staticmethod
    def _require_reason(reason: str) -> None:
        if not reason or not reason.strip():
            raise ValueError("reason is required.")

    @staticmethod
    def _require_text(value: str, field_name: str) -> None:
        if not value or not value.strip():
            raise ValueError(f"{field_name} is required.")

    @staticmethod
    def _require_status(caregiver: CaregiverRecord, allowed_statuses: set[str], action: str) -> None:
        if caregiver.status not in allowed_statuses:
            allowed = ", ".join(sorted(allowed_statuses))
            raise ValueError(
                f"{action} is not allowed when caregiver status is {caregiver.status}; expected one of: {allowed}."
            )

    @staticmethod
    def _transition(
        *,
        caregiver: CaregiverRecord,
        actor: dict[str, str],
        action: str,
        reason: str,
        to_status: str,
    ) -> None:
        caregiver.transitions.append(
            CaregiverTransition(
                from_status=caregiver.status,
                to_status=to_status,
                action=action,
                actor_emp_id=actor["emp_id"],
                reason=reason,
            )
        )
        caregiver.status = to_status

    def _record_and_publish(
        self,
        *,
        caregiver: CaregiverRecord,
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
            module="caregiver",
            action=action,
            action_type=audit_action,
            reason=reason,
            result=result,
            target_type="caregiver",
            target_id=caregiver.caregiver_id,
            metadata={
                "caregiver_name": caregiver.caregiver_name,
                "skill_level": caregiver.skill_level,
                **metadata,
            },
        )
        event = self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="caregiver",
                subject="caregiver",
                action=event_action,
                emp_id=actor["emp_id"],
                actor_name=actor["name"],
                payload=caregiver.to_dict(),
                correlation_id=caregiver.caregiver_id,
                metadata=metadata,
            )
        )
        return {"caregiver": caregiver.to_dict(), "audit": audit, "event": event}
