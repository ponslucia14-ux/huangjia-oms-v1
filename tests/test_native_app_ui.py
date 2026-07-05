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
        self.assertIn("我现在应该做什么？", html)
        self.assertIn("Action｜要做什么", html)
        self.assertIn("Status｜现在发生什么", html)
        self.assertIn("Risk｜哪里有问题", html)
        self.assertIn("\\u73b0\\u5728\\u53d1\\u751f\\u4ec0\\u4e48", script)
        self.assertIn("todayWorkSection", html)
        self.assertIn("businessFlowSection", html)
        self.assertIn("riskExceptionSection", html)
        self.assertIn("HOME", html + script)
        for label in ["Action", "Status", "Risk"]:
            self.assertIn(label, html + script)
        for technical_label in ["business_schema", "runtime", "workflow", "event", "schema_view", "runtime_view"]:
            self.assertNotIn(technical_label, html)
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
        for key in ['key: "home"', 'key: "action"', 'key: "status"', 'key: "risk"']:
            self.assertIn(key, script)
        for removed_key in ['key: "work"', 'key: "business"', 'key: "data"']:
            self.assertNotIn(removed_key, script)
        self.assertIn("productDataStrip", script)
        self.assertIn('traceChainRow("\\u6765\\u6e90\\u6587\\u4ef6"', script)
        self.assertIn('traceChainRow("\\u8868\\u683c\\u884c"', script)
        self.assertNotIn('traceChainRow("business_event_id"', script)
        self.assertNotIn('traceChainRow("workflow_task_id"', script)
        self.assertNotIn('traceChainRow("hr_execution_id"', script)
        for token in ["schema_view", "runtime_view"]:
            self.assertNotIn(token, script)

    def test_product_closure_humanizes_data_and_makes_cards_actionable(self):
        script = self.read("app.js")
        styles = self.read("styles.css")
        combined = script + styles

        for token in ["humanWorkCount", "humanRiskCount", "humanPanelCount", "workActionButton", "handleWorkActionClick"]:
            self.assertIn(token, script)
        for label in ["开始处理", "查看详情", "处理风险", "追踪来源"]:
            self.assertIn(label, script)
        for token in ["data-work-action", "clickable-card", "is-selected-action"]:
            self.assertIn(token, combined)
        self.assertIn("已选择", combined)
        self.assertIn("\\u4eca\\u5929\\u8981\\u505a", script)
        self.assertIn("\\u73b0\\u5728\\u53d1\\u751f\\u4ec0\\u4e48", script)
        self.assertIn("\\u54ea\\u91cc\\u6709\\u95ee\\u9898", script)

        for raw_counter in ["9749", "8765"]:
            self.assertNotIn(raw_counter, script)
        for system_counter_pattern in [
            "String(globalView.task_count || execution.total || 0)",
            "String(globalView.unfinished_task_count || execution.unfinished || 0)",
            "String(risk.risk_count || 0)",
            "value: String(count)",
            "Number(item.value)",
            "全部任务",
            "全部风险",
            "Layer 1:",
            "Layer 2:",
            "Layer 3:",
        ]:
            self.assertNotIn(system_counter_pattern, script)

    def test_interaction_layer_routes_state_and_api_bridge_are_active(self):
        html = self.read("index.html")
        script = self.read("app.js")
        styles = self.read("styles.css")
        combined = script + styles

        for token in [
            "interactionState",
            "selected_task",
            "current_room",
            "active_workflow",
            "handleWorkNavigationClick",
            "handleWorkRouteChange",
            "routeForAction",
            "actionDisplayLabel",
            "navigateToWorkRoute",
            "parseWorkRoute",
            "renderInteractionPanel",
            "restoreSelectedActionCard",
            "triggerInteractionApiBridge",
            "OMS_BOOT_CHAIN_STEPS",
            "markBootChainStep",
            "syncInteractionDebugState",
            "bootOmsFrontend",
            "mountOmsFrontend",
        ]:
            self.assertIn(token, script)

        self.assertIn('id="omsAppScript"', html)
        self.assertIn('data-entry-file="app.js"', html)
        self.assertIn("omsAppScript='loaded'", html)
        self.assertIn('window.addEventListener("hashchange", handleWorkRouteChange)', script)
        self.assertIn('document.addEventListener("click", handleWorkActionClick, true)', script)
        self.assertIn('document.addEventListener("DOMContentLoaded", mountOmsFrontend, { once: true })', script)
        self.assertIn("fetchRuntimeHome(endpoint, identity)", script)
        self.assertIn("window.OMS_BOOT_STATE", script)
        self.assertIn("window.OMS_INTERACTION_STATE", script)
        self.assertIn("document.documentElement.dataset.workRoute", script)
        self.assertIn("document.documentElement.dataset.omsJsBoot", script)
        self.assertIn("document.documentElement.dataset.omsEventBinding", script)
        self.assertIn("document.documentElement.dataset.omsRouter", script)
        self.assertIn("document.documentElement.dataset.omsStateLayer", script)
        self.assertIn("api_status", script)
        self.assertIn("interactionDetailPanel", script)
        self.assertIn("interaction-detail-panel", combined)
        self.assertIn("interaction-state-grid", combined)
        self.assertIn("interaction-action-row", combined)
        for route in ['"action"', '"status"', '"risk"', '"room"', '"finance"', '"sales"', '"data"']:
            self.assertIn(route, script)


if __name__ == "__main__":
    unittest.main()
