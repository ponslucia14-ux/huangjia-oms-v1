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

const BUSINESS_MENU = Object.freeze([
  { key: "resident", label: "\u623f\u6001", schemaKey: "resident_flow_schema", caption: "\u5728\u4f4f / \u5165\u4f4f / \u51fa\u9986", tone: "green" },
  { key: "finance", label: "\u8d22\u52a1", schemaKey: "finance_schema", caption: "\u6536\u5165 / \u5e94\u6536 / \u5229\u6da6", tone: "red" },
  { key: "sales", label: "\u9500\u552e", schemaKey: "sales_schema", caption: "\u7ebf\u7d22 / \u7b7e\u7ea6 / \u8f6c\u5316", tone: "blue" },
  { key: "service", label: "\u670d\u52a1", schemaKey: "service_schema", caption: "\u5165\u4f4f / \u670d\u52a1\u4e2d / \u5b8c\u6210", tone: "orange" },
  { key: "hr", label: "\u4eba\u6548", schemaKey: "hr_schema", caption: "\u5728\u5c97 / \u6392\u73ed / \u7ee9\u6548", tone: "purple" },
]);

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
    chenchangyi: workspaceMeta("7. 陈昌辉（产护部总监）", "产护工作台", "产护工作台"),
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
  return data;
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
    renderRuntimeDataBlock("runtime_home_missing");
    return;
  }
  prepareFullSchemaRepaint();
  const currentUser = runtimeHome.current_user || {};
  $("#homeTitle").textContent = currentUser.name ? `晚上好，${currentUser.name}` : runtimeHome.home_title || "OMS";
  $("#homeSubtitle").textContent = "真实数据来自 OMS business_schema";
  $("#lockedUserName").textContent = currentUser.name || "OMS";
  $("#lockedUserRole").textContent = currentUser.role ? `${currentUser.role} / business_schema` : "business_schema";
  $("#workspaceStatus").textContent = "business_schema";
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

function renderRuntimeDataBlock(reason) {
  document.body.classList.add("identity-error-mode");
  $(".app-shell").innerHTML = `
    <section class="identity-error-panel" aria-label="OMS business schema required">
      <p class="eyebrow">OMS</p>
      <h1>business_schema 不可用</h1>
      <p>OMS UI 已禁止虚拟数据、演示数据和初始占位状态。请确认真实数据已完成校准，并且 business_schema 已生成。</p>
      <div class="error-actions">
        <strong>business_schema</strong>
        <span>${escapeHtml(reason)}</span>
      </div>
      <button id="retryAuthFlow" class="auth-retry-button" type="button">重新加载 business_schema</button>
    </section>
  `;
  bindRetry();
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
  const componentTree = schemaDrivenRenderer(runtimeHome);
  $("#scoreboardCards").innerHTML = componentTree.scoreboard.map(scoreCardTemplate).join("");
  $("#priorityCards").innerHTML = componentTree.priorityCards.map(priorityCardTemplate).join("");
  $("#sideBusinessMenu").innerHTML = componentTree.businessMenu.map(sideBusinessMenuTemplate).join("");
  $("#businessMenu").innerHTML = componentTree.businessMenu.map(businessMenuCardTemplate).join("");
  $("#personalWorkspacePanels").innerHTML = componentTree.workspacePanels.map(personalWorkspacePanelTemplate).join("");
  $("#sourceEvidenceRecords").innerHTML = componentTree.sourceEvidence.map(sourceEvidenceGroupTemplate).join("");
  $("#overviewGrid").innerHTML = componentTree.overview.map(overviewGroupTemplate).join("");
  $("#quickLinks").innerHTML = `
    <h3>Schema Renderer</h3>
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

function schemaDrivenRenderer(runtimeHome) {
  const schema = requireBusinessSchema(runtimeHome);
  const truthLock = requireDataTruthLock(runtimeHome);
  const sourceEvidence = requireSourceEvidenceVerifiedData(runtimeHome);
  const sections = runtimeSections(runtimeHome);
  return {
    source: "business_schema",
    pipeline: "business_schema -> single_user_business_os -> personal_workspace",
    scoreboard: schemaScoreboard(schema),
    priorityCards: schemaPriorityCards(schema, sections),
    businessMenu: schemaBusinessMenu(schema),
    workspacePanels: schemaWorkspacePanels(sections),
    sourceEvidence: schemaSourceEvidence(sourceEvidence),
    overview: schemaOverview(schema),
    quickLinks: schemaQuickLinks(schema, sections),
    truthLock,
  };
}

function requireBusinessSchema(runtimeHome) {
  const dashboard = (runtimeHome && runtimeHome.business_dashboard) || {};
  const schema = dashboard.business_schema || {};
  if (!schema.schema_version) {
    throw new Error("business_schema_required");
  }
  return schema;
}

function requireDataTruthLock(runtimeHome) {
  const dashboard = (runtimeHome && runtimeHome.business_dashboard) || {};
  const truthLock = dashboard.data_truth_alignment || {};
  if (truthLock.policy !== "source_evidence_required") {
    throw new Error("data_truth_alignment_required");
  }
  if (truthLock.data_source !== "source_evidence_verified_data") {
    throw new Error("source_evidence_verified_data_required");
  }
  return truthLock;
}

function requireSourceEvidenceVerifiedData(runtimeHome) {
  const dashboard = (runtimeHome && runtimeHome.business_dashboard) || {};
  const data = dashboard.source_evidence_verified_data || {};
  if (data.policy !== "source_evidence_verified_data") {
    throw new Error("source_evidence_verified_data_required");
  }
  return data;
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

function schemaScoreboard(schema) {
  const metrics = schemaMetrics(schema);
  return [
    scoreMetric("房态层", String(metrics.resident_count), "在住 / 入住 / 出馆", `${metrics.today_checkins} 入住 · ${metrics.today_checkouts} 出馆`, "green"),
    scoreMetric("财务层", formatMoney(metrics.finance_collected), "收入 / 应收 / 利润", `${metrics.finance_receivable} 应收 · ${formatMoney(metrics.finance_profit)} 利润`, "red"),
    scoreMetric("销售层", String(metrics.sales_contracts), "线索 / 签约 / 转化", `${metrics.sales_leads} 线索 · ${formatPercent(metrics.sales_conversion)} 转化`, "blue"),
    scoreMetric("服务层", String(metrics.service_progress), "入住准备 / 服务中 / 完成", `${metrics.service_exceptions} 异常 · ${metrics.service_completed} 完成`, "orange"),
    scoreMetric("人效层", String(metrics.hr_on_duty), "在岗 / 排班 / 绩效", `${metrics.hr_shifts} 排班 · ${metrics.hr_performance} 绩效`, "purple"),
  ];
}

function schemaPriorityCards(schema, sections) {
  const metrics = schemaMetrics(schema);
  return [
    scoreMetric("我的待办", String((sections.my_todos || {}).count || metrics.today_todos), "schema semantic_status", "当前用户", "red"),
    scoreMetric("当前风险", String(metrics.risk_alerts), "schema semantic_status", "需确认", "orange"),
    scoreMetric("今日关键任务", String((sections.role_home || {}).count || 0), "workspace schema view", "当前用户", "green"),
    scoreMetric("我的审批", String((sections.my_approvals || {}).count || 0), "workspace schema view", "确认事项", "blue"),
    scoreMetric("我的任务", String((sections.my_tasks || {}).count || 0), "workspace schema view", "可执行", "purple"),
  ];
}

function schemaBusinessMenu(schema) {
  const metrics = schemaMetrics(schema);
  const valueMap = {
    resident: metrics.resident_count,
    finance: formatMoney(metrics.finance_collected),
    sales: metrics.sales_contracts,
    service: metrics.service_progress,
    hr: metrics.hr_on_duty,
  };
  return BUSINESS_MENU.map((item) => ({
    ...item,
    value: String(valueMap[item.key] || 0),
    available: Boolean(schema[item.schemaKey]),
    source: item.schemaKey,
  }));
}

function schemaWorkspacePanels(sections) {
  return [
    workspacePanel("\u6211\u7684\u5f85\u529e", sections.my_todos, "\u5f53\u524d user_id \u5f85\u5904\u7406\u4e8b\u9879", "red"),
    workspacePanel("\u6211\u7684\u4efb\u52a1", sections.my_tasks, "\u5f53\u524d user_id \u6267\u884c\u4efb\u52a1", "green"),
    workspacePanel("\u6211\u7684\u5ba1\u6279", sections.my_approvals, "\u5f53\u524d user_id \u5ba1\u6279\u4e8b\u9879", "blue"),
    workspacePanel("\u6211\u7684\u6d41\u7a0b", sections.role_home, "\u5f53\u524d user_id \u4e1a\u52a1\u6d41\u7a0b", "purple"),
  ];
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
    sourceEvidenceGroup("\u623f\u6001\u6570\u636e", sourceEvidence.room_status_data),
    sourceEvidenceGroup("\u9500\u552e\u5408\u540c", sourceEvidence.sales_contract_data),
    sourceEvidenceGroup("\u8d22\u52a1\u6570\u636e", sourceEvidence.finance_data),
    sourceEvidenceGroup("\u670d\u52a1\u6570\u636e", sourceEvidence.service_data),
    sourceEvidenceGroup("\u8d22\u52a1\u4e8b\u4ef6", sourceEvidence.financial_events),
  ];
  return groups.filter((group) => group.records.length);
}

function sourceEvidenceGroup(title, records) {
  return {
    title,
    records: Array.isArray(records) ? records.slice(0, 6) : [],
  };
}

function schemaOverview(schema) {
  const metrics = schemaMetrics(schema);
  return [
    overviewGroup("房态层", [
      metric("在住", String(metrics.resident_count)),
      metric("入住", String(metrics.today_checkins)),
      metric("出馆", String(metrics.today_checkouts)),
      metric("房态记录", String(metrics.room_status_records)),
    ]),
    overviewGroup("财务层", [
      metric("收入", formatMoney(metrics.finance_income)),
      metric("应收", String(metrics.finance_receivable)),
      metric("已收", formatMoney(metrics.finance_collected)),
      metric("利润", formatMoney(metrics.finance_profit)),
    ]),
    overviewGroup("销售层", [
      metric("线索", String(metrics.sales_leads)),
      metric("签约", String(metrics.sales_contracts)),
      metric("转化", formatPercent(metrics.sales_conversion)),
      metric("流失", String(metrics.sales_lost)),
    ]),
    overviewGroup("服务层", [
      metric("入住准备", String(metrics.service_preparation)),
      metric("服务中", String(metrics.service_progress)),
      metric("异常处理", String(metrics.service_exceptions)),
      metric("完成服务", String(metrics.service_completed)),
    ]),
    overviewGroup("人效层", [
      metric("在岗", String(metrics.hr_on_duty)),
      metric("排班", String(metrics.hr_shifts)),
      metric("绩效", String(metrics.hr_performance)),
      metric("出勤率", formatPercent(metrics.hr_attendance_rate)),
    ]),
  ];
}

function schemaQuickLinks(schema, sections) {
  return [
    ...Object.values(sections).map((section) => section.title).filter(Boolean),
    schema.resident_flow_schema ? "房态层" : "",
    schema.finance_schema ? "财务层" : "",
    schema.sales_schema ? "销售层" : "",
    schema.service_schema ? "服务层" : "",
    schema.hr_schema ? "人效层" : "",
    "我的待办",
  ].filter(Boolean);
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
  return `<a href="#businessMenu"><span class="rank-badge tone-${escapeHtml(item.tone)}">${escapeHtml(item.label.slice(0, 1))}</span>${escapeHtml(item.label)}</a>`;
}

function businessMenuCardTemplate(item) {
  return `
    <article class="business-menu-card tone-${escapeHtml(item.tone)}" data-business-domain="${escapeHtml(item.key)}" data-schema-source="${escapeHtml(item.source)}">
      <header>
        <span class="score-icon" aria-hidden="true"></span>
        <strong>${escapeHtml(item.label)}</strong>
      </header>
      <b>${escapeHtml(item.value)}</b>
      <p>${escapeHtml(item.caption)}</p>
      <small>${item.available ? "business_schema locked" : "schema missing"}</small>
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
      <span>${escapeHtml(evidence.truth_source || "")} / ${escapeHtml(evidence.source_type || record.business_domain || "")} / ${escapeHtml(sourceFile)} / row ${escapeHtml(evidence.row_number || "")}</span>
      <small>${escapeHtml(evidence.record_id || record.work_item_id || "")}</small>
      ${fieldText ? `<em>${escapeHtml(fieldText)}</em>` : ""}
    </div>
  `;
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
    renderRuntimeDataBlock(errorMessage(error));
  }
}

startOmsApp();
