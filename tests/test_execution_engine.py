import unittest

from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_engine import EventEngine
from oms_v1.execution_engine import ExecutionEngine
from oms_v1.input_hub import OMSInputHub


class ExecutionEngineTests(unittest.TestCase):
    def setUp(self):
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.events = EventEngine()
        self.decisions = DecisionEngine()
        self.execution = ExecutionEngine()

    def _execution_stream(self, text):
        env = self.hub.accept_text(text)
        parsed = self.parser.parse(env)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        return self.execution.build_execution_stream(decision_stream)

    def test_execution_stream_required_fields(self):
        stream = self._execution_stream(
            "客户姓名：李梅，签约无敌套餐，合同编号 HJ-2026-001，全款费用 49800 元；"
            "刘姐收到定金 10000 元，7月2日到账；备注：安排8月1日入住，管家跟进服务。"
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
        stream = self._execution_stream("刘姐收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001")
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


if __name__ == "__main__":
    unittest.main()
