import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "oms_app"


class NativeAppUITests(unittest.TestCase):
    def test_native_app_files_exist(self):
        self.assertTrue((APP_ROOT / "index.html").exists())
        self.assertTrue((APP_ROOT / "styles.css").exists())
        self.assertTrue((APP_ROOT / "app.js").exists())

    def test_native_app_aligns_to_operating_center_v11(self):
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("凰家运营中心（OMS）V1.1", html)
        self.assertIn("11个人，每人一个工作台", html + script)
        self.assertIn("拼成一个运营中心", html)
        for name in ["王梦为", "欢欢", "六月", "刘姐", "张姐", "娜娜", "陈昌伊", "周辰", "尧维", "宋雪", "于淳"]:
            self.assertIn(name, script)

    def test_native_app_locks_identity_without_user_switching(self):
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("lockedUserName", html)
        self.assertIn("lockedUserRole", html)
        self.assertIn("resolveLockedIdentity", script)
        self.assertIn("OMS_FEISHU_USER_WORKSPACE_MAP", script)
        self.assertNotIn("userSelect", html + script)
        self.assertNotIn("<select", html)
        self.assertNotIn("<option", html)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("searchParams", script)
        self.assertNotIn("location.search", script)

    def test_native_app_does_not_expose_structure_layers(self):
        combined = "\n".join(
            [
                (APP_ROOT / "index.html").read_text(encoding="utf-8"),
                (APP_ROOT / "app.js").read_text(encoding="utf-8"),
            ]
        )

        self.assertNotIn("business_layer", combined)
        self.assertNotIn("support_layer", combined)
        self.assertNotIn("system_capability_layer", combined)
        self.assertNotIn("operating_center_structure", combined)


if __name__ == "__main__":
    unittest.main()
