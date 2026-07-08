import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.business_rules import BusinessRulesEngine
from oms_v1.master_data import OMSMasterData
from oms_v1.scheduler import Scheduler, SchedulerEngine, SchedulingContext, SchedulingRequest
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
        self.engine = SchedulerEngine(business_rules=self.rules)
        self.stay = {
            "stay_id": "stay_001",
            "customer_id": "customer_001",
            "contract_id": "contract_001",
            "status": "WAITING_CHECKIN",
        }
        self.rooms = (
            {"room_id": "room_001", "room_number": "A-101", "status": "AVAILABLE"},
            {"room_id": "room_002", "room_number": "A-102", "status": "MAINTENANCE"},
        )
        self.caregivers = (
            {"caregiver_id": "caregiver_001", "caregiver_name": "Caregiver A", "status": "AVAILABLE"},
            {"caregiver_id": "caregiver_002", "caregiver_name": "Caregiver B", "status": "ON_LEAVE"},
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_scheduler_generates_suggestions_without_mutating_resources(self):
        rooms_before = copy.deepcopy(self.rooms)
        caregivers_before = copy.deepcopy(self.caregivers)
        request = SchedulingRequest(stay=self.stay, actor_emp_id="EMP008")
        context = SchedulingContext(rooms=self.rooms, caregivers=self.caregivers, business_rules=self.rules)

        result = self.engine.schedule(request, context)

        self.assertEqual(result["status"], "WARNING")
        self.assertFalse(result["mutates_business_state"])
        self.assertEqual(result["recommendations"][0]["room_id"], "room_001")
        self.assertEqual(result["recommendations"][0]["caregiver_id"], "caregiver_001")
        self.assertFalse(result["recommendations"][0]["auto_assigned"])
        self.assertEqual(self.rooms, rooms_before)
        self.assertEqual(self.caregivers, caregivers_before)

    def test_business_rules_reject_maintenance_and_disabled_rooms(self):
        request = SchedulingRequest(stay=self.stay, actor_emp_id="EMP008")
        context = SchedulingContext(
            rooms=(
                {"room_id": "room_002", "room_number": "A-102", "status": "MAINTENANCE"},
                {"room_id": "room_003", "room_number": "A-103", "status": "DISABLED"},
            ),
            caregivers=({"caregiver_id": "caregiver_001", "status": "AVAILABLE"},),
            business_rules=self.rules,
        )

        result = self.engine.schedule(request, context)

        self.assertEqual(result["status"], "WARNING")
        self.assertEqual([candidate["status"] for candidate in result["room_candidates"]], ["REJECT", "REJECT"])
        self.assertTrue(any("Room is under maintenance and cannot be checked in." in reason for reason in result["rejects"]))
        self.assertTrue(any("Room is disabled and cannot be checked in." in reason for reason in result["rejects"]))
        self.assertEqual(result["recommendations"][0]["room_id"], "")
        self.assertEqual(result["recommendations"][0]["caregiver_id"], "caregiver_001")

    def test_requested_resources_are_marked_when_they_do_not_match(self):
        request = SchedulingRequest(
            stay=self.stay,
            actor_emp_id="EMP008",
            requested_room_id="room_002",
            requested_caregiver_id="caregiver_002",
        )
        context = SchedulingContext(rooms=self.rooms, caregivers=self.caregivers, business_rules=self.rules)

        result = self.engine.schedule(request, context)

        self.assertEqual(result["room_candidates"][0]["status"], "WARNING")
        self.assertEqual(result["room_candidates"][0]["reason"], "Room does not match requested_room_id.")
        self.assertEqual(result["caregiver_candidates"][0]["status"], "WARNING")
        self.assertEqual(result["caregiver_candidates"][0]["reason"], "Caregiver does not match requested_caregiver_id.")

    def test_missing_resources_return_warning(self):
        request = SchedulingRequest(stay=self.stay, actor_emp_id="EMP008")

        no_rooms = self.engine.schedule(request, SchedulingContext(rooms=(), caregivers=self.caregivers))
        no_caregivers = self.engine.schedule(request, SchedulingContext(rooms=self.rooms, caregivers=()))

        self.assertEqual(no_rooms["status"], "WARNING")
        self.assertEqual(no_rooms["reason"], "No room resources were provided for scheduling analysis.")
        self.assertEqual(no_caregivers["status"], "WARNING")
        self.assertEqual(no_caregivers["reason"], "No caregiver resources were provided for scheduling analysis.")

    def test_all_unschedulable_resources_reject(self):
        request = SchedulingRequest(stay=self.stay, actor_emp_id="EMP008")
        result = self.engine.schedule(
            request,
            SchedulingContext(
                rooms=({"room_id": "room_002", "status": "MAINTENANCE"},),
                caregivers=({"caregiver_id": "caregiver_002", "status": "ON_LEAVE"},),
                business_rules=self.rules,
            ),
        )

        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(result["recommendations"], ())

    def test_request_requires_stay_and_emp(self):
        with self.assertRaises(ValueError):
            SchedulingRequest(stay={}, actor_emp_id="EMP008")
        with self.assertRaises(ValueError):
            SchedulingRequest(stay=self.stay, actor_emp_id="")

    def test_scheduler_facade_delegates_to_engine(self):
        scheduler = Scheduler(engine=self.engine)
        result = scheduler.schedule(
            {"stay": self.stay, "actor_emp_id": "EMP008"},
            {"rooms": self.rooms, "caregivers": self.caregivers, "business_rules": self.rules},
        )

        self.assertIn(result["status"], {"PASS", "WARNING"})
        self.assertFalse(result["mutates_business_state"])


if __name__ == "__main__":
    unittest.main()
