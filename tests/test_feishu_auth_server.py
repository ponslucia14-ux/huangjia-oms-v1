import unittest
import json
import os
import tempfile
import threading
from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import oms_v1.feishu_auth_server as server_module
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
                        "counts": {"resident_data": 40, "room_status_data": 0},
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
            "execution_result": {"execution_result_id": "exec_result_test", "explainability_status": "explained"},
            "state_update": {"state_update_id": "state_test"},
            "decision_chain": {
                "decision_chain_id": "decision_test",
                "decision_summary": "test decision",
                "why": ["test reason"],
                "retrigger_available": True,
            },
            "retrigger_closure": {
                "status": "not_requested",
                "message": "not requested",
            },
            "business_state_writeback": {
                "status": "applied",
                "truth_source_updated": True,
                "business_state_id": "bst_test",
            },
            "lifecycle_closure": {
                "domain": "room",
                "current_stage": "in_house",
                "next_action": "advance_room_to_cleaning",
                "closure_detection": {"status": "open", "completed": False},
            },
            "trace_chain": {
                "execution_result_id": "exec_result_test",
                "state_update_id": "state_test",
            },
            "ui_reflect": {"message": "done"},
        }


class FeishuAuthServerTests(unittest.TestCase):
    def test_cors_preflight_allows_authorization_header(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request(
                "OPTIONS",
                "/api/oms/home",
                headers={
                    "Origin": "https://ponslucia14-ux.github.io",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            )
            response = conn.getresponse()
            response.read()
            self.assertEqual(response.status, 200)
            allowed = response.getheader("Access-Control-Allow-Headers") or ""
            self.assertIn("Authorization", allowed)
        finally:
            server.shutdown()
            server.server_close()

    def test_cors_allows_github_pages_with_credentials(self):
        self.assertIn("https://ponslucia14-ux.github.io", FeishuAuthHandler.allowed_origins)

    def test_runtime_env_does_not_load_user_identity_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feishu.env"
            path.write_text("FEISHU_USER_ID_SHILEI=a2c82cb4\nFEISHU_APP_ID=cli_test\n", encoding="utf-8")
            os.environ.pop("FEISHU_USER_ID_SHILEI", None)
            os.environ.pop("FEISHU_APP_ID", None)
            try:
                load_runtime_env(path)
                self.assertNotIn("FEISHU_USER_ID_SHILEI", os.environ)
                self.assertEqual(os.environ["FEISHU_APP_ID"], "cli_test")
            finally:
                os.environ.pop("FEISHU_USER_ID_SHILEI", None)
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
            repo_root = str(Path(__file__).resolve().parents[1])
            self.assertIn(str(Path(repo_root) / "OMS_TRUTH_SOURCE"), data["runtime_source"]["truth_root"])
            self.assertIn(str(Path(repo_root) / "live_runtime"), data["runtime_source"]["live_root"])
            self.assertEqual(data["runtime_source"]["cloud_role"], "request_forwarding_only")
            self.assertFalse(data["runtime_source"]["remote_data_generation_allowed"])
            self.assertFalse(data["runtime_source"]["remote_mock_allowed"])
            todos = data["sections"]["my_todos"]
            self.assertEqual(todos["total_count"], 60)
            self.assertEqual(todos["items"], [])
            self.assertIn("items_endpoint", todos)
            self.assertNotIn("timeline", data)
            self.assertEqual(data["payload_policy"], "home_summary_only")
            self.assertIn({"key": "sales", "title": "销售中心", "endpoint": "/api/oms/sales"}, data["center_entries"])
            source_data = data["business_dashboard"]["source_evidence_available_data"]
            self.assertEqual(source_data["resident_data_total_count"], 40)
            self.assertNotIn("resident_data", source_data)
        finally:
            server.shutdown()
            server.server_close()
            FeishuAuthHandler.home_ui = original_home_ui

    def test_static_root_serves_local_oms_entry(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request("GET", "/")
            response = conn.getresponse()
            body = response.read().decode("utf-8", errors="replace")
            self.assertEqual(response.status, 200)
            self.assertIn("text/html", response.getheader("Content-Type"))
            self.assertIn("omsConfigScript", body)
            self.assertIn("omsAppScript", body)
        finally:
            server.shutdown()
            server.server_close()

    def test_local_owner_access_returns_identity_and_writes_audit(self):
        original_home_ui = FeishuAuthHandler.home_ui
        original_audit_root = FeishuAuthHandler.audit_root
        original_owner_user_id = FeishuAuthHandler.local_owner_user_id
        original_enabled = FeishuAuthHandler.local_owner_access_enabled
        with tempfile.TemporaryDirectory() as tmp:
            FeishuAuthHandler.home_ui = FakeHomeUI()
            FeishuAuthHandler.audit_root = Path(tmp) / "audit_center"
            FeishuAuthHandler.local_owner_user_id = "a2c82cb4"
            FeishuAuthHandler.local_owner_access_enabled = True
            server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                conn.request(
                    "POST",
                    "/api/oms/local-owner-access",
                    body=json.dumps({"reason": "test_recovery"}),
                    headers={"Content-Type": "application/json", "Host": f"127.0.0.1:{server.server_port}"},
                )
                response = conn.getresponse()
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(payload["id"], "oms.local_owner_access")
                self.assertEqual(payload["status"], "ready")
                self.assertEqual(payload["source"], "OMS_TRUTH_SOURCE")
                self.assertEqual(payload["payload"]["user_id"], "a2c82cb4")
                self.assertEqual(payload["payload"]["workspace_key"], "boss")
                self.assertEqual(payload["payload"]["source"], "local_owner_access")
                self.assertTrue(payload["payload"]["audit_id"])

                audit_path = FeishuAuthHandler.audit_root / "audit_events.jsonl"
                rows = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
                actions = [row["action"] for row in rows]
                self.assertIn("login.recovery.request", actions)
                self.assertIn("login.recovery.success", actions)
            finally:
                server.shutdown()
                server.server_close()
                FeishuAuthHandler.home_ui = original_home_ui
                FeishuAuthHandler.audit_root = original_audit_root
                FeishuAuthHandler.local_owner_user_id = original_owner_user_id
                FeishuAuthHandler.local_owner_access_enabled = original_enabled

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

    def test_runtime_production_endpoint_returns_full_dataset(self):
        original_truth_root = server_module.LOCAL_TRUTH_SOURCE_ROOT
        original_live_root = server_module.LOCAL_LIVE_RUNTIME_ROOT
        original_operating_root = server_module.LOCAL_OPERATING_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            truth_root = root / "OMS_TRUTH_SOURCE"
            truth_root.mkdir(parents=True)
            evidence = {
                "source_file": str(root / "sales.xlsx"),
                "source_file_name": "sales.xlsx",
                "source_sheet": "sales",
                "row_number": 2,
                "record_id": "sales_row_2",
                "trace_id": "sales.xlsx::sales::R2::sales_row_2",
            }
            (truth_root / "sales.json").write_text(
                json.dumps(
                    {
                        "schema_version": "oms.v1.truth_source.sales",
                        "mode": "single_source_of_truth",
                        "domain": "sales",
                        "updated_at": "2026-07-10T12:00:00+08:00",
                        "source_file_name": "sales.xlsx",
                        "entities": [
                            {
                                "entity_id": "sales_1",
                                "contract_id": "HJ-001",
                                "customer_name": "Customer A",
                                "sign_date": "2026-07-01",
                                "package_name": "Package A",
                                "amount": 30000,
                                "actual_received_amount": 10000,
                                "unpaid_balance_amount": 20000,
                                "salesperson_name": "Sales A",
                                "source_record_id": "sales_row_2",
                                "source_evidence": evidence,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            for name in ("finance", "room", "stay", "customer", "contract"):
                (truth_root / f"{name}.json").write_text(
                    json.dumps({"schema_version": f"oms.v1.truth_source.{name}", "mode": "single_source_of_truth", "domain": name}, ensure_ascii=False),
                    encoding="utf-8",
                )
            server_module.LOCAL_TRUTH_SOURCE_ROOT = truth_root
            server_module.LOCAL_LIVE_RUNTIME_ROOT = root / "live_runtime"
            server_module.LOCAL_OPERATING_ROOT = root / "live_runtime" / "operational_core"
            server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                conn.request("GET", "/api/oms/production/sales", headers={"Origin": "https://ponslucia14-ux.github.io"})
                response = conn.getresponse()
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(payload["id"], "oms.production.sales")
                self.assertEqual(payload["status"], "ready")
                data = payload["payload"]
                self.assertEqual(data["dataset"], "sales")
                self.assertEqual(data["record_count"], 1)
                self.assertEqual(data["metrics"]["contract_amount_total"], 30000)
                self.assertEqual(data["records"][0]["source_line"], "sales.xlsx / sales / 第2行")
                self.assertFalse(data["data_policy"]["mock_allowed"])
            finally:
                server.shutdown()
                server.server_close()
                server_module.LOCAL_TRUTH_SOURCE_ROOT = original_truth_root
                server_module.LOCAL_LIVE_RUNTIME_ROOT = original_live_root
                server_module.LOCAL_OPERATING_ROOT = original_operating_root

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
            self.assertEqual(data["decision_chain"]["decision_summary"], "test decision")
            self.assertEqual(data["retrigger_closure"]["status"], "not_requested")
            self.assertEqual(data["business_state_writeback"]["status"], "applied")
            self.assertEqual(data["lifecycle_closure"]["closure_detection"]["status"], "open")
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
                    "counts": {"resident_data": 40, "financial_events": 31},
                    "resident_data": [{"id": str(index)} for index in range(40)],
                },
                "source_evidence_verified_data": {
                    "policy": "source_evidence_available_data",
                    "financial_events": [{"id": str(index)} for index in range(31)],
                },
                "lifecycle": {
                    "open_lifecycles": [{"id": str(index)} for index in range(33)],
                    "action_queue": [{"id": str(index)} for index in range(34)],
                },
            },
        }

        compact = handler._compact_home_payload(home)

        source_data = compact["business_dashboard"]["source_evidence_available_data"]
        self.assertEqual(source_data["resident_data_total_count"], 40)
        self.assertNotIn("resident_data", source_data)
        self.assertNotIn("source_evidence_verified_data", compact["business_dashboard"])
        self.assertEqual(compact["payload_policy"], "home_summary_only")
        self.assertEqual(compact["business_dashboard"]["risk_summary"]["risk_alerts"], 0)

    def test_paginated_records_strip_trace_until_detail_request(self):
        handler = object.__new__(FeishuAuthHandler)
        records = [
            {
                "record_id": f"room_{index}",
                "room_id": str(index),
                "status": "AVAILABLE",
                "title": f"房间 {index}",
                "source_evidence": {"source_file": "room.xlsx", "row_number": index, "record_id": f"room_{index}"},
                "trace_chain": {"trace_id": f"trace_{index}"},
            }
            for index in range(1, 4)
        ]

        page = handler._paginate_records("rooms", records, {"page": 1, "page_size": 2})
        self.assertEqual(page["total"], 3)
        self.assertEqual(page["returned"], 2)
        self.assertTrue(page["records"][0]["trace_available"])
        self.assertNotIn("source_evidence", page["records"][0])
        detail = handler._paginate_records("rooms", records, {"record_id": "room_2"})
        self.assertEqual(detail["total"], 1)
        self.assertIn("source_evidence", detail["records"][0])


if __name__ == "__main__":
    unittest.main()
