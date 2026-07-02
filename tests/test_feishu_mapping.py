import tempfile
import unittest

from oms_v1.feishu_mapping import FeishuObjectSyncer


class FeishuMappingTests(unittest.TestCase):
    def test_build_mapping_from_real_snapshot_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = f"{tmp}/feishu.env"
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write("FEISHU_APP_ID=cli_test\n")
                handle.write("FEISHU_APP_SECRET=secret\n")
                handle.write("OMS_MAP_LIUJIE_APPROVAL_CODE=must_not_be_used\n")
                handle.write("OMS_MAP_BOSS_CHAT_ID=must_not_be_used\n")

            syncer = FeishuObjectSyncer(env_path=env_path, mapping_root=tmp)
            snapshot = {
                "users": [
                    {"name": "六月", "user_id": "user_june", "open_id": "ou_june"},
                    {"name": "刘姐", "user_id": "user_liujie", "open_id": "ou_liujie"},
                    {"name": "娜娜", "user_id": "user_nana", "open_id": "ou_nana"},
                ],
                "chats": [
                    {"name": "销售群", "chat_id": "oc_sales"},
                    {"name": "六月排房", "chat_id": "oc_june"},
                ],
                "approvals": [{"name": "刘姐", "approval_code": "approval_env"}],
            }

            rows = syncer.build_mapping(snapshot)
            by_name = {row.name: row for row in rows}

            self.assertEqual(by_name["六月"].user_id, "user_june")
            self.assertEqual(by_name["六月"].open_id, "ou_june")
            self.assertEqual(by_name["六月"].chat_id, "oc_june")
            self.assertEqual(by_name["刘姐"].approval_code, "approval_env")
            self.assertEqual(by_name["BOSS"].chat_id, "")

    def test_capability_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            syncer = FeishuObjectSyncer(mapping_root=tmp)
            rows = syncer.build_mapping(
                {
                    "users": [{"name": "娜娜", "user_id": "user_nana", "open_id": "ou_nana"}],
                    "chats": [],
                    "approvals": [],
                }
            )
            nana = {row.name: row for row in rows}["娜娜"]

            self.assertTrue(syncer.resolve_action(nana, "send_message")["ready"])
            self.assertTrue(syncer.resolve_action(nana, "assign_task")["ready"])
            self.assertFalse(syncer.resolve_action(nana, "create_approval")["ready"])

    def test_role_action_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            syncer = FeishuObjectSyncer(mapping_root=tmp)
            mapping = {
                "rows": [
                    {
                        "name": "六月",
                        "role": "店铺总监",
                        "user_id": "user_june",
                        "open_id": "ou_june",
                        "chat_id": "oc_june",
                        "approval_code": "",
                    },
                    {
                        "name": "刘姐",
                        "role": "财务",
                        "user_id": "user_liujie",
                        "open_id": "ou_liujie",
                        "chat_id": "oc_finance",
                        "approval_code": "approval_finance",
                    },
                    {
                        "name": "销售",
                        "role": "销售",
                        "user_id": "",
                        "open_id": "",
                        "chat_id": "oc_sales",
                        "approval_code": "",
                    },
                ]
            }

            self.assertEqual(syncer.send_message("六月", mapping)["target_id"], "oc_june")
            self.assertEqual(syncer.create_approval("刘姐", mapping)["approval_code"], "approval_finance")
            self.assertEqual(syncer.assign_task("销售", mapping)["reason"], "missing user_id/open_id")


if __name__ == "__main__":
    unittest.main()
