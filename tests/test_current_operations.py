import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from oms_v1.current_operations import CurrentOperationsService
from oms_v1.auth_session import AuthSessionSigner
from oms_v1.feishu_auth_server import FeishuAuthHandler


class FakeMasterData:
    def __init__(self):
        self.rows = [
            SimpleNamespace(emp="EMP003", name="张敬东", role_code="ROLE_ACCOUNTANT", user_id="uid003", open_id="", union_id=""),
            SimpleNamespace(emp="EMP004", name="刘晶", role_code="ROLE_CASHIER", user_id="uid004", open_id="", union_id=""),
            SimpleNamespace(emp="EMP008", name="刘芳羽", role_code="ROLE_STORE_MANAGER", user_id="uid008", open_id="", union_id=""),
            SimpleNamespace(emp="EMP009", name="尚丽娜", role_code="ROLE_BUTLER", user_id="uid009", open_id="", union_id=""),
        ]

    def employees(self):
        return list(self.rows)


class CurrentOperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.service = CurrentOperationsService(self.root, master_data=FakeMasterData())

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def claims(emp):
        workspaces = {"003": "zhangjingdong", "004": "liujie", "008": "june", "009": "nana"}
        suffix = emp[-3:]
        return {"user_id": f"uid{suffix}", "workspace_key": workspaces[suffix]}

    def test_finance_requires_cashier_record_and_accountant_review(self):
        pending = self.service.record_finance_current(
            self.claims("EMP004"),
            {
                "effective_date": "2026-07-11",
                "income": "1000",
                "expense": "250.25",
                "receivable": "300",
                "payable": "120",
                "cash_balance": "929.75",
                "reason": "Cutover期初财务日结",
            },
        )
        self.assertEqual(pending["status"], "PENDING_REVIEW")
        self.assertIsNone(self.service.current_summary()["finance"])

        approved = self.service.review_finance_current(
            self.claims("EMP003"),
            {"record_id": pending["record_id"], "approved": True, "reason": "会计复核通过"},
        )
        self.assertEqual(approved["status"], "CURRENT")
        self.assertEqual(self.service.current_summary()["finance"]["cash_balance"], 929.75)

    def test_finance_rejects_wrong_employee(self):
        with self.assertRaises(PermissionError):
            self.service.record_finance_current(
                self.claims("EMP008"),
                {
                    "effective_date": "2026-07-11",
                    "income": 0,
                    "expense": 0,
                    "receivable": 0,
                    "payable": 0,
                    "cash_balance": 0,
                    "reason": "unauthorized",
                },
            )

    def test_room_requires_exactly_42_unique_rooms(self):
        rooms = [
            {"room_number": f"R{index:03d}", "status": "OCCUPIED" if index == 1 else "AVAILABLE", "customer_name": "客户甲" if index == 1 else ""}
            for index in range(1, 43)
        ]
        current = self.service.publish_room_current(
            self.claims("EMP008"),
            {"effective_time": "2026-07-11T18:00:00+08:00", "rooms": rooms, "reason": "逐房确认"},
        )
        self.assertEqual(current["room_count"], 42)
        self.assertEqual(self.service.current_summary()["room"]["status"], "CURRENT")

        with self.assertRaisesRegex(ValueError, "exactly 42"):
            self.service.publish_room_current(
                self.claims("EMP008"),
                {"effective_time": "2026-07-11T18:01:00+08:00", "rooms": rooms[:41], "reason": "缺房间"},
            )

    def test_actual_stay_requires_room_current_and_butler_verification(self):
        rooms = [
            {"room_number": f"R{index:03d}", "status": "OCCUPIED" if index == 1 else "AVAILABLE", "customer_name": "客户甲" if index == 1 else ""}
            for index in range(1, 43)
        ]
        self.service.publish_room_current(
            self.claims("EMP008"),
            {"effective_time": "2026-07-11T18:00:00+08:00", "rooms": rooms, "reason": "逐房确认"},
        )
        current = self.service.publish_actual_stay(
            self.claims("EMP008"),
            {
                "effective_time": "2026-07-11T18:05:00+08:00",
                "reason": "确认实际入住",
                "stays": [
                    {"stay_id": "STAY-001", "customer_name": "客户甲", "room_number": "R001", "checkin_time": "2026-07-11T10:00:00+08:00", "status": "IN_STAY"}
                ],
            },
        )
        self.assertEqual(current["resident_count"], 1)
        self.assertEqual(current["service_verification_status"], "PENDING")
        verified = self.service.verify_actual_stay(
            self.claims("EMP009"),
            {"record_id": current["record_id"], "reason": "管家核对服务状态"},
        )
        self.assertEqual(verified["service_verification_status"], "VERIFIED")

    def test_emp008_check_in_and_check_out_update_stay_and_room_together(self):
        rooms = [{"room_number": f"R{index:03d}", "status": "AVAILABLE"} for index in range(1, 43)]
        self.service.publish_room_current(
            self.claims("EMP008"),
            {"effective_time": "2026-07-12T08:00:00+08:00", "rooms": rooms, "reason": "首次确认42间房"},
        )

        checked_in = self.service.check_in(
            self.claims("EMP008"),
            {
                "stay_id": "STAY-008",
                "customer_name": "客户乙",
                "room_number": "R008",
                "checkin_time": "2026-07-12T09:00:00+08:00",
                "reason": "客户实际到馆",
            },
        )
        self.assertEqual(checked_in["action"], "CHECK_IN")
        summary = self.service.current_summary()
        self.assertEqual(summary["actual_stay"]["resident_count"], 1)
        self.assertEqual(next(item for item in summary["room"]["rooms"] if item["room_number"] == "R008")["status"], "OCCUPIED")

        checked_out = self.service.check_out(
            self.claims("EMP008"),
            {"stay_id": "STAY-008", "checkout_time": "2026-07-12T18:00:00+08:00", "reason": "完成出馆交接"},
        )
        self.assertEqual(checked_out["action"], "CHECK_OUT")
        summary = self.service.current_summary()
        self.assertEqual(summary["actual_stay"]["resident_count"], 0)
        self.assertEqual(next(item for item in summary["room"]["rooms"] if item["room_number"] == "R008")["status"], "CLEANING")

    def test_emp008_room_status_update_enforces_active_stay_link(self):
        rooms = [{"room_number": f"R{index:03d}", "status": "AVAILABLE"} for index in range(1, 43)]
        self.service.publish_room_current(
            self.claims("EMP008"),
            {"effective_time": "2026-07-12T08:00:00+08:00", "rooms": rooms, "reason": "首次确认42间房"},
        )
        updated = self.service.update_room_status(
            self.claims("EMP008"),
            {"room_number": "R002", "status": "MAINTENANCE", "effective_time": "2026-07-12T10:00:00+08:00", "reason": "设备维修"},
        )
        self.assertEqual(next(item for item in updated["rooms"] if item["room_number"] == "R002")["status"], "MAINTENANCE")
        with self.assertRaisesRegex(ValueError, "occupied room"):
            self.service.update_room_status(
                self.claims("EMP008"),
                {"room_number": "R003", "status": "OCCUPIED", "effective_time": "2026-07-12T10:05:00+08:00", "reason": "错误占用"},
            )

    def test_audit_and_event_are_persisted(self):
        self.service.record_finance_current(
            self.claims("EMP004"),
            {"effective_date": "2026-07-11", "income": 1, "expense": 0, "receivable": 0, "payable": 0, "cash_balance": 1, "reason": "test"},
        )
        audits = [json.loads(line) for line in (self.root / "audit_center" / "audit_events.jsonl").read_text(encoding="utf-8").splitlines()]
        events = [json.loads(line) for line in (self.root / "events" / "current_operations.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(audits[-1]["action"], "finance.current.record")
        self.assertEqual(events[-1]["event_type"], "finance.current.recorded")

    def test_http_current_write_requires_signed_session(self):
        original_service = FeishuAuthHandler.current_operations
        original_signer = FeishuAuthHandler.session_signer
        signer = AuthSessionSigner("http-current-session-secret-32-characters")
        FeishuAuthHandler.current_operations = self.service
        FeishuAuthHandler.session_signer = signer
        server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        body = json.dumps(
            {
                "effective_date": "2026-07-11",
                "income": 100,
                "expense": 0,
                "receivable": 0,
                "payable": 0,
                "cash_balance": 100,
                "reason": "API录入",
            }
        )
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request("POST", "/api/oms/current/finance/record", body=body, headers={"Content-Type": "application/json"})
            denied = conn.getresponse()
            denied.read()
            self.assertEqual(denied.status, 401)

            token = signer.issue(user_id="uid004", workspace_key="liujie", source="feishu_webapp_sso")["token"]
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request(
                "POST",
                "/api/oms/current/finance/record",
                body=body,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            )
            accepted = conn.getresponse()
            payload = json.loads(accepted.read().decode("utf-8"))
            self.assertEqual(accepted.status, 200)
            self.assertEqual(payload["payload"]["record"]["status"], "PENDING_REVIEW")
        finally:
            server.shutdown()
            server.server_close()
            FeishuAuthHandler.current_operations = original_service
            FeishuAuthHandler.session_signer = original_signer


if __name__ == "__main__":
    unittest.main()
