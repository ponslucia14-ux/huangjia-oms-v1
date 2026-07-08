import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.business_rules import BusinessRulesEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.scheduler import (
    DECISION_PENDING,
    DECISION_RECOMMENDED,
    DECISION_REJECTED,
    Scheduler,
    SchedulerEngine,
    SchedulingContext,
    SchedulingRequest,
)
from tests.test_health_check import write_identity, write_organization


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_organization_master_data.md"
        identity_path = root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.rules = BusinessRulesEngine(master_data=self.master_data)
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.engine = SchedulerEngine(
            business_rules=self.rules,
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )
        self.stay_context = {
            "stay_id": "stay_001",
            "guest_id": "guest_001",
            "expected_check_in": "2026-07-09",
            "expected_check_out": "2026-07-28",
            "care_level": "standard",
            "special_requirements": [],
            "current_status": "WAITING_CHECKIN",
        }
        self.rooms = (
            {"room_id": "room_001", "room_number": "A-101", "room_status": "AVAILABLE"},
            {"room_id": "room_002", "room_number": "A-102", "room_status": "MAINTENANCE"},
        )
        self.caregivers = (
            {"caregiver_id": "caregiver_001", "caregiver_name": "Caregiver A", "availability_status": "AVAILABLE"},
            {"caregiver_id": "caregiver_002", "caregiver_name": "Caregiver B", "availability_status": "ON_LEAVE"},
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _request(self, **overrides):
        payload = {
            "request_id": "sched_req_001",
            "request_type": "combined",
            "actor_emp_id": "EMP008",
            "reason": "Need scheduling analysis for upcoming check-in.",
            "stay_id": "stay_001",
            "source_module": "stay",
            "requirements": {"room_type": "single", "care_level": "standard"},
            "priority": "normal",
            "correlation_id": "biz_evt_001",
        }
        payload.update(overrides)
        return SchedulingRequest(**payload)

    def _context(self, **overrides):
        payload = {
            "stay_context": self.stay_context,
            "room_candidates": self.rooms,
            "caregiver_candidates": self.caregivers,
            "business_rule_results": (),
            "business_rules": self.rules,
        }
        payload.update(overrides)
        return SchedulingContext(**payload)

    def test_request_creation_contains_p12_fields(self):
        request = self._request()

        payload = request.to_dict()
        self.assertEqual(payload["request_id"], "sched_req_001")
        self.assertEqual(payload["request_type"], "combined")
        self.assertEqual(payload["actor_emp_id"], "EMP008")
        self.assertEqual(payload["reason"], "Need scheduling analysis for upcoming check-in.")
        self.assertEqual(payload["stay_id"], "stay_001")
        self.assertEqual(payload["source_module"], "stay")
        self.assertEqual(payload["requirements"]["room_type"], "single")
        self.assertEqual(payload["priority"], "normal")
        self.assertEqual(payload["correlation_id"], "biz_evt_001")

    def test_request_requires_emp_reason_stay_and_source(self):
        with self.assertRaises(ValueError):
            self._request(actor_emp_id="")
        with self.assertRaises(ValueError):
            self._request(reason="")
        with self.assertRaises(ValueError):
            self._request(stay_id="")
        with self.assertRaises(ValueError):
            self._request(source_module="")
        with self.assertRaises(ValueError):
            self._request(request_type="unknown")

    def test_context_contains_stay_room_caregiver_and_business_rules(self):
        context = self._context(
            business_rule_results=(
                {
                    "rule_id": "BR_TEST",
                    "overall_status": "PASS",
                    "reject_reasons": [],
                    "warning_reasons": [],
                },
            )
        )

        payload = context.to_dict()
        self.assertEqual(payload["stay_context"]["stay_id"], "stay_001")
        self.assertEqual(payload["room_candidates"][0]["room_id"], "room_001")
        self.assertEqual(payload["caregiver_candidates"][0]["caregiver_id"], "caregiver_001")
        self.assertEqual(payload["business_rule_results"][0]["rule_id"], "BR_TEST")
        self.assertTrue(payload["has_business_rules"])

    def test_scheduler_returns_result_without_mutating_room_stay_or_caregiver(self):
        request = self._request()
        context = self._context()
        stay_before = copy.deepcopy(self.stay_context)
        rooms_before = copy.deepcopy(self.rooms)
        caregivers_before = copy.deepcopy(self.caregivers)

        result = self.engine.schedule(request, context)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["decision_status"], DECISION_RECOMMENDED)
        self.assertFalse(result["mutates_business_state"])
        self.assertEqual(result["recommendations"][0]["recommended_room_id"], "room_001")
        self.assertEqual(result["recommendations"][0]["recommended_caregiver_id"], "caregiver_001")
        self.assertFalse(result["recommendations"][0]["auto_assigned"])
        self.assertEqual(self.stay_context, stay_before)
        self.assertEqual(self.rooms, rooms_before)
        self.assertEqual(self.caregivers, caregivers_before)

    def test_event_publishing_and_audit_writing_for_completed_schedule(self):
        result = self.engine.schedule(self._request(), self._context())

        self.assertEqual([event["event_type"] for event in self.bus.events()], ["scheduling.requested", "scheduling.completed"])
        self.assertEqual([event["action"] for event in self.audit.events(sort_by_time=False)], [
            "scheduling.request",
            "scheduling.context_built",
            "scheduling.complete",
        ])
        self.assertEqual([record["action"] for record in result["audit_records"]], [
            "scheduling.request",
            "scheduling.context_built",
            "scheduling.complete",
        ])
        self.assertEqual(result["events"][0]["event"]["event_type"], "scheduling.requested")
        self.assertEqual(result["events"][1]["event"]["event_type"], "scheduling.completed")
        self.assertEqual(result["events"][0]["event"]["payload"]["decision_status"], DECISION_PENDING)
        self.assertEqual(result["events"][1]["event"]["payload"]["decision_status"], DECISION_RECOMMENDED)
        self.assertTrue(all(record["reason"] for record in result["audit_records"]))
        self.assertEqual({record["emp_id"] for record in result["audit_records"]}, {"EMP008"})

    def test_failed_schedule_publishes_failed_event_and_rejected_decision_status(self):
        request = self._request()
        context = self._context(
            room_candidates=({"room_id": "room_002", "room_status": "MAINTENANCE"},),
            caregiver_candidates=({"caregiver_id": "caregiver_002", "availability_status": "ON_LEAVE"},),
        )

        result = self.engine.schedule(request, context)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["decision_status"], DECISION_REJECTED)
        self.assertEqual(result["recommendations"], [])
        self.assertTrue(result["failure_reasons"])
        self.assertEqual([event["event_type"] for event in self.bus.events()], ["scheduling.requested", "scheduling.failed"])
        self.assertEqual(self.audit.events(sort_by_time=False)[-1]["action"], "scheduling.fail")

    def test_decision_status_flow_is_pending_then_recommended_or_rejected(self):
        recommended = self.engine.schedule(self._request(request_id="sched_req_recommended"), self._context())
        self.assertEqual(recommended["events"][0]["event"]["payload"]["decision_status"], DECISION_PENDING)
        self.assertEqual(recommended["decision_status"], DECISION_RECOMMENDED)

        rejected_context = self._context(
            room_candidates=({"room_id": "room_002", "room_status": "DISABLED"},),
            caregiver_candidates=({"caregiver_id": "caregiver_002", "availability_status": "ON_LEAVE"},),
        )
        rejected = self.engine.schedule(self._request(request_id="sched_req_rejected"), rejected_context)
        self.assertEqual(rejected["events"][0]["event"]["payload"]["decision_status"], DECISION_PENDING)
        self.assertEqual(rejected["decision_status"], DECISION_REJECTED)

    def test_business_rule_trace_is_returned(self):
        result = self.engine.schedule(self._request(), self._context())

        self.assertTrue(result["business_rule_trace"])
        self.assertIn("rule_result", result["business_rule_trace"][0])
        self.assertFalse(result["business_rule_trace"][0]["rule_result"]["mutates_business_state"])

    def test_scheduler_facade_delegates_to_engine(self):
        scheduler = Scheduler(engine=self.engine)
        result = scheduler.schedule(self._request(), self._context())

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["decision_status"], DECISION_RECOMMENDED)


if __name__ == "__main__":
    unittest.main()
