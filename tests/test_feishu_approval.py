import tempfile
import unittest

from oms_v1.feishu_approval import FeishuDefaultApprovalClient
from oms_v1.feishu_mapping import FeishuApiResult


class FeishuDefaultApprovalTests(unittest.TestCase):
    def test_default_type_selection(self):
        client = FeishuDefaultApprovalClient(env_path="missing.env")

        self.assertEqual(client.default_type_for({"action_type": "create_payment_todo"}, {}), "payment")
        self.assertEqual(client.default_type_for({"action_type": "flag_financial_risk"}, {}), "finance")
        self.assertEqual(client.default_type_for({"action_type": "generate_room_exception_task"}, {}), "general")

    def test_find_default_definition(self):
        client = FeishuDefaultApprovalClient(env_path="missing.env")
        definitions = [
            {"name": "费用报销", "approval_code": "code_finance"},
            {"name": "付款申请", "approval_code": "code_payment"},
        ]

        self.assertEqual(client.find_default_definition("finance", definitions)["approval_code"], "code_finance")
        self.assertEqual(client.find_default_definition("payment", definitions)["approval_code"], "code_payment")
        self.assertIsNone(client.find_default_definition("general", definitions))

    def test_missing_submitter_falls_back_to_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = f"{tmp}/feishu.env"
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write("FEISHU_APP_ID=cli_test\nFEISHU_APP_SECRET=secret\n")

            client = FeishuDefaultApprovalClient(env_path=env_path)
            client._tenant_access_token = lambda: FeishuApiResult(True, data={"expire": 7200})
            client.list_available_definitions = lambda: FeishuApiResult(
                True, data=[{"name": "付款申请", "approval_code": "code_payment"}]
            )

            attempt = client.create_default_approval({"action_type": "create_payment_todo"}, {})

            self.assertFalse(attempt.ok)
            self.assertEqual(attempt.status, "pending")
            self.assertEqual(attempt.approval_type, "payment")
            self.assertIn("submitter", attempt.message)


if __name__ == "__main__":
    unittest.main()
