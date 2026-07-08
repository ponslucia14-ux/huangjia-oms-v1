import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.stay_engine import STAY_LIFECYCLE, StayService, StayStore
from tests.test_health_check import write_identity, write_organization


class StayEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_organization_master_data.md"
        identity_path = root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.store = StayStore()
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.delivered_events = []
        for event_type in ["stay.created", "stay.checked_in", "stay.extended", "stay.checked_out", "stay.cancelled"]:
            self.bus.subscribe(
                module="test_listener",
                event_type=event_type,
                handler=lambda event: self.delivered_events.append(event.event_type) or "ok",
            )
        self.service = StayService(
            store=self.store,
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _create_stay(self):
        return self.service.create_stay(
            actor_emp_id="EMP008",
            customer_id="customer_001",
            customer_name="Customer A",
            contract_id="contract_001",
            planned_checkin_date="2026-08-01",
            planned_checkout_date="2026-08-29",
            reason="Contract signed and stay plan created.",
        )

    def test_lifecycle_definition_matches_p8_contract(self):
        self.assertEqual(
            STAY_LIFECYCLE,
            (
                "CONTRACTED",
                "WAITING_CHECKIN",
                "CHECKED_IN",
                "IN_STAY",
                "CHECKED_OUT",
                "EXTENDED",
                "CANCELLED",
            ),
        )

    def test_stay_lifecycle_flow_writes_audit_and_publishes_events(self):
        created = self._create_stay()
        stay_id = created["stay"]["stay_id"]
        checked_in = self.service.check_in(actor_emp_id="EMP009", stay_id=stay_id, reason="Customer arrived.")
        extended = self.service.extend_stay(
            actor_emp_id="EMP008",
            stay_id=stay_id,
            extended_until="2026-09-05",
            reason="Customer confirmed stay extension.",
        )
        checked_out = self.service.check_out(actor_emp_id="EMP009", stay_id=stay_id, reason="Customer completed stay.")

        self.assertEqual(created["stay"]["status"], "WAITING_CHECKIN")
        self.assertEqual(checked_in["stay"]["status"], "IN_STAY")
        self.assertEqual(extended["stay"]["status"], "EXTENDED")
        self.assertEqual(checked_out["stay"]["status"], "CHECKED_OUT")
        self.assertEqual(
            self.delivered_events,
            ["stay.created", "stay.checked_in", "stay.extended", "stay.checked_out"],
        )

        audit_events = self.audit.events(sort_by_time=False)
        self.assertEqual(
            [event["action"] for event in audit_events],
            ["create_stay", "check_in", "extend_stay", "check_out"],
        )
        self.assertEqual({event["emp_id"] for event in audit_events}, {"EMP008", "EMP009"})
        self.assertTrue(all(event["reason"] for event in audit_events))

    def test_cancel_stay_writes_audit_and_event(self):
        created = self._create_stay()
        stay_id = created["stay"]["stay_id"]

        cancelled = self.service.cancel_stay(actor_emp_id="EMP008", stay_id=stay_id, reason="Customer cancelled plan.")

        self.assertEqual(cancelled["stay"]["status"], "CANCELLED")
        self.assertEqual(self.delivered_events, ["stay.created", "stay.cancelled"])
        self.assertEqual([event["action"] for event in self.audit.events(sort_by_time=False)], ["create_stay", "cancel_stay"])

    def test_reason_is_required_for_each_key_action(self):
        with self.assertRaises(ValueError):
            self.service.create_stay(
                actor_emp_id="EMP008",
                customer_id="customer_001",
                customer_name="Customer A",
                contract_id="contract_001",
                planned_checkin_date="2026-08-01",
                planned_checkout_date="2026-08-29",
                reason="",
            )
        stay_id = self._create_stay()["stay"]["stay_id"]
        with self.assertRaises(ValueError):
            self.service.check_in(actor_emp_id="EMP009", stay_id=stay_id, reason="")
        with self.assertRaises(ValueError):
            self.service.extend_stay(actor_emp_id="EMP008", stay_id=stay_id, extended_until="", reason="Need date.")

    def test_actor_must_be_emp_and_have_stay_permission(self):
        with self.assertRaises(KeyError):
            self.service.create_stay(
                actor_emp_id="Official Name Is Not EMP",
                customer_id="customer_001",
                customer_name="Customer A",
                contract_id="contract_001",
                planned_checkin_date="2026-08-01",
                planned_checkout_date="2026-08-29",
                reason="Actor must use EMP.",
            )
        with self.assertRaises(PermissionError):
            self.service.create_stay(
                actor_emp_id="EMP006",
                customer_id="customer_001",
                customer_name="Customer A",
                contract_id="contract_001",
                planned_checkin_date="2026-08-01",
                planned_checkout_date="2026-08-29",
                reason="Sales role cannot modify Stay.",
            )

    def test_invalid_state_transitions_are_rejected(self):
        stay_id = self._create_stay()["stay"]["stay_id"]

        with self.assertRaises(ValueError):
            self.service.check_out(actor_emp_id="EMP009", stay_id=stay_id, reason="Cannot checkout before check-in.")

        self.service.check_in(actor_emp_id="EMP009", stay_id=stay_id, reason="Customer arrived.")

        with self.assertRaises(ValueError):
            self.service.check_in(actor_emp_id="EMP009", stay_id=stay_id, reason="Duplicate check-in.")
        with self.assertRaises(ValueError):
            self.service.cancel_stay(actor_emp_id="EMP008", stay_id=stay_id, reason="Cannot cancel after check-in.")


if __name__ == "__main__":
    unittest.main()
