const SOURCE_OF_TRUTH = "凰家运营中心（OMS）V1.1";
const SINGLE_IDENTITY_POLICY = "feishu_user_id_only";
const DEFAULT_FEISHU_APP_ID = "cli_aaac7e6da2b95cfc";
const CANONICAL_FEISHU_REDIRECT_URI = "https://ponslucia14-ux.github.io/huangjia-oms-v1/";
const FEISHU_OAUTH_REDIRECT_WHITELIST = Object.freeze([
  "https://ponslucia14-ux.github.io/huangjia-oms-v1/",
]);
const FEISHU_LOGIN_SCOPE_LIST = Object.freeze([]);
const FEISHU_VALID_SCOPE_PATTERN = /^[a-z][a-z0-9_]*:[a-z0-9_.]+(?::[a-z0-9_]+)*$/i;
const AUTH_FLOW_STATES = Object.freeze({
  INIT: "init",
  CONTAINER_VALIDATED: "container_validated",
  CONFIG_VALIDATED: "config_validated",
  REQUESTING_ACCESS: "requesting_access",
  EXCHANGING_CODE: "exchanging_code",
  RESOLVING_WORKSPACE: "resolving_workspace",
  AUTHENTICATED: "authenticated",
  BLOCKED: "blocked",
});
const AUTH_FLOW_STEPS = Object.freeze([
  "feishu_container",
  "requestAccess",
  "auth_code",
  "server_exchange",
  "user_id",
  "workspace",
  "personal_workspace",
]);

const WORKSPACE_ORDER = [
  "boss",
  "huanhuan",
  "june",
  "liujie",
  "zhangjie",
  "nana",
  "chenchangyi",
  "zhouchen",
  "yaowei",
  "songxue",
  "yuchun",
];

const DAILY_WORKBENCH_MENU = Object.freeze([
  { key: "today", label: "\u4eca\u65e5", tone: "red" },
  { key: "todos", label: "\u5f85\u529e", tone: "orange" },
  { key: "in_progress", label: "\u8fdb\u884c\u4e2d", tone: "green" },
  { key: "risk", label: "\u98ce\u9669", tone: "purple" },
  { key: "data", label: "\u6570\u636e", tone: "blue" },
]);

const BUSINESS_FLOW_MENU = Object.freeze([
  { key: "room_flow", label: "\u623f\u6001\u6d41", userLabel: "\u5165\u4f4f / \u51fa\u9986", schemaKey: "resident_flow_schema", steps: ["\u5165\u4f4f\u7533\u8bf7", "\u6392\u623f", "\u5165\u4f4f\u6267\u884c", "\u51fa\u9986\u7ed3\u7b97"], tone: "blue" },
  { key: "finance_flow", label: "\u8d22\u52a1\u6d41", userLabel: "\u6536\u6b3e / \u5bf9\u8d26", schemaKey: "finance_schema", steps: ["\u6536\u6b3e", "\u5e94\u6536\u786e\u8ba4", "\u5bf9\u8d26", "\u5229\u6da6\u66f4\u65b0"], tone: "red" },
  { key: "sales_flow", label: "\u9500\u552e\u6d41", userLabel: "\u7b7e\u7ea6 / \u8f6c\u5316", schemaKey: "sales_schema", steps: ["\u7ebf\u7d22", "\u8ddf\u8fdb", "\u7b7e\u7ea6", "\u8f6c\u5316"], tone: "green" },
  { key: "service_flow", label: "\u670d\u52a1\u6d41", userLabel: "\u5165\u4f4f / \u62a4\u7406", schemaKey: "service_schema", steps: ["\u5165\u4f4f\u51c6\u5907", "\u670d\u52a1\u6267\u884c", "\u5f02\u5e38\u5904\u7406", "\u5b8c\u6210\u786e\u8ba4"], tone: "orange" },
  { key: "hr_flow", label: "\u4eba\u6548\u6d41", userLabel: "\u6392\u73ed / \u6267\u884c", schemaKey: "hr_schema", steps: ["\u6392\u73ed", "\u6267\u884c", "\u7ee9\u6548", "\u590d\u76d8"], tone: "purple" },
]);

const BUSINESS_MENU = DAILY_WORKBENCH_MENU;

const EMPTY_BUSINESS_SCHEMA = Object.freeze({
  schema_version: "oms.business.empty",
  resident_flow_schema: {},
  finance_schema: {},
  sales_schema: {},
  service_schema: {},
  hr_schema: {},
  semantic_status: {},
});

const operatingCenterV11 = {
  source: SOURCE_OF_TRUTH,
  principle: "运营中心第一原则：不要落下客户，不要遗忘客户",
  workspaces: {
    boss: workspaceMeta("1. 主理办（你）", "总览 | 决策 | 授权", "主理办工作台"),
    huanhuan: workspaceMeta("2. 欢欢（销售）", "销售工作台", "销售工作台"),
    june: workspaceMeta("3. 六月（店总 + 销售）", "店总工作台", "店总工作台"),
    liujie: workspaceMeta("4. 刘姐（出纳）", "财务工作台", "财务工作台"),
    zhangjie: workspaceMeta("5. 张姐（财务总监/会计）", "财务总监工作台", "财务总监工作台"),
    nana: workspaceMeta("6. 娜娜（管家）", "管家工作台", "管家工作台"),
    chenchangyi: workspaceMeta("7. 陈晶辉（产护部总监）", "产护工作台", "产护工作台"),
    zhouchen: workspaceMeta("8. 周厨（厨师长）", "料理工作台", "料理工作台"),
    yaowei: workspaceMeta("9. 维维（行政采购 + 照护师工资决算）", "行政采购工作台", "行政采购工作台"),
    songxue: workspaceMeta("10. 宗惠（人事行政）", "人事行政工作台", "人事行政工作台"),
    yuchun: workspaceMeta("11. 子渝（食材采购 + 销售）", "食材采购 + 销售工作台", "食材采购 + 销售工作台"),
  },
};

const trustedWorkspaceKeys = Object.freeze(
  WORKSPACE_ORDER.reduce((acc, key) => {
    acc[key] = key;
    return acc;
  }, {})
);
const workspaceData = operatingCenterV11.workspaces;
const $ = (selector) => document.querySelector(selector);
const SCHEMA_RENDER_TARGETS = Object.freeze(["#scoreboardCards", "#priorityCards", "#sideBusinessMenu", "#businessMenu", "#personalWorkspacePanels", "#sourceEvidenceRecords", "#overviewGrid", "#quickLinks"]);
let identity = identityBindingError("identity_bootstrap_not_started", "");
let currentWorkspace = null;
let authFlowState = AUTH_FLOW_STATES.INIT;
let authFlowAttempt = 0;
let schemaRenderSequence = 0;

function workspaceMeta(label, role, title) {
  return { label, role, title };
}

function resolveLockedIdentity() {
  const trustedContext = window.OMS_USER_CONTEXT || {};
  const trustedUserMap = window.OMS_FEISHU_USER_WORKSPACE_MAP || {};
  const identityPayload = {
    user_id: window.OMS_CURRENT_USER_ID || trustedContext.user_id || "",
    open_id: trustedContext.open_id || "",
    union_id: trustedContext.union_id || "",
    workspace_key: trustedContext.source === "feishu_webapp_sso" ? trustedContext.workspace_key || "" : "",
  };
  const trustedUserId = firstNonEmpty(identityPayload.user_id, identityPayload.open_id, identityPayload.union_id);
  if (!trustedUserId) {
    return identityBindingError("missing_feishu_user_id", "");
  }
  const mappedWorkspace = String(
    identityPayload.workspace_key ||
      trustedUserMap[identityPayload.user_id] ||
      trustedUserMap[identityPayload.open_id] ||
      trustedUserMap[identityPayload.union_id] ||
      ""
  ).trim();
  const workspaceKey = trustedWorkspaceKeys[mappedWorkspace] || "";
  if (!workspaceKey) {
    return identityBindingError("unmapped_feishu_user_id", trustedUserId);
  }
  return {
    userId: trustedUserId,
    workspaceKey,
    source: "feishu_login_state",
    policy: SINGLE_IDENTITY_POLICY,
    bindingStatus: "ready",
    identityPayload,
  };
}

function identityBindingError(errorType, userId, runtimeContext = null) {
  return {
    userId,
    workspaceKey: "",
    source: "feishu_login_state",
    policy: SINGLE_IDENTITY_POLICY,
    bindingStatus: "error",
    errorType,
    runtimeContext,
  };
}

function firstNonEmpty(...values) {
  for (const value of values) {
    const text = String(value || "").trim();
    if (text) {
      return text;
    }
  }
  return "";
}

function hasInjectedIdentity() {
  const context = window.OMS_USER_CONTEXT || {};
  return Boolean(firstNonEmpty(window.OMS_CURRENT_USER_ID, context.user_id, context.open_id, context.union_id));
}

function isFeishuClient() {
  return feishuRuntimeContext().is_feishu_client;
}

function isLarkWebView() {
  return feishuRuntimeContext().is_lark_webview;
}

function isFeishuWorkbenchContainer() {
  return feishuRuntimeContext().is_feishu_workbench_container;
}

function feishuRuntimeContext() {
  const userAgent = String(window.navigator && window.navigator.userAgent ? window.navigator.userAgent : "");
  const hasAuthApi = Boolean(window.tt && typeof window.tt.requestAccess === "function");
  const isFeishuClientRuntime = /Feishu|Lark/i.test(userAgent);
  const isLarkWebview = Boolean(window.h5sdk && window.tt) || /Lark/i.test(userAgent);
  return {
    is_feishu_client: isFeishuClientRuntime,
    is_lark_webview: isLarkWebview,
    is_feishu_workbench_container: Boolean(window.h5sdk && window.tt && hasAuthApi),
    has_h5sdk: Boolean(window.h5sdk),
    has_tt: Boolean(window.tt),
    has_auth_api: hasAuthApi,
    user_agent: userAgent,
  };
}

function authConfig() {
  return {
    appId: String(window.OMS_FEISHU_APP_ID || DEFAULT_FEISHU_APP_ID).trim(),
    endpoint: String(window.OMS_AUTH_ENDPOINT || "/api/feishu/identity").trim(),
    homeEndpoint: String(window.OMS_HOME_ENDPOINT || "").trim(),
    redirectUri: String(window.OMS_FEISHU_REDIRECT_URI || CANONICAL_FEISHU_REDIRECT_URI).trim(),
    scopeList: validatedFeishuScopeList(window.OMS_FEISHU_SCOPE_LIST || FEISHU_LOGIN_SCOPE_LIST),
  };
}

async function bootstrapIdentity() {
  resetAuthFlowState({ clearLoginContext: false });
  const runtime = feishuRuntimeContext();
  if (!runtime.is_feishu_workbench_container) {
    return authFlowFailure("not_feishu_runtime_context", "", runtime);
  }
  setAuthFlowState(AUTH_FLOW_STATES.CONTAINER_VALIDATED);
  if (hasInjectedIdentity()) {
    const injectedIdentity = resolveLockedIdentity();
    injectedIdentity.runtimeContext = runtime;
    setAuthFlowState(injectedIdentity.bindingStatus === "ready" ? AUTH_FLOW_STATES.AUTHENTICATED : AUTH_FLOW_STATES.BLOCKED);
    return injectedIdentity;
  }
  try {
    const config = authConfig();
    if (!config.appId) {
      return authFlowFailure("missing_feishu_app_id", "", runtime);
    }
    if (!config.endpoint) {
      return authFlowFailure("missing_oms_auth_endpoint", "", runtime);
    }
    validateFeishuOAuthConfig(config);
    setAuthFlowState(AUTH_FLOW_STATES.CONFIG_VALIDATED);
    if (ensureCanonicalRedirectUri(config.redirectUri)) {
      return authFlowFailure("normalizing_redirect_uri", "", runtime);
    }
    validateCurrentFeishuRedirectUri(config.redirectUri);
    await waitForFeishuReady();
    setAuthFlowState(AUTH_FLOW_STATES.REQUESTING_ACCESS);
    const code = await requestFeishuAuthCode(config);
    setAuthFlowState(AUTH_FLOW_STATES.EXCHANGING_CODE);
    const payload = await exchangeFeishuAuthCode(config.endpoint, code);
    window.OMS_USER_CONTEXT = payload;
    setAuthFlowState(AUTH_FLOW_STATES.RESOLVING_WORKSPACE);
    const authenticatedIdentity = resolveLockedIdentity();
    authenticatedIdentity.runtimeContext = runtime;
    if (authenticatedIdentity.bindingStatus !== "ready") {
      setAuthFlowState(AUTH_FLOW_STATES.BLOCKED);
      return authenticatedIdentity;
    }
    setAuthFlowState(AUTH_FLOW_STATES.AUTHENTICATED);
    return authenticatedIdentity;
  } catch (error) {
    return authFlowFailure(`feishu_auth_failed:${errorMessage(error)}`, "", runtime);
  }
}

function validateFeishuOAuthConfig(config) {
  if (!/^cli_[A-Za-z0-9]+$/.test(config.appId)) {
    throw new Error("invalid_feishu_app_id");
  }
  if (!FEISHU_OAUTH_REDIRECT_WHITELIST.includes(config.redirectUri)) {
    throw new Error("redirect_uri_not_whitelisted");
  }
  if (canonicalizeRedirectUri(config.redirectUri) !== config.redirectUri) {
    throw new Error("redirect_uri_not_canonical");
  }
  validatedFeishuScopeList(config.scopeList);
}

function validateCurrentFeishuRedirectUri(redirectUri) {
  if (canonicalizeRedirectUri(window.location.href) !== redirectUri) {
    throw new Error("redirect_uri_current_url_mismatch");
  }
}

function validatedFeishuScopeList(scopeList) {
  if (!Array.isArray(scopeList)) {
    throw new Error("invalid_feishu_scope_list");
  }
  return scopeList.map((scope) => {
    const value = String(scope || "").trim();
    if (!value || !FEISHU_VALID_SCOPE_PATTERN.test(value)) {
      throw new Error("invalid_feishu_scope");
    }
    return value;
  });
}

function ensureCanonicalRedirectUri(redirectUri) {
  const currentUri = canonicalizeRedirectUri(window.location.href);
  const expectedUri = canonicalizeRedirectUri(redirectUri);
  if (currentUri === expectedUri) {
    return false;
  }
  window.location.replace(expectedUri);
  return true;
}

function canonicalizeRedirectUri(value) {
  const url = new URL(value, window.location.origin);
  url.hash = "";
  url.search = "";
  url.pathname = url.pathname.replace(/\/index\.html$/i, "/");
  if (!url.pathname.endsWith("/")) {
    url.pathname += "/";
  }
  return url.toString();
}

function waitForFeishuReady() {
  return new Promise((resolve, reject) => {
    if (!window.h5sdk || typeof window.h5sdk.ready !== "function") {
      reject(new Error("h5sdk_unavailable"));
      return;
    }
    window.h5sdk.ready(resolve);
    if (typeof window.h5sdk.error === "function") {
      window.h5sdk.error((error) => reject(error));
    }
  });
}

function requestFeishuAuthCode(config) {
  return new Promise((resolve, reject) => {
    const success = (res) => (res && res.code ? resolve(res.code) : reject(new Error("empty_auth_code")));
    const fail = (error) => reject(error);
    if (window.tt && typeof window.tt.requestAccess === "function") {
      window.tt.requestAccess({
        appID: config.appId,
        scopeList: validatedFeishuScopeList(config.scopeList),
        state: buildFeishuOAuthState(),
        success,
        fail,
      });
      return;
    }
    reject(new Error("feishu_request_access_unavailable"));
  });
}

function buildFeishuOAuthState() {
  const bytes = new Uint8Array(16);
  if (window.crypto && typeof window.crypto.getRandomValues === "function") {
    window.crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  return `oms_${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

async function exchangeFeishuAuthCode(endpoint, code) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ code, source: "feishu_workbench", href: window.location.href }),
  });
  if (!response.ok) {
    throw new Error(`auth_endpoint_${response.status}`);
  }
  const payload = await response.json();
  const data = payload.data || payload;
  if (!firstNonEmpty(data.user_id, data.open_id, data.union_id)) {
    throw new Error("auth_endpoint_missing_identity");
  }
  return data;
}

async function fetchRuntimeHome(endpoint, lockedIdentity) {
  if (!endpoint) {
    throw new Error("missing_oms_home_endpoint");
  }
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      user_id: lockedIdentity.userId,
      workspace_key: lockedIdentity.workspaceKey,
      source: "oms_runtime_store",
    }),
  });
  if (!response.ok) {
    throw new Error(`runtime_home_endpoint_${response.status}`);
  }
  const payload = await response.json();
  const data = payload.data || payload;
  if (!data || data.entry !== "personal_workspace" || !data.current_user) {
    throw new Error("runtime_home_invalid_payload");
  }
  if (!isLocalRuntimeHome(data)) {
    throw new Error("runtime_home_not_local_live_runtime");
  }
  return data;
}

function isLocalRuntimeHome(data) {
  const source = data.runtime_source || ((data.business_dashboard || {}).runtime_source) || {};
  return source.type === "local_live_runtime" && source.mode === "single_source_of_truth" && source.remote_data_generation_allowed === false;
}

function resetAuthFlowState(options = {}) {
  authFlowAttempt += 1;
  setAuthFlowState(AUTH_FLOW_STATES.INIT);
  if (options.clearLoginContext) {
    window.OMS_USER_CONTEXT = null;
    window.OMS_CURRENT_USER_ID = "";
  }
  identity = identityBindingError("identity_bootstrap_not_started", "");
  currentWorkspace = null;
  clearSchemaRenderTargets();
}

function setAuthFlowState(state) {
  authFlowState = state;
  document.documentElement.dataset.authState = state;
}

function authFlowFailure(errorType, userId, runtimeContext = null) {
  setAuthFlowState(AUTH_FLOW_STATES.BLOCKED);
  return identityBindingError(errorType, userId, runtimeContext);
}

function errorMessage(error) {
  if (!error) {
    return "unknown";
  }
  return String(error.message || error.errString || error.errMsg || error);
}

function render(runtimeHome = null) {
  if (identity.bindingStatus === "error") {
    renderIdentityError();
    return;
  }
  if (!runtimeHome) {
    runtimeHome = buildUsableRuntimeHome("runtime_home_missing");
  }
  prepareFullSchemaRepaint();
  const currentUser = runtimeHome.current_user || {};
  $("#homeTitle").textContent = currentUser.name ? `晚上好，${currentUser.name}` : runtimeHome.home_title || "OMS";
  $("#homeSubtitle").textContent = "今日关键事项、我的工作和风险提醒";
  $("#lockedUserName").textContent = currentUser.name || "OMS";
  $("#lockedUserRole").textContent = currentUser.role || "我的工作台";
  $("#workspaceStatus").textContent = "实时更新";
  renderClock();
  renderSingleUserBusinessOS(runtimeHome);
}

function prepareFullSchemaRepaint() {
  document.body.classList.remove("identity-error-mode");
  clearSchemaRenderTargets();
  schemaRenderSequence += 1;
  document.documentElement.dataset.schemaRenderId = String(schemaRenderSequence);
}

function clearSchemaRenderTargets() {
  for (const selector of SCHEMA_RENDER_TARGETS) {
    const target = $(selector);
    if (target) {
      target.replaceChildren();
      target.dataset.renderSource = "business_schema";
      target.dataset.renderState = "cleared";
    }
  }
}

function renderLoading() {
  $("#homeTitle").textContent = "OMS";
  if ($("#homeSubtitle")) {
    $("#homeSubtitle").textContent = "identity authenticating";
  }
  $("#lockedUserName").textContent = "Feishu";
  $("#lockedUserRole").textContent = "identity authenticating";
  $("#workspaceStatus").textContent = "authenticating";
}

function renderClock() {
  const now = new Date();
  $("#todayLabel").textContent = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`;
  $("#todayClock").textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

function renderIdentityError() {
  if (identity.errorType === "not_feishu_runtime_context") {
    renderRuntimeContextBlock();
    return;
  }
  document.body.classList.add("identity-error-mode");
  $(".app-shell").innerHTML = `
    <section class="identity-error-panel" aria-label="OMS identity binding error">
      <p class="eyebrow">OMS</p>
      <h1>飞书身份认证失败</h1>
      <p>OMS 已识别飞书运行容器，但认证链路未完成。请重新初始化 Feishu Native 登录链路。</p>
      <div class="error-actions">
        <strong>认证状态 / ${escapeHtml(authFlowState)}</strong>
        <span>${escapeHtml(identity.userId ? "未映射到运营中心岗位" : identity.errorType)}</span>
      </div>
      <button id="retryAuthFlow" class="auth-retry-button" type="button">重新初始化飞书认证</button>
    </section>
  `;
  bindRetry();
}

function renderRuntimeContextBlock() {
  document.body.classList.add("identity-error-mode");
  $(".app-shell").innerHTML = `
    <section class="identity-error-panel" aria-label="OMS Feishu runtime context required">
      <p class="eyebrow">OMS</p>
      <h1>\u8bf7\u4ece\u98de\u4e66\u5de5\u4f5c\u53f0\u6253\u5f00</h1>
      <p>OMS 只能在 Feishu Workbench / H5 Runtime Context 内运行。直接 URL 访问已被阻止。</p>
      <div class="error-actions">
        <strong>runtime context</strong>
        <span>is_feishu_workbench_container=false</span>
      </div>
    </section>
  `;
}

function buildUsableRuntimeHome(reason, runtimeHome = {}) {
  const currentUser = runtimeHome.current_user || {};
  const workspace = currentWorkspace || workspaceData[identity.workspaceKey] || {};
  const dashboard = runtimeHome.business_dashboard || {};
  const displayName = currentUser.name || workspace.label || identity.workspaceKey || "OMS";
  const role = currentUser.role || workspace.role || "Usable Product Mode";
  return {
    entry: "personal_workspace",
    mode: "usable_product_mode",
    home_title: displayName,
    current_user: {
      user_id: identity.userId || "",
      workspace_key: identity.workspaceKey || "",
      name: displayName,
      role,
    },
    sections: runtimeHome.sections || emptyWorkspaceSections(reason),
    business_dashboard: {
      ...dashboard,
      schema_source: "business_schema",
      source: dashboard.source || "usable_runtime_data",
      data_truth_alignment: {
        policy: "soft_validation_mode",
        data_source: "available_runtime_data",
        display_policy: "always_render_with_warning",
        status: "degraded_placeholder",
        warning: reason,
        verified_work_items: 0,
        uncalibrated_work_items: 0,
        visible_work_items: 0,
        ...(dashboard.data_truth_alignment || {}),
      },
      business_schema: dashboard.business_schema || EMPTY_BUSINESS_SCHEMA,
      source_evidence_available_data: dashboard.source_evidence_available_data || {
        policy: "source_evidence_available_data",
        warning: reason,
        resident_data: [],
        room_status_data: [],
        sales_contract_data: [],
        finance_data: [],
        service_data: [],
        financial_events: [],
        business_event_flow: [],
        workflow_distribution: [],
        hr_execution_flow: [],
        current_user_visible_data: [],
      },
    },
  };
}

function emptyWorkspaceSections(reason) {
  const empty = (title) => ({
    title,
    count: 0,
    status: "empty_placeholder",
    warning: reason,
    items: [],
  });
  return {
    my_todos: empty("\u6211\u7684\u5f85\u529e"),
    my_tasks: empty("\u6211\u7684\u4efb\u52a1"),
    my_approvals: empty("\u6211\u7684\u5ba1\u6279"),
    role_home: empty("\u6211\u7684\u6d41\u7a0b"),
  };
}

function bindRetry() {
  const retry = $("#retryAuthFlow");
  if (retry) {
    retry.addEventListener("click", restartAuthFlow);
  }
}

function restartAuthFlow() {
  resetAuthFlowState({ clearLoginContext: true });
  window.location.reload();
}

function renderSingleUserBusinessOS(runtimeHome) {
  const componentTree = dailyWorkbenchLogicLayerRenderer(runtimeHome);
  $("#scoreboardCards").innerHTML = componentTree.scoreboard.map(scoreCardTemplate).join("");
  $("#priorityCards").innerHTML = componentTree.businessFlows.map(priorityCardTemplate).join("");
  $("#sideBusinessMenu").innerHTML = componentTree.taskMenu.map(sideBusinessMenuTemplate).join("");
  $("#businessMenu").innerHTML = componentTree.riskCards.map(businessMenuCardTemplate).join("");
  $("#personalWorkspacePanels").innerHTML = componentTree.workspacePanels.map(personalWorkspacePanelTemplate).join("");
  $("#sourceEvidenceRecords").innerHTML = componentTree.sourceEvidence.map(sourceEvidenceGroupTemplate).join("");
  $("#overviewGrid").innerHTML = componentTree.overview.map(overviewGroupTemplate).join("");
  $("#quickLinks").innerHTML = `
    <h3>\u5feb\u6377\u64cd\u4f5c</h3>
    <div class="quick-link-list">
      ${componentTree.quickLinks.map((link) => `<button type="button">${escapeHtml(link)}</button>`).join("")}
    </div>
  `;
  markSchemaRenderComplete(componentTree);
}

function markSchemaRenderComplete(componentTree) {
  for (const selector of SCHEMA_RENDER_TARGETS) {
    const target = $(selector);
    if (target) {
      target.dataset.renderSource = componentTree.source;
      target.dataset.renderState = "mounted";
      target.dataset.renderPipeline = componentTree.pipeline;
      target.dataset.renderId = String(schemaRenderSequence);
    }
  }
}

function dailyWorkbenchLogicLayerRenderer(runtimeHome) {
  const schema = requireBusinessSchema(runtimeHome);
  const truthLock = requireDataTruthLock(runtimeHome);
  const sourceEvidence = requireSourceEvidenceVerifiedData(runtimeHome);
  const sections = runtimeSections(runtimeHome);
  const visibleData = requireVisibleBusinessData(runtimeHome, sourceEvidence, sections);
  const productSections = ensureVisibleSections(sections, visibleData);
  return dailyWorkbenchLogicLayer(schema, truthLock, visibleData, productSections);
}

function dailyWorkbenchLogicLayer(schema, truthLock, visibleData, sections) {
  return {
    source: "daily_workbench_logic_layer",
    pipeline: "business_schema -> daily_workbench_logic_layer -> task_first_ui",
    scoreboard: dailyTodayTasks(schema, sections, visibleData),
    businessFlows: dailyBusinessFlows(schema, visibleData),
    taskMenu: dailyTaskMenu(schema, sections, visibleData),
    riskCards: dailyRiskExceptions(schema, sections, visibleData),
    workspacePanels: dailyWorkspacePanels(sections),
    sourceEvidence: dailyWritebackLog(visibleData),
    overview: dailyWorkbenchSummary(schema, sections, visibleData),
    quickLinks: dailyQuickActions(schema, sections),
    truthLock,
  };
}

function requireBusinessSchema(runtimeHome) {
  const dashboard = (runtimeHome && runtimeHome.business_dashboard) || {};
  const schema = dashboard.business_schema || {};
  if (!schema.schema_version) {
    return EMPTY_BUSINESS_SCHEMA;
  }
  return schema;
}

function requireDataTruthLock(runtimeHome) {
  const dashboard = (runtimeHome && runtimeHome.business_dashboard) || {};
  const truthLock = dashboard.data_truth_alignment || {};
  return {
    policy: truthLock.policy || "source_evidence_soft_label",
    data_source: truthLock.data_source || "available_runtime_data",
    display_policy: truthLock.display_policy || "always_render_with_confidence_label",
    status: truthLock.status || "missing_fields_warning",
    verified_work_items: Number(truthLock.verified_work_items || 0),
    uncalibrated_work_items: Number(truthLock.uncalibrated_work_items || 0),
  };
}

function requireSourceEvidenceVerifiedData(runtimeHome) {
  const dashboard = (runtimeHome && runtimeHome.business_dashboard) || {};
  return dashboard.source_evidence_available_data || {
    policy: "source_evidence_available_data",
    resident_data: [],
    room_status_data: [],
    sales_contract_data: [],
    finance_data: [],
    service_data: [],
    financial_events: [],
    business_event_flow: [],
    workflow_distribution: [],
    hr_execution_flow: [],
    current_user_visible_data: [],
  };
}

function schemaMetrics(schema) {
  const resident = schema.resident_flow_schema || {};
  const finance = schema.finance_schema || {};
  const sales = schema.sales_schema || {};
  const service = schema.service_schema || {};
  const hr = schema.hr_schema || {};
  const semantic = schema.semantic_status || {};
  return {
    resident_count: resident.resident_count || 0,
    active_stays: resident.active_stays || 0,
    today_checkins: resident.upcoming_checkins || 0,
    today_checkouts: resident.checkouts || 0,
    room_status_records: resident.room_status_records || 0,
    finance_income: finance.income || 0,
    finance_receivable: finance.receivable || 0,
    finance_collected: finance.collected || 0,
    finance_expenses: finance.expenses || 0,
    finance_profit: finance.profit || 0,
    finance_records: finance.event_records || 0,
    sales_leads: sales.leads || 0,
    sales_contracts: sales.contracts || 0,
    sales_conversion: sales.conversion || 0,
    sales_lost: sales.lost || 0,
    service_preparation: service.checkin_preparation || 0,
    service_progress: service.in_service || 0,
    service_exceptions: service.exceptions || 0,
    service_completed: service.completed || 0,
    hr_on_duty: hr.on_duty_staff || 0,
    hr_shifts: hr.scheduled_shifts || 0,
    hr_performance: hr.performance || 0,
    hr_attendance_rate: hr.attendance_rate || 0,
    today_todos: semantic.pending_work_items || 0,
    risk_alerts: semantic.risk_items || 0,
  };
}

function runtimeSections(runtimeHome) {
  return (runtimeHome && runtimeHome.sections) || {};
}

function requireVisibleBusinessData(runtimeHome, sourceEvidence, sections) {
  const sectionItems = Object.values(sections || {}).flatMap((section) => Array.isArray(section.items) ? section.items : []);
  const normalizedSectionItems = sectionItems.map((item, index) => normalizeVisibleItem(item, index));
  const available = {
    resident_data: [...arrayValue(sourceEvidence.resident_data)],
    room_status_data: [...arrayValue(sourceEvidence.room_status_data)],
    sales_contract_data: [...arrayValue(sourceEvidence.sales_contract_data)],
    finance_data: [...arrayValue(sourceEvidence.finance_data)],
    service_data: [...arrayValue(sourceEvidence.service_data)],
    financial_events: [...arrayValue(sourceEvidence.financial_events)],
    business_event_flow: [...arrayValue(sourceEvidence.business_event_flow)],
    workflow_distribution: [...arrayValue(sourceEvidence.workflow_distribution)],
    hr_execution_flow: [...arrayValue(sourceEvidence.hr_execution_flow)],
    current_user_visible_data: [...arrayValue(sourceEvidence.current_user_visible_data), ...normalizedSectionItems],
  };
  for (const item of normalizedSectionItems) {
    const domain = classifyVisibleDomain(item);
    available[domain].push(item);
  }
  return {
    policy: "visible_data_first",
    display_policy: "data_visible_over_data_perfect",
    ...available,
  };
}

function ensureVisibleSections(sections, visibleData) {
  const records = eventDrivenRecords(sections, visibleData);
  return {
    ...sections,
    my_todos: sectionFromRecords(sections.my_todos, "\u6211\u7684\u5f85\u529e", records),
    my_tasks: sectionFromRecords(sections.my_tasks, "\u6211\u7684\u4efb\u52a1", records),
    my_approvals: sections.my_approvals || { title: "\u6211\u7684\u5ba1\u6279", count: 0, items: [] },
    role_home: sectionFromRecords(sections.role_home, "\u6211\u7684\u4e1a\u52a1\u6d41", records),
    event_execution_flow: sectionFromRecords(sections.event_execution_flow, "\u4e8b\u4ef6\u6267\u884c\u6d41", records),
  };
}

function eventDrivenRecords(sections, visibleData) {
  const eventSectionItems = arrayValue((sections.event_execution_flow || {}).items);
  return dedupeVisibleRecords([
    ...eventSectionItems,
    ...arrayValue(visibleData.business_event_flow),
    ...arrayValue(visibleData.workflow_distribution),
    ...arrayValue(visibleData.hr_execution_flow),
  ]);
}

function sectionFromRecords(section, title, records) {
  return {
    ...(section || {}),
    title: (section && section.title) || title,
    count: records.length,
    items: records,
    empty_text: records.length ? "" : ((section && section.empty_text) || "\u6682\u65e0\u4e8b\u4ef6\u9a71\u52a8\u4efb\u52a1"),
  };
}

function sectionWithVisibleFallback(section, title, records) {
  const existingItems = Array.isArray(section && section.items) ? section.items : [];
  if (existingItems.length) {
    return section;
  }
  return {
    ...(section || {}),
    title: (section && section.title) || title,
    count: records.length,
    status: records.length ? "visible_runtime_data" : "empty_placeholder",
    items: records.slice(0, 8),
  };
}

function dedupeVisibleRecords(records) {
  const seen = new Set();
  return records.filter((record, index) => {
    const key = record.work_item_id || record.event_id || record.record_id || record.title || `record_${index}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function normalizeVisibleItem(item, index) {
  const evidence = item && typeof item.source_evidence === "object" ? item.source_evidence : {};
  return {
    ...item,
    business_domain: item.business_domain || item.domain || "",
    work_item_id: item.work_item_id || item.action_id || item.id || `visible_item_${index + 1}`,
    title: item.title || item.daily_process || item.name || item.summary || "\u5df2\u6709\u6570\u636e",
    data_confidence: item.data_confidence || (Object.keys(evidence).length ? "source_verified" : "uncalibrated_warning"),
    source_evidence: evidence,
    display_fields: Array.isArray(item.display_fields) ? item.display_fields : visibleDisplayFields(item),
  };
}

function visibleDisplayFields(item) {
  return Object.entries(item || {})
    .filter(([key, value]) => !key.startsWith("_") && !["source_evidence", "display_fields"].includes(key) && value !== "" && value !== null && typeof value !== "object")
    .slice(0, 4)
    .map(([key, value]) => ({ label: key, value: String(value) }));
}

function classifyVisibleDomain(item) {
  const text = [item.business_domain, item.role, item.workspace, item.title, item.summary, item.daily_process, item.action]
    .map((value) => String(value || ""))
    .join(" ");
  if (/财务|收款|付款|收入|支出|finance|payment|cash/i.test(text)) {
    return "finance_data";
  }
  if (/销售|签约|客户|合同|sales|contract|crm/i.test(text)) {
    return "sales_contract_data";
  }
  if (/房|排房|入住|出馆|room|resident|stay/i.test(text)) {
    return /房态|排房|room/i.test(text) ? "room_status_data" : "resident_data";
  }
  if (/服务|护理|产护|service|care/i.test(text)) {
    return "service_data";
  }
  return "service_data";
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

function visibleCounts(visibleData) {
  return {
    resident: arrayValue(visibleData.resident_data).length,
    room: arrayValue(visibleData.room_status_data).length,
    sales: arrayValue(visibleData.sales_contract_data).length,
    finance: arrayValue(visibleData.finance_data).length + arrayValue(visibleData.financial_events).length,
    service: arrayValue(visibleData.service_data).length,
    events: arrayValue(visibleData.business_event_flow).length + arrayValue(visibleData.workflow_distribution).length,
    hr: arrayValue(visibleData.hr_execution_flow).length,
    current: arrayValue(visibleData.current_user_visible_data).length,
  };
}

function firstPositive(...values) {
  return values.find((value) => Number(value) > 0) || 0;
}

function workspacePanel(title, section, caption, tone) {
  const safeSection = section || {};
  return {
    title,
    caption,
    tone,
    count: Number(safeSection.count || 0),
    items: Array.isArray(safeSection.items) ? safeSection.items.slice(0, 4) : [],
  };
}

function schemaSourceEvidence(sourceEvidence) {
  const groups = [
    sourceEvidenceGroup("\u5728\u4f4f\u6570\u636e", sourceEvidence.resident_data),
    sourceEvidenceGroup("\u623f\u95f4\u8bb0\u5f55", sourceEvidence.room_status_data),
    sourceEvidenceGroup("\u5ba2\u6237\u5408\u540c", sourceEvidence.sales_contract_data),
    sourceEvidenceGroup("\u6536\u652f\u8bb0\u5f55", sourceEvidence.finance_data),
    sourceEvidenceGroup("\u670d\u52a1\u6570\u636e", sourceEvidence.service_data),
    sourceEvidenceGroup("\u8d22\u52a1\u4e8b\u4ef6", sourceEvidence.financial_events),
    sourceEvidenceGroup("\u4e1a\u52a1\u4e8b\u4ef6", sourceEvidence.business_event_flow),
    sourceEvidenceGroup("\u4eba\u6548\u6267\u884c", sourceEvidence.hr_execution_flow),
  ];
  return groups.filter((group) => group.records.length);
}

function sourceEvidenceGroup(title, records) {
  return {
    title,
    records: Array.isArray(records) ? records.slice(0, 6) : [],
  };
}

function dailyTodayTasks(schema, sections, visibleData) {
  const records = allDailyRecords(sections, visibleData).sort((left, right) => dailyTaskPriority(right) - dailyTaskPriority(left));
  const targetCount = Math.min(7, Math.max(3, records.length));
  const tasks = records.slice(0, targetCount).map((record, index) => dailyTaskFromRecord(record, index));
  while (tasks.length < 3) {
    tasks.push(dailyPlaceholderTask(schema, tasks.length));
  }
  return tasks;
}

function dailyBusinessFlows(schema, visibleData) {
  const metrics = schemaMetrics(schema);
  const visible = visibleCounts(visibleData);
  return BUSINESS_FLOW_MENU.map((flow) => {
    const count = dailyFlowCount(flow.key, metrics, visible);
    const state = dailyFlowState(flow, count, metrics);
    return {
      ...flow,
      type: "business_flow_progress",
      value: String(count),
      currentStep: state.currentStep,
      nextAction: state.nextAction,
      riskNote: state.riskNote,
      status: state.status,
      source: "daily_workbench_logic_layer",
    };
  });
}

function dailyTaskMenu(schema, sections, visibleData) {
  const metrics = schemaMetrics(schema);
  const visible = visibleCounts(visibleData);
  const records = allDailyRecords(sections, visibleData);
  const counts = {
    today: Math.min(7, Math.max(3, records.length)),
    todos: firstPositive((sections.my_todos || {}).count, metrics.today_todos, records.length),
    in_progress: firstPositive((sections.my_tasks || {}).count, (sections.role_home || {}).count, visible.current),
    risk: firstPositive(metrics.risk_alerts, metrics.service_exceptions),
    data: visible.finance + visible.room + visible.resident + visible.sales + visible.service,
  };
  const captions = {
    today: "\u4eca\u5929\u5148\u505a",
    todos: "\u7b49\u6211\u5904\u7406",
    in_progress: "\u6b63\u5728\u63a8\u8fdb",
    risk: "\u9700\u8981\u5173\u6ce8",
    data: "\u53ef\u89c1\u6570\u636e",
  };
  return DAILY_WORKBENCH_MENU.map((item) => ({
    ...item,
    type: "daily_menu",
    value: String(counts[item.key] || 0),
    caption: captions[item.key],
  }));
}

function dailyRiskExceptions(schema, sections, visibleData) {
  const metrics = schemaMetrics(schema);
  const records = allDailyRecords(sections, visibleData);
  const delayed = records.filter((record) => /\u5ef6\u8fdf|\u903e\u671f|delay|overdue|late/i.test(dailyRecordText(record))).length;
  const financeExceptions = firstPositive(metrics.finance_receivable - metrics.finance_collected > 0 ? metrics.finance_receivable - metrics.finance_collected : 0, 0);
  const roomConflicts = Math.max(0, metrics.today_checkins + metrics.active_stays - metrics.resident_count);
  const unfinished = firstPositive((sections.my_todos || {}).count, metrics.today_todos, records.length);
  return [
    dailyRiskCard("\u5ef6\u8fdf\u4e8b\u9879", delayed, "\u5148\u5904\u7406\u903e\u671f\u4efb\u52a1", delayed ? "\u9700\u7acb\u5373\u5904\u7406" : "\u6682\u65e0\u5ef6\u8fdf", "orange"),
    dailyRiskCard("\u8d22\u52a1\u5f02\u5e38", financeExceptions, "\u6838\u5bf9\u5f85\u6536\u548c\u5b9e\u6536", financeExceptions ? "\u6536\u6b3e\u5dee\u989d\u5f85\u786e\u8ba4" : "\u6682\u65e0\u5f02\u5e38", "red"),
    dailyRiskCard("\u623f\u6001\u51b2\u7a81", roomConflicts, "\u786e\u8ba4\u5165\u4f4f\u548c\u53ef\u7528\u623f", roomConflicts ? "\u6392\u623f\u9700\u590d\u6838" : "\u6682\u65e0\u51b2\u7a81", "blue"),
    dailyRiskCard("\u672a\u5b8c\u6210\u4efb\u52a1", unfinished, "\u5b8c\u6210\u4eca\u65e5\u5f85\u529e", unfinished ? "\u8fd8\u9700\u63a8\u8fdb" : "\u4eca\u65e5\u5df2\u6e05\u7a7a", "purple"),
  ];
}

function dailyWorkspacePanels(sections) {
  return [
    workspacePanel("\u4eca\u65e5\u5fc5\u505a", sections.my_todos, "\u6309\u4f18\u5148\u7ea7\u6267\u884c", "red"),
    workspacePanel("\u8fdb\u884c\u4e2d", sections.my_tasks, "\u6b63\u5728\u63a8\u8fdb\u7684\u5de5\u4f5c", "green"),
    workspacePanel("\u6211\u7684\u5ba1\u6279", sections.my_approvals, "\u9700\u8981\u6211\u786e\u8ba4", "blue"),
    workspacePanel("\u6211\u7684\u4e1a\u52a1", sections.role_home, "\u53ea\u770b\u5f53\u524d\u7528\u6237\u76f8\u5173", "purple"),
  ];
}

function dailyWritebackLog(visibleData) {
  return schemaSourceEvidence(visibleData);
}

function dailyWorkbenchSummary(schema, sections, visibleData) {
  const metrics = schemaMetrics(schema);
  const visible = visibleCounts(visibleData);
  return [
    overviewGroup("\u4eca\u65e5", [
      metric("\u5fc5\u505a\u4efb\u52a1", String(Math.min(7, Math.max(3, allDailyRecords(sections, visibleData).length)))),
      metric("\u4eca\u65e5\u5165\u4f4f", String(firstPositive(metrics.today_checkins, visible.resident))),
      metric("\u4eca\u65e5\u51fa\u9986", String(metrics.today_checkouts)),
      metric("\u5f85\u5904\u7406", String(firstPositive(metrics.today_todos, visible.current))),
    ]),
    overviewGroup("\u5f85\u529e", [
      metric("\u6211\u7684\u5f85\u529e", String(firstPositive((sections.my_todos || {}).count, metrics.today_todos))),
      metric("\u6211\u7684\u5ba1\u6279", String((sections.my_approvals || {}).count || 0)),
      metric("\u6211\u7684\u4efb\u52a1", String((sections.my_tasks || {}).count || 0)),
      metric("\u6211\u7684\u4e1a\u52a1", String((sections.role_home || {}).count || 0)),
    ]),
    overviewGroup("\u8fdb\u884c\u4e2d", [
      metric("\u5165\u4f4f/\u51fa\u9986", String(firstPositive(metrics.active_stays, visible.resident))),
      metric("\u6536\u6b3e/\u5bf9\u8d26", String(firstPositive(metrics.finance_records, visible.finance))),
      metric("\u7b7e\u7ea6/\u8f6c\u5316", String(firstPositive(metrics.sales_contracts, visible.sales))),
      metric("\u5165\u4f4f/\u62a4\u7406", String(firstPositive(metrics.service_progress, visible.service))),
    ]),
    overviewGroup("\u98ce\u9669", [
      metric("\u5ef6\u8fdf", String(allDailyRecords(sections, visibleData).filter((record) => /\u5ef6\u8fdf|\u903e\u671f|delay|overdue|late/i.test(dailyRecordText(record))).length)),
      metric("\u5f02\u5e38", String(firstPositive(metrics.risk_alerts, metrics.service_exceptions))),
      metric("\u672a\u5b8c\u6210", String(firstPositive(metrics.today_todos, visible.current))),
      metric("\u6570\u636e\u672a\u6821\u9a8c", String((visibleData.current_user_visible_data || []).filter((item) => item.data_confidence !== "source_verified").length)),
    ]),
    overviewGroup("\u6570\u636e", [
      metric("\u53ef\u89c1\u8bb0\u5f55", String(visible.finance + visible.room + visible.resident + visible.sales + visible.service)),
      metric("\u5728\u4f4f", String(firstPositive(metrics.resident_count, visible.resident))),
      metric("\u6536\u652f", String(firstPositive(metrics.finance_records, visible.finance))),
      metric("\u5ba2\u6237", String(firstPositive(metrics.sales_leads + metrics.sales_contracts, visible.sales))),
    ]),
  ];
}

function dailyQuickActions(schema, sections) {
  return [
    "\u5f00\u59cb\u7b2c1\u4ef6\u4e8b",
    "\u5904\u7406\u5f85\u529e",
    "\u67e5\u770b\u8fdb\u884c\u4e2d",
    "\u5904\u7406\u98ce\u9669",
    "\u67e5\u770b\u6570\u636e",
    "\u8ffd\u8e2a pending_outbox",
  ];
}

function allDailyRecords(sections, visibleData) {
  return eventDrivenRecords(sections, visibleData);
}

function dailyTaskFromRecord(record, index) {
  const flow = dailyFlowForRecord(record);
  const currentStep = inferDailyStep(record, flow);
  const nextAction = inferDailyAction(record, flow, currentStep);
  return {
    type: "daily_task",
    rank: index + 1,
    label: record.title || record.name || record.summary || record.work_item_id || "\u5f85\u5904\u7406\u4e8b\u9879",
    value: `#${index + 1}`,
    caption: flow.userLabel,
    delta: `\u4f18\u5148\u7ea7 ${dailyTaskPriority(record)}`,
    currentStep,
    nextAction,
    actionLabel: nextAction,
    riskNote: inferDailyRisk(record),
    tone: dailyTaskTone(record, flow),
  };
}

function dailyPlaceholderTask(schema, index) {
  const flow = BUSINESS_FLOW_MENU[index % BUSINESS_FLOW_MENU.length];
  const state = dailyFlowState(flow, dailyFlowCount(flow.key, schemaMetrics(schema), { resident: 0, room: 0, sales: 0, finance: 0, service: 0, events: 0, hr: 0, current: 0 }), schemaMetrics(schema));
  return {
    type: "daily_task",
    rank: index + 1,
    label: `${flow.userLabel}\u5f85\u89e6\u53d1`,
    value: `#${index + 1}`,
    caption: flow.userLabel,
    delta: "\u7b49\u5f85\u771f\u5b9e\u4e1a\u52a1",
    currentStep: state.currentStep,
    nextAction: state.nextAction,
    actionLabel: state.nextAction,
    riskNote: "\u6682\u65e0\u5f85\u5904\u7406\u4e8b\u9879",
    tone: flow.tone,
  };
}

function dailyRiskCard(label, value, nextAction, riskNote, tone) {
  return {
    type: "daily_risk_card",
    label,
    value: String(value || 0),
    nextAction,
    riskNote,
    tone,
  };
}

function dailyTaskPriority(record) {
  const text = dailyRecordText(record);
  let score = 10;
  if (/\u98ce\u9669|\u5f02\u5e38|\u51b2\u7a81|\u5ef6\u8fdf|\u903e\u671f|risk|error|blocked|overdue/i.test(text)) score += 70;
  if (/\u6536\u6b3e|\u5e94\u6536|\u5bf9\u8d26|\u5f85\u4ed8|finance|payment|cash|collection|reconciliation/i.test(text)) score += 55;
  if (/\u4eca\u65e5|\u5165\u4f4f|\u51fa\u9986|today|checkin|checkout/i.test(text)) score += 45;
  if (/\u5ba1\u6279|\u786e\u8ba4|approval|confirm/i.test(text)) score += 30;
  if (record.data_confidence !== "source_verified") score += 8;
  return score;
}

function dailyTaskTone(record, flow) {
  const text = dailyRecordText(record);
  if (/\u98ce\u9669|\u5f02\u5e38|\u51b2\u7a81|\u5ef6\u8fdf|\u903e\u671f|risk|error|blocked|overdue/i.test(text)) {
    return "orange";
  }
  return flow.tone;
}

function dailyFlowCount(key, metrics, visible) {
  const counts = {
    room_flow: firstPositive(metrics.today_checkins + metrics.today_checkouts + metrics.active_stays + metrics.room_status_records, visible.resident + visible.room),
    finance_flow: firstPositive(metrics.finance_records, visible.finance),
    sales_flow: firstPositive(metrics.sales_contracts + metrics.sales_leads, visible.sales),
    service_flow: firstPositive(metrics.service_preparation + metrics.service_progress + metrics.service_exceptions + metrics.service_completed, visible.service),
    hr_flow: firstPositive(metrics.hr_shifts + metrics.hr_performance + metrics.hr_on_duty, visible.hr),
  };
  return Number(counts[key] || 0);
}

function dailyFlowState(flow, count, metrics) {
  const currentStep = dailyCurrentStep(flow, count, metrics);
  return {
    currentStep,
    nextAction: count ? dailyNextStep(flow, currentStep) : `\u7b49\u5f85${flow.steps[0]}`,
    riskNote: dailyFlowRisk(flow, metrics),
    status: count ? "\u8fdb\u884c\u4e2d" : "\u5f85\u89e6\u53d1",
  };
}

function dailyCurrentStep(flow, count, metrics) {
  if (!count) return flow.steps[0];
  if (flow.key === "room_flow") {
    if (metrics.today_checkouts) return "\u51fa\u9986\u7ed3\u7b97";
    if (metrics.active_stays || metrics.resident_count) return "\u5165\u4f4f\u6267\u884c";
    if (metrics.room_status_records) return "\u6392\u623f";
    return "\u5165\u4f4f\u7533\u8bf7";
  }
  if (flow.key === "finance_flow") {
    if (metrics.finance_profit) return "\u5229\u6da6\u66f4\u65b0";
    if (metrics.finance_records || metrics.finance_collected) return "\u5bf9\u8d26";
    if (metrics.finance_receivable) return "\u5e94\u6536\u786e\u8ba4";
    return "\u6536\u6b3e";
  }
  if (flow.key === "sales_flow") {
    if (metrics.sales_conversion) return "\u8f6c\u5316";
    if (metrics.sales_contracts) return "\u7b7e\u7ea6";
    if (metrics.sales_leads) return "\u8ddf\u8fdb";
    return "\u7ebf\u7d22";
  }
  if (flow.key === "service_flow") {
    if (metrics.service_exceptions) return "\u5f02\u5e38\u5904\u7406";
    if (metrics.service_completed) return "\u5b8c\u6210\u786e\u8ba4";
    if (metrics.service_progress) return "\u670d\u52a1\u6267\u884c";
    return "\u5165\u4f4f\u51c6\u5907";
  }
  if (flow.key === "hr_flow") {
    if (metrics.hr_performance) return "\u7ee9\u6548";
    if (metrics.hr_shifts) return "\u6267\u884c";
    if (metrics.hr_on_duty) return "\u6392\u73ed";
    return "\u6392\u73ed";
  }
  return flow.steps[Math.min(flow.steps.length - 1, count % flow.steps.length)];
}

function dailyNextStep(flow, currentStep) {
  const index = flow.steps.indexOf(currentStep);
  if (index < 0) return flow.steps[0];
  return flow.steps[index + 1] || "\u5b8c\u6210\u5e76\u56de\u5199";
}

function dailyFlowRisk(flow, metrics) {
  if (flow.key === "service_flow" && metrics.service_exceptions) {
    return `${metrics.service_exceptions} \u4e2a\u670d\u52a1\u5f02\u5e38`;
  }
  if (metrics.risk_alerts) {
    return `${metrics.risk_alerts} \u4e2a\u98ce\u9669\u9700\u770b`;
  }
  return "\u65e0\u5f02\u5e38";
}

function dailyFlowForRecord(record) {
  const text = dailyRecordText(record);
  if (/\u8d22\u52a1|\u6536\u6b3e|\u4ed8\u6b3e|\u6536\u5165|\u652f\u51fa|finance|payment|cash|collection|reconciliation/i.test(text)) {
    return BUSINESS_FLOW_MENU.find((flow) => flow.key === "finance_flow");
  }
  if (/\u9500\u552e|\u7b7e\u7ea6|\u5ba2\u6237|\u5408\u540c|sales|contract|crm|lead|conversion/i.test(text)) {
    return BUSINESS_FLOW_MENU.find((flow) => flow.key === "sales_flow");
  }
  if (/\u623f\u6001|\u6392\u623f|\u5165\u4f4f|\u51fa\u9986|room|resident|stay|checkin|checkout/i.test(text)) {
    return BUSINESS_FLOW_MENU.find((flow) => flow.key === "room_flow");
  }
  if (/\u4eba\u6548|\u4eba\u4e8b|\u6392\u73ed|\u7ee9\u6548|\u5de5\u8d44|hr|staff|attendance|performance/i.test(text)) {
    return BUSINESS_FLOW_MENU.find((flow) => flow.key === "hr_flow");
  }
  return BUSINESS_FLOW_MENU.find((flow) => flow.key === "service_flow");
}

function dailyRecordText(record) {
  return [record.business_domain, record.event_action, record.event_name, record.role, record.workspace, record.title, record.name, record.summary, record.daily_process, record.action, record.status]
    .map((value) => String(value || ""))
    .join(" ");
}

function inferDailyStep(record, flow) {
  const explicitStep = record.current_step || record.step || record.workflow_step || "";
  if (explicitStep) return String(explicitStep);
  const text = dailyRecordText(record);
  return flow.steps.find((step) => text.includes(step)) || flow.steps[0];
}

function inferDailyAction(record, flow, currentStep) {
  if (record.next_action || record.recommended_action) {
    return String(record.next_action || record.recommended_action);
  }
  return dailyNextStep(flow, currentStep);
}

function inferDailyRisk(record) {
  const risk = record.blocker || record.blockers || record.risk || record.error || "";
  if (risk) return String(risk);
  return record.data_confidence === "source_verified" ? "\u53ef\u76f4\u63a5\u5904\u7406" : "\u6570\u636e\u672a\u5b8c\u5168\u6821\u9a8c";
}

function scoreMetric(label, value, caption, delta, tone) {
  return { label, value, caption, delta, tone };
}

function overviewGroup(title, metrics) {
  return { title, metrics };
}

function metric(label, value) {
  return { label, value };
}

function scoreCardTemplate(item) {
  if (item.type === "daily_task") {
    return dailyTaskCardTemplate(item);
  }
  return `
    <article class="score-card tone-${escapeHtml(item.tone)}">
      <span class="score-icon" aria-hidden="true"></span>
      <h2>${escapeHtml(item.label)}</h2>
      <strong>${escapeHtml(item.value)}</strong>
      <p><span>${escapeHtml(item.caption)}</span><b>${escapeHtml(item.delta)}</b></p>
      <div class="sparkline" aria-hidden="true"></div>
    </article>
  `;
}

function priorityCardTemplate(item) {
  if (item.type === "business_flow_progress") {
    return dailyBusinessFlowCardTemplate(item);
  }
  return `
    <article class="priority-card tone-${escapeHtml(item.tone)}">
      <span class="score-icon" aria-hidden="true"></span>
      <strong>${escapeHtml(item.value)}</strong>
      <div>
        <h3>${escapeHtml(item.label)}</h3>
        <p>${escapeHtml(item.delta)}</p>
      </div>
    </article>
  `;
}

function sideBusinessMenuTemplate(item) {
  return `<a href="#scoreboardCards"><span class="rank-badge tone-${escapeHtml(item.tone)}">${escapeHtml(item.value || item.label.slice(0, 1))}</span>${escapeHtml(item.label)}<small>${escapeHtml(item.caption || "")}</small></a>`;
}

function businessMenuCardTemplate(item) {
  if (item.type === "daily_risk_card") {
    return dailyRiskCardTemplate(item);
  }
  return `
    <article class="business-menu-card tone-${escapeHtml(item.tone)}" data-business-domain="${escapeHtml(item.key)}" data-schema-source="${escapeHtml(item.source)}">
      <header>
        <span class="score-icon" aria-hidden="true"></span>
        <strong>${escapeHtml(item.label)}</strong>
      </header>
      <b>${escapeHtml(item.value)}</b>
      <p>${escapeHtml(item.caption)}</p>
      <small>${item.available ? "可操作" : "等待数据"}</small>
    </article>
  `;
}

function dailyTaskCardTemplate(item) {
  return `
    <article class="score-card daily-task-card tone-${escapeHtml(item.tone)}">
      <div class="daily-card-head">
        <span class="daily-rank">${escapeHtml(item.value)}</span>
        <span class="daily-flow-label">${escapeHtml(item.caption)}</span>
      </div>
      <h2>${escapeHtml(item.label)}</h2>
      <strong>${escapeHtml(item.nextAction)}</strong>
      <p><span>${escapeHtml(item.caption)}</span><b>${escapeHtml(item.delta)}</b></p>
      <small class="daily-warning">${escapeHtml("\u63d0\u9192\uff1a")}${escapeHtml(item.riskNote)}</small>
      <button class="daily-action-button" type="button">${escapeHtml(item.actionLabel)}</button>
    </article>
  `;
}

function dailyBusinessFlowCardTemplate(item) {
  return `
    <article class="priority-card daily-flow-card tone-${escapeHtml(item.tone)}">
      <span class="score-icon" aria-hidden="true"></span>
      <strong>${escapeHtml(item.value)}</strong>
      <div>
        <h3>${escapeHtml(item.userLabel)}</h3>
        <p>${escapeHtml("\u8fdb\u884c\u4e2d\uff1a")}${escapeHtml(item.currentStep)}</p>
        <small>${escapeHtml("\u4e0b\u4e00\u6b65\u52a8\u4f5c\uff1a")}${escapeHtml(item.nextAction)}</small>
        <em>${escapeHtml("\u98ce\u9669\uff1a")}${escapeHtml(item.riskNote)}</em>
      </div>
    </article>
  `;
}

function dailyRiskCardTemplate(item) {
  return `
    <article class="business-menu-card daily-risk-card tone-${escapeHtml(item.tone)}">
      <header>
        <span class="score-icon" aria-hidden="true"></span>
        <strong>${escapeHtml(item.label)}</strong>
      </header>
      <b>${escapeHtml(item.value)}</b>
      <div class="daily-risk-list">
        <span><em>${escapeHtml("\u4e0b\u4e00\u6b65")}</em><strong>${escapeHtml(item.nextAction)}</strong></span>
        <span><em>${escapeHtml("\u72b6\u6001")}</em><strong>${escapeHtml(item.riskNote)}</strong></span>
      </div>
      <small>${Number(item.value) ? "\u9700\u5904\u7406" : "\u6682\u65e0\u5f02\u5e38"}</small>
    </article>
  `;
}

function personalWorkspacePanelTemplate(panel) {
  const items = panel.items.length
    ? panel.items.map((item) => {
        const fields = Array.isArray(item.display_fields) ? item.display_fields.slice(0, 3) : [];
        const fieldText = fields.map((field) => `${field.label}:${field.value}`).join(" / ");
        return `
          <li>
            <strong>${escapeHtml(item.title || item.name || item.summary || item.id || "\u5f85\u5904\u7406\u4e8b\u9879")}</strong>
            <b class="confidence-label confidence-${escapeHtml(item.data_confidence || "uncalibrated_warning")}">${escapeHtml(confidenceLabel(item.data_confidence))}</b>
            ${item.source_summary ? `<small>${escapeHtml(item.source_summary)}</small>` : ""}
            ${fieldText ? `<em>${escapeHtml(fieldText)}</em>` : ""}
          </li>
        `;
      }).join("")
    : "<li>\u6682\u65e0\u5f53\u524d\u7528\u6237\u4e8b\u9879</li>";
  return `
    <article class="workspace-panel-card tone-${escapeHtml(panel.tone)}">
      <header>
        <div>
          <h3>${escapeHtml(panel.title)}</h3>
          <p>${escapeHtml(panel.caption)}</p>
        </div>
        <strong>${escapeHtml(panel.count)}</strong>
      </header>
      <ul>${items}</ul>
    </article>
  `;
}

function sourceEvidenceGroupTemplate(group) {
  return `
    <article class="source-evidence-card">
      <h3>${escapeHtml(group.title)}</h3>
      <div class="source-record-list">
        ${group.records.map(sourceRecordTemplate).join("")}
      </div>
    </article>
  `;
}

function sourceRecordTemplate(record) {
  const evidence = record.source_evidence || {};
  const sourceFile = basename(evidence.source_file || "");
  const fields = Array.isArray(record.display_fields) ? record.display_fields.slice(0, 4) : [];
  const fieldText = fields.map((field) => `${field.label}:${field.value}`).join(" / ");
  return `
    <div class="source-record">
      <strong>${escapeHtml(record.title || record.event_id || record.work_item_id || record.business_domain || "source record")}</strong>
      <b class="confidence-label confidence-${escapeHtml(record.data_confidence || "uncalibrated_warning")}">${escapeHtml(confidenceLabel(record.data_confidence))}</b>
      <span>${escapeHtml(evidence.truth_source || "")} / ${escapeHtml(evidence.source_type || record.business_domain || "")} / ${escapeHtml(sourceFile)} / row ${escapeHtml(evidence.row_number || "")}</span>
      <small>${escapeHtml(evidence.record_id || record.work_item_id || "")}</small>
      ${fieldText ? `<em>${escapeHtml(fieldText)}</em>` : ""}
    </div>
  `;
}

function confidenceLabel(value) {
  return value === "source_verified" ? "\u5df2\u6821\u9a8c\u6765\u6e90" : "\u672a\u5b8c\u5168\u6821\u9a8c";
}

function basename(value) {
  const text = String(value || "");
  const parts = text.split(/[\\/]/);
  return parts[parts.length - 1] || text;
}

function overviewGroupTemplate(group) {
  return `
    <article class="overview-group">
      <h3>${escapeHtml(group.title)}</h3>
      <div class="metric-grid">
        ${group.metrics.map((item) => `<div><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong></div>`).join("")}
      </div>
    </article>
  `;
}

function roleTone(key) {
  const tones = {
    boss: "red",
    huanhuan: "green",
    june: "teal",
    liujie: "orange",
    zhangjie: "blue",
    nana: "teal",
    chenchangyi: "purple",
    zhouchen: "orange",
    yaowei: "teal",
    songxue: "blue",
    yuchun: "purple",
  };
  return tones[key] || "blue";
}

function formatMoney(value) {
  const amount = Number(value || 0);
  return `¥${amount.toLocaleString("zh-CN")}`;
}

function formatPercent(value) {
  const ratio = Number(value || 0);
  return `${Math.round(ratio * 100)}%`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function startOmsApp() {
  renderLoading();
  identity = await bootstrapIdentity();
  currentWorkspace = identity.bindingStatus === "ready" ? workspaceData[identity.workspaceKey] : null;
  if (identity.bindingStatus === "ready" && !currentWorkspace) {
    identity = identityBindingError("workspace_route_not_found_after_auth", identity.userId, identity.runtimeContext);
    currentWorkspace = null;
  }
  if (identity.bindingStatus !== "ready") {
    render();
    return;
  }
  try {
    const runtimeHome = await fetchRuntimeHome(authConfig().homeEndpoint, identity);
    render(runtimeHome);
  } catch (error) {
    render(buildUsableRuntimeHome(errorMessage(error)));
  }
}

startOmsApp();
