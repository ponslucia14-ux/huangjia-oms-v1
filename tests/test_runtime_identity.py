import json
import tempfile
import unittest
from pathlib import Path

from oms_v1.operating_center_source import (
    OPERATING_CENTER_PEOPLE,
    UNMAPPED_IDENTITY,
    feishu_identity_bindings,
    workspace_key_for_feishu_identity,
)


EXPECTED_IDENTITIES = {
    "EMP001": ("石磊", "ROLE_OWNER", "a2c82cb4", "boss"),
    "EMP002": ("宗惠", "ROLE_HR", "ef8a11c3", "songxue"),
    "EMP003": ("张敬东", "ROLE_ACCOUNTANT", "7611528c", "zhangjie"),
    "EMP004": ("刘晶", "ROLE_CASHIER", "8eag4627", "liujie"),
    "EMP005": ("石昊昕", "ROLE_ADMIN", "19d9f5c2", "yaowei"),
    "EMP006": ("杨欢欢", "ROLE_SALES", "e83f88ga", "huanhuan"),
    "EMP007": ("薛子渝", "ROLE_SALES", "ge8gb853", "yuchun"),
    "EMP008": ("刘芳羽", "ROLE_STORE_MANAGER", "39g7c1f2", "june"),
    "EMP009": ("尚丽娜", "ROLE_BUTLER", "9dcg7e27", "nana"),
    "EMP010": ("陈晶辉", "ROLE_NURSING_DIRECTOR", "49916de2", "chenchangyi"),
    "EMP011": ("周志朋", "ROLE_KITCHEN_DIRECTOR", "7e6595fg", "zhouchen"),
}


class RuntimeIdentityTests(unittest.TestCase):
    def test_master_data_resolves_all_eleven_real_user_ids(self):
        bindings = feishu_identity_bindings()

        self.assertEqual(set(bindings), {item[3] for item in EXPECTED_IDENTITIES.values()})
        for emp, (name, role_code, user_id, workspace_key) in EXPECTED_IDENTITIES.items():
            identity = bindings[workspace_key]
            self.assertEqual(identity["source"], "oms_master_data")
            self.assertEqual(identity["emp"], emp)
            self.assertEqual(identity["name"], name)
            self.assertEqual(identity["role_code"], role_code)
            self.assertEqual(identity["user_id"], user_id)
            self.assertEqual(identity["workspace_key"], workspace_key)
            self.assertEqual(identity["workspace"], OPERATING_CENTER_PEOPLE[workspace_key]["title"])

            resolved_key, source = workspace_key_for_feishu_identity({user_id})
            self.assertEqual(resolved_key, workspace_key)
            self.assertEqual(source, "oms_master_data")

    def test_open_id_and_union_id_resolve_to_the_same_workspace(self):
        bindings = feishu_identity_bindings()

        for workspace_key, identity in bindings.items():
            open_key, open_source = workspace_key_for_feishu_identity({identity["open_id"]})
            union_key, union_source = workspace_key_for_feishu_identity({identity["union_id"]})

            self.assertEqual(open_key, workspace_key)
            self.assertEqual(open_source, "oms_master_data")
            self.assertEqual(union_key, workspace_key)
            self.assertEqual(union_source, "oms_master_data")

    def test_old_partial_mapping_does_not_block_master_data_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp)
            mapping_path = live_root / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
            mapping_path.parent.mkdir(parents=True, exist_ok=True)
            mapping_path.write_text(json.dumps({"rows": []}, ensure_ascii=False), encoding="utf-8")

            key, source = workspace_key_for_feishu_identity({"ef8a11c3"}, live_root=live_root)

        self.assertEqual(key, "songxue")
        self.assertEqual(source, "oms_master_data")

    def test_snapshot_conflict_does_not_override_master_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp)
            snapshot_path = live_root / "realworld_mapping" / "feishu_object_snapshot.json"
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(
                json.dumps(
                    {
                        "users": [
                            {
                                "name": "错误姓名",
                                "user_id": "ef8a11c3",
                                "open_id": "wrong_open",
                                "union_id": "wrong_union",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            bindings = feishu_identity_bindings(live_root=live_root)
            key, source = workspace_key_for_feishu_identity({"ef8a11c3"}, live_root=live_root)

        self.assertEqual(bindings["songxue"]["name"], "宗惠")
        self.assertEqual(bindings["songxue"]["open_id"], "ou_eb1403cda0e322323d26a8781b9aa1e2")
        self.assertEqual(key, "songxue")
        self.assertEqual(source, "oms_master_data")

    def test_unknown_user_id_returns_unmapped_identity_without_boss_fallback(self):
        key, source = workspace_key_for_feishu_identity({"unknown-user-id"})

        self.assertEqual(key, "")
        self.assertEqual(source, UNMAPPED_IDENTITY)

    def test_workspace_menu_preview_can_be_generated_for_all_eleven_people(self):
        bindings = feishu_identity_bindings()
        previews = []
        for workspace_key, identity in bindings.items():
            person = OPERATING_CENTER_PEOPLE[workspace_key]
            previews.append(
                {
                    "emp": identity["emp"],
                    "name": identity["name"],
                    "role_code": identity["role_code"],
                    "workspace": person["title"],
                    "primary_menus": person["focus"],
                }
            )

        self.assertEqual(len(previews), 11)
        self.assertTrue(all(item["primary_menus"] for item in previews))
        self.assertEqual({item["emp"] for item in previews}, set(EXPECTED_IDENTITIES))


if __name__ == "__main__":
    unittest.main()
