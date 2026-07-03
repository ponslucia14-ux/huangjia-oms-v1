import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "oms_app"


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
        self.assertIn("background: var(--bg)", styles)
        self.assertNotIn("FIFA", combined)
        self.assertNotIn("World Cup", combined)
        self.assertNotIn("background: #000", styles)
        self.assertNotIn("color-scheme: dark", styles)

    def test_native_app_is_single_user_business_os(self):
        html = self.read("index.html")
        script = self.read("app.js")
        combined = html + script

        self.assertIn("OMS Single User Business OS", html)
        self.assertIn("personalWorkspacePanels", combined)
        self.assertIn("sourceEvidenceRecords", combined)
        self.assertIn("businessMenu", combined)
        self.assertIn("sideBusinessMenu", combined)
        self.assertIn("renderSingleUserBusinessOS(runtimeHome)", script)
        self.assertIn("single_user_business_os", script)
        self.assertNotIn("workspaceCards", combined)
        self.assertNotIn("sideWorkspaceList", combined)
        self.assertNotIn("workspace-grid-v11", html + self.read("styles.css"))
        self.assertNotIn("workspaceCardTemplate", script)
        self.assertNotIn("sideWorkspaceTemplate", script)
        self.assertNotIn("renderOperatingCenterV11", script)

    def test_native_app_has_fixed_business_second_level_menu(self):
        script = self.read("app.js")
        html = self.read("index.html")

        self.assertIn("const BUSINESS_MENU", script)
        expected_sequence = [
            'key: "resident"',
            'key: "finance"',
            'key: "sales"',
            'key: "service"',
            'key: "hr"',
        ]
        last_index = -1
        for item in expected_sequence:
            current_index = script.index(item)
            self.assertGreater(current_index, last_index)
            last_index = current_index

        for token in ["resident_flow_schema", "finance_schema", "sales_schema", "service_schema", "hr_schema"]:
            self.assertIn(token, script)
        self.assertIn("房态 / 财务 / 销售 / 服务 / 人效", html)
        self.assertIn("schemaBusinessMenu", script)
        self.assertIn("businessMenuCardTemplate", script)

    def test_native_app_uses_required_dashboard_metrics(self):
        combined = "\n".join([self.read("index.html"), self.read("app.js")])

        for text in ["房态", "财务", "销售", "服务", "人效"]:
            self.assertIn(text, combined)
        for text in ["resident_flow_schema", "finance_schema", "sales_schema", "service_schema", "hr_schema"]:
            self.assertIn(text, combined)
        for text in ["\\u5728\\u4f4f / \\u5165\\u4f4f / \\u51fa\\u9986", "\\u6536\\u5165 / \\u5e94\\u6536 / \\u5229\\u6da6", "\\u7ebf\\u7d22 / \\u7b7e\\u7ea6 / \\u8f6c\\u5316", "\\u5165\\u4f4f / \\u670d\\u52a1\\u4e2d / \\u5b8c\\u6210", "\\u5728\\u5c97 / \\u6392\\u73ed / \\u7ee9\\u6548"]:
            self.assertIn(text, combined)
        for text in ["schemaDrivenRenderer", "componentTree", "Schema Renderer", "我的待办"]:
            self.assertIn(text, combined)

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
        script = self.read("app.js")

        self.assertIn("trustedContext.user_id", script)
        self.assertIn("trustedContext.open_id", script)
        self.assertIn("trustedContext.union_id", script)
        self.assertIn('trustedContext.source === "feishu_webapp_sso"', script)
        self.assertIn("renderIdentityError", script)
        self.assertIn("renderRuntimeContextBlock", script)
        self.assertIn("prepareFullSchemaRepaint", script)
        self.assertIn("clearSchemaRenderTargets", script)
        self.assertIn("markSchemaRenderComplete", script)
        self.assertIn("SCHEMA_RENDER_TARGETS", script)
        self.assertIn("schemaRenderSequence", script)
        self.assertNotIn("restoreWorkspaceShell", script)
        self.assertNotIn("initialShell", script)
        self.assertIn("dataset.schemaRenderId", script)
        self.assertIn("dataset.renderState", script)
        self.assertIn("window.location.reload()", script)
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
        script = self.read("app.js")

        self.assertIn("if (!runtime.is_feishu_workbench_container)", script)
        self.assertLess(script.index("if (!runtime.is_feishu_workbench_container)"), script.index("if (hasInjectedIdentity())"))
        self.assertIn("\\u8bf7\\u4ece\\u98de\\u4e66\\u5de5\\u4f5c\\u53f0\\u6253\\u5f00", script)
        self.assertIn("URL", script)

    def test_native_app_routes_to_personal_workspace_after_auth_success(self):
        script = self.read("app.js")

        self.assertIn("window.OMS_USER_CONTEXT = payload", script)
        self.assertIn('authenticatedIdentity.bindingStatus !== "ready"', script)
        self.assertIn('currentWorkspace = identity.bindingStatus === "ready" ? workspaceData[identity.workspaceKey] : null', script)
        self.assertIn('identity = identityBindingError("workspace_route_not_found_after_auth"', script)
        self.assertIn("fetchRuntimeHome(authConfig().homeEndpoint, identity)", script)
        self.assertIn("render(runtimeHome)", script)
        self.assertIn("renderSingleUserBusinessOS(runtimeHome)", script)
        self.assertLess(script.index("fetchRuntimeHome(authConfig().homeEndpoint, identity)"), script.index("render(runtimeHome)"))

    def test_native_app_forces_runtime_home_data_not_demo_state(self):
        script = self.read("app.js")
        runtime_config = self.read("oms-config.js")

        self.assertIn("OMS_HOME_ENDPOINT", runtime_config)
        self.assertIn("https://description-toronto-causing-default.trycloudflare.com/api/oms/home", runtime_config)
        self.assertNotIn("127.0.0.1:8787/api/oms/home", runtime_config)
        self.assertIn("function fetchRuntimeHome", script)
        self.assertIn('"runtime_home_missing"', script)
        self.assertIn("runtime_home_endpoint_", script)
        self.assertIn("runtime_home_invalid_payload", script)
        self.assertIn("buildUsableRuntimeHome", script)
        self.assertIn("soft_validation_mode", script)
        self.assertIn("always_render_with_warning", script)
        self.assertIn("empty_placeholder", script)
        self.assertNotIn('renderRuntimeDataBlock("runtime_home_missing")', script)
        self.assertNotIn("renderRuntimeDataBlock(errorMessage(error))", script)
        self.assertNotIn("makeItems", script)

    def test_native_app_derives_ui_from_business_schema_and_truth_lock(self):
        script = self.read("app.js")

        self.assertIn("schemaDrivenRenderer", script)
        self.assertIn("prepareFullSchemaRepaint", script)
        self.assertIn("markSchemaRenderComplete", script)
        self.assertIn("replaceChildren", script)
        self.assertIn("dataset.renderPipeline", script)
        self.assertIn("dataset.renderState", script)
        self.assertIn("requireBusinessSchema", script)
        self.assertIn("requireDataTruthLock", script)
        self.assertIn("requireSourceEvidenceVerifiedData", script)
        self.assertIn("source_evidence_soft_label", script)
        self.assertIn("source_evidence_available_data", script)
        self.assertIn("always_render_with_confidence_label", script)
        self.assertIn("confidenceLabel", script)
        self.assertIn("uncalibrated_warning", script)
        self.assertNotIn("throw new Error(\"data_truth_alignment_required\")", script)
        self.assertNotIn("throw new Error(\"source_evidence_verified_data_required\")", script)
        self.assertIn("schemaScoreboard", script)
        self.assertIn("schemaOverview", script)
        self.assertIn("schemaPriorityCards", script)
        self.assertIn("schemaBusinessMenu", script)
        self.assertIn("schemaWorkspacePanels", script)
        self.assertIn("schemaSourceEvidence", script)
        self.assertIn("sourceEvidenceGroupTemplate", script)
        self.assertIn("sourceRecordTemplate", script)
        self.assertIn("business_schema", script)
        self.assertIn("semantic_status", script)
        self.assertIn("EMPTY_BUSINESS_SCHEMA", script)
        self.assertNotIn("throw new Error(\"business_schema_required\")", script)
        self.assertNotIn("return dashboard.metrics || {}", script)
        self.assertNotIn("runtimeScoreboard", script)
        self.assertNotIn("runtimeOverview", script)
        self.assertNotIn("runtimeQuickLinks", script)
        self.assertNotIn("OMS runtime", script)
        self.assertNotIn("live_runtime", script)

    def test_native_app_loads_feishu_h5_sdk_and_runtime_config(self):
        html = self.read("index.html")
        script = self.read("app.js")
        runtime_config = self.read("oms-config.js")
        sample_config = self.read("oms-config.sample.js")

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
        self.assertIn("https://description-toronto-causing-default.trycloudflare.com/api/feishu/identity", runtime_config)
        self.assertIn("https://description-toronto-causing-default.trycloudflare.com/api/oms/home", runtime_config)
        self.assertNotIn("127.0.0.1:8787", runtime_config)
        self.assertIn("https://ponslucia14-ux.github.io/huangjia-oms-v1/", runtime_config)
        self.assertIn("cli_aaac7e6da2b95cfc", runtime_config)
        self.assertIn("OMS_FEISHU_APP_ID", sample_config)
        self.assertIn("OMS_FEISHU_SCOPE_LIST", sample_config)
        self.assertIn("OMS_AUTH_ENDPOINT", sample_config)
        self.assertIn("OMS_HOME_ENDPOINT", sample_config)
        self.assertNotIn("localhost", runtime_config + sample_config + script)
        self.assertNotIn("auth/callback", runtime_config + sample_config + script)
        self.assertNotIn("index.html", runtime_config + sample_config)

    def test_native_app_does_not_expose_backend_layer_names(self):
        combined = "\n".join([self.read("index.html"), self.read("app.js")])

        self.assertNotIn("business_layer", combined)
        self.assertNotIn("support_layer", combined)
        self.assertNotIn("system_capability_layer", combined)
        self.assertNotIn("operating_center_structure", combined)


if __name__ == "__main__":
    unittest.main()
