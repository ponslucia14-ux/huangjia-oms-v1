import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "oms_app"


class NativeAppUITests(unittest.TestCase):
    def test_native_app_files_exist(self):
        self.assertTrue((APP_ROOT / "index.html").exists())
        self.assertTrue((APP_ROOT / "styles.css").exists())
        self.assertTrue((APP_ROOT / "app.js").exists())

    def test_native_app_is_single_user_workspace(self):
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("OMS Single User Workspace", html)
        self.assertIn("我的待办", html)
        self.assertIn("我的任务", html)
        self.assertIn("我的审批", html)
        self.assertIn("我的流程", html)
        self.assertNotIn("11个人，每人一个工作台", html + script)
        self.assertNotIn("拼成一个运营中心", html + script)
        self.assertNotIn("unifiedOverview", html + script)
        self.assertNotIn("operatingCenter", html + script)

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
