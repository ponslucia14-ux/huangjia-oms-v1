from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .domain import DomainRegistry, default_domain_registry
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .schemas import new_id, now_iso


ROOM_SCHEMA_VERSION = "oms.v1.room"
ROOM_LIFECYCLE = (
    "AVAILABLE",
    "RESERVED",
    "OCCUPIED",
    "CLEANING",
    "MAINTENANCE",
    "DISABLED",
)


@dataclass
class RoomTransition:
    from_status: str
    to_status: str
    action: str
    actor_emp_id: str
    reason: str
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RoomRecord:
    room_number: str
    room_type: str
    floor: str
    created_by_emp: str
    room_id: str = field(default_factory=lambda: new_id("room"))
    schema_version: str = ROOM_SCHEMA_VERSION
    status: str = "AVAILABLE"
    created_at: str = field(default_factory=now_iso)
    reserved_by_emp: str = ""
    reserved_at: str = ""
    occupied_by_emp: str = ""
    occupied_at: str = ""
    released_by_emp: str = ""
    released_at: str = ""
    maintenance_by_emp: str = ""
    maintenance_at: str = ""
    enabled_by_emp: str = ""
    enabled_at: str = ""
    notes: str = ""
    transitions: list[RoomTransition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["transitions"] = [transition.to_dict() for transition in self.transitions]
        return payload


class RoomStore:
    """In-memory store for the P9 Room resource engine."""

    def __init__(self):
        self.rooms: dict[str, RoomRecord] = {}

    def add_room(self, room: RoomRecord) -> RoomRecord:
        if any(existing.room_number == room.room_number for existing in self.rooms.values()):
            raise ValueError(f"Duplicate room_number: {room.room_number}")
        self.rooms[room.room_id] = room
        return room

    def room(self, room_id: str) -> RoomRecord:
        if room_id not in self.rooms:
            raise KeyError(f"Unknown room_id: {room_id}")
        return self.rooms[room_id]


class RoomActorResolver:
    def __init__(self, master_data: OMSMasterData | None = None):
        self.master_data = master_data or OMSMasterData()

    def resolve(self, emp_id: str, allowed_roles: tuple[str, ...]) -> dict[str, str]:
        employee = self.master_data.employee_by_emp(emp_id)
        if employee.role_code not in allowed_roles:
            raise PermissionError(f"{emp_id} is not allowed to modify Room.")
        return {"emp_id": employee.emp, "name": employee.name, "role_code": employee.role_code}


class RoomService:
    """Manage room resource states without Stay, caregiver, allocation algorithm, UI, or database coupling."""

    def __init__(
        self,
        *,
        store: RoomStore | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
        domains: DomainRegistry | None = None,
    ):
        self.store = store or RoomStore()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.domains = domains or default_domain_registry()
        self.actor_resolver = RoomActorResolver(master_data)

    def create_room(
        self,
        *,
        actor_emp_id: str,
        room_number: str,
        room_type: str,
        floor: str,
        reason: str,
        notes: str = "",
    ) -> dict[str, Any]:
        self._require_reason(reason)
        self._require_text(room_number, "room_number")
        actor = self._actor(actor_emp_id)
        room = RoomRecord(
            room_number=room_number,
            room_type=room_type,
            floor=floor,
            created_by_emp=actor["emp_id"],
            notes=notes,
        )
        room.transitions.append(
            RoomTransition(
                from_status="",
                to_status="AVAILABLE",
                action="create_room",
                actor_emp_id=actor["emp_id"],
                reason=reason,
            )
        )
        self.store.add_room(room)
        return self._record_and_publish(
            room=room,
            actor=actor,
            action="create_room",
            audit_action="room.create",
            event_type="room.created",
            event_action="created",
            reason=reason,
            result="AVAILABLE",
            metadata={"from_status": "", "to_status": "AVAILABLE"},
        )

    def reserve_room(self, *, actor_emp_id: str, room_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        room = self.store.room(room_id)
        previous_status = room.status
        self._require_status(room, {"AVAILABLE"}, "reserve_room")
        self._transition(room=room, actor=actor, action="reserve_room", reason=reason, to_status="RESERVED")
        room.reserved_by_emp = actor["emp_id"]
        room.reserved_at = now_iso()
        return self._record_and_publish(
            room=room,
            actor=actor,
            action="reserve_room",
            audit_action="room.reserve",
            event_type="room.reserved",
            event_action="reserved",
            reason=reason,
            result="RESERVED",
            metadata={"from_status": previous_status, "to_status": "RESERVED"},
        )

    def check_in_room(self, *, actor_emp_id: str, room_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        room = self.store.room(room_id)
        previous_status = room.status
        self._require_status(room, {"RESERVED"}, "check_in_room")
        self._transition(room=room, actor=actor, action="check_in_room", reason=reason, to_status="OCCUPIED")
        room.occupied_by_emp = actor["emp_id"]
        room.occupied_at = now_iso()
        return self._record_and_publish(
            room=room,
            actor=actor,
            action="check_in_room",
            audit_action="room.check_in",
            event_type="room.checked_in",
            event_action="checked_in",
            reason=reason,
            result="OCCUPIED",
            metadata={"from_status": previous_status, "to_status": "OCCUPIED"},
        )

    def release_room(self, *, actor_emp_id: str, room_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        room = self.store.room(room_id)
        previous_status = room.status
        self._require_status(room, {"RESERVED", "OCCUPIED"}, "release_room")
        next_status = "AVAILABLE" if previous_status == "RESERVED" else "CLEANING"
        self._transition(room=room, actor=actor, action="release_room", reason=reason, to_status=next_status)
        room.released_by_emp = actor["emp_id"]
        room.released_at = now_iso()
        return self._record_and_publish(
            room=room,
            actor=actor,
            action="release_room",
            audit_action="room.release",
            event_type="room.released",
            event_action="released",
            reason=reason,
            result=next_status,
            metadata={"from_status": previous_status, "to_status": next_status},
        )

    def maintenance_room(
        self,
        *,
        actor_emp_id: str,
        room_id: str,
        reason: str,
        target_status: str = "MAINTENANCE",
    ) -> dict[str, Any]:
        self._require_reason(reason)
        if target_status not in {"MAINTENANCE", "DISABLED"}:
            raise ValueError("target_status must be MAINTENANCE or DISABLED.")
        actor = self._actor(actor_emp_id)
        room = self.store.room(room_id)
        previous_status = room.status
        self._require_status(room, {"AVAILABLE", "RESERVED", "CLEANING", "MAINTENANCE", "DISABLED"}, "maintenance_room")
        self._transition(room=room, actor=actor, action="maintenance_room", reason=reason, to_status=target_status)
        room.maintenance_by_emp = actor["emp_id"]
        room.maintenance_at = now_iso()
        return self._record_and_publish(
            room=room,
            actor=actor,
            action="maintenance_room",
            audit_action="room.maintenance",
            event_type="room.maintenance",
            event_action="maintenance",
            reason=reason,
            result=target_status,
            metadata={"from_status": previous_status, "to_status": target_status},
        )

    def enable_room(self, *, actor_emp_id: str, room_id: str, reason: str) -> dict[str, Any]:
        self._require_reason(reason)
        actor = self._actor(actor_emp_id)
        room = self.store.room(room_id)
        previous_status = room.status
        self._require_status(room, {"CLEANING", "MAINTENANCE", "DISABLED"}, "enable_room")
        self._transition(room=room, actor=actor, action="enable_room", reason=reason, to_status="AVAILABLE")
        room.enabled_by_emp = actor["emp_id"]
        room.enabled_at = now_iso()
        return self._record_and_publish(
            room=room,
            actor=actor,
            action="enable_room",
            audit_action="room.enable",
            event_type="room.enabled",
            event_action="enabled",
            reason=reason,
            result="AVAILABLE",
            metadata={"from_status": previous_status, "to_status": "AVAILABLE"},
        )

    def _actor(self, actor_emp_id: str) -> dict[str, str]:
        return self.actor_resolver.resolve(actor_emp_id, self.domains.get("Room").mutable_by_roles)

    @staticmethod
    def _require_reason(reason: str) -> None:
        if not reason or not reason.strip():
            raise ValueError("reason is required.")

    @staticmethod
    def _require_text(value: str, field_name: str) -> None:
        if not value or not value.strip():
            raise ValueError(f"{field_name} is required.")

    @staticmethod
    def _require_status(room: RoomRecord, allowed_statuses: set[str], action: str) -> None:
        if room.status not in allowed_statuses:
            allowed = ", ".join(sorted(allowed_statuses))
            raise ValueError(f"{action} is not allowed when room status is {room.status}; expected one of: {allowed}.")

    @staticmethod
    def _transition(*, room: RoomRecord, actor: dict[str, str], action: str, reason: str, to_status: str) -> None:
        room.transitions.append(
            RoomTransition(
                from_status=room.status,
                to_status=to_status,
                action=action,
                actor_emp_id=actor["emp_id"],
                reason=reason,
            )
        )
        room.status = to_status

    def _record_and_publish(
        self,
        *,
        room: RoomRecord,
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
            module="room",
            action=action,
            action_type=audit_action,
            reason=reason,
            result=result,
            target_type="room",
            target_id=room.room_id,
            metadata={
                "room_number": room.room_number,
                "room_type": room.room_type,
                "floor": room.floor,
                **metadata,
            },
        )
        event = self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="room",
                subject="room",
                action=event_action,
                emp_id=actor["emp_id"],
                actor_name=actor["name"],
                payload=room.to_dict(),
                correlation_id=room.room_id,
                metadata=metadata,
            )
        )
        return {"room": room.to_dict(), "audit": audit, "event": event}
