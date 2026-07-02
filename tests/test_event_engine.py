import unittest

from oms_v1.data_parser import OMSDataParser
from oms_v1.event_engine import EventEngine
from oms_v1.input_hub import OMSInputHub


class EventEngineTests(unittest.TestCase):
    def setUp(self):
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.engine = EventEngine()

    def test_one_input_can_split_to_multiple_events(self):
        env = self.hub.accept_text(
            "客户姓名：李梅，签约无敌套餐，合同编号 HJ-2026-001，全款费用 49800 元；"
            "刘姐收到定金 10000 元，7月2日到账；备注：安排8月1日入住，管家跟进服务。"
        )
        parsed = self.parser.parse(env)
        stream = self.engine.build_event_stream(parsed)
        event_types = {event["event_type"] for event in stream["events"]}

        self.assertTrue(stream["audit"]["multi_event"])
        self.assertIn("sales_event", event_types)
        self.assertIn("financial_event", event_types)
        self.assertIn("room_status_event", event_types)
        self.assertIn("service_event", event_types)
        self.assertIn("finance_module", stream["dispatch"])
        self.assertIn("room_status_module", stream["dispatch"])
        self.assertIn("service_module", stream["dispatch"])
        financial_event = next(event for event in stream["events"] if event["event_type"] == "financial_event")
        self.assertEqual(financial_event["payload"]["amount"]["amount"], 10000)
        self.assertEqual(financial_event["payload"]["payment_type"], "定金")

    def test_event_schema_has_required_fields(self):
        env = self.hub.accept_text("维维报销厨房采购鸡蛋 360 元，美团，6.29 单据已发")
        parsed = self.parser.parse(env)
        stream = self.engine.build_event_stream(parsed)
        event = stream["events"][0]

        for field in ["event_type", "source", "entity", "action", "payload", "timestamp"]:
            self.assertIn(field, event)
        self.assertEqual(event["event_type"], "financial_event")
        self.assertEqual(event["action"], "reimbursement_submitted")


if __name__ == "__main__":
    unittest.main()
