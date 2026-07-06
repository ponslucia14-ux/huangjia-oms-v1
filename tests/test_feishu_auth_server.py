import unittest
import json
import os
import tempfile
import threading
from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from oms_v1.feishu_auth_server import FeishuAuthHandler, load_runtime_env


class FakeHomeUI:
    def build_home_from_saved_state(self, *, user_id=None):
        return {
            "home_type": "user_centric_operating_interface",
            "entry": "personal_workspace",
            "current_user": {"user_id": user_id, "workspace_key": "boss", "name": "主理办（你）"},
            "business_dashboard": {
                "title": "today",
                "metrics": {"resident_count": 1, "today_collection": 100},
                "source_evidence_available_data": {
                    "policy": "source_evidence_available_data",
                    "resident_data": [{"id": str(index)} for index in range(40)],
                },
            },
            "sections": {
                "my_todos": {
                    "title": "我的待办",
                    "count": 60,
                    "items": [{"id": str(index)} for index in range(60)],
                }
            },
        }


class FakeHistoricalView:
    def build_history_view(self, **kwargs):
        return {
            "schema_version": "oms.v1.historical_data_view",
            "mode": "historical_data_view",
            "source_of_truth": "OMS_TRUTH_SOURCE",
            "flow": "Excel/data_import -> business_event -> workflow_distribution -> hr_execution -> completion_log",
            "filters": kwargs,
            "counts": {"matched_timeline_items": 90},
            "timeline": [{"timeline_id": str(index), "trace_chain": {"business_event_id": str(index)}} for index in range(90)],
            "multidimensional_history": {
                "room_history": {"items": [{"id": str(index)} for index in range(90)]},
            },
            "traceability": {"total": 90},
        }


class FakeExecutionClosure:
    def execute_action(self, payload):
        return {
            "schema_version": "oms.v1.business_execution_closure",
            "status": "completed",
            "closure_status": "closed",
            "business_command": {"entity": "task"},
            "execution_result": {"execution_result_id": "exec_result_test"},
            "state_update": {"state_update_id": "state_test"},
            "trace_chain": {
                "execution_result_id": "exec_result_test",
                "state_update_id": "state_test",
            },
            "ui_reflect": {"message": "done"},
        }


class FeishuAuthServerTests(unittest.TestCase):
    def test_cors_allows_github_pages_with_credentials(self):
        self.assertIn("https://ponslucia14-ux.github.io", FeishuAuthHandler.allowed_origins)

    def test_runtime_env_does_not_load_user_identity_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feishu.env"
            path.write_text("FEISHU_USER_ID_BOSS=a2c82cb4\nFEISHU_APP_ID=cli_test\n", encoding="utf-8")
            os.environ.pop("FEISHU_USER_ID_BOSS", None)
            os.environ.pop("FEISHU_APP_ID", None)
            try:
                load_runtime_env(path)
                self.assertNotIn("FEISHU_USER_ID_BOSS", os.environ)
                self.assertEqual(os.environ["FEISHU_APP_ID"], "cli_test")
            finally:
                os.environ.pop("FEISHU_USER_ID_BOSS", None)
                os.environ.pop("FEISHU_APP_ID", None)

    def test_runtime_home_endpoint_returns_personal_workspace(self):
        original_home_ui = FeishuAuthHandler.home_ui
        FeishuAuthHandler.home_ui = FakeHomeUI()
        server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request(
                "POST",
                "/api/oms/home",
                body=json.dumps({"user_id": "a2c82cb4"}),
                headers={"Content-Type": "application/json", "Origin": "https://ponslucia14-ux.github.io"},
            )
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["entity"], "task")
            self.assertEqual(payload["id"], "oms.home")
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["source"], "OMS_TRUTH_SOURCE")
            self.assertEqual(payload["contract_version"], "oms.contract.v1.0")
            data = payload["payload"]
            self.assertEqual(data["entry"], "personal_workspace")
            self.assertEqual(data["home_type"], "user_centric_operating_interface")
            self.assertEqual(data["current_user"]["user_id"], "a2c82cb4")
            self.assertEqual(data["runtime_source"]["mode"], "single_source_of_truth")
            self.assertEqual(data["runtime_source"]["type"], "OMS_TRUTH_SOURCE")
            self.assertIn("D:\\OMS_V1\\OMS_TRUTH_SOURCE", data["runtime_source"]["truth_root"])
            self.assertIn("D:\\OMS_V1\\live_runtime", data["runtime_source"]["live_root"])
            self.assertEqual(data["runtime_source"]["cloud_role"], "request_forwarding_only")
            self.assertFalse(data["runtime_source"]["remote_data_generation_allowed"])
            self.assertFalse(data["runtime_source"]["remote_mock_allowed"])
            todos = data["sections"]["my_todos"]
            self.assertEqual(todos["total_count"], 60)
            self.assertEqual(todos["visible_count"], 50)
            self.assertEqual(len(todos["items"]), 50)
            self.assertNotIn("timeline", data)
            source_data = data["business_dashboard"]["source_evidence_available_data"]
            self.assertEqual(source_data["resident_data_visible_count"], 25)
        finally:
            server.shutdown()
            server.server_close()
            FeishuAuthHandler.home_ui = original_home_ui

    def test_runtime_history_endpoint_returns_compacted_timeline(self):
        original_history = FeishuAuthHandler.historical_view
        FeishuAuthHandler.historical_view = FakeHistoricalView()
        server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request(
                "GET",
                "/api/oms/history?limit=90&workspace_key=boss",
                headers={"Origin": "https://ponslucia14-ux.github.io"},
            )
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["entity"], "task")
            self.assertEqual(payload["id"], "oms.history")
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["source"], "OMS_TRUTH_SOURCE")
            data = payload["payload"]
            self.assertEqual(data["schema_version"], "oms.v1.historical_data_view")
            self.assertEqual(data["timeline_total_count"], 90)
            self.assertEqual(data["timeline_visible_count"], 80)
            self.assertEqual(len(data["timeline"]), 80)
            self.assertEqual(data["runtime_source"]["type"], "OMS_TRUTH_SOURCE")
            self.assertEqual(data["multidimensional_history"]["room_history"]["items_visible_count"], 80)
        finally:
            server.shutdown()
            server.server_close()
            FeishuAuthHandler.historical_view = original_history

    def test_history_alias_is_on_demand_query_only(self):
        original_history = FeishuAuthHandler.historical_view
        FeishuAuthHandler.historical_view = FakeHistoricalView()
        server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request(
                "POST",
                "/history",
                body=json.dumps({"limit": 90}),
                headers={"Content-Type": "application/json", "Origin": "https://ponslucia14-ux.github.io"},
            )
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["entity"], "task")
            self.assertEqual(payload["id"], "oms.history")
            self.assertEqual(payload["status"], "ready")
            data = payload["payload"]
            self.assertEqual(data["schema_version"], "oms.v1.historical_data_view")
            self.assertEqual(data["timeline_total_count"], 90)
            self.assertEqual(data["timeline_visible_count"], 80)
        finally:
            server.shutdown()
            server.server_close()
            FeishuAuthHandler.historical_view = original_history

    def test_runtime_execute_endpoint_returns_execution_closure(self):
        original_closure = FeishuAuthHandler.execution_closure
        FeishuAuthHandler.execution_closure = FakeExecutionClosure()
        server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request(
                "POST",
                "/api/oms/execute",
                body=json.dumps({"user_id": "a2c82cb4", "route": "room", "action": "open-room", "target": "201"}),
                headers={"Content-Type": "application/json", "Origin": "https://ponslucia14-ux.github.io"},
            )
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["entity"], "task")
            self.assertEqual(payload["id"], "oms.execute")
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["source"], "OMS_TRUTH_SOURCE")
            data = payload["payload"]
            self.assertEqual(data["closure_status"], "closed")
            self.assertEqual(data["trace_chain"]["execution_result_id"], "exec_result_test")
            self.assertEqual(data["trace_chain"]["state_update_id"], "state_test")
        finally:
            server.shutdown()
            server.server_close()
            FeishuAuthHandler.execution_closure = original_closure

    def test_runtime_home_payload_compacts_source_evidence_lists(self):
        handler = object.__new__(FeishuAuthHandler)
        home = {
            "sections": {},
            "business_dashboard": {
                "source_evidence_available_data": {
                    "policy": "source_evidence_available_data",
                    "resident_data": [{"id": str(index)} for index in range(40)],
                },
                "source_evidence_verified_data": {
                    "policy": "source_evidence_available_data",
                    "financial_events": [{"id": str(index)} for index in range(31)],
                },
            },
        }

        compact = handler._compact_home_payload(home)

        source_data = compact["business_dashboard"]["source_evidence_available_data"]
        verified_data = compact["business_dashboard"]["source_evidence_verified_data"]
        self.assertEqual(len(source_data["resident_data"]), 25)
        self.assertEqual(source_data["resident_data_visible_count"], 25)
        self.assertEqual(source_data["resident_data_total_count"], 40)
        self.assertEqual(len(verified_data["financial_events"]), 25)
        self.assertEqual(verified_data["financial_events_total_count"], 31)
        self.assertEqual(source_data["payload_policy"], "compacted_for_feishu_h5_runtime")


if __name__ == "__main__":
    unittest.main()
