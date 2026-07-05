import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "oms_app"
SERVER_PATH = Path(__file__).resolve().parents[1] / "oms_v1" / "feishu_auth_server.py"


class NativeAppUITests(unittest.TestCase):
    def read(self, name):
        return (APP_ROOT / name).read_text(encoding="utf-8")

    def test_native_app_files_exist(self):
        self.assertTrue((APP_ROOT / "index.html").exists())
        self.assertTrue((APP_ROOT / "styles.css").exists())
        self.assertTrue((APP_ROOT / "app.js").exists())

    def test_native_app_locks_light_sports_visual_identity(self):
        html = self.read("index.html")
        script = self.read("app.js")
        styles = self.read("styles.css")
        combined = html + script + styles

        self.assertIn("brand-lockup", html)
        self.assertIn("brand-mark", html)
        self.assertIn('data-logo-source="github"', html)
        self.assertIn("color-rail", html + styles)
        for token in ["--red", "--blue", "--green", "--orange", "--purple"]:
            self.assertIn(token, styles)
        for token in ["scoreboard-grid", "business-menu-grid", "personal-workspace-grid", "overview-layout"]:
            self.assertIn(token, html + styles)
        self.assertIn("score-card", script + styles)
        self.assertNotIn("FIFA", combined)
        self.assertNotIn("World Cup", combined)
        self.assertNotIn("background: #000", styles)
        self.assertNotIn("color-scheme: dark", styles)

    def test_native_app_locks_identity_without_user_switching(self):
        html = self.read("index.html")
        script = self.read("app.js")

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
        self.assertIn("AUTH_FLOW_STATES", script)
        self.assertIn("AUTH_FLOW_STEPS", script)
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
        self.assertNotIn("trustedContext.role", script)
        self.assertNotIn("trustedContext.name", script)
        self.assertIn('trustedContext.source === "feishu_webapp_sso"', script)

    def test_native_app_blocks_direct_url_before_identity_injection(self):
        script = self.read("app.js")

        self.assertIn("if (!runtime.is_feishu_workbench_container)", script)
        self.assertLess(script.index("if (!runtime.is_feishu_workbench_container)"), script.index("if (hasInjectedIdentity())"))
        self.assertIn("\\u8bf7\\u4ece\\u98de\\u4e66\\u5de5\\u4f5c\\u53f0\\u6253\\u5f00", script)
        self.assertIn("URL", script)

    def test_native_app_forces_historical_view_as_single_entry(self):
        script = self.read("app.js")
        server = SERVER_PATH.read_text(encoding="utf-8")

        self.assertIn('data.entry !== "historical_view"', script)
        self.assertIn("renderHistoricalViewOS(runtimeHome)", script)
        self.assertIn("historicalViewRenderer(runtimeHome)", script)
        self.assertIn("historical_view_single_entry", script)
        self.assertIn("historical_view.py -> timeline -> replay -> trace_chain -> task_evolution", script)
        self.assertIn('"entry"] = "historical_view"', server)
        self.assertIn('"home_type"] = "historical_first_operating_interface"', server)
        self.assertIn('"single_entry_point": True', server)

        render_body = script.split("function render(runtimeHome = null)", 1)[1].split("function renderHistoricalLoadError", 1)[0]
        self.assertIn("renderHistoricalViewOS(runtimeHome)", render_body)
        self.assertNotIn("renderMasterControlOS", render_body)
        self.assertNotIn("renderSingleUserBusinessOS", render_body)

    def test_historical_home_contains_required_views(self):
        script = self.read("app.js")

        for token in ["时间轴", "业务回放", "数据追溯链", "任务演化流", "BOSS历史分析"]:
            self.assertIn(token, script)
        for token in ["historicalReplayCards", "historicalRiskCards", "historicalTaskEvolutionPanels", "historicalOverview"]:
            self.assertIn(token, script)
        self.assertIn("sourceEvidenceGroup(\"历史时间轴\"", script)
        self.assertIn("sourceEvidenceGroup(\"数据追溯链\"", script)
        self.assertIn("sourceEvidenceGroup(\"任务演化流\"", script)
        self.assertIn("completion_log", script)
        self.assertIn("stage_sequence", script)
        self.assertIn("trace_chain", script)

    def test_dashboard_and_workspace_are_secondary_modules_only(self):
        server = SERVER_PATH.read_text(encoding="utf-8")

        self.assertIn("secondary_modules", server)
        self.assertIn('"dashboard": compact_home.get("business_dashboard")', server)
        self.assertIn('"workspace_detail": compact_home.get("sections")', server)
        self.assertIn('"schema_ui": {"visibility": "debug_only"}', server)
        self.assertIn('"dashboard_first_screen_allowed": False', server)
        self.assertIn('"schema_first_screen_allowed": False', server)

    def test_native_app_uses_runtime_home_endpoint_without_demo_state(self):
        script = self.read("app.js")
        runtime_config = self.read("oms-config.js")

        self.assertIn("OMS_HOME_ENDPOINT", runtime_config)
        self.assertIn("trycloudflare.com/api/oms/home", runtime_config)
        self.assertNotIn("description-toronto-causing-default", runtime_config)
        self.assertNotIn("127.0.0.1:8787/api/oms/home", runtime_config)
        self.assertIn("function fetchRuntimeHome", script)
        self.assertIn("runtime_home_endpoint_", script)
        self.assertIn("runtime_home_invalid_payload", script)
        self.assertIn("runtime_home_not_local_live_runtime", script)
        self.assertIn("function isLocalRuntimeHome", script)
        self.assertIn("local_live_runtime", script + runtime_config)
        self.assertIn("single_source_of_truth", script)
        self.assertIn("OMS_RUNTIME_SOURCE", runtime_config)
        self.assertIn("OMS_LIVE_RUNTIME_ROOT", runtime_config)
        self.assertIn("OMS_REMOTE_DATA_GENERATION_ALLOWED = false", runtime_config)
        self.assertIn("renderHistoricalLoadError", script)
        self.assertIn("historicalEmptyPayload", script)
        self.assertNotIn('renderRuntimeDataBlock("runtime_home_missing")', script)
        self.assertNotIn("renderRuntimeDataBlock(errorMessage(error))", script)
        self.assertNotIn("makeItems", script)


if __name__ == "__main__":
    unittest.main()
