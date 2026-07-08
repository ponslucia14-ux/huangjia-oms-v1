import tempfile
import unittest
import os
from pathlib import Path

from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_engine import EventEngine
from oms_v1.execution_engine import ExecutionEngine
from oms_v1.governance_engine import GovernanceEngine
from oms_v1.input_hub import OMSInputHub
from oms_v1.live_connector import LiveConnector


class FakeApprovalAttempt:
    ok = True
    status = "success"
    approval_type = "finance"
    default_name = "费用报销"
    data = {"instance_code": "instance_001"}

    def to_dict(self):
        return {
            "ok": self.ok,
            "status": self.status,
            "approval_type": self.approval_type,
            "default_name": self.default_name,
            "data": self.data,
            "message": "created",
        }


class FakeApprovalClient:
    def create_default_approval(self, action, governance):
        return FakeApprovalAttempt()


class LiveConnectorTests(unittest.TestCase):
    def setUp(self):
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.events = EventEngine()
        self.decisions = DecisionEngine()
        self.execution = ExecutionEngine()
        self.governance = GovernanceEngine()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["OMS_FEISHU_APPROVAL_MODE"] = "PENDING_ONLY"
        self.live = LiveConnector(self.tmp.name)

    def tearDown(self):
        os.environ.pop("OMS_FEISHU_APPROVAL_MODE", None)
        self.tmp.cleanup()

    def _streams(self, text):
        env = self.hub.accept_text(text)
        parsed = self.parser.parse(env)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        execution_stream = self.execution.build_execution_stream(decision_stream)
        governance_stream = self.governance.build_governance_stream(execution_stream)
        live_stream = self.live.build_live_stream(execution_stream, governance_stream)
        return execution_stream, governance_stream, live_stream

    def test_live_schema_required_fields(self):
        _, _, stream = self._streams(
            "客户姓名：李梅，签约无敌套餐，合同编号 HJ-2026-001，全款费用 49800 元；"
            "备注：安排8月1日入住，管家跟进服务。"
        )

        self.assertTrue(stream["sync_results"])
        self.assertEqual(stream["audit"]["mode"], "Feishu_Pending_Mode")
        self.assertEqual(stream["audit"]["feishu_status"], "PENDING_REVIEW")
        self.assertEqual(stream["audit"]["external_write_mode"], "DISABLED")
        self.assertEqual(stream["audit"]["outbox_mode"], "ACTIVE")
        for result in stream["sync_results"]:
            for field in [
                "sync_target",
                "sync_type",
                "sync_result",
                "status",
                "rollback_supported",
                "audit_log",
            ]:
                self.assertIn(field, result)
            self.assertIn(result["status"], {"success", "failed", "pending"})
            self.assertIn("external_status", result)

    def test_allowed_room_plan_writes_excel_ledger(self):
        _, _, stream = self._streams("备注：安排8月1日入住，管家跟进服务。")
        excel_results = [
            result for result in stream["sync_results"] if result["sync_target"] == "Excel_刘芳羽排房表"
        ]

        self.assertTrue(excel_results)
        self.assertEqual(excel_results[0]["status"], "success")
        csv_path = Path(self.tmp.name) / "excel_sync" / "Excel_刘芳羽排房表.csv"
        self.assertTrue(csv_path.exists())
        self.assertIn("action_id", csv_path.read_text(encoding="utf-8-sig"))

    def test_approval_required_action_goes_to_manual_flow(self):
        _, _, stream = self._streams("刘晶收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001")
        manual_results = [result for result in stream["sync_results"] if result["sync_target"] == "人工审批流"]

        self.assertTrue(manual_results)
        self.assertTrue(all(result["status"] == "pending" for result in manual_results))
        approval_path = Path(self.tmp.name) / "pending_outbox" / "人工审批流.jsonl"
        self.assertTrue(approval_path.exists())

    def test_feishu_targets_are_isolated_to_pending_outbox(self):
        _, _, stream = self._streams("备注：安排8月1日入住，管家跟进服务。")
        feishu_results = [result for result in stream["sync_results"] if result["sync_target"].startswith("飞书")]

        self.assertTrue(feishu_results)
        self.assertTrue(all(result["status"] == "pending" for result in feishu_results))
        self.assertTrue(all(result["external_status"]["real_feishu_api_called"] is False for result in feishu_results))
        self.assertTrue((Path(self.tmp.name) / "pending_outbox").exists())
        self.assertFalse((Path(self.tmp.name) / "feishu_outbox").exists())

    def test_missing_governance_blocks_live_sync(self):
        execution_stream, _, _ = self._streams("备注：安排8月1日入住，管家跟进服务。")
        stream = self.live.build_live_stream(execution_stream, {"governance": []})
        failed = [result for result in stream["sync_results"] if result["status"] == "failed"]

        self.assertTrue(failed)
        self.assertTrue(all(not result["rollback_supported"] for result in failed))

    def test_audit_logs_are_written(self):
        _, _, stream = self._streams("备注：安排8月1日入住，管家跟进服务。")

        for result in stream["sync_results"]:
            self.assertTrue(Path(result["audit_log"]).exists())

    def test_api_driven_approval_success_route(self):
        os.environ["OMS_FEISHU_APPROVAL_MODE"] = "API_DRIVEN"
        live = LiveConnector(self.tmp.name)
        live.approval_client = FakeApprovalClient()
        action = {
            "action_id": "act_001",
            "action_type": "flag_financial_risk",
            "execution_payload": {"reason": "test"},
        }
        governance = {
            "governance_id": "gov_001",
            "approval_required": True,
            "required_roles": ["财务"],
        }

        result = live._write_approval_request("人工审批流", "approval_request", action, governance)

        self.assertEqual(result.status, "success")
        self.assertTrue(result.external_status["real_feishu_api_called"])
        self.assertEqual(result.external_status["route"], "FEISHU_APPROVAL_API")


if __name__ == "__main__":
    unittest.main()
