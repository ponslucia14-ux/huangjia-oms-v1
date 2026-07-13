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
        self.assertTrue((APP_ROOT / "oms-config.dev.js").exists())
        self.assertTrue((APP_ROOT / "oms-config.prod.js").exists())
        self.assertTrue((APP_ROOT / "assets" / "huangjia-operations-brand.png").exists())
        self.assertTrue((APP_ROOT / "assets" / "emp001-boss-avatar.jpg").exists())
        self.assertTrue((APP_ROOT / "assets" / "emp008-liufangyu-avatar.jpg").exists())
        self.assertTrue((APP_ROOT / "workspace-profiles.js").exists())
        for avatar in [
            "emp002-zonghui-avatar.jpg",
            "emp003-zhangjingdong-avatar.jpg",
            "emp004-liujing-avatar.jpg",
            "emp005-shihaoxin-avatar.jpg",
            "emp006-yanghuanhuan-avatar.jpg",
            "emp007-xueziyu-avatar.jpg",
            "emp009-shanglina-avatar.jpg",
            "emp010-chenjinghui-avatar.jpg",
            "emp011-zhouzhipeng-avatar.jpg",
        ]:
            self.assertTrue((APP_ROOT / "assets" / avatar).exists(), avatar)

    def test_native_app_locks_light_sports_visual_identity(self):
        html = self.read("index.html")
        script = self.read("app.js")
        styles = self.read("styles.css")
        combined = html + script + styles

        self.assertIn("brand-lockup", html)
        self.assertIn("brand-mark", html)
        self.assertIn("./assets/huangjia-operations-brand.png", html)
        self.assertIn('alt="凰家运营中心"', html)
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
        self.assertIn("./assets/emp001-boss-avatar.jpg", html)
        self.assertIn("lockedUserRole", html)
        self.assertIn("currentOperationsPanel", html)
        self.assertIn("resolveLockedIdentity", script)
        self.assertIn("bootstrapIdentity", script)
        self.assertIn("feishuRuntimeContext", script)
        self.assertIn("isFeishuClient", script)
        self.assertIn("isLarkWebView", script)
        self.assertIn("isFeishuWorkbenchContainer", script)
        self.assertIn("requestFeishuAuthCode", script)
        self.assertIn("requestLocalOwnerAccess", script)
        self.assertIn("handleCurrentOperationSubmit", script)
        self.assertIn("/api/oms/current/finance/record", script)
        self.assertIn("/api/oms/current/rooms/publish", script)
        self.assertIn("/api/oms/current/stays/publish", script)
        self.assertIn("requestAccess", script)
        self.assertIn("requestLegacyFeishuAuthCode", script)
        self.assertIn("requestAuthCode", script)
        self.assertIn("shouldUseLegacyFeishuAuthCode", script)
        self.assertIn("AUTH_FLOW_STATES", script)
        self.assertIn("AUTH_FLOW_STEPS", script)
        self.assertIn("OMS_FEISHU_USER_WORKSPACE_MAP", script)
        self.assertIn("OMS_LOCAL_OWNER_ACCESS_ENABLED", self.read("oms-config.js"))
        self.assertIn("OMS_LOCAL_OWNER_ACCESS_ENDPOINT", self.read("oms-config.js"))
        self.assertIn("feishu_user_id_only", script)
        self.assertIn("not_feishu_runtime_context", script)
        self.assertNotIn("userSelect", html + script)
        self.assertNotIn("<select", html)
        self.assertNotIn("<option", html)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("sessionStorage", script)
        self.assertIn("new URLSearchParams(window.location.search)", script)
        self.assertIn("OMS_WORKSPACE_PREVIEW_ENABLED", script)
        self.assertIn('environment === "development"', self.read("oms-config.js"))
        self.assertIn("workspacePreviewEnabled: false", self.read("oms-config.prod.js"))
        self.assertNotIn("trustedContext.role", script)
        self.assertNotIn("trustedContext.name", script)
        self.assertIn('["feishu_webapp_sso", "local_owner_access"].includes(trustedSource)', script)

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
        self.assertIn("今日工作", html)
        self.assertIn("经营状态", html)
        self.assertIn("风险异常", html)
        self.assertIn("\\u73b0\\u5728\\u53d1\\u751f\\u4ec0\\u4e48", script)
        self.assertIn("todayWorkSection", html)
        self.assertIn("businessFlowSection", html)
        self.assertIn("riskExceptionSection", html)
        for label in ["首页", "销售经营", "资金经营", "运营经营", "组织执行", "审计追溯"]:
            self.assertIn(label, html + script)
        profiles = self.read("workspace-profiles.js")
        self.assertIn("尚未初始化", script + profiles)
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
        development_config = self.read("oms-config.dev.js")
        production_config = self.read("oms-config.prod.js")

        self.assertIn("OMS_HOME_ENDPOINT", runtime_config)
        self.assertIn("OMS_CONTRACT_VERSION", runtime_config)
        self.assertIn("oms.contract.v1.0", runtime_config)
        self.assertIn("OMS_CONTRACT_URL", runtime_config)
        self.assertIn("contract.json", runtime_config)
        self.assertIn('apiBaseUrl: "http://127.0.0.1:8787"', development_config)
        self.assertIn('apiBaseUrl: "https://api.wonderfulseki.cn"', production_config)
        self.assertIn("`${apiBaseUrl}/api/oms/home`", runtime_config)
        self.assertIn("`${apiBaseUrl}/api/oms/local-owner-access`", runtime_config)
        self.assertNotIn("127.0.0.1", production_config)
        self.assertNotIn("localhost", production_config)
        self.assertNotIn("description-toronto-causing-default", runtime_config)
        self.assertNotIn("trycloudflare.com/api/oms/home", runtime_config)
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
        self.assertIn('traceRequiredRow("\\u6765\\u6e90\\u6587\\u4ef6"', script)
        self.assertIn('traceRequiredRow("\\u8868\\u683c\\u884c"', script)
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
        self.assertIn('apiBaseUrl: "http://127.0.0.1:8787"', self.read("oms-config.dev.js"))
        self.assertIn("`${apiBaseUrl}/api/oms/execute`", self.read("oms-config.js"))
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

    def test_emp001_workbench_separates_read_only_view_from_execution(self):
        script = self.read("app.js")
        contract = self.read("contract.json")
        styles = self.read("styles.css")

        self.assertIn('if (isExecutionWorkAction(action))', script)
        self.assertIn('data-boss-view-record', script)
        self.assertIn('>查看详情</button>', script)
        self.assertNotIn('workActionButton("查看处理"', script)
        self.assertIn('data-boss-query-form', script)
        self.assertIn('data-boss-page', script)
        self.assertIn('数据健康', script)
        self.assertIn('质量状态', script)
        self.assertIn('boss-center-filter', styles)
        self.assertIn('bossReadOnlyDialog', script)
        self.assertIn('handleBossRecordDetailClick', script)
        self.assertIn('document.addEventListener("click", handleBossRecordDetailClick)', script)
        self.assertIn('data-close-readonly-detail', script)
        self.assertIn('此窗口仅查看，不会修改状态或触发执行', script)
        self.assertIn('traceRequiredRow("工作表"', script)
        self.assertIn('traceRequiredRow("字段"', script)
        self.assertIn('compact-primary-nav', self.read("index.html"))
        self.assertIn('compact-primary-nav', styles)
        self.assertIn('"operations", "organization", "service"', script)
        self.assertIn('organization: "审批与授权"', script)
        self.assertIn('organization: "这里查看今日责任人与尚未闭环的事项"', script)
        self.assertNotIn('"label": "客户跟进"', contract)
        self.assertNotIn('"label": "转化指标"', contract)
        for label in ("签约客户", "合同", "收款状态", "销售结果", "经营指标"):
            self.assertIn(f'"label": "{label}"', contract)

    def test_mobile_workbench_uses_shared_drawer_and_single_column_layout(self):
        html = self.read("index.html")
        script = self.read("app.js")
        styles = self.read("styles.css")

        for element_id in ["mobileMenuButton", "mobileMenuCloseButton", "mobileBackButton", "mobileDrawerBackdrop", "businessNavigationDrawer"]:
            self.assertIn(f'id="{element_id}"', html)
        for function_name in ["bindMobileNavigation", "openMobileNavigation", "closeMobileNavigation", "handleMobileBack", "syncMobileNavigationState"]:
            self.assertIn(f"function {function_name}", script)
        for function_name in ["renderMobileWorkspaceShell", "mobileHomePage", "mobilePrimaryMenuPage", "mobileTaskPage"]:
            self.assertIn(f"function {function_name}", script)
        self.assertIn('id="mobileWorkspaceRoot"', html)
        self.assertIn('"mobile-menu", "mobile-task"', script)
        self.assertIn('level === "parent" ? "mobile-menu" : "mobile-task"', script)
        self.assertIn('closeMobileNavigation();', script)
        self.assertIn('body.mobile-navigation-open .brand-sidebar', styles)
        self.assertIn('transform: translateX(-105%)', styles)
        self.assertIn('.dashboard-main > :not(.mobile-workspace-root)', styles)
        self.assertIn('.brand-sidebar .navigation-submenu', styles)
        self.assertIn('.mobile-secondary-list', styles)
        self.assertIn('grid-template-columns: 1fr', styles)
        self.assertIn('min-height: 44px', styles)
        self.assertEqual(styles.count("{"), styles.count("}"))
        self.assertIn('当前经营数据尚未初始化', script)
        self.assertEqual(script.count("function buildBossCenterPage("), 1)

        owner_tree = script.split("function emp001NavigationTree()", 1)[1].split("function activeNavigationTree()", 1)[0]
        for label in [
            "首页", "今日必须处理", "经营快照", "风险提醒", "资金状态", "在住与房态",
            "待我决策", "待审批", "待授权", "经营异常待决策", "已超时事项", "我的经营指令",
            "经营状态", "销售状态", "运营状态", "在住状态", "房态状态", "人员状态",
            "风险异常", "销售风险", "资金风险", "排房风险", "房态风险", "服务异常", "人员异常", "系统异常",
            "决策追溯", "我的审批", "我的授权", "异常处理结果", "关键数据来源", "历史操作记录",
        ]:
            self.assertIn(label, owner_tree)
        for forbidden in ["销售中心", "财务中心", "运营中心", "审批与授权", "数据追溯", "经营分析助手"]:
            self.assertNotIn(f'label: "{forbidden}"', owner_tree)
        profiles = self.read("workspace-profiles.js")
        self.assertIn("只看、判断、审批、授权和追溯", profiles)
        self.assertIn("不录入销售、财务、入住、房态和排房日常事实", profiles)

    def test_emp008_store_manager_workbench_is_scoped_and_chinese(self):
        html = self.read("index.html")
        script = self.read("app.js")
        profiles = self.read("workspace-profiles.js")

        self.assertNotIn('if (!["boss", "june"].includes(identity.workspaceKey))', script)
        self.assertIn("currentWorkspaceProfile()", script)
        self.assertIn("window.OMS_WORKSPACE_PROFILES", script)
        self.assertIn("workspace-profiles.js", html)
        self.assertIn('function emp008NavigationTree()', script)
        for label in [
            "今日入住与出馆", "待处理房态", "入住与在住", "待确认入住", "当前在住", "入住变更", "出馆确认", "延住处理",
            "房态管理", "房间总览", "调房", "清洁状态", "维修状态", "停用管理",
            "排房管理", "未来排房总览", "六月排房法", "客户入住计划", "房间调整", "冲突检查", "排房记录",
            "我的销售", "我的客户", "我的签约", "我的合同", "我的收款状态", "我的销售业绩", "运营异常", "长时间未处理事项",
        ]:
            self.assertIn(label, profiles + script)
        emp008_tree = script.split("function emp008NavigationTree()", 1)[1].split("function emp001NavigationTree()", 1)[0]
        for forbidden in ["AI", "财务", "历史档案", "经营预测", "办理入住", "办理出馆"]:
            self.assertNotIn(forbidden, emp008_tree)
        self.assertIn('["stay", "room", "allocation", "sales", "operations"]', script)
        self.assertIn("六月排房法当前仅采集真实规则，不进行自动排房", script)
        self.assertIn("尚未初始化", script + profiles)
        self.assertIn("不替管家重复录入已有客户资料", profiles)
        self.assertIn('homeItems: ["今日入住与出馆", "待确认运营事实", "房态与排房", "我的销售待办"]', profiles)
        self.assertIn("emp008-liufangyu-avatar.jpg", profiles)
        self.assertIn('id="compactPrimaryNav"', html)
        self.assertIn('data-current-operation="stay-check-in"', script)
        self.assertIn('data-current-operation="stay-check-out"', script)
        self.assertIn('data-current-operation="room-update"', script)
        current_templates = script.split("function roomAndStayCurrentTemplate()", 1)[1].split("function actualStayRowTemplate", 1)[0]
        self.assertNotIn("办理入住", current_templates)
        self.assertNotIn("办理出馆", current_templates)
        self.assertIn("确认当前入住", current_templates)
        self.assertIn("确认出馆", current_templates)

    def test_all_eleven_workspaces_have_real_pages_identity_and_boundaries(self):
        html = self.read("index.html")
        script = self.read("app.js")
        profiles = self.read("workspace-profiles.js")
        dev_config = self.read("oms-config.dev.js")
        prod_config = self.read("oms-config.prod.js")

        self.assertLess(html.index("workspace-profiles.js"), html.index("app.js?v="))
        for emp_id, name, workspace in [
            ("EMP001", "10晓磊", "boss"),
            ("EMP002", "宗惠", "songxue"),
            ("EMP003", "张敬东", "zhangjie"),
            ("EMP004", "刘晶", "liujie"),
            ("EMP005", "石昊盺", "yaowei"),
            ("EMP006", "杨欢欢", "huanhuan"),
            ("EMP007", "薛子渝", "yuchun"),
            ("EMP008", "刘芳羽", "june"),
            ("EMP009", "尚丽娜", "nana"),
            ("EMP010", "陈晶辉", "chenchangyi"),
            ("EMP011", "周志朋", "zhouchen"),
        ]:
            self.assertIn(f'{workspace}: profile({{', profiles)
            self.assertIn(f'empId: "{emp_id}"', profiles)
            self.assertIn(f'name: "{name}"', profiles)

        server = SERVER_PATH.read_text(encoding="utf-8")
        self.assertIn('"/workspace-profiles.js": "workspace-profiles.js"', server)
        for emp_number in range(2, 12):
            self.assertIn(f'"/assets/emp{emp_number:03d}-', server)

        for token in [
            "desktopWorkspaceMenuTemplate",
            "desktopWorkspaceTaskTemplate",
            "mobilePrimaryMenuPage",
            "mobileTaskPage",
            'route: "workspace"',
            "当前经营数据尚未初始化",
        ]:
            self.assertIn(token, profiles + script)

        for section_label in [
            "行政采购报销",
            "照护师工资",
            "食材采购",
            "我的销售",
            "入住与在住",
        ]:
            self.assertIn(section_label, profiles)

        emp010 = profiles.split("chenchangyi: profile({", 1)[1].split("zhouchen: profile({", 1)[0]
        emp011 = profiles.split("zhouchen: profile({", 1)[1].split("window.OMS_WORKSPACE_PROFILES", 1)[0]
        for readonly_profile in [emp010, emp011]:
            self.assertIn("readOnly: true", readonly_profile)
            for forbidden in ["录入", "提交", "确认", "处理", "审批", "执行", "上报", "补充"]:
                self.assertNotIn(f'access: "{forbidden}"', readonly_profile)

        self.assertIn("workspacePreviewEnabled: true", dev_config)
        self.assertIn("workspacePreviewEnabled: false", prod_config)
        self.assertIn("applyLocalWorkspacePreview()", script)
        self.assertIn('["localhost", "127.0.0.1", "::1"]', script)


if __name__ == "__main__":
    unittest.main()
