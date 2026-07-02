import unittest

from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_engine import EventEngine
from oms_v1.input_hub import OMSInputHub


class DecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.events = EventEngine()
        self.decisions = DecisionEngine()

    def _decision_stream(self, text):
        env = self.hub.accept_text(text)
        parsed = self.parser.parse(env)
        event_stream = self.events.build_event_stream(parsed)
        return self.decisions.build_decision_stream(event_stream)

    def test_multi_domain_recommendations_are_created(self):
        stream = self._decision_stream(
            "客户姓名：李梅，签约无敌套餐，合同编号 HJ-2026-001，全款费用 49800 元；"
            "刘姐收到定金 10000 元，7月2日到账；备注：安排8月1日入住，管家跟进服务。"
        )
        decision_types = {decision["decision_type"] for decision in stream["decisions"]}

        self.assertIn("sales_to_operations", decision_types)
        self.assertIn("finance_reconciliation", decision_types)
        self.assertIn("room_assignment", decision_types)
        self.assertIn("service_preparation", decision_types)
        self.assertNotIn("service_coordination", decision_types)
        self.assertFalse(stream["audit"]["direct_execution_allowed"])
        self.assertTrue(stream["audit"]["human_override_required"])

    def test_decision_schema_required_fields_and_override(self):
        stream = self._decision_stream("维维报销厨房采购鸡蛋 360 元，美团，6.29 单据已发")
        decision = stream["decisions"][0]

        for field in ["event_id", "decision_type", "recommended_action", "priority", "risk_level", "reason"]:
            self.assertIn(field, decision)
        self.assertTrue(decision["human_override_allowed"])
        self.assertGreater(len(decision["override_roles"]), 0)

    def test_room_risk_keywords_raise_high_risk(self):
        stream = self._decision_stream("备注：客户已生，8月1日入住，但房间不够，可能需要调房。")
        high_risk = [decision for decision in stream["decisions"] if decision["risk_level"] == "high"]
        self.assertTrue(high_risk)
        self.assertTrue(any(decision["decision_type"] in {"room_risk", "room_scheduling"} for decision in high_risk))


if __name__ == "__main__":
    unittest.main()
