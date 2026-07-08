import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.scheduler import DECISION_PENDING, DECISION_RECOMMENDED, DECISION_REJECTED, SchedulingContext
from oms_v1.scheduling_decision import (
    DecisionContext,
    SchedulingDecisionEngine,
)
from tests.test_health_check import write_identity, write_organization


class SchedulingDecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_organization_master_data.md"
        identity_path = root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.engine = SchedulingDecisionEngine(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )
        self.stay_context = {
            "stay_id": "stay_001",
            "guest_id": "guest_001",
            "expected_check_in": "2026-07-09",
            "care_level": "standard",
        }
        self.room_candidates = (
            {"room_id": "room_001", "room_number": "A-101", "room_status": "AVAILABLE"},
            {"room_id": "room_002", "room_number": "A-102", "room_status": "RESERVED"},
            {"room_id": "room_003", "room_number": "A-103", "room_status": "MAINTENANCE"},
        )
        self.caregiver_candidates = (
            {"caregiver_id": "caregiver_001", "caregiver_name": "Caregiver A", "availability_status": "AVAILABLE"},
            {"caregiver_id": "caregiver_002", "caregiver_name": "Caregiver B", "availability_status": "ON_LEAVE"},
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _scheduling_context(self, **overrides):
        payload = {
            "stay_context": self.stay_context,
            "room_candidates": self.room_candidates,
            "caregiver_candidates": self.caregiver_candidates,
            "business_rule_results": (),
        }
        payload.update(overrides)
        return SchedulingContext(**payload)

    def _decision_context(self, **overrides):
        payload = {
            "request_id": "sched_dec_req_001",
            "actor_emp_id": "EMP008",
            "reason": "Rank scheduling candidates for human confirmation.",
            "scheduling_context": self._scheduling_context(),
            "business_rule_results": (
                {
                    "rule_id": "BR_TEST",
                    "overall_status": "PASS",
                    "reject_reasons": [],
                    "warning_reasons": [],
                },
            ),
            "correlation_id": "sched_req_001",
        }
        payload.update(overrides)
        return DecisionContext(**payload)

    def test_decision_context_contains_required_inputs(self):
        context = self._decision_context()

        payload = context.to_dict()
        self.assertEqual(payload["request_id"], "sched_dec_req_001")
        self.assertEqual(payload["actor_emp_id"], "EMP008")
        self.assertEqual(payload["reason"], "Rank scheduling candidates for human confirmation.")
        self.assertEqual(payload["scheduling_context"]["stay_context"]["stay_id"], "stay_001")
        self.assertEqual(payload["business_rule_results"][0]["rule_id"], "BR_TEST")

    def test_default_rule_list_contains_p13_rule_batch(self):
        rule_ids = [definition["rule_id"] for definition in self.engine.definitions()]

        self.assertEqual(
            rule_ids,
            [
                "SDR_ROOM_AVAILABILITY_PRIORITY",
                "SDR_ROOM_STATUS_RESTRICTION",
                "SDR_ROOM_MAINTENANCE_DISABLED_EXCLUSION",
                "SDR_CAREGIVER_STATUS_RESTRICTION",
                "SDR_PERMISSION_AUTHORIZATION",
            ],
        )

    def test_decision_engine_ranks_available_room_and_caregiver_first(self):
        result = self.engine.decide(self._decision_context())

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["decision_status"], DECISION_RECOMMENDED)
        self.assertFalse(result["mutates_business_state"])
        self.assertEqual(result["ranked_recommendations"][0]["room_id"], "room_001")
        self.assertEqual(result["ranked_recommendations"][0]["caregiver_id"], "caregiver_001")
        self.assertTrue(result["ranked_recommendations"][0]["requires_human_confirmation"])
        self.assertFalse(result["ranked_recommendations"][0]["auto_executed"])

    def test_maintenance_and_disabled_rooms_are_rejected(self):
        context = self._decision_context(
            candidate_resources=(
                {
                    "option_id": "maint_room",
                    "room_id": "room_maint",
                    "room_status": "MAINTENANCE",
                    "caregiver_id": "caregiver_001",
                    "caregiver_status": "AVAILABLE",
                },
                {
                    "option_id": "disabled_room",
                    "room_id": "room_disabled",
                    "room_status": "DISABLED",
                    "caregiver_id": "caregiver_001",
                    "caregiver_status": "AVAILABLE",
                },
            )
        )

        result = self.engine.decide(context)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["decision_status"], DECISION_REJECTED)
        self.assertEqual(result["ranked_recommendations"], [])
        self.assertEqual({item["option_id"] for item in result["rejected_options"]}, {"maint_room", "disabled_room"})
        self.assertTrue(
            all("SDR_ROOM_MAINTENANCE_DISABLED_EXCLUSION" in item["rejected_by"] for item in result["rejected_options"])
        )

    def test_unavailable_caregiver_is_rejected(self):
        context = self._decision_context(
            candidate_resources=(
                {
                    "option_id": "bad_caregiver",
                    "room_id": "room_001",
                    "room_status": "AVAILABLE",
                    "caregiver_id": "caregiver_bad",
                    "caregiver_status": "ON_LEAVE",
                },
            )
        )

        result = self.engine.decide(context)

        self.assertEqual(result["decision_status"], DECISION_REJECTED)
        self.assertEqual(result["rejected_options"][0]["option_id"], "bad_caregiver")
        self.assertIn("SDR_CAREGIVER_STATUS_RESTRICTION", result["rejected_options"][0]["rejected_by"])

    def test_permission_authorization_rejects_unauthorized_actor(self):
        context = self._decision_context(actor_emp_id="EMP006")

        result = self.engine.decide(context)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["decision_status"], DECISION_REJECTED)
        self.assertEqual(result["ranked_recommendations"], [])
        self.assertTrue(
            all("SDR_PERMISSION_AUTHORIZATION" in item["rejected_by"] for item in result["rejected_options"])
        )

    def test_events_and_audit_are_written(self):
        result = self.engine.decide(self._decision_context())

        self.assertEqual(
            [event["event_type"] for event in self.bus.events()],
            ["scheduling.decision.requested", "scheduling.decision.completed"],
        )
        self.assertEqual(
            [event["action"] for event in self.audit.events(sort_by_time=False)],
            ["scheduling_decision.request", "scheduling_decision.complete"],
        )
        self.assertEqual(result["events"][0]["event"]["payload"]["decision_status"], DECISION_PENDING)
        self.assertEqual(result["events"][1]["event"]["payload"]["decision_status"], DECISION_RECOMMENDED)
        self.assertTrue(all(record["reason"] for record in result["audit_records"]))

    def test_failed_decision_publishes_failed_event(self):
        result = self.engine.decide(
            self._decision_context(
                candidate_resources=(
                    {
                        "option_id": "disabled_room",
                        "room_id": "room_disabled",
                        "room_status": "DISABLED",
                        "caregiver_id": "caregiver_bad",
                        "caregiver_status": "ON_LEAVE",
                    },
                )
            )
        )

        self.assertEqual(result["events"][0]["event"]["payload"]["decision_status"], DECISION_PENDING)
        self.assertEqual(result["events"][1]["event"]["event_type"], "scheduling.decision.failed")
        self.assertEqual(result["events"][1]["event"]["payload"]["decision_status"], DECISION_REJECTED)
        self.assertEqual(self.audit.events(sort_by_time=False)[-1]["action"], "scheduling_decision.fail")

    def test_reserved_resources_remain_human_review_warnings_not_execution(self):
        context = self._decision_context(
            candidate_resources=(
                {
                    "option_id": "reserved_option",
                    "room_id": "room_reserved",
                    "room_status": "RESERVED",
                    "caregiver_id": "caregiver_reserved",
                    "caregiver_status": "RESERVED",
                },
            )
        )

        result = self.engine.decide(context)

        self.assertEqual(result["decision_status"], DECISION_RECOMMENDED)
        self.assertEqual(result["ranked_recommendations"][0]["option_id"], "reserved_option")
        self.assertTrue(result["warnings"])
        self.assertFalse(result["ranked_recommendations"][0]["auto_executed"])

    def test_decision_does_not_mutate_input_context_or_candidates(self):
        context = self._decision_context()
        original_context = copy.deepcopy(context.to_dict())

        result = self.engine.decide(context)

        self.assertEqual(context.to_dict(), original_context)
        self.assertFalse(result["mutates_business_state"])


if __name__ == "__main__":
    unittest.main()
