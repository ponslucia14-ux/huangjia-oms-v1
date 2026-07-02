import unittest

from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_engine import EventEngine
from oms_v1.execution_engine import ExecutionEngine
from oms_v1.governance_engine import GovernanceEngine, ROLE_PERMISSIONS
from oms_v1.input_hub import OMSInputHub


class GovernanceEngineTests(unittest.TestCase):
    def setUp(self):
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.events = EventEngine()
        self.decisions = DecisionEngine()
        self.execution = ExecutionEngine()
        self.governance = GovernanceEngine()

    def _governance_stream(self, text):
        env = self.hub.accept_text(text)
        parsed = self.parser.parse(env)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        execution_stream = self.execution.build_execution_stream(decision_stream)
        return self.governance.build_governance_stream(execution_stream)

    def test_governance_schema_required_fields(self):
        stream = self._governance_stream(
            "客户姓名：李梅，签约无敌套餐，合同编号 HJ-2026-001，全款费用 49800 元；"
            "刘姐收到定金 10000 元，7月2日到账；备注：安排8月1日入住，管家跟进服务。"
        )

        self.assertGreaterEqual(len(stream["governance"]), 3)
        for item in stream["governance"]:
            for field in [
                "action_id",
                "allowed",
                "approval_required",
                "required_roles",
                "risk_level",
                "reason",
                "override_policy",
            ]:
                self.assertIn(field, item)
            self.assertIn(item["risk_level"], {"low", "medium", "high", "critical"})

    def test_low_risk_task_can_be_auto_allowed(self):
        stream = self._governance_stream("备注：安排8月1日入住，管家跟进服务。")
        auto_items = [item for item in stream["governance"] if item["risk_level"] == "low"]

        self.assertTrue(auto_items)
        self.assertTrue(all(item["allowed"] for item in auto_items))
        self.assertTrue(all(not item["approval_required"] for item in auto_items))
        self.assertTrue(all(item["required_roles"] == ["系统"] for item in auto_items))

    def test_reconciliation_requires_finance_approval(self):
        stream = self._governance_stream("刘姐收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001")
        reconciliation = [
            item
            for item in stream["governance"]
            if item["action_type"] == "generate_reconciliation_task"
        ][0]

        self.assertFalse(reconciliation["allowed"])
        self.assertTrue(reconciliation["approval_required"])
        self.assertEqual(reconciliation["risk_level"], "medium")
        self.assertIn("刘姐", reconciliation["required_roles"])

    def test_high_risk_room_action_requires_boss(self):
        stream = self._governance_stream("备注：客户已生，8月1日入住，但房间不够，可能需要调房。")
        high_items = [item for item in stream["governance"] if item["risk_level"] == "high"]

        self.assertTrue(high_items)
        self.assertTrue(all(not item["allowed"] for item in high_items))
        self.assertTrue(any("BOSS" in item["required_roles"] for item in high_items))

    def test_requires_execution_stream(self):
        with self.assertRaises(ValueError):
            self.governance.build_governance_stream({"decisions": []})

    def test_role_permissions_include_final_override(self):
        self.assertIn("all", ROLE_PERMISSIONS["BOSS"]["override"])
        self.assertEqual(ROLE_PERMISSIONS["系统"]["approve"], [])
        self.assertEqual(ROLE_PERMISSIONS["系统"]["override"], [])


if __name__ == "__main__":
    unittest.main()
