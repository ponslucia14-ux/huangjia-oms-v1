import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.room_engine import ROOM_LIFECYCLE, RoomService, RoomStore
from tests.test_health_check import write_identity, write_organization


class RoomEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_organization_master_data.md"
        identity_path = root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.store = RoomStore()
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.delivered_events = []
        for event_type in [
            "room.created",
            "room.reserved",
            "room.checked_in",
            "room.released",
            "room.maintenance",
            "room.enabled",
        ]:
            self.bus.subscribe(
                module="test_listener",
                event_type=event_type,
                handler=lambda event: self.delivered_events.append(event.event_type) or "ok",
            )
        self.service = RoomService(
            store=self.store,
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _create_room(self, room_number: str = "A-101"):
        return self.service.create_room(
            actor_emp_id="EMP008",
            room_number=room_number,
            room_type="single",
            floor="1F",
            reason="Create official room resource.",
        )

    def test_lifecycle_definition_matches_p9_contract(self):
        self.assertEqual(
            ROOM_LIFECYCLE,
            (
                "AVAILABLE",
                "RESERVED",
                "OCCUPIED",
                "CLEANING",
                "MAINTENANCE",
                "DISABLED",
            ),
        )

    def test_room_resource_flow_writes_audit_and_publishes_events(self):
        created = self._create_room()
        room_id = created["room"]["room_id"]
        reserved = self.service.reserve_room(actor_emp_id="EMP008", room_id=room_id, reason="Reserve room resource.")
        occupied = self.service.check_in_room(actor_emp_id="EMP008", room_id=room_id, reason="Room is now occupied.")
        cleaning = self.service.release_room(actor_emp_id="EMP008", room_id=room_id, reason="Release room after checkout.")
        available = self.service.enable_room(actor_emp_id="EMP008", room_id=room_id, reason="Cleaning completed.")

        self.assertEqual(created["room"]["status"], "AVAILABLE")
        self.assertEqual(reserved["room"]["status"], "RESERVED")
        self.assertEqual(occupied["room"]["status"], "OCCUPIED")
        self.assertEqual(cleaning["room"]["status"], "CLEANING")
        self.assertEqual(available["room"]["status"], "AVAILABLE")
        self.assertEqual(
            self.delivered_events,
            ["room.created", "room.reserved", "room.checked_in", "room.released", "room.enabled"],
        )

        audit_events = self.audit.events(sort_by_time=False)
        self.assertEqual(
            [event["action"] for event in audit_events],
            ["create_room", "reserve_room", "check_in_room", "release_room", "enable_room"],
        )
        self.assertEqual({event["emp_id"] for event in audit_events}, {"EMP008"})
        self.assertTrue(all(event["reason"] for event in audit_events))

    def test_maintenance_and_disabled_states(self):
        room_id = self._create_room()["room"]["room_id"]

        maintenance = self.service.maintenance_room(
            actor_emp_id="EMP005",
            room_id=room_id,
            reason="Room requires maintenance.",
        )
        enabled = self.service.enable_room(actor_emp_id="EMP005", room_id=room_id, reason="Maintenance completed.")
        disabled = self.service.maintenance_room(
            actor_emp_id="EMP005",
            room_id=room_id,
            reason="Room is disabled for long-term repair.",
            target_status="DISABLED",
        )

        self.assertEqual(maintenance["room"]["status"], "MAINTENANCE")
        self.assertEqual(enabled["room"]["status"], "AVAILABLE")
        self.assertEqual(disabled["room"]["status"], "DISABLED")
        self.assertEqual(
            self.delivered_events,
            ["room.created", "room.maintenance", "room.enabled", "room.maintenance"],
        )

    def test_release_reserved_room_returns_available(self):
        room_id = self._create_room()["room"]["room_id"]
        self.service.reserve_room(actor_emp_id="EMP008", room_id=room_id, reason="Reserve room resource.")

        released = self.service.release_room(actor_emp_id="EMP008", room_id=room_id, reason="Reservation cancelled.")

        self.assertEqual(released["room"]["status"], "AVAILABLE")

    def test_reason_is_required_for_each_key_action(self):
        with self.assertRaises(ValueError):
            self.service.create_room(
                actor_emp_id="EMP008",
                room_number="A-101",
                room_type="single",
                floor="1F",
                reason="",
            )
        room_id = self._create_room()["room"]["room_id"]
        with self.assertRaises(ValueError):
            self.service.reserve_room(actor_emp_id="EMP008", room_id=room_id, reason="")
        with self.assertRaises(ValueError):
            self.service.maintenance_room(actor_emp_id="EMP008", room_id=room_id, reason="", target_status="MAINTENANCE")

    def test_actor_must_be_emp_and_have_room_permission(self):
        with self.assertRaises(KeyError):
            self.service.create_room(
                actor_emp_id="Official Name Is Not EMP",
                room_number="A-101",
                room_type="single",
                floor="1F",
                reason="Actor must use EMP.",
            )
        with self.assertRaises(PermissionError):
            self.service.create_room(
                actor_emp_id="EMP006",
                room_number="A-101",
                room_type="single",
                floor="1F",
                reason="Sales role cannot modify Room.",
            )

    def test_invalid_state_transitions_are_rejected(self):
        room_id = self._create_room()["room"]["room_id"]

        with self.assertRaises(ValueError):
            self.service.check_in_room(actor_emp_id="EMP008", room_id=room_id, reason="Cannot occupy available room directly.")

        self.service.reserve_room(actor_emp_id="EMP008", room_id=room_id, reason="Reserve room resource.")
        self.service.check_in_room(actor_emp_id="EMP008", room_id=room_id, reason="Room is now occupied.")

        with self.assertRaises(ValueError):
            self.service.reserve_room(actor_emp_id="EMP008", room_id=room_id, reason="Cannot reserve occupied room.")
        with self.assertRaises(ValueError):
            self.service.maintenance_room(actor_emp_id="EMP008", room_id=room_id, reason="Cannot maintain occupied room.")

    def test_room_number_must_be_unique(self):
        self._create_room("A-101")
        with self.assertRaises(ValueError):
            self._create_room("A-101")


if __name__ == "__main__":
    unittest.main()
