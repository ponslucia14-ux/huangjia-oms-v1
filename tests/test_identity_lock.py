import unittest

from oms_v1.operating_center_source import (
    IDENTITY_BINDING_ERROR,
    IDENTITY_LOCK_POLICY,
    OPERATING_CENTER_PEOPLE,
    ROLE_USER_ALIASES,
)


class IdentityLockTests(unittest.TestCase):
    def test_operating_center_v11_names_are_locked(self):
        expected_names = {
            "boss": "石磊",
            "huanhuan": "杨欢欢",
            "june": "刘芳羽",
            "liujie": "刘晶",
            "zhangjie": "张敬东",
            "nana": "尚丽娜",
            "chenchangyi": "陈晶辉",
            "zhouchen": "周志朋",
            "yaowei": "石昊盺",
            "songxue": "宗惠",
            "yuchun": "薛子渝",
        }

        self.assertEqual(IDENTITY_LOCK_POLICY, "source_of_truth_locked_no_runtime_alias")
        self.assertEqual({key: person["name"] for key, person in OPERATING_CENTER_PEOPLE.items()}, expected_names)

    def test_identity_model_has_no_runtime_alias_or_fallback_name(self):
        drifted_names = {"王梦为", "陈昌伊", "周辰", "尧维", "宋雪", "于淳"}
        actual_names = {person["name"] for person in OPERATING_CENTER_PEOPLE.values()}

        self.assertFalse(drifted_names & actual_names)
        self.assertEqual(ROLE_USER_ALIASES, {})
        self.assertEqual(IDENTITY_BINDING_ERROR["error_type"], "identity_binding_required")
        self.assertEqual(IDENTITY_BINDING_ERROR["entry"], "login_required")
        for person in OPERATING_CENTER_PEOPLE.values():
            self.assertNotIn("aliases", person)


if __name__ == "__main__":
    unittest.main()
