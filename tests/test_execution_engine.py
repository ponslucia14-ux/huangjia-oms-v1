import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_bus import EventBus
from oms_v1.event_engine import EventEngine
from oms_v1.execution_engine import (
    EXECUTION_COMPLETED,
    EXECUTION_FAILED,
    ExecutionCommand,
    ExecutionEngine,
    ExecutionRequest,
)
from oms_v1.input_hub import OMSInputHub
from oms_v1.master_data import OMSMasterData
from oms_v1.scheduling_approval import APPROVAL_APPROVED, APPROVAL_REJECTED
from tests.test_health_check import write_identity, write_organization


class ExecutionEngineTests(unittest.TestCase):
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
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.events = EventEngine()
        self.decisions = DecisionEngine()
        self.execution = ExecutionEngine(self.master_data, audit=self.audit, event_bus=self.bus)

    def tearDown(self):
        self.tmp.cleanup()

    def _execution_stream(self, text):
        env = self.hub.accept_text(text)
        parsed = self.parser.parse(env)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        return self.execution.build_execution_stream(decision_stream)

    def _decision_result(self, **overrides):
        payload = {
            "result_id": "scheddec_res_001",
            "decision_status": "RECOMMENDED",
            "ranked_recommendations": [
                {
                    "recommendation_id": "scheddec_rec_001",
                    "option_id": "option_001",
                    "room_id": "room_001",
                    "caregiver_id": "caregiver_001",
                    "decision_status": "RECOMMENDED",
                    "requires_human_confirmation": True,
                    "auto_executed": False,
                }
            ],
            "mutates_business_state": False,
        }
        payload.update(overrides)
        return payload

    def _approval_workflow(self, **overrides):
        payload = {
            "approval_id": "sched_appr_001",
            "decision_id": "scheddec_res_001",
            "current_status": APPROVAL_APPROVED,
            "execution_authorized": True,
            "mutates_business_state": False,
        }
        payload.update(overrides)
        return payload

    def _execution_request(self, **overrides):
        payload = {
            "request_id": "exec_req_001",
            "decision_result": self._decision_result(),
            "approval_workflow": self._approval_workflow(),
            "requester_emp_id": "EMP008",
            "reason": "Execute approved scheduling recommendation in simulation mode.",
            "correlation_id": "sched_appr_001",
        }
        payload.update(overrides)
        return ExecutionRequest(**payload)

    def test_execution_stream_required_fields(self):
        stream = self._execution_stream(
            "客户姓名：李梅，签约无敌套餐，合同编号 HJ-2026-001，全款费用 49800 元；"
            "刘晶收到定金 10000 元，7月2日到账；备注：安排8月1日入住，管家跟进服务。"
        )

        self.assertGreaterEqual(len(stream["actions"]), 3)
        for action in stream["actions"]:
            for field in [
                "action_type",
                "target_module",
                "execution_result",
                "status",
                "timestamp",
                "rollback_supported",
            ]:
                self.assertIn(field, action)
            self.assertIn(action["status"], {"success", "failed", "pending"})
            self.assertTrue(action["rollback_supported"])
            self.assertTrue(action["human_override_allowed"])
            self.assertGreater(len(action["override_roles"]), 0)

    def test_execution_requires_decision_stream(self):
        with self.assertRaises(ValueError):
            self.execution.build_execution_stream({"events": []})

    def test_finance_decision_generates_finance_action(self):
        stream = self._execution_stream("刘晶收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001")
        finance_actions = [action for action in stream["actions"] if action["target_module"] == "finance_module"]

        self.assertTrue(finance_actions)
        self.assertTrue(any(action["action_type"] == "generate_reconciliation_task" for action in finance_actions))

    def test_high_risk_actions_wait_for_final_review(self):
        stream = self._execution_stream("备注：客户已生，8月1日入住，但房间不够，可能需要调房。")
        risky_actions = [
            action
            for action in stream["actions"]
            if action["execution_payload"].get("risk_level") == "high"
        ]

        self.assertTrue(risky_actions)
        self.assertTrue(all(action["status"] == "pending" for action in risky_actions))

    def test_execution_request_contains_required_fields(self):
        request = self._execution_request()

        payload = request.to_dict()
        self.assertEqual(payload["request_id"], "exec_req_001")
        self.assertEqual(payload["decision_result"]["result_id"], "scheddec_res_001")
        self.assertEqual(payload["approval_workflow"]["approval_id"], "sched_appr_001")
        self.assertEqual(payload["requester_emp_id"], "EMP008")
        self.assertEqual(payload["reason"], "Execute approved scheduling recommendation in simulation mode.")

    def test_authorized_execution_completes_in_simulation_mode(self):
        result = self.execution.execute(self._execution_request())

        self.assertEqual(result["status"], EXECUTION_COMPLETED)
        self.assertTrue(result["execution_authorized"])
        self.assertFalse(result["mutates_business_state"])
        self.assertTrue(result["command"]["simulation_only"])
        self.assertFalse(result["command"]["mutates_business_state"])
        self.assertEqual(result["command"]["decision_id"], "scheddec_res_001")
        self.assertEqual(result["command"]["approval_id"], "sched_appr_001")
        self.assertEqual(result["simulated_actions"][0]["room_id"], "room_001")
        self.assertEqual(result["simulated_actions"][0]["caregiver_id"], "caregiver_001")
        self.assertFalse(result["simulated_actions"][0]["mutates_business_state"])
        self.assertEqual([event["event_type"] for event in self.bus.events()], ["execution.requested", "execution.completed"])
        self.assertEqual([event["action"] for event in self.audit.events(sort_by_time=False)], ["execution.request", "execution.complete"])

    def test_rejected_approval_blocks_execution(self):
        result = self.execution.execute(
            self._execution_request(
                approval_workflow=self._approval_workflow(
                    current_status=APPROVAL_REJECTED,
                    execution_authorized=False,
                )
            )
        )

        self.assertEqual(result["status"], EXECUTION_FAILED)
        self.assertFalse(result["execution_authorized"])
        self.assertIsNone(result["command"])
        self.assertEqual(
            {reason["code"] for reason in result["failure_reasons"]},
            {"approval_not_approved", "execution_not_authorized"},
        )
        self.assertEqual([event["event_type"] for event in self.bus.events()], ["execution.requested", "execution.failed"])
        self.assertEqual([event["action"] for event in self.audit.events(sort_by_time=False)], ["execution.request", "execution.fail"])

    def test_approved_without_authorization_blocks_execution(self):
        result = self.execution.execute(
            self._execution_request(
                approval_workflow=self._approval_workflow(
                    current_status=APPROVAL_APPROVED,
                    execution_authorized=False,
                )
            )
        )

        self.assertEqual(result["status"], EXECUTION_FAILED)
        self.assertEqual([reason["code"] for reason in result["failure_reasons"]], ["execution_not_authorized"])

    def test_decision_and_approval_mismatch_blocks_execution(self):
        result = self.execution.execute(
            self._execution_request(
                approval_workflow=self._approval_workflow(decision_id="other_decision"),
            )
        )

        self.assertEqual(result["status"], EXECUTION_FAILED)
        self.assertIn("decision_approval_mismatch", {reason["code"] for reason in result["failure_reasons"]})

    def test_execution_command_cannot_be_real_execution_in_p15(self):
        with self.assertRaises(ValueError):
            ExecutionCommand(
                request_id="exec_req_001",
                decision_id="scheddec_res_001",
                approval_id="sched_appr_001",
                command_type="simulate_scheduling_execution",
                simulation_only=False,
            )

    def test_authorized_execution_does_not_mutate_request_payload(self):
        request = self._execution_request()
        before = copy.deepcopy(request.to_dict())

        result = self.execution.execute(request)

        self.assertEqual(request.to_dict(), before)
        self.assertFalse(result["mutates_business_state"])


if __name__ == "__main__":
    unittest.main()
