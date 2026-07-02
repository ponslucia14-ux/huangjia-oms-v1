import tempfile
import unittest
from pathlib import Path

from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_engine import EventEngine
from oms_v1.execution_engine import ExecutionEngine
from oms_v1.governance_engine import GovernanceEngine
from oms_v1.input_hub import OMSInputHub
from oms_v1.live_connector import LiveConnector
from oms_v1.operational_core import OMSOperationalCore


class OperationalCoreTests(unittest.TestCase):
    def setUp(self):
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.events = EventEngine()
        self.decisions = DecisionEngine()
        self.execution = ExecutionEngine()
        self.governance = GovernanceEngine()
        self.tmp = tempfile.TemporaryDirectory()
        self.live = LiveConnector(Path(self.tmp.name) / "live")
        self.operational = OMSOperationalCore(Path(self.tmp.name) / "operational")

    def tearDown(self):
        self.tmp.cleanup()

    def _operating_stream(self, text):
        env = self.hub.accept_text(text)
        parsed = self.parser.parse(env)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        execution_stream = self.execution.build_execution_stream(decision_stream)
        governance_stream = self.governance.build_governance_stream(execution_stream)
        live_stream = self.live.build_live_stream(execution_stream, governance_stream)
        return self.operational.build_operating_stream(execution_stream, governance_stream, live_stream)

    def test_operating_mode_default_entry_policy(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")

        self.assertEqual(stream["operating_mode"], "daily_operating_mode")
        self.assertEqual(stream["default_entry_policy"]["default_entry"], "OMS")
        self.assertEqual(stream["default_entry_policy"]["excel_role"], "只读历史和迁移来源")
        self.assertEqual(stream["default_entry_policy"]["wechat_role"], "输入来源和人工确认回写来源")

    def test_room_and_service_work_items_are_routed_to_roles(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")
        roles = {item["role"] for item in stream["work_items"]}

        self.assertIn("六月", roles)
        self.assertIn("娜娜", roles)
        self.assertIn("BOSS", roles)
        self.assertIn("六月", stream["role_views"])

    def test_finance_confirmation_waits_for_liujie(self):
        stream = self._operating_stream("刘姐收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001")
        finance_items = [item for item in stream["work_items"] if item["role"] == "刘姐"]

        self.assertTrue(finance_items)
        self.assertTrue(any(item["confirmation_required"] for item in finance_items))
        self.assertTrue(any(item["status"] == "waiting_confirmation" for item in finance_items))

    def test_legacy_system_policy_is_downgraded(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")

        for item in stream["work_items"]:
            self.assertEqual(item["legacy_policy"]["Excel"], "read_only_history")
            self.assertEqual(item["legacy_policy"]["微信"], "input_source_only")
            self.assertEqual(item["primary_entry"], "OMS")

    def test_management_cutover_is_explicit_not_faked(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")
        criteria = stream["operational_readiness"]["completion_criteria"]

        self.assertEqual(criteria["六月不再用Excel排房"], "requires_management_cutover")
        self.assertEqual(criteria["销售不再群里报数据"], "requires_management_cutover")

    def test_operational_work_items_are_persisted(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")
        path = Path(stream["audit"]["operating_root"]) / "daily_work_items.jsonl"

        self.assertTrue(path.exists())
        self.assertIn("primary_entry", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
