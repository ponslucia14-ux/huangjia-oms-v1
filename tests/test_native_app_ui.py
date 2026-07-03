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
        self.assertIn("bootstrapIdentity", script)
        self.assertIn("feishuRuntimeContext", script)
        self.assertIn("isFeishuClient", script)
        self.assertIn("isLarkWebView", script)
        self.assertIn("isFeishuWorkbenchContainer", script)
        self.assertIn("requestFeishuAuthCode", script)
        self.assertIn("requestAccess", script)
        self.assertIn("requestAuthCode", script)
        self.assertIn("OMS_FEISHU_USER_WORKSPACE_MAP", script)
        self.assertIn("feishu_user_id_only", script)
        self.assertIn("not_feishu_runtime_context", script)
        self.assertNotIn("userSelect", html + script)
        self.assertNotIn("<select", html)
        self.assertNotIn("<option", html)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("sessionStorage", script)
        self.assertNotIn("searchParams", script)
        self.assertNotIn("location.search", script)
        self.assertNotIn("trustedContext.workspace", script)
        self.assertNotIn("workspace_key", script)

    def test_native_app_rejects_workspace_override(self):
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("trustedContext.user_id", script)
        self.assertIn("trustedContext.open_id", script)
        self.assertIn("trustedContext.union_id", script)
        self.assertIn("renderIdentityError", script)
        self.assertIn("renderRuntimeContextBlock", script)
        self.assertIn("identityBindingError", script)
        self.assertNotIn('"__unresolved__"', script)
        self.assertNotIn("unresolvedWorkspace", script)
        self.assertNotIn("trustedContext.role", script)
        self.assertNotIn("trustedContext.name", script)
        self.assertNotIn("trustedContext.workspace", script)
        self.assertNotIn("suppliedWorkspace", script)
        self.assertNotIn("mappedWorkspace ||", script)

    def test_native_app_blocks_direct_url_before_identity_injection(self):
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("if (!runtime.is_feishu_workbench_container)", script)
        self.assertLess(script.index("if (!runtime.is_feishu_workbench_container)"), script.index("if (hasInjectedIdentity())"))
        self.assertIn("\\u8bf7\\u4ece\\u98de\\u4e66\\u5de5\\u4f5c\\u53f0\\u6253\\u5f00", script)
        self.assertIn("URL", script)

    def test_native_app_loads_feishu_h5_sdk_and_runtime_config(self):
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        sample_config = (APP_ROOT / "oms-config.sample.js").read_text(encoding="utf-8")

        self.assertIn("h5-js-sdk", html)
        self.assertIn("oms-config.js", html)
        self.assertIn("OMS_FEISHU_APP_ID", sample_config)
        self.assertIn("OMS_AUTH_ENDPOINT", sample_config)

    def test_native_app_uses_v11_person_role_workspace_bindings(self):
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn('SOURCE_OF_TRUTH = "凰家运营中心（OMS）V1.1"', script)
        for text in [
            "主理办（你）",
            "主理办工作台",
            "欢欢",
            "销售工作台",
            "六月",
            "店总工作台",
            "刘姐",
            "财务工作台",
            "张姐",
            "财务总监工作台",
            "娜娜",
            "管家工作台",
            "陈昌辉",
            "产护工作台",
            "周厨",
            "料理工作台",
            "维维",
            "行政采购工作台",
            "宗惠",
            "人事行政工作台",
            "子渝",
            "食材采购 + 销售工作台",
        ]:
            self.assertIn(text, script)
        for drifted_name in ["王梦为", "陈昌伊", "周辰", "尧维", "宋雪", "于淳"]:
            self.assertNotIn(drifted_name, script)
        for old_key in ["admin:", "procurement:", "maternity_care:", "kitchen:", "logistics:"]:
            self.assertNotIn(old_key, script)

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
