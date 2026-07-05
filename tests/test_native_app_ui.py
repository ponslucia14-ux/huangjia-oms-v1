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
        for token in ["product-home-block", "home-data-strip", "business-menu-grid", "personal-workspace-grid"]:
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

    def test_home_is_locked_to_real_time_operational_dashboard(self):
        html = self.read("index.html")
        script = self.read("app.js")
        server = SERVER_PATH.read_text(encoding="utf-8")

        self.assertIn('data.entry === "personal_workspace"', script)
        self.assertIn('data.entry === "master_control_dashboard"', script)
        self.assertIn("renderSingleUserBusinessOS(runtimeHome)", script)
        self.assertIn("renderMasterControlOS(runtimeHome)", script)
        self.assertIn("现在正在发生什么", script)
        self.assertIn("实时经营", script)
        self.assertIn("todayWorkSection", html)
        self.assertIn("businessFlowSection", html)
        self.assertIn("riskExceptionSection", html)
        self.assertIn("HOME", html + script)
        for label in ["工作", "业务", "风险", "数据"]:
            self.assertIn(label, html + script)
        for removed_entry in ["workspace-section", "source-evidence-section", "overview-band", "overviewGrid", "quickLinks"]:
            self.assertNotIn(removed_entry, html)
        self.assertIn('self._send_json({"ok": True, "data": self._compact_home_payload(home)})', server)
        self.assertNotIn("_historical_home_payload", server)
        self.assertNotIn("historical_first_operating_interface", server)

        render_body = script.split("function render(runtimeHome = null)", 1)[1].split("function prepareFullSchemaRepaint", 1)[0]
        self.assertIn("renderSingleUserBusinessOS(runtimeHome)", render_body)
        self.assertIn("renderMasterControlOS(runtimeHome)", render_body)
        self.assertNotIn("renderHistoricalViewOS", render_body)
        self.assertNotIn("renderHistoricalLoadError", render_body)

    def test_history_is_on_demand_query_only(self):
        script = self.read("app.js")
        server = SERVER_PATH.read_text(encoding="utf-8")

        self.assertIn('path in {"/api/oms/history", "/history"}', server)
        self.assertIn("def _send_history", server)
        self.assertNotIn('data.entry !== "historical_view"', script)
        self.assertNotIn("renderHistoricalLoadError", script)
        self.assertNotIn("sourceEvidence.historical_timeline", script)

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
        self.assertIn("buildUsableRuntimeHome(errorMessage(error))", script)
        self.assertNotIn('renderRuntimeDataBlock("runtime_home_missing")', script)
        self.assertNotIn("renderRuntimeDataBlock(errorMessage(error))", script)
        self.assertNotIn("makeItems", script)

    def test_daily_workbench_remains_task_first_product_ui(self):
        script = self.read("app.js")

        self.assertIn("dailyWorkbenchLogicLayerRenderer", script)
        self.assertIn("dailyWorkbenchLogicLayer", script)
        self.assertIn("single_entry_home -> today_work -> business_flow -> risk_exception", script)
        for key in ['key: "home"', 'key: "work"', 'key: "business"', 'key: "risk"', 'key: "data"']:
            self.assertIn(key, script)
        self.assertIn("productDataStrip", script)
        for token in ["schema_view", "runtime_view"]:
            self.assertNotIn(token, script)


if __name__ == "__main__":
    unittest.main()
