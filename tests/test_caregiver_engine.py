import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.caregiver_engine import CAREGIVER_LIFECYCLE, CaregiverService, CaregiverStore
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class CaregiverEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_organization_master_data.md"
        identity_path = root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.store = CaregiverStore()
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.delivered_events = []
        for event_type in [
            "caregiver.created",
            "caregiver.reserved",
            "caregiver.assigned",
            "caregiver.released",
            "caregiver.leave",
            "caregiver.enabled",
        ]:
            self.bus.subscribe(
                module="test_listener",
                event_type=event_type,
                handler=lambda event: self.delivered_events.append(event.event_type) or "ok",
            )
        self.service = CaregiverService(
            store=self.store,
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _create_caregiver(self):
        return self.service.create_caregiver(
            actor_emp_id="EMP010",
            caregiver_name="Caregiver A",
            skill_level="senior",
            phone="13800000000",
            reason="Create official caregiver resource.",
        )

    def test_lifecycle_definition_matches_p11_contract(self):
        self.assertEqual(
            CAREGIVER_LIFECYCLE,
            (
                "AVAILABLE",
                "RESERVED",
                "ASSIGNED",
                "ON_LEAVE",
                "OFF_DUTY",
                "DISABLED",
            ),
        )

    def test_caregiver_resource_flow_writes_audit_and_publishes_events(self):
        created = self._create_caregiver()
        caregiver_id = created["caregiver"]["caregiver_id"]
        reserved = self.service.reserve_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Reserve caregiver resource.",
        )
        assigned = self.service.assign_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Assign caregiver resource.",
        )
        off_duty = self.service.release_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Release caregiver from assignment.",
        )
        available = self.service.enable_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Caregiver is ready again.",
        )

        self.assertEqual(created["caregiver"]["status"], "AVAILABLE")
        self.assertEqual(reserved["caregiver"]["status"], "RESERVED")
        self.assertEqual(assigned["caregiver"]["status"], "ASSIGNED")
        self.assertEqual(off_duty["caregiver"]["status"], "OFF_DUTY")
        self.assertEqual(available["caregiver"]["status"], "AVAILABLE")
        self.assertEqual(
            self.delivered_events,
            [
                "caregiver.created",
                "caregiver.reserved",
                "caregiver.assigned",
                "caregiver.released",
                "caregiver.enabled",
            ],
        )

        audit_events = self.audit.events(sort_by_time=False)
        self.assertEqual(
            [event["action"] for event in audit_events],
            [
                "create_caregiver",
                "reserve_caregiver",
                "assign_caregiver",
                "release_caregiver",
                "enable_caregiver",
            ],
        )
        self.assertEqual({event["emp_id"] for event in audit_events}, {"EMP010"})
        self.assertTrue(all(event["reason"] for event in audit_events))

    def test_leave_and_disabled_states(self):
        caregiver_id = self._create_caregiver()["caregiver"]["caregiver_id"]

        on_leave = self.service.leave_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Caregiver requested leave.",
        )
        enabled = self.service.enable_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Leave completed.",
        )
        disabled = self.service.leave_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Caregiver resource is disabled.",
            target_status="DISABLED",
        )

        self.assertEqual(on_leave["caregiver"]["status"], "ON_LEAVE")
        self.assertEqual(enabled["caregiver"]["status"], "AVAILABLE")
        self.assertEqual(disabled["caregiver"]["status"], "DISABLED")
        self.assertEqual(
            self.delivered_events,
            ["caregiver.created", "caregiver.leave", "caregiver.enabled", "caregiver.leave"],
        )

    def test_release_reserved_caregiver_returns_available(self):
        caregiver_id = self._create_caregiver()["caregiver"]["caregiver_id"]
        self.service.reserve_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Reserve caregiver resource.",
        )

        released = self.service.release_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Reservation cancelled.",
        )

        self.assertEqual(released["caregiver"]["status"], "AVAILABLE")

    def test_reason_is_required_for_each_key_action(self):
        with self.assertRaises(ValueError):
            self.service.create_caregiver(
                actor_emp_id="EMP010",
                caregiver_name="Caregiver A",
                skill_level="senior",
                phone="13800000000",
                reason="",
            )
        caregiver_id = self._create_caregiver()["caregiver"]["caregiver_id"]
        with self.assertRaises(ValueError):
            self.service.reserve_caregiver(actor_emp_id="EMP010", caregiver_id=caregiver_id, reason="")
        with self.assertRaises(ValueError):
            self.service.leave_caregiver(actor_emp_id="EMP010", caregiver_id=caregiver_id, reason="")

    def test_actor_must_be_emp_and_have_caregiver_permission(self):
        with self.assertRaises(KeyError):
            self.service.create_caregiver(
                actor_emp_id="Official Name Is Not EMP",
                caregiver_name="Caregiver A",
                skill_level="senior",
                phone="13800000000",
                reason="Actor must use EMP.",
            )
        with self.assertRaises(PermissionError):
            self.service.create_caregiver(
                actor_emp_id="EMP006",
                caregiver_name="Caregiver A",
                skill_level="senior",
                phone="13800000000",
                reason="Sales role cannot modify Caregiver.",
            )

    def test_invalid_state_transitions_are_rejected(self):
        caregiver_id = self._create_caregiver()["caregiver"]["caregiver_id"]

        with self.assertRaises(ValueError):
            self.service.assign_caregiver(
                actor_emp_id="EMP010",
                caregiver_id=caregiver_id,
                reason="Cannot assign available caregiver directly.",
            )

        self.service.reserve_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Reserve caregiver resource.",
        )
        self.service.assign_caregiver(
            actor_emp_id="EMP010",
            caregiver_id=caregiver_id,
            reason="Assign caregiver resource.",
        )

        with self.assertRaises(ValueError):
            self.service.reserve_caregiver(
                actor_emp_id="EMP010",
                caregiver_id=caregiver_id,
                reason="Cannot reserve assigned caregiver.",
            )
        with self.assertRaises(ValueError):
            self.service.leave_caregiver(
                actor_emp_id="EMP010",
                caregiver_id=caregiver_id,
                reason="Assigned caregiver cannot be put on leave before release.",
            )

    def test_invalid_leave_target_status_is_rejected(self):
        caregiver_id = self._create_caregiver()["caregiver"]["caregiver_id"]

        with self.assertRaises(ValueError):
            self.service.leave_caregiver(
                actor_emp_id="EMP010",
                caregiver_id=caregiver_id,
                reason="Invalid target status.",
                target_status="OFF_DUTY",
            )


if __name__ == "__main__":
    unittest.main()
