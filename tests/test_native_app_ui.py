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
        self.assertIn('response_id="oms.home"', server)
        self.assertIn('contract_status="ready"', server)
        self.assertIn("payload=self._compact_home_payload(home)", server)
        self.assertNotIn("_historical_home_payload", server)
        self.assertNotIn("historical_first_operating_interface", server)

        render_body = script.split("function render(runtimeHome = null)", 1)[1].split("function prepareFullSchemaRepaint", 1)[0]
        self.assertIn("renderSingleUserBusinessOS(contractRuntimeHome)", render_body)
        self.assertIn("renderMasterControlOS(contractRuntimeHome)", render_body)
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
        self.assertIn("OMS_CONTRACT_VERSION", runtime_config)
        self.assertIn("oms.contract.v1.0", runtime_config)
        self.assertIn("OMS_CONTRACT_URL", runtime_config)
        self.assertIn("contract.json", runtime_config)
        self.assertIn("trycloudflare.com/api/oms/home", runtime_config)
        self.assertNotIn("description-toronto-causing-default", runtime_config)
        self.assertNotIn("127.0.0.1:8787/api/oms/home", runtime_config)
        self.assertIn("function fetchRuntimeHome", script)
        self.assertIn("function unwrapContractPayload", script)
        self.assertIn("async function ensureContractLayerLoaded", script)
        self.assertIn("function validateContractLayer", script)
        self.assertIn("function mapPayloadThroughContract", script)
        self.assertIn("function requireContractMappedRuntimeHome", script)
        self.assertIn("function validateUiVsContractPayload", script)
        self.assertIn("function renderContractError", script)
        self.assertIn("responsePayload.source === \"OMS_TRUTH_SOURCE\"", script)
        self.assertIn("Object.prototype.hasOwnProperty.call(responsePayload, \"payload\")", script)
        self.assertIn("contract.json -> UI render engine -> DOM", script)
        self.assertIn("contract_navigation_tree_missing", script)
        self.assertIn("contract_mapping_missing", script)
        self.assertIn("runtime_home_endpoint_", script)
        self.assertIn("runtime_home_invalid_payload", script)
        self.assertIn("runtime_home_not_oms_truth_source", script)
        self.assertIn("function isTruthSourceHome", script)
        self.assertIn("OMS_TRUTH_SOURCE", script + runtime_config)
        self.assertIn("single_source_of_truth", script)
        self.assertIn("OMS_RUNTIME_SOURCE", runtime_config)
        self.assertIn("OMS_TRUTH_SOURCE_ROOT", runtime_config)
        self.assertIn("OMS_LIVE_RUNTIME_ROOT", runtime_config)
        self.assertIn("OMS_REMOTE_DATA_GENERATION_ALLOWED = false", runtime_config)
        self.assertIn("renderContractError(`contract_runtime_fetch_failed:${errorMessage(error)}`)", script)
        self.assertIn("renderContractError(`contract_boot_failed:${errorMessage(error)}`)", script)
        self.assertNotIn("function buildUsableRuntimeHome", script)
        self.assertNotIn("function emptyWorkspaceSections", script)
        self.assertNotIn("render(buildUsableRuntimeHome(errorMessage(error)))", script)
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
        for navigation_key in ['key: "work"', 'key: "business"', 'key: "data"']:
            self.assertIn(navigation_key, script)
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
            "executeBusinessAction",
            "execution_status",
            "closure_status",
            "execution_trace_id",
            "state_update_id",
            "business_state_status",
            "businessStateText",
            "decision_summary",
            "retrigger_status",
            "retriggerActionLabel",
            "retriggerStatusText",
            "lifecycle_stage",
            "lifecycle_status",
            "lifecycleStatusText",
            "OMS_BOOT_CHAIN_STEPS",
            "markBootChainStep",
            "syncInteractionDebugState",
            "bootOmsFrontend",
            "mountOmsFrontend",
            "NAVIGATION_MENU_TREE",
            "initializeRouter",
            "mountMenuTree",
            "bindMenuTreeClick",
            "handleNavigationMenuClick",
            "navigationState",
            "OMS_NAVIGATION_STATE",
            "OMS_CONTRACT_STATE",
            "OMS_UI_CHAIN_STATE",
            "contractNavigationTree",
            "applyContractRenderMetadata",
            "validateComponentTreeAgainstContract",
            "validateEndToEndUiChain",
            "updateUiChainStep",
            "syncUiChainDebugState",
            "blockUiChain",
            "FINAL_RENDER_SINK",
            "OMS_FINAL_RENDER_STATE",
            "buildFinalRenderSnapshot",
            "enqueueFinalRender",
            "commitFinalRenderQueue",
            "validateFinalRenderSnapshot",
            "diffFinalRenderSnapshot",
            "commitFinalRenderSnapshot",
            "commitFinalRenderPatch",
            "syncFinalRenderDebugState",
        ]:
            self.assertIn(token, script)

        self.assertIn('id="omsAppScript"', html)
        self.assertIn('data-entry-file="app.js"', html)
        self.assertIn("omsAppScript='loaded'", html)
        self.assertIn('window.addEventListener("hashchange", handleWorkRouteChange)', script)
        self.assertIn('document.addEventListener("click", handleWorkActionClick, true)', script)
        self.assertIn('document.addEventListener("DOMContentLoaded", mountOmsFrontend, { once: true })', script)
        self.assertIn("fetchRuntimeHome(config.homeEndpoint, identity)", script)
        self.assertIn("executeBusinessAction(config.executeEndpoint, identity)", script)
        self.assertIn("window.OMS_EXECUTE_ENDPOINT", self.read("oms-config.js"))
        self.assertIn("trycloudflare.com/api/oms/execute", self.read("oms-config.js"))
        self.assertIn("window.OMS_BOOT_STATE", script)
        self.assertIn("window.OMS_INTERACTION_STATE", script)
        self.assertIn("document.documentElement.dataset.omsExecutionStatus", script)
        self.assertIn("document.documentElement.dataset.omsClosureStatus", script)
        self.assertIn("document.documentElement.dataset.omsBusinessStateStatus", script)
        self.assertIn("document.documentElement.dataset.omsDecisionSummary", script)
        self.assertIn("document.documentElement.dataset.omsRetriggerStatus", script)
        self.assertIn("document.documentElement.dataset.omsLifecycleStage", script)
        self.assertIn("document.documentElement.dataset.omsLifecycleStatus", script)
        self.assertIn("document.documentElement.dataset.workRoute", script)
        self.assertIn("document.documentElement.dataset.omsJsBoot", script)
        self.assertIn("document.documentElement.dataset.omsEventBinding", script)
        self.assertIn("document.documentElement.dataset.omsRouter", script)
        self.assertIn("document.documentElement.dataset.omsStateLayer", script)
        self.assertIn("document.documentElement.dataset.omsNavigation", script)
        self.assertIn("document.documentElement.dataset.omsContractLayer", script)
        self.assertIn("document.documentElement.dataset.omsContractRender", script)
        self.assertIn("document.documentElement.dataset.omsUiChain", script)
        self.assertIn("document.documentElement.dataset.omsFinalRender", script)
        self.assertIn("document.documentElement.dataset.omsFinalRenderVersion", script)
        self.assertIn("document.documentElement.dataset.omsFinalRenderLocked", script)
        self.assertIn("data -> behavior -> display", script)
        self.assertIn("data -> diff -> commit -> render -> commit DOM", script)
        self.assertIn('target.dataset.renderSource = "contract.json"', script)
        self.assertIn("target.dataset.renderState = \"committed\"", script)
        self.assertIn("missing_interaction", script)
        self.assertIn("empty_dom", script)
        self.assertIn("ui_chain_diff", script)
        self.assertIn('data-nav-route', script)
        self.assertIn('data-nav-key', script)
        self.assertIn("api_status", script)
        self.assertIn("interactionDetailPanel", script)
        self.assertIn("interaction-detail-panel", combined)
        self.assertIn("interaction-state-grid", combined)
        self.assertIn("interaction-action-row", combined)
        self.assertIn("execution-closure-result", combined)
        self.assertIn("lifecycle-closure-panel", combined)
        self.assertIn("decision-explainability-panel", combined)
        self.assertIn("businessStateText", script)
        self.assertIn("decisionChain", script)
        self.assertIn("retriggerClosure", script)
        self.assertIn("navigation-menu-node", combined)
        self.assertIn("navigation-submenu", combined)
        for route in ['"action"', '"status"', '"risk"', '"room"', '"finance"', '"sales"', '"service"', '"hr"', '"data"']:
            self.assertIn(route, script)

    def test_final_render_sink_replaces_direct_main_dom_writes(self):
        script = self.read("app.js")
        render_single = script.split("function renderSingleUserBusinessOS(runtimeHome)", 1)[1].split("function bindWorkActionFeedback", 1)[0]
        render_master = script.split("function renderMasterControlOS(runtimeHome)", 1)[1].split("function masterControlLayerRenderer", 1)[0]

        self.assertIn("return buildFinalRenderSnapshot(runtimeHome, componentTree, \"single_user\")", render_single)
        self.assertIn("return buildFinalRenderSnapshot(runtimeHome, componentTree, \"master_control\")", render_master)
        self.assertNotIn("setHTML(", render_single + render_master)
        self.assertNotIn(".innerHTML", render_single + render_master)
        self.assertNotIn(".textContent", render_single + render_master)
        self.assertNotIn("function setHTML", script)
        self.assertIn("FINAL_RENDER_SINK.queue = [snapshot]", script)
        self.assertIn("FINAL_RENDER_SINK.locked = true", script)
        self.assertIn("snapshot.hash = finalRenderSnapshotHash(snapshot)", script)


if __name__ == "__main__":
    unittest.main()
