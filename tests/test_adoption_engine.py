import tempfile
import unittest
from pathlib import Path

from oms_v1.adoption_engine import AdoptionEngine
from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_engine import EventEngine
from oms_v1.execution_engine import ExecutionEngine
from oms_v1.governance_engine import GovernanceEngine
from oms_v1.input_hub import OMSInputHub
from oms_v1.live_connector import LiveConnector
from oms_v1.operational_core import OMSOperationalCore


class AdoptionEngineTests(unittest.TestCase):
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
        self.adoption = AdoptionEngine(Path(self.tmp.name) / "adoption")

    def tearDown(self):
        self.tmp.cleanup()

    def _adoption_stream(self, text, bypass=None, overrides=None):
        env = self.hub.accept_text(text)
        parsed = self.parser.parse(env)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        execution_stream = self.execution.build_execution_stream(decision_stream)
        governance_stream = self.governance.build_governance_stream(execution_stream)
        live_stream = self.live.build_live_stream(execution_stream, governance_stream)
        operational_stream = self.operational.build_operating_stream(execution_stream, governance_stream, live_stream)
        return self.adoption.build_adoption_stream(
            operational_stream,
            live_stream,
            governance_stream,
            bypass_events=bypass or [],
            manual_overrides=overrides or [],
        )

    def test_adoption_schema_required_fields_for_roles(self):
        stream = self._adoption_stream(
            "客户姓名：李梅，签约无敌套餐，合同编号 HJ-2026-001，全款费用 49800 元；"
            "刘晶收到定金 10000 元，7月2日到账；备注：安排8月1日入住，管家跟进服务。"
        )
        roles = {item["role"] for item in stream["adoption"]}

        self.assertEqual(roles, {"刘芳羽", "刘晶", "销售", "尚丽娜"})
        for item in stream["adoption"]:
            for field in [
                "role",
                "adoption_status",
                "blockers",
                "migration_tasks",
                "recommended_actions",
                "risk_level",
            ]:
                self.assertIn(field, item)
            self.assertIn(item["adoption_status"], {"not_started", "partial", "active", "full"})

    def test_bypass_is_logged_and_reduces_adoption(self):
        stream = self._adoption_stream(
            "备注：安排8月1日入住，管家跟进服务。",
            bypass=[{"role": "刘芳羽", "source": "Excel", "reason": "临时用旧排房表"}],
        )
        liufangyu = [item for item in stream["adoption"] if item["role"] == "刘芳羽"][0]

        self.assertEqual(liufangyu["adoption_status"], "partial")
        self.assertEqual(liufangyu["risk_level"], "high")
        self.assertTrue(liufangyu["bypass_log"])
        self.assertTrue(any("绕过" in blocker for blocker in liufangyu["blockers"]))

    def test_manual_override_is_logged(self):
        stream = self._adoption_stream(
            "刘晶收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001",
            overrides=[{"role": "刘晶", "operator": "刘晶", "reason": "线下确认到账"}],
        )
        liujing = [item for item in stream["adoption"] if item["role"] == "刘晶"][0]

        self.assertTrue(liujing["manual_override_log"])

    def test_not_started_role_has_high_risk(self):
        stream = self._adoption_stream("刘晶收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001")
        shanglina = [item for item in stream["adoption"] if item["role"] == "尚丽娜"][0]

        self.assertEqual(shanglina["adoption_status"], "not_started")
        self.assertEqual(shanglina["risk_level"], "high")

    def test_adoption_status_is_persisted(self):
        stream = self._adoption_stream("备注：安排8月1日入住，管家跟进服务。")
        path = Path(stream["audit"]["adoption_root"]) / "adoption_status.jsonl"

        self.assertTrue(path.exists())
        self.assertIn("adoption_status", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
