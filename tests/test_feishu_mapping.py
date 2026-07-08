import tempfile
import unittest

from oms_v1.feishu_mapping import FeishuObjectSyncer
from oms_v1.master_data import OMSMasterData


def write_identity_mapping(path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            "\n".join(
                [
                    "| EMP | OMS 正式姓名 | 飞书名称 | 系统角色 | Department | Job Title | user_id | open_id | union_id | 工作邮箱 | 手机号 | Employee Status | 是否启用 | 入职日期 / 创建时间 |",
                    "|------|--------------|----------|----------|------------|-----------|---------|---------|----------|----------|--------|-----------------|----------|--------------------|",
                    "| EMP001 | 石磊 | 石磊 | ROLE_OWNER | 主理办 | 主理人 | a2c82cb4 | ou_owner | on_owner | -- | -- | 在职 | 是 | 2019-01-01 |",
                    "| EMP004 | 刘晶 | 刘晶 | ROLE_CASHIER | 财务部 | 出纳 | 8eag4627 | ou_liujing | on_liujing | -- | -- | 在职 | 是 | 2026-07-02 |",
                    "| EMP008 | 刘芳羽 | 刘芳羽 | ROLE_STORE_MANAGER | 店总办公室 | 店铺总监 | 39g7c1f2 | ou_liufangyu | on_liufangyu | -- | -- | 在职 | 是 | 2026-07-08 |",
                    "| EMP009 | 尚丽娜 | 尚丽娜 | ROLE_BUTLER | 店总办公室 | 管家 | 9dcg7e27 | ou_shanglina | on_shanglina | -- | -- | 在职 | 是 | 2026-07-02 |",
                ]
            )
        )


def write_organization_master_data(path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            """
# OMS 组织主数据

## EMP001

姓名：

石磊

部门：

主理办

岗位：

- 主理人

系统角色：

ROLE_OWNER

权限等级：

LEVEL_0

---

## EMP004

姓名：

刘晶

部门：

财务部

岗位：

- 出纳

系统角色：

ROLE_CASHIER

权限等级：

LEVEL_3

---

## EMP008

姓名：

刘芳羽

部门：

店总办公室

岗位：

- 店铺总监

系统角色：

ROLE_STORE_MANAGER

权限等级：

LEVEL_1

---

## EMP009

姓名：

尚丽娜

部门：

店总办公室

岗位：

- 管家

系统角色：

ROLE_BUTLER

权限等级：

LEVEL_3
""".strip()
        )


class FeishuMappingTests(unittest.TestCase):
    def test_build_mapping_from_real_snapshot_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = f"{tmp}/feishu.env"
            mapping_path = f"{tmp}/OMS_飞书身份映射.md"
            organization_path = f"{tmp}/OMS_组织主数据.md"
            write_identity_mapping(mapping_path)
            write_organization_master_data(organization_path)
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write("FEISHU_APP_ID=cli_test\n")
                handle.write("FEISHU_APP_SECRET=secret\n")
                handle.write("OMS_MAP_LIUJING_APPROVAL_CODE=must_not_be_used\n")
                handle.write("OMS_MAP_SHILEI_CHAT_ID=must_not_be_used\n")

            master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=mapping_path)
            syncer = FeishuObjectSyncer(env_path=env_path, mapping_root=tmp, master_data=master_data)
            snapshot = {
                "users": [
                    {"name": "刘芳羽", "user_id": "user_liufangyu", "open_id": "ou_liufangyu"},
                    {"name": "刘晶", "user_id": "user_liujing", "open_id": "ou_liujing"},
                    {"name": "尚丽娜", "user_id": "user_shanglina", "open_id": "ou_shanglina"},
                ],
                "chats": [
                    {"name": "销售群", "chat_id": "oc_sales"},
                    {"name": "刘芳羽排房", "chat_id": "oc_liufangyu"},
                ],
                "approvals": [{"name": "刘晶", "approval_code": "approval_env"}],
            }

            rows = syncer.build_mapping(snapshot)
            by_name = {row.name: row for row in rows}

            self.assertEqual(by_name["刘芳羽"].user_id, "user_liufangyu")
            self.assertEqual(by_name["刘芳羽"].open_id, "ou_liufangyu")
            self.assertEqual(by_name["刘芳羽"].chat_id, "oc_liufangyu")
            self.assertEqual(by_name["刘晶"].approval_code, "approval_env")
            self.assertEqual(by_name["石磊"].chat_id, "")

    def test_capability_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            mapping_path = f"{tmp}/OMS_飞书身份映射.md"
            organization_path = f"{tmp}/OMS_组织主数据.md"
            write_identity_mapping(mapping_path)
            write_organization_master_data(organization_path)
            master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=mapping_path)
            syncer = FeishuObjectSyncer(mapping_root=tmp, master_data=master_data)
            rows = syncer.build_mapping(
                {
                    "users": [{"name": "尚丽娜", "user_id": "user_shanglina", "open_id": "ou_shanglina"}],
                    "chats": [],
                    "approvals": [],
                }
            )
            shanglina = {row.name: row for row in rows}["尚丽娜"]

            self.assertTrue(syncer.resolve_action(shanglina, "send_message")["ready"])
            self.assertTrue(syncer.resolve_action(shanglina, "assign_task")["ready"])
            approval = syncer.resolve_action(shanglina, "create_approval")
            self.assertTrue(approval["ready"])
            self.assertEqual(approval["approval_type"], "general")
            self.assertEqual(approval["approval_code_policy"], "auto_discover_by_api; no manual configuration")

    def test_chat_members_are_not_used_as_identity_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            mapping_path = f"{tmp}/OMS_飞书身份映射.md"
            organization_path = f"{tmp}/OMS_组织主数据.md"
            write_identity_mapping(mapping_path)
            write_organization_master_data(organization_path)
            master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=mapping_path)
            syncer = FeishuObjectSyncer(mapping_root=tmp, master_data=master_data)
            rows = syncer.build_mapping(
                {
                    "users": [],
                    "chat_members_as_users": [
                        {
                            "name": "10晓磊（总裁）",
                            "user_id": "a2c82cb4",
                            "open_id": "ou_boss",
                            "source_chat_name": "财务群",
                            "_source": "chat_member",
                        },
                        {
                            "name": "刘晶",
                            "user_id": "8eag4627",
                            "open_id": "ou_liujing",
                            "source_chat_name": "财务群",
                            "_source": "chat_member",
                        },
                    ],
                    "chats": [{"name": "财务群", "chat_id": "oc_finance"}],
                    "approvals": [],
                }
            )
            by_name = {row.name: row for row in rows}

            self.assertEqual(by_name["石磊"].user_id, "")
            self.assertEqual(by_name["刘晶"].user_id, "")
            self.assertEqual(by_name["刘晶"].open_id, "")
            self.assertEqual(by_name["刘芳羽"].user_id, "")

    def test_org_users_are_the_only_identity_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            mapping_path = f"{tmp}/OMS_飞书身份映射.md"
            organization_path = f"{tmp}/OMS_组织主数据.md"
            write_identity_mapping(mapping_path)
            write_organization_master_data(organization_path)
            master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=mapping_path)
            syncer = FeishuObjectSyncer(mapping_root=tmp, master_data=master_data)
            rows = syncer.build_mapping(
                {
                    "org_users": [
                        {"name": "刘晶", "user_id": "8eag4627", "open_id": "ou_liujing"},
                        {"name": "石磊", "user_id": "a2c82cb4", "open_id": "ou_owner"},
                    ],
                    "chat_members_as_users": [
                        {"name": "刘晶", "user_id": "must_not_bind", "open_id": "must_not_bind"}
                    ],
                    "chats": [],
                    "approvals": [],
                }
            )
            by_name = {row.name: row for row in rows}

            self.assertEqual(by_name["石磊"].user_id, "a2c82cb4")
            self.assertEqual(by_name["刘晶"].user_id, "8eag4627")
            self.assertEqual(by_name["刘晶"].open_id, "ou_liujing")
            self.assertEqual(by_name["刘晶"].source["user_id"], "feishu_org_user_match")

    def test_role_action_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            syncer = FeishuObjectSyncer(mapping_root=tmp)
            mapping = {
                "rows": [
                    {
                        "name": "刘芳羽",
                        "role": "店铺总监",
                        "user_id": "user_liufangyu",
                        "open_id": "ou_liufangyu",
                        "chat_id": "oc_liufangyu",
                        "approval_code": "",
                    },
                    {
                        "name": "刘晶",
                        "role": "财务",
                        "user_id": "user_liujing",
                        "open_id": "ou_liujing",
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

            self.assertEqual(syncer.send_message("刘芳羽", mapping)["target_id"], "oc_liufangyu")
            self.assertEqual(syncer.create_approval("刘晶", mapping)["approval_code"], "approval_finance")
            self.assertEqual(syncer.create_approval("刘晶", mapping)["approval_type"], "finance")
            self.assertEqual(syncer.assign_task("销售", mapping)["reason"], "missing user_id/open_id")


if __name__ == "__main__":
    unittest.main()
