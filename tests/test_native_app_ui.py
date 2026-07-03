import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "oms_app"


class NativeAppUITests(unittest.TestCase):
    def test_native_app_files_exist(self):
        self.assertTrue((APP_ROOT / "index.html").exists())
        self.assertTrue((APP_ROOT / "styles.css").exists())
        self.assertTrue((APP_ROOT / "app.js").exists())

    def test_native_app_locks_light_sports_visual_identity(self):
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")
        styles = (APP_ROOT / "styles.css").read_text(encoding="utf-8")
        combined = html + script + styles

        self.assertIn("brand-lockup", html)
        self.assertIn("brand-mark", html)
        self.assertIn('data-logo-source="github"', html)
        self.assertIn("color-rail", html + styles)
        for token in ["--red", "--blue", "--green", "--orange", "--purple"]:
            self.assertIn(token, styles)
        self.assertIn("scoreboard-grid", html + styles)
        self.assertIn("score-card", script + styles)
        self.assertIn("workspace-grid-v11", html + styles)
        self.assertIn("overview-layout", html + styles)
        self.assertIn("background: var(--bg)", styles)
        self.assertNotIn("世界杯 LOGO", combined)
        self.assertNotIn("FIFA", combined)
        self.assertNotIn("World Cup", combined)
        self.assertNotIn("background: #000", styles)
        self.assertNotIn("color-scheme: dark", styles)

    def test_native_app_aligns_to_operating_center_v11_layout(self):
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("OMS Operating Center V1.1", html)
        self.assertIn("凰家运营中心（OMS）V1.1", html + script)
        self.assertIn("11个人，每人一个工作台，最后拼成一个运营中心", html + script)
        self.assertIn("scoreboardCards", html + script)
        self.assertIn("priorityCards", html + script)
        self.assertIn("workspaceCards", html + script)
        self.assertIn("sideWorkspaceList", html + script)
        self.assertIn("overviewGrid", html + script)
        self.assertIn("quickLinks", html + script)
        self.assertIn("operatingCenterV11", script)
        self.assertIn("WORKSPACE_ORDER", script)

    def test_native_app_uses_v11_workspace_names_and_order(self):
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        expected_sequence = [
            '"boss"',
            '"huanhuan"',
            '"june"',
            '"liujie"',
            '"zhangjie"',
            '"nana"',
            '"chenchangyi"',
            '"zhouchen"',
            '"yaowei"',
            '"songxue"',
            '"yuchun"',
        ]
        last_index = -1
        for item in expected_sequence:
            current_index = script.index(item)
            self.assertGreater(current_index, last_index)
            last_index = current_index

        for text in [
            "1. 主理办（你）",
            "2. 欢欢（销售）",
            "3. 六月（店总 + 销售）",
            "4. 刘姐（出纳）",
            "5. 张姐（财务总监/会计）",
            "6. 娜娜（管家）",
            "7. 陈昌辉（产护部总监）",
            "8. 周厨（厨师长）",
            "9. 维维（行政采购 + 照护师工资决算）",
            "10. 宗惠（人事行政）",
            "11. 子渝（食材采购 + 销售）",
        ]:
            self.assertIn(text, script)

    def test_native_app_uses_required_dashboard_metrics(self):
        combined = "\n".join(
            [
                (APP_ROOT / "index.html").read_text(encoding="utf-8"),
                (APP_ROOT / "app.js").read_text(encoding="utf-8"),
            ]
        )

        for text in ["今日营收", "在住妈妈", "可用房间", "风险预警", "人效评分"]:
            self.assertIn(text, combined)
        for text in ["经营总览", "财务总览", "房态总览", "人效总览", "快捷入口"]:
            self.assertIn(text, combined)
        for text in ["数据分析中心", "风险预警中心", "审批中心", "我的待办", "系统设置"]:
            self.assertIn(text, combined)

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
        self.assertNotIn("requestAuthCode", script)
        self.assertIn("AUTH_FLOW_STATES", script)
        self.assertIn("AUTH_FLOW_STEPS", script)
        self.assertIn("resetAuthFlowState", script)
        self.assertIn("restartAuthFlow", script)
        self.assertIn("authFlowFailure", script)
        self.assertIn("retryAuthFlow", script)
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
        self.assertNotIn("trustedContext.workspace ||", script)
        self.assertNotIn("trustedContext.workspace ", script)
        self.assertIn('trustedContext.source === "feishu_webapp_sso"', script)

    def test_native_app_rejects_workspace_override(self):
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("trustedContext.user_id", script)
        self.assertIn("trustedContext.open_id", script)
        self.assertIn("trustedContext.union_id", script)
        self.assertIn('trustedContext.source === "feishu_webapp_sso"', script)
        self.assertIn("renderIdentityError", script)
        self.assertIn("renderRuntimeContextBlock", script)
        self.assertIn("restoreWorkspaceShell", script)
        self.assertIn("identityBindingError", script)
        self.assertNotIn('"__unresolved__"', script)
        self.assertNotIn("unresolvedWorkspace", script)
        self.assertNotIn("trustedContext.role", script)
        self.assertNotIn("trustedContext.name", script)
        self.assertNotIn("trustedContext.workspace ||", script)
        self.assertNotIn("trustedContext.workspace ", script)
        self.assertIn("trustedContext.workspace_key", script)
        self.assertNotIn("suppliedWorkspace", script)
        self.assertNotIn("mappedWorkspace ||", script)

    def test_native_app_blocks_direct_url_before_identity_injection(self):
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("if (!runtime.is_feishu_workbench_container)", script)
        self.assertLess(script.index("if (!runtime.is_feishu_workbench_container)"), script.index("if (hasInjectedIdentity())"))
        self.assertIn("\\u8bf7\\u4ece\\u98de\\u4e66\\u5de5\\u4f5c\\u53f0\\u6253\\u5f00", script)
        self.assertIn("URL", script)

    def test_native_app_routes_to_operating_center_after_auth_success(self):
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("window.OMS_USER_CONTEXT = payload", script)
        self.assertIn('authenticatedIdentity.bindingStatus !== "ready"', script)
        self.assertIn('currentWorkspace = identity.bindingStatus === "ready" ? workspaceData[identity.workspaceKey] : null', script)
        self.assertIn('identity = identityBindingError("workspace_route_not_found_after_auth"', script)
        self.assertIn("renderOperatingCenterV11()", script)
        self.assertLess(script.index("restoreWorkspaceShell()"), script.index("renderOperatingCenterV11()"))

    def test_native_app_loads_feishu_h5_sdk_and_runtime_config(self):
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")
        runtime_config = (APP_ROOT / "oms-config.js").read_text(encoding="utf-8")
        sample_config = (APP_ROOT / "oms-config.sample.js").read_text(encoding="utf-8")

        self.assertIn("h5-js-sdk", html)
        self.assertIn("oms-config.js", html)
        self.assertIn("DEFAULT_FEISHU_APP_ID", script)
        self.assertIn("CANONICAL_FEISHU_REDIRECT_URI", script)
        self.assertIn("FEISHU_OAUTH_REDIRECT_WHITELIST", script)
        self.assertIn("FEISHU_LOGIN_SCOPE_LIST", script)
        self.assertIn("validateFeishuOAuthConfig", script)
        self.assertIn("validateCurrentFeishuRedirectUri", script)
        self.assertIn("validatedFeishuScopeList", script)
        self.assertIn("buildFeishuOAuthState", script)
        self.assertIn("ensureCanonicalRedirectUri", script)
        self.assertIn("canonicalizeRedirectUri", script)
        self.assertIn("window.location.replace(expectedUri)", script)
        self.assertIn("appID: config.appId", script)
        self.assertIn("scopeList: validatedFeishuScopeList(config.scopeList)", script)
        self.assertIn("state: buildFeishuOAuthState()", script)
        self.assertIn("feishu_request_access_unavailable", script)
        self.assertIn("cli_aaac7e6da2b95cfc", script)
        self.assertIn("OMS_FEISHU_APP_ID", runtime_config)
        self.assertIn("OMS_FEISHU_REDIRECT_URI", runtime_config)
        self.assertIn("OMS_FEISHU_SCOPE_LIST", runtime_config)
        self.assertIn("http://127.0.0.1:8787/api/feishu/identity", runtime_config)
        self.assertIn("https://ponslucia14-ux.github.io/huangjia-oms-v1/", runtime_config)
        self.assertIn("cli_aaac7e6da2b95cfc", runtime_config)
        self.assertIn("OMS_FEISHU_APP_ID", sample_config)
        self.assertIn("OMS_FEISHU_SCOPE_LIST", sample_config)
        self.assertIn("OMS_AUTH_ENDPOINT", sample_config)
        self.assertNotIn("localhost", runtime_config + sample_config + script)
        self.assertNotIn("auth/callback", runtime_config + sample_config + script)
        self.assertNotIn("index.html", runtime_config + sample_config)

    def test_native_app_does_not_expose_backend_layer_names(self):
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
