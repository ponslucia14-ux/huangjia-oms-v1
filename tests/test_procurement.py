import base64
import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from oms_v1.procurement import ADMIN_PURCHASE, FOOD_PURCHASE, ProcurementService
from oms_v1.auth_session import AuthSessionSigner
from oms_v1.feishu_auth_server import FeishuAuthHandler


class FakeMasterData:
    def __init__(self):
        self.rows = [
            SimpleNamespace(emp="EMP001", name="10晓磊", user_id="uid001", open_id="", union_id=""),
            SimpleNamespace(emp="EMP003", name="张敬东", user_id="uid003", open_id="", union_id=""),
            SimpleNamespace(emp="EMP004", name="刘晶", user_id="uid004", open_id="", union_id=""),
            SimpleNamespace(emp="EMP005", name="石昊盺", user_id="uid005", open_id="", union_id=""),
            SimpleNamespace(emp="EMP007", name="薛子渝", user_id="uid007", open_id="", union_id=""),
            SimpleNamespace(emp="EMP008", name="刘芳羽", user_id="uid008", open_id="", union_id=""),
        ]

    def employees(self):
        return list(self.rows)


class ProcurementServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.service = ProcurementService(self.root, master_data=FakeMasterData())

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def claims(emp):
        workspaces = {
            "EMP001": "boss",
            "EMP003": "zhangjie",
            "EMP004": "liujie",
            "EMP005": "yaowei",
            "EMP007": "yuchun",
            "EMP008": "june",
        }
        return {"user_id": f"uid{emp[-3:]}", "workspace_key": workspaces[emp]}

    @staticmethod
    def attachment(name="采购凭证.png"):
        # The service intentionally permits manual correction when OCR cannot read an image.
        content = b"\x89PNG\r\n\x1a\nprocurement-test"
        return {
            "name": name,
            "data_url": "data:image/png;base64," + base64.b64encode(content).decode("ascii"),
        }

    def admin_draft(self):
        return self.service.save_draft(
            self.claims("EMP005"),
            {
                "attachment": self.attachment("网购订单.png"),
                "title": "打印纸和清洁用品",
                "amount": "328.50",
                "purchase_date": "2026-07-14",
                "supplier": "办公用品店",
                "category": "行政用品",
                "remark": "办公室补充采购",
                "reason": "保存行政采购草稿",
            },
        )

    def test_administrative_purchase_full_closure_and_trace(self):
        draft = self.admin_draft()
        self.assertEqual(draft["purchase_type"], ADMIN_PURCHASE)
        self.assertEqual(draft["status"], "DRAFT")
        self.assertEqual(draft["recognition"]["status"], "NEEDS_MANUAL_REVIEW")
        self.assertTrue(draft["attachments"][0]["data_url"].startswith("data:image/png;base64,"))
        self.assertTrue(draft["manual_changes"])

        submitted = self.service.submit(
            self.claims("EMP005"),
            {"record_id": draft["record_id"], "reason": "采购信息核对完成"},
        )
        self.assertEqual(submitted["status"], "PENDING_APPROVAL")
        self.assertEqual(self.service.list_records(self.claims("EMP004"))["total"], 0)
        self.assertEqual(self.service.list_records(self.claims("EMP003"))["total"], 0)

        approved = self.service.decide(
            self.claims("EMP001"),
            {"record_id": draft["record_id"], "approved": True, "reason": "行政采购用途合理"},
        )
        self.assertEqual(approved["status"], "APPROVED")
        self.assertEqual(approved["payment_status"], "PENDING")
        self.assertEqual(self.service.list_records(self.claims("EMP004"))["total"], 1)
        self.assertEqual(self.service.list_records(self.claims("EMP003"))["total"], 0)

        paid = self.service.record_payment(
            self.claims("EMP004"),
            {
                "record_id": draft["record_id"],
                "payment_reference": "PAY-001",
                "payment_note": "微信支付",
                "reason": "按审批结果付款",
            },
        )
        self.assertEqual(paid["status"], "PAID")
        self.assertEqual(self.service.list_records(self.claims("EMP003"))["total"], 1)

        accounted = self.service.record_accounting(
            self.claims("EMP003"),
            {
                "record_id": draft["record_id"],
                "accounting_category": "行政支出",
                "accounting_note": "凭证完整",
                "reason": "完成采购核算",
            },
        )
        self.assertEqual(accounted["status"], "ACCOUNTED")
        self.assertEqual(accounted["accounting_status"], "COMPLETED")

        owner_result = self.service.get_record(self.claims("EMP005"), draft["record_id"])
        self.assertEqual(owner_result["status"], "ACCOUNTED")
        audits = [
            json.loads(line)
            for line in (self.root / "audit_center" / "audit_events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        events = [
            json.loads(line)
            for line in (self.root / "events" / "procurement.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(
            [row["action"] for row in audits],
            ["procurement.draft.save", "procurement.submit", "procurement.approve", "procurement.payment", "procurement.account"],
        )
        self.assertEqual(events[-1]["event_type"], "procurement.accounted")

    def test_food_arrival_return_edit_and_resubmit(self):
        draft = self.service.save_draft(
            self.claims("EMP007"),
            {
                "attachment": self.attachment("手写食材单.png"),
                "title": "蔬菜和肉类",
                "amount": "186.20",
                "purchase_date": "2026-07-14",
                "supplier": "农贸市场",
                "category": "生鲜食材",
                "items": [
                    {"name": "西红柿", "quantity": "5", "unit": "斤", "unit_price": "4", "amount": "20"},
                    {"name": "猪肉", "quantity": "4", "unit": "斤", "unit_price": "28", "amount": "112"},
                ],
                "remark": "手写识别后人工核对",
                "reason": "保存食材采购草稿",
            },
        )
        self.assertEqual(draft["purchase_type"], FOOD_PURCHASE)
        arrived = self.service.confirm_arrival(
            self.claims("EMP007"),
            {"record_id": draft["record_id"], "reason": "食材已实际到货"},
        )
        self.assertEqual(arrived["arrival_status"], "RECEIVED")
        self.service.submit(self.claims("EMP007"), {"record_id": draft["record_id"], "reason": "提交食材采购审批"})
        returned = self.service.decide(
            self.claims("EMP001"),
            {"record_id": draft["record_id"], "approved": False, "reason": "请补充供应商说明"},
        )
        self.assertEqual(returned["status"], "RETURNED")
        self.assertEqual(returned["returned_reason"], "请补充供应商说明")

        edited = self.service.save_draft(
            self.claims("EMP007"),
            {
                "record_id": draft["record_id"],
                "supplier": "光复路农贸市场",
                "remark": "已补充供应商全称",
                "reason": "按退回意见补充",
            },
        )
        self.assertEqual(edited["supplier"], "光复路农贸市场")
        self.assertEqual(edited["status"], "DRAFT")
        resubmitted = self.service.submit(
            self.claims("EMP007"),
            {"record_id": draft["record_id"], "reason": "补充后重新提交"},
        )
        self.assertEqual(resubmitted["status"], "PENDING_APPROVAL")
        self.assertEqual(resubmitted["arrival_status"], "RECEIVED")

    def test_permissions_separate_owners_approval_payment_and_accounting(self):
        draft = self.admin_draft()
        with self.assertRaises(PermissionError):
            self.service.get_record(self.claims("EMP007"), draft["record_id"])
        with self.assertRaises(PermissionError):
            self.service.save_draft(
                self.claims("EMP007"),
                {"record_id": draft["record_id"], "title": "越权修改", "reason": "越权"},
            )
        with self.assertRaises(PermissionError):
            self.service.decide(
                self.claims("EMP004"),
                {"record_id": draft["record_id"], "approved": True, "reason": "越权审批"},
            )
        with self.assertRaises(PermissionError):
            self.service.record_payment(
                self.claims("EMP001"),
                {"record_id": draft["record_id"], "reason": "越权付款"},
            )
        with self.assertRaises(PermissionError):
            self.service.list_records(self.claims("EMP008"))

    def test_draft_persists_across_service_restart(self):
        draft = self.admin_draft()
        restarted = ProcurementService(self.root, master_data=FakeMasterData())
        restored = restarted.get_record(self.claims("EMP005"), draft["record_id"])
        self.assertEqual(restored["title"], "打印纸和清洁用品")
        self.assertEqual(restored["remark"], "办公室补充采购")
        self.assertTrue(restored["attachments"][0]["data_url"].startswith("data:image/png;base64,"))


class ProcurementHTTPTests(unittest.TestCase):
    def test_authenticated_draft_and_list_contract(self):
        original_procurement = FeishuAuthHandler.procurement
        original_signer = FeishuAuthHandler.session_signer
        with tempfile.TemporaryDirectory() as tmp:
            FeishuAuthHandler.procurement = ProcurementService(tmp, master_data=FakeMasterData())
            FeishuAuthHandler.session_signer = AuthSessionSigner("procurement-http-test-secret-123456")
            issued = FeishuAuthHandler.session_signer.issue(user_id="uid005", workspace_key="yaowei", source="test")
            server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                attachment = ProcurementServiceTests.attachment("行政采购.png")
                body = json.dumps(
                    {
                        "attachment": attachment,
                        "title": "行政采购测试",
                        "amount": "88.00",
                        "purchase_date": "2026-07-14",
                        "supplier": "测试供应商",
                        "category": "行政用品",
                        "reason": "接口保存草稿",
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                conn.request(
                    "POST",
                    "/api/oms/procurement/draft",
                    body=body,
                    headers={
                        "Authorization": f"Bearer {issued['token']}",
                        "Content-Type": "application/json; charset=utf-8",
                        "Content-Length": str(len(body)),
                    },
                )
                response = conn.getresponse()
                envelope = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(envelope["status"], "ready")
                self.assertEqual(envelope["payload"]["record"]["status"], "DRAFT")

                conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                conn.request(
                    "GET",
                    "/api/oms/procurement?purchase_type=ADMIN",
                    headers={"Authorization": f"Bearer {issued['token']}"},
                )
                response = conn.getresponse()
                envelope = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(envelope["payload"]["total"], 1)
                self.assertEqual(envelope["payload"]["records"][0]["purchase_type"], "ADMIN")
            finally:
                server.shutdown()
                server.server_close()
                FeishuAuthHandler.procurement = original_procurement
                FeishuAuthHandler.session_signer = original_signer


if __name__ == "__main__":
    unittest.main()
