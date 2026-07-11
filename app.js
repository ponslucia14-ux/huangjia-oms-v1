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
  { key: "home", label: "首页", tone: "red" },
  { key: "action", label: "今日工作", tone: "orange" },
  { key: "status", label: "经营状态", tone: "green" },
  { key: "risk", label: "风险异常", tone: "purple" },
]);

const BUSINESS_FLOW_MENU = Object.freeze([
  { key: "room_flow", label: "\u623f\u6001", userLabel: "\u5165\u4f4f / \u51fa\u9986", schemaKey: "resident_flow_schema", steps: ["\u5165\u4f4f\u7533\u8bf7", "\u6392\u623f", "\u5165\u4f4f\u6267\u884c", "\u51fa\u9986\u7ed3\u7b97"], tone: "blue" },
  { key: "finance_flow", label: "\u8d22\u52a1", userLabel: "\u6536\u6b3e / \u5bf9\u8d26", schemaKey: "finance_schema", steps: ["\u6536\u6b3e", "\u5e94\u6536\u786e\u8ba4", "\u5bf9\u8d26", "\u5229\u6da6\u66f4\u65b0"], tone: "red" },
  { key: "sales_flow", label: "\u9500\u552e", userLabel: "\u7b7e\u7ea6 / \u6536\u6b3e", schemaKey: "sales_schema", steps: ["\u7b7e\u7ea6\u5ba2\u6237", "\u5408\u540c", "\u6536\u6b3e\u72b6\u6001", "\u9500\u552e\u7ed3\u679c"], tone: "green" },
  { key: "service_flow", label: "\u670d\u52a1", userLabel: "\u5165\u4f4f / \u62a4\u7406", schemaKey: "service_schema", steps: ["\u5165\u4f4f\u51c6\u5907", "\u670d\u52a1\u6267\u884c", "\u5f02\u5e38\u5904\u7406", "\u5b8c\u6210\u786e\u8ba4"], tone: "orange" },
  { key: "hr_flow", label: "\u4eba\u5458", userLabel: "\u6392\u73ed / \u6267\u884c", schemaKey: "hr_schema", steps: ["\u6392\u73ed", "\u6267\u884c", "\u7ee9\u6548", "\u590d\u76d8"], tone: "purple" },
]);

const NAVIGATION_MENU_TREE = Object.freeze([
  {
    key: "home",
    label: "首页",
    route: "home",
    target: "\u552f\u4e00\u9996\u9875",
    tone: "red",
    children: [
      { key: "today", label: "\u4eca\u65e5\u5de5\u4f5c", route: "action", target: "\u4eca\u65e5\u8981\u505a\u4ec0\u4e48", tone: "orange" },
      { key: "now", label: "\u73b0\u5728\u72b6\u6001", route: "status", target: "\u73b0\u5728\u53d1\u751f\u4ec0\u4e48", tone: "green" },
      { key: "exceptions", label: "\u98ce\u9669\u5f02\u5e38", route: "risk", target: "\u54ea\u91cc\u6709\u95ee\u9898", tone: "purple" },
    ],
  },
  {
    key: "work",
    label: "\u5de5\u4f5c",
    route: "action",
    target: "\u6211\u7684\u5de5\u4f5c",
    tone: "orange",
    children: [
      { key: "my_todos", label: "\u6211\u7684\u5f85\u529e", route: "action", target: "\u6211\u7684\u5f85\u529e", tone: "orange" },
      { key: "my_tasks", label: "\u6211\u7684\u4efb\u52a1", route: "action", target: "\u6211\u7684\u4efb\u52a1", tone: "green" },
      { key: "my_approvals", label: "\u6211\u7684\u5ba1\u6279", route: "action", target: "\u6211\u7684\u5ba1\u6279", tone: "blue" },
    ],
  },
  {
    key: "business",
    label: "\u4e1a\u52a1",
    route: "status",
    target: "\u4e1a\u52a1\u6d41",
    tone: "green",
    children: [
      { key: "room", label: "\u623f\u6001", route: "room", target: "\u623f\u6001\u6d41", tone: "blue" },
      { key: "finance", label: "\u8d22\u52a1", route: "finance", target: "\u8d22\u52a1\u6d41", tone: "red" },
      { key: "sales", label: "\u9500\u552e", route: "sales", target: "\u9500\u552e\u6d41", tone: "green" },
      { key: "service", label: "\u670d\u52a1", route: "service", target: "\u670d\u52a1\u6d41", tone: "orange" },
      { key: "hr", label: "\u4eba\u6548", route: "hr", target: "\u4eba\u6548\u6d41", tone: "purple" },
    ],
  },
  {
    key: "risk",
    label: "\u98ce\u9669",
    route: "risk",
    target: "\u98ce\u9669\u4e0e\u5f02\u5e38",
    tone: "purple",
    children: [
      { key: "delay", label: "\u5ef6\u8fdf\u4e8b\u9879", route: "risk", target: "\u5ef6\u8fdf\u4e8b\u9879", tone: "orange" },
      { key: "finance_risk", label: "\u8d22\u52a1\u5f02\u5e38", route: "finance", target: "\u8d22\u52a1\u5f02\u5e38", tone: "red" },
      { key: "room_risk", label: "\u623f\u6001\u51b2\u7a81", route: "room", target: "\u623f\u6001\u51b2\u7a81", tone: "blue" },
    ],
  },
  {
    key: "data",
    label: "\u6570\u636e",
    route: "data",
    target: "\u6570\u636e\u8ffd\u6eaf",
    tone: "blue",
    children: [
      { key: "trace", label: "\u6765\u6e90\u8ffd\u6eaf", route: "data", target: "\u6765\u6e90\u8ffd\u6eaf", tone: "blue" },
      { key: "history", label: "\u5386\u53f2\u67e5\u8be2", route: "data", target: "\u5386\u53f2\u67e5\u8be2", tone: "purple" },
    ],
  },
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
    boss: workspaceMeta("1. 石磊（主理人）", "总览 | 决策 | 授权", "主理办工作台"),
    huanhuan: workspaceMeta("2. 杨欢欢（销售）", "销售工作台", "销售工作台"),
    june: workspaceMeta("3. 刘芳羽（店总 + 销售）", "店总工作台", "店总工作台"),
    liujie: workspaceMeta("4. 刘晶（出纳）", "财务工作台", "财务工作台"),
    zhangjie: workspaceMeta("5. 张敬东（财务总监/会计）", "财务总监工作台", "财务总监工作台"),
    nana: workspaceMeta("6. 尚丽娜（管家）", "管家工作台", "管家工作台"),
    chenchangyi: workspaceMeta("7. 陈晶辉（产护部总监）", "产护工作台", "产护工作台"),
    zhouchen: workspaceMeta("8. 周志朋（厨师长）", "料理工作台", "料理工作台"),
    yaowei: workspaceMeta("9. 石昊盺（行政采购 + 照护师工资决算）", "行政采购工作台", "行政采购工作台"),
    songxue: workspaceMeta("10. 宗惠（人事行政）", "人事行政工作台", "人事行政工作台"),
    yuchun: workspaceMeta("11. 薛子渝（食材采购 + 销售）", "食材采购 + 销售工作台", "食材采购 + 销售工作台"),
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
const SCHEMA_RENDER_TARGETS = Object.freeze(["#scoreboardCards", "#priorityCards", "#sideBusinessMenu", "#businessMenu", "#personalWorkspacePanels", "#currentOperationsPanel", "#sourceEvidenceRecords", "#todayWorkData"]);
const OMS_BOOT_CHAIN_STEPS = Object.freeze(["js_entry", "dom_ready", "event_binding", "router_init", "state_layer", "app_mount"]);
const CONTRACT_REQUIRED_ENVELOPE_FIELDS = Object.freeze(["entity", "id", "status", "payload", "timestamp", "source"]);
const CONTRACT_REQUIRED_HOME_SECTIONS = Object.freeze(["Action", "Status", "Risk"]);
const FINAL_RENDER_COMMIT_TARGETS = Object.freeze([
  "#homeTitle",
  "#homeSubtitle",
  "#lockedUserName",
  "#lockedUserRole",
  "#lockedUserAvatar",
  "#compactPrimaryNav",
  "#workspaceStatus",
  "#scoreboardCards",
  "#priorityCards",
  "#sideBusinessMenu",
  "#businessMenu",
  "#personalWorkspacePanels",
  "#currentOperationsPanel",
  "#sourceEvidenceRecords",
  "#todayWorkData",
]);
let identity = identityBindingError("identity_bootstrap_not_started", "");
let currentWorkspace = null;
let latestRuntimeHome = null;
let bossCenterDataCache = {};
let bossCenterDataLoading = {};
let bossCenterQueryState = {
  sales: { page: 1, pageSize: 20, keyword: "", status: "", startDate: "", endDate: "" },
  finance: { page: 1, pageSize: 20, keyword: "", status: "", startDate: "", endDate: "" },
  operations: { page: 1, pageSize: 20, keyword: "", status: "", startDate: "", endDate: "" },
  data: { page: 1, pageSize: 20, keyword: "", status: "", startDate: "", endDate: "" },
};
let omsContract = null;
let authFlowState = AUTH_FLOW_STATES.INIT;
let authFlowAttempt = 0;
let schemaRenderSequence = 0;
let interactionLayerBound = false;
let navigationLayerBound = false;
let routerInitialized = false;
let interactionState = {
  current_route: "home",
  selected_task: "",
  current_room: "",
  active_workflow: "",
  selected_target: "",
  selected_action: "",
  api_status: "idle",
  api_message: "\u7b49\u5f85\u70b9\u51fb",
  execution_status: "idle",
  execution_message: "",
  closure_status: "",
  execution_trace_id: "",
  state_update_id: "",
  business_state_status: "",
  business_state_id: "",
  decision_summary: "",
  decision_why: "",
  retrigger_status: "",
  retrigger_message: "",
  lifecycle_stage: "",
  lifecycle_status: "",
  lifecycle_next_action: "",
  last_error: "",
};
let navigationState = {
  initialized: false,
  mounted: false,
  current_route: "home",
  current_menu_key: "home",
  selected_target: "",
};
let bootChainState = {
  js_entry: "pending",
  dom_ready: "pending",
  event_binding: "pending",
  router_init: "pending",
  state_layer: "pending",
  app_mount: "pending",
  last_error: "",
};
let contractLayerState = {
  loaded: false,
  source: "contract.json",
  version: "",
  render_source: "",
  validation_status: "pending",
  diff: [],
  fallback_render_allowed: false,
};
let uiChainState = {
  status: "pending",
  chain_name: "data -> behavior -> display",
  steps: {
    contract_loaded: "pending",
    api_payload_mapped: "pending",
    component_tree_built: "pending",
    dom_rendered: "pending",
    interaction_bound: "pending",
    api_refresh_bridge_bound: "pending",
  },
  diff: [],
  last_action: "",
  last_route: "",
  last_render_id: "",
};
let finalRenderVersion = 0;
let finalRenderSinkState = {
  status: "idle",
  render_flow: "data -> diff -> commit -> render -> commit DOM",
  queue_length: 0,
  locked: false,
  current_version: 0,
  committed_version: 0,
  last_hash: "",
  last_diff: [],
  last_mode: "",
  last_error: "",
};
const FINAL_RENDER_SINK = {
  name: "FINAL_RENDER_SINK",
  queue: [],
  locked: false,
  currentSnapshot: null,
};

markBootChainStep("js_entry", "executed");

function workspaceMeta(label, role, title) {
  return { label, role, title };
}

function resolveLockedIdentity() {
  const trustedContext = window.OMS_USER_CONTEXT || {};
  const trustedUserMap = window.OMS_FEISHU_USER_WORKSPACE_MAP || {};
  const trustedSource = String(trustedContext.source || "");
  const identityPayload = {
    user_id: window.OMS_CURRENT_USER_ID || trustedContext.user_id || "",
    open_id: trustedContext.open_id || "",
    union_id: trustedContext.union_id || "",
    workspace_key: ["feishu_webapp_sso", "local_owner_access"].includes(trustedSource) ? trustedContext.workspace_key || "" : "",
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
    source: trustedSource || "feishu_login_state",
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
    homeEndpoint: String(window.OMS_HOME_ENDPOINT || "/api/oms/home").trim(),
    executeEndpoint: String(window.OMS_EXECUTE_ENDPOINT || "/api/oms/execute").trim(),
    localOwnerEndpoint: String(window.OMS_LOCAL_OWNER_ACCESS_ENDPOINT || "/api/oms/local-owner-access").trim(),
    localOwnerAccessEnabled: Boolean(window.OMS_LOCAL_OWNER_ACCESS_ENABLED),
    redirectUri: String(window.OMS_FEISHU_REDIRECT_URI || CANONICAL_FEISHU_REDIRECT_URI).trim(),
    scopeList: validatedFeishuScopeList(window.OMS_FEISHU_SCOPE_LIST || FEISHU_LOGIN_SCOPE_LIST),
  };
}

async function bootstrapIdentity() {
  resetAuthFlowState({ clearLoginContext: false });
  const runtime = feishuRuntimeContext();
  const config = authConfig();
  if (!runtime.is_feishu_workbench_container) {
    if (isLocalOwnerAccessEnabled(config)) {
      return requestLocalOwnerAccess(config, "not_feishu_runtime_context", runtime);
    }
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
    if (isLocalOwnerAccessEnabled(config)) {
      return requestLocalOwnerAccess(config, `feishu_auth_failed:${errorMessage(error)}`, runtime);
    }
    return authFlowFailure(`feishu_auth_failed:${errorMessage(error)}`, "", runtime);
  }
}

function isLocalOwnerAccessEnabled(config) {
  return Boolean(config && config.localOwnerAccessEnabled && config.localOwnerEndpoint);
}

async function requestLocalOwnerAccess(config, reason, runtime) {
  try {
    if (!config.localOwnerEndpoint) {
      return authFlowFailure("missing_local_owner_access_endpoint", "", runtime);
    }
    setAuthFlowState(AUTH_FLOW_STATES.RESOLVING_WORKSPACE);
    const response = await fetch(config.localOwnerEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        reason,
        source: "local_owner_access",
        href: window.location.href,
      }),
    });
    if (!response.ok) {
      throw new Error(`local_owner_access_endpoint_${response.status}`);
    }
    const payload = unwrapContractPayload(await response.json(), "/api/oms/local-owner-access");
    if (!payload.user_id || !payload.workspace_key || payload.source !== "local_owner_access") {
      throw new Error("local_owner_access_invalid_payload");
    }
    window.OMS_USER_CONTEXT = payload;
    window.OMS_SESSION_TOKEN = String(payload.session_token || "");
    const localIdentity = resolveLockedIdentity();
    localIdentity.runtimeContext = runtime;
    if (localIdentity.bindingStatus !== "ready") {
      setAuthFlowState(AUTH_FLOW_STATES.BLOCKED);
      return localIdentity;
    }
    setAuthFlowState(AUTH_FLOW_STATES.AUTHENTICATED);
    return localIdentity;
  } catch (error) {
    return authFlowFailure(`local_owner_access_failed:${errorMessage(error)}`, "", runtime);
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
    const fail = (error) => {
      if (shouldUseLegacyFeishuAuthCode(error)) {
        requestLegacyFeishuAuthCode(config).then(resolve).catch(reject);
        return;
      }
      reject(error);
    };
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

function shouldUseLegacyFeishuAuthCode(error) {
  const errno = Number(error && error.errno);
  const message = errorMessage(error);
  return errno === 103 || /failed to fetch|not support|unsupported/i.test(message);
}

function requestLegacyFeishuAuthCode(config) {
  return new Promise((resolve, reject) => {
    if (!window.tt || typeof window.tt.requestAuthCode !== "function") {
      reject(new Error("feishu_request_auth_code_unavailable"));
      return;
    }
    window.tt.requestAuthCode({
      appId: config.appId,
      success: (res) => (res && res.code ? resolve(res.code) : reject(new Error("empty_legacy_auth_code"))),
      fail: (error) => reject(error),
    });
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
  const payload = unwrapContractPayload(await response.json(), "/api/feishu/identity");
  const data = payload.data || payload;
  if (!firstNonEmpty(data.user_id, data.open_id, data.union_id)) {
    throw new Error("auth_endpoint_missing_identity");
  }
  window.OMS_SESSION_TOKEN = String(data.session_token || "");
  return data;
}

function omsAuthenticatedHeaders(extra = {}) {
  const token = String(window.OMS_SESSION_TOKEN || "").trim();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : { ...extra };
}

async function fetchRuntimeHome(endpoint, lockedIdentity) {
  if (!endpoint) {
    throw new Error("missing_oms_home_endpoint");
  }
  const response = await fetch(endpoint, {
    method: "POST",
    headers: omsAuthenticatedHeaders({ "Content-Type": "application/json" }),
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
  const data = mapPayloadThroughContract(unwrapContractPayload(await response.json(), "/api/oms/home"), "/api/oms/home");
  const isRealtimeHome = data && (data.entry === "personal_workspace" || data.entry === "master_control_dashboard");
  if (!isRealtimeHome || !data.current_user || !data.business_dashboard) {
    throw new Error("runtime_home_invalid_payload");
  }
  if (!isTruthSourceHome(data)) {
    throw new Error("runtime_home_not_oms_truth_source");
  }
  bossCenterDataCache = {};
  bossCenterDataLoading = {};
  return data;
}

function omsApiEndpoint(path) {
  const config = authConfig();
  try {
    const url = new URL(config.homeEndpoint || "/api/oms/home", window.location.href);
    url.pathname = path;
    url.search = "";
    return url.toString();
  } catch (error) {
    return path;
  }
}

function bossCenterCacheKey(endpointKey, options = {}) {
  return [
    endpointKey,
    Number(options.page || 1),
    Number(options.pageSize || 20),
    options.includeTrace ? "trace" : "list",
    String(options.keyword || ""),
    String(options.status || ""),
    String(options.startDate || ""),
    String(options.endDate || ""),
    String(options.recordId || ""),
  ].join(":");
}

async function fetchBossCenterRecords(endpointKey, options = {}) {
  const page = Number(options.page || 1);
  const pageSize = Number(options.pageSize || 20);
  const includeTrace = Boolean(options.includeTrace);
  const cacheKey = bossCenterCacheKey(endpointKey, { ...options, page, pageSize, includeTrace });
  if (bossCenterDataCache[cacheKey]) {
    return bossCenterDataCache[cacheKey];
  }
  if (bossCenterDataLoading[cacheKey]) {
    return bossCenterDataLoading[cacheKey];
  }
  const endpointPath = `/api/oms/${endpointKey}`;
  const url = new URL(omsApiEndpoint(endpointPath), window.location.href);
  url.searchParams.set("page", String(page));
  url.searchParams.set("page_size", String(pageSize));
  if (includeTrace) {
    url.searchParams.set("include_trace", "1");
  }
  if (options.keyword) url.searchParams.set("keyword", String(options.keyword));
  if (options.status) url.searchParams.set("status", String(options.status));
  if (options.startDate) url.searchParams.set("start_date", String(options.startDate));
  if (options.endDate) url.searchParams.set("end_date", String(options.endDate));
  if (options.recordId) url.searchParams.set("record_id", String(options.recordId));
  bossCenterDataLoading[cacheKey] = fetch(url.toString(), {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`${endpointKey}_endpoint_${response.status}`);
      }
      const payload = mapPayloadThroughContract(unwrapContractPayload(await response.json(), endpointPath), endpointPath);
      bossCenterDataCache[cacheKey] = payload;
      return payload;
    })
    .finally(() => {
      delete bossCenterDataLoading[cacheKey];
    });
  return bossCenterDataLoading[cacheKey];
}

function cachedBossCenterRecords(endpointKey, options = {}) {
  const cacheKey = bossCenterCacheKey(endpointKey, options);
  return arrayValue((bossCenterDataCache[cacheKey] || {}).records).map((record, index) =>
    normalizeVisibleItem(record, index)
  );
}

function cachedBossCenterTotal(endpointKey, options = {}) {
  const cacheKey = bossCenterCacheKey(endpointKey, options);
  const payload = bossCenterDataCache[cacheKey] || {};
  return Number(payload.total || arrayValue(payload.records).length || 0);
}

function bossCenterQuery(route) {
  return bossCenterQueryState[route] || bossCenterQueryState.operations;
}

function operationsEndpointForTarget(target = interactionState.selected_target) {
  return String(target || "").trim() === "入住管理" ? "stays" : "rooms";
}

function requiredBossCenterLoads(route) {
  if (ownerCurrentNotInitialized(latestRuntimeHome)) return [];
  const query = bossCenterQuery(route);
  if (route === "sales") {
    return [
      ["sales", query],
      ["contracts", { ...query, page: 1, pageSize: 1 }],
    ];
  }
  if (route === "finance") {
    return [["finance", query]];
  }
  if (route === "operations") {
    return [[operationsEndpointForTarget(), query]];
  }
  if (route === "data") {
    return [
      ["sales", { page: 1, pageSize: 20, includeTrace: true }],
      ["contracts", { page: 1, pageSize: 20, includeTrace: true }],
      ["finance", { page: 1, pageSize: 20, includeTrace: true }],
      ["rooms", { page: 1, pageSize: 20, includeTrace: true }],
      ["stays", { page: 1, pageSize: 20, includeTrace: true }],
    ];
  }
  return [];
}

function ensureBossCenterRouteData(route) {
  const loads = requiredBossCenterLoads(route).filter(([endpointKey, options]) => {
    const cacheKey = bossCenterCacheKey(endpointKey, options);
    return !bossCenterDataCache[cacheKey];
  });
  if (!loads.length) {
    return null;
  }
  return Promise.all(loads.map(([endpointKey, options]) => fetchBossCenterRecords(endpointKey, options)));
}

async function executeBusinessAction(endpoint, lockedIdentity) {
  if (!endpoint) {
    throw new Error("missing_oms_execute_endpoint");
  }
  const response = await fetch(endpoint, {
    method: "POST",
    headers: omsAuthenticatedHeaders({ "Content-Type": "application/json" }),
    credentials: "include",
    body: JSON.stringify({
      user_id: lockedIdentity.userId,
      workspace_key: lockedIdentity.workspaceKey,
      route: interactionState.current_route,
      action: interactionState.selected_action || "execute",
      target: interactionState.selected_target,
      selected_task: interactionState.selected_task,
      current_room: interactionState.current_room,
      active_workflow: interactionState.active_workflow,
      source: "oms_ui",
      timestamp: new Date().toISOString(),
    }),
  });
  if (!response.ok) {
    throw new Error(`runtime_execute_endpoint_${response.status}`);
  }
  return mapPayloadThroughContract(unwrapContractPayload(await response.json(), "/api/oms/execute"), "/api/oms/execute");
}

async function ensureContractLayerLoaded() {
  if (omsContract) {
    return omsContract;
  }
  const contractUrl = String(window.OMS_CONTRACT_URL || "./contract.json").trim();
  if (!contractUrl) {
    throw new Error("contract_url_missing");
  }
  const response = await fetch(contractUrl, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`contract_load_${response.status}`);
  }
  const contract = await response.json();
  validateContractLayer(contract);
  omsContract = contract;
  contractLayerState = {
    loaded: true,
    source: "contract.json",
    version: contract.schema_version,
    render_source: contract.ui_render_contract.render_source,
    validation_status: "ready",
    diff: [],
    fallback_render_allowed: Boolean(contract.ui_render_contract.fallback_render_allowed),
  };
  syncContractDebugState();
  updateUiChainStep("contract_loaded", "ready", contract.schema_version);
  return omsContract;
}

function validateContractLayer(contract) {
  if (!contract || contract.schema_version !== String(window.OMS_CONTRACT_VERSION || "oms.contract.v1.0")) {
    throw new Error("contract_version_mismatch");
  }
  if (contract.source !== "OMS_TRUTH_SOURCE") {
    throw new Error("contract_source_mismatch");
  }
  if (!contract.rules || !contract.rules.ui_must_read_payload_not_raw_response || !contract.rules.ui_without_behavior_is_forbidden) {
    throw new Error("contract_rules_incomplete");
  }
  const envelope = (contract.data_contract || {}).response_envelope || {};
  const fields = envelope.required_fields || [];
  for (const field of CONTRACT_REQUIRED_ENVELOPE_FIELDS) {
    if (!fields.includes(field)) {
      throw new Error(`contract_missing_envelope_field_${field}`);
    }
  }
  const renderContract = contract.ui_render_contract || {};
  if (renderContract.render_source !== "contract.json") {
    throw new Error("contract_render_source_invalid");
  }
  if (renderContract.fallback_render_allowed !== false || renderContract.direct_api_field_mapping_allowed !== false) {
    throw new Error("contract_render_policy_invalid");
  }
  const homeSections = renderContract.home_sections || {};
  for (const section of CONTRACT_REQUIRED_HOME_SECTIONS) {
    if (!homeSections[section]) {
      throw new Error(`contract_missing_home_section_${section}`);
    }
  }
  if (!Array.isArray(renderContract.navigation_tree) || !renderContract.navigation_tree.length) {
    throw new Error("contract_navigation_tree_missing");
  }
  if (!Array.isArray(renderContract.payload_mapping) || !renderContract.payload_mapping.length) {
    throw new Error("contract_payload_mapping_missing");
  }
  if (!Array.isArray(((contract.action_contract || {}).ui_behavior_mapping_table)) || !contract.action_contract.ui_behavior_mapping_table.length) {
    throw new Error("contract_action_mapping_missing");
  }
}

function requireLoadedContract(reason = "contract_required") {
  if (!omsContract) {
    throw new Error(reason);
  }
  return omsContract;
}

function syncContractDebugState() {
  window.OMS_CONTRACT_STATE = { ...contractLayerState };
  document.documentElement.dataset.omsContractLayer = contractLayerState.loaded ? "ready" : "blocked";
  document.documentElement.dataset.omsContractVersion = contractLayerState.version || "";
  document.documentElement.dataset.omsRenderSource = contractLayerState.render_source || "";
  document.documentElement.dataset.omsContractValidation = contractLayerState.validation_status || "pending";
}

function updateUiChainStep(step, status, detail = "") {
  if (!Object.prototype.hasOwnProperty.call(uiChainState.steps, step)) {
    return;
  }
  uiChainState = {
    ...uiChainState,
    steps: { ...uiChainState.steps, [step]: status },
    status: Object.values({ ...uiChainState.steps, [step]: status }).every((value) => value === "ready") ? "ready" : "pending",
    last_error: status === "blocked" ? detail : uiChainState.last_error || "",
  };
  syncUiChainDebugState(detail);
}

function syncUiChainDebugState(detail = "") {
  window.OMS_UI_CHAIN_STATE = { ...uiChainState };
  document.documentElement.dataset.omsUiChain = uiChainState.status || "pending";
  document.documentElement.dataset.omsUiChainDiff = (uiChainState.diff || []).join("|");
  document.documentElement.dataset.omsUiChainDetail = detail || "";
}

function blockUiChain(reason) {
  uiChainState = {
    ...uiChainState,
    status: "blocked",
    diff: Array.from(new Set([...(uiChainState.diff || []), reason])),
    last_error: reason,
  };
  syncUiChainDebugState(reason);
}

function unwrapContractPayload(responsePayload, apiPath = "") {
  const contract = requireLoadedContract("contract_layer_not_loaded");
  if (
    responsePayload &&
    responsePayload.source === "OMS_TRUTH_SOURCE" &&
    Object.prototype.hasOwnProperty.call(responsePayload, "payload")
  ) {
    validateContractEnvelope(responsePayload, contract, apiPath);
    if (responsePayload.status && !["ready", "partial", "pending"].includes(responsePayload.status)) {
      throw new Error(`contract_status_${responsePayload.status}`);
    }
    return responsePayload.payload || {};
  }
  if (((contract.rules || {}).api_must_return_contract_envelope)) {
    throw new Error("contract_envelope_missing");
  }
  return (responsePayload && (responsePayload.data || responsePayload)) || {};
}

function validateContractEnvelope(envelope, contract, apiPath) {
  const requiredFields = (((contract.data_contract || {}).response_envelope || {}).required_fields) || CONTRACT_REQUIRED_ENVELOPE_FIELDS;
  for (const field of requiredFields) {
    if (!Object.prototype.hasOwnProperty.call(envelope, field)) {
      throw new Error(`contract_envelope_missing_${field}`);
    }
  }
  if (envelope.source !== (((contract.data_contract || {}).response_envelope || {}).source_required_value || "OMS_TRUTH_SOURCE")) {
    throw new Error("contract_envelope_source_mismatch");
  }
  const allowedStatuses = (((contract.data_contract || {}).response_envelope || {}).status_enum) || [];
  if (allowedStatuses.length && !allowedStatuses.includes(envelope.status)) {
    throw new Error(`contract_envelope_status_invalid_${envelope.status}`);
  }
  const apiSpec = contractApiSpec(apiPath);
  if (apiSpec && apiSpec.id && apiSpec.id !== envelope.id) {
    throw new Error(`contract_envelope_id_mismatch_${apiPath}`);
  }
}

function contractApiSpec(apiPath) {
  const contract = requireLoadedContract("contract_layer_not_loaded");
  const specs = (((contract.data_contract || {}).api_field_spec_table) || []);
  return specs.find((item) => item.api === apiPath) || null;
}

function mapPayloadThroughContract(payload, apiPath) {
  const contract = requireLoadedContract("contract_layer_not_loaded");
  const diff = validateContractPayloadPaths(payload, apiPath);
  const renderContract = contract.ui_render_contract || {};
  const mappedPayload = {
    ...payload,
    _contract_render: {
      source: renderContract.render_source,
      pipeline: renderContract.render_pipeline,
      contract_version: contract.schema_version,
      api: apiPath,
      required_home_sections: renderContract.required_home_sections || CONTRACT_REQUIRED_HOME_SECTIONS,
      payload_mapping: renderContract.payload_mapping || [],
      validation_status: diff.length ? "blocked" : "ready",
      diff,
    },
  };
  if (diff.length && ((renderContract.validation || {}).missing_required_payload_path_blocks_render)) {
    throw new Error(`contract_payload_missing:${diff.join(",")}`);
  }
  contractLayerState = { ...contractLayerState, validation_status: diff.length ? "blocked" : "ready", diff };
  syncContractDebugState();
  updateUiChainStep("api_payload_mapped", diff.length ? "blocked" : "ready", apiPath);
  return mappedPayload;
}

function validateContractPayloadPaths(payload, apiPath) {
  const spec = contractApiSpec(apiPath);
  if (!spec) {
    return [`missing_api_spec:${apiPath}`];
  }
  const diff = [];
  for (const path of spec.required_payload_fields || []) {
    if (String(path).includes(" or ")) {
      continue;
    }
    if (!hasContractPayloadPath(payload, path)) {
      diff.push(path);
    }
  }
  return diff;
}

function hasContractPayloadPath(payload, path) {
  const text = String(path || "").trim();
  if (!text) {
    return false;
  }
  if (text.startsWith("payload.")) {
    return hasPath({ payload }, text);
  }
  return hasPath(payload, text) || hasPath({ payload }, `payload.${text}`);
}

function hasPath(root, path) {
  const parts = String(path || "").split(".").filter(Boolean);
  let cursor = root;
  for (const part of parts) {
    if (!cursor || !Object.prototype.hasOwnProperty.call(cursor, part)) {
      return false;
    }
    cursor = cursor[part];
  }
  return true;
}

function isTruthSourceHome(data) {
  const source = data.runtime_source || ((data.business_dashboard || {}).runtime_source) || {};
  return source.type === "OMS_TRUTH_SOURCE" && source.mode === "single_source_of_truth" && source.remote_data_generation_allowed === false;
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

function userFacingError() {
  return "系统暂时无法完成此操作，请稍后重试。";
}

function render(runtimeHome = null) {
  if (identity.bindingStatus === "error") {
    renderIdentityError();
    return;
  }
  if (!["boss", "june"].includes(identity.workspaceKey)) {
    renderWorkspacePending();
    return;
  }
  if (!runtimeHome) {
    renderContractError("contract_runtime_home_missing");
    return;
  }
  let contractRuntimeHome = null;
  try {
    contractRuntimeHome = requireContractMappedRuntimeHome(runtimeHome);
  } catch (error) {
    renderContractError(errorMessage(error));
    return;
  }
  latestRuntimeHome = contractRuntimeHome;
  const snapshot = isMasterControlHome(contractRuntimeHome)
    ? renderMasterControlOS(contractRuntimeHome)
    : renderSingleUserBusinessOS(contractRuntimeHome);
  enqueueFinalRender(snapshot);
}

function nextFinalRenderVersion() {
  finalRenderVersion += 1;
  return finalRenderVersion;
}

function buildFinalRenderSnapshot(runtimeHome, componentTree, mode) {
  const currentUser = runtimeHome.current_user || {};
  const isBossHome = currentUser.workspace_key === "boss";
  const isEmp008Home = currentUser.emp_id === "EMP008" || currentUser.workspace_key === "june";
  const currentNotInitialized = (((runtimeHome.business_dashboard || {}).operating_mode || {}).current_status) === "NOT_INITIALIZED";
  const subtitle = isEmp008Home && currentNotInitialized
    ? "今天先确认入住、出馆、房态和运营异常"
    : currentNotInitialized
    ? "先完成十一人工作台设计，再由真实业务动作产生经营数据"
    : isBossHome
    ? "先看在住、销售、财务和风险，再进入对应中心处理"
    : "先做今日任务，再看当前状态和风险";
  const dom = {
    "#homeTitle": { text: isEmp008Home && currentNotInitialized ? "当前运营数据尚未初始化" : (currentNotInitialized ? "当前经营：尚未初始化" : (isBossHome ? "石磊，今天先看这三件事" : "刘芳羽，今天先处理这些运营事项")) },
    "#homeSubtitle": { text: subtitle },
    "#lockedUserName": { text: isBossHome ? "石磊" : (isEmp008Home ? "刘芳羽" : currentUser.name || "OMS") },
    "#lockedUserRole": { text: isEmp008Home ? "店总 + 销售" : currentUser.role || "\u5b9e\u65f6\u7ecf\u8425" },
    "#lockedUserAvatar": { attrs: { src: isEmp008Home ? "./assets/emp008-liufangyu-avatar.jpg?v=emp008-workbench-v1-20260712-2" : "./assets/emp001-boss-avatar.jpg?v=emp008-workbench-v1-20260712-2", alt: isEmp008Home ? "刘芳羽头像" : "石磊头像" } },
    "#compactPrimaryNav": { html: compactNavigationTemplate(componentTree.navigationTree), navigation: true },
    "#workspaceStatus": { text: currentNotInitialized ? "当前状态：尚未初始化" : "当前状态：正在发生什么" },
    "#scoreboardCards": { html: renderCollectionOrEmpty(componentTree.scoreboard, scoreCardTemplate, "今天没有系统生成的待办") },
    "#priorityCards": { html: renderCollectionOrEmpty(componentTree.businessFlows, priorityCardTemplate, "当前没有进行中的业务流") },
    "#sideBusinessMenu": { html: componentTree.navigationTree.map(navigationMenuTemplate).join(""), navigation: true },
    "#businessMenu": { html: renderCollectionOrEmpty(componentTree.riskCards, businessMenuCardTemplate, "当前没有风险异常") },
    "#personalWorkspacePanels": { html: renderCollectionOrEmpty(componentTree.workspacePanels, personalWorkspacePanelTemplate, "当前工作区暂无任务") },
    "#currentOperationsPanel": { html: currentOperationsPanelTemplate(currentUser) },
    "#sourceEvidenceRecords": { html: renderCollectionOrEmpty(componentTree.sourceEvidence, sourceEvidenceGroupTemplate, "来源记录将在打开明细时按需加载") },
    "#todayWorkData": { html: renderCollectionOrEmpty(componentTree.dataStrip, dataPillTemplate, "经营摘要暂未生成") },
  };
  const snapshot = {
    version: nextFinalRenderVersion(),
    source: "contract.json",
    mode,
    componentTree,
    dom,
    runtime_entry: runtimeHome.entry || "",
    created_at: new Date().toISOString(),
  };
  snapshot.hash = finalRenderSnapshotHash(snapshot);
  return snapshot;
}

function renderWorkspacePending() {
  document.body.classList.add("identity-error-mode");
  $(".app-shell").innerHTML = `
    <section class="identity-error-panel" aria-label="OMS 工作台建设提示">
      <p class="eyebrow">OMS</p>
      <h1>个人工作台尚未开放</h1>
      <p>当前仅开放石磊工作台。您的岗位工作台正在按真实职责设计，暂不使用旧页面。</p>
      <div class="error-actions">
        <strong>当前状态</strong>
        <span>等待岗位工作台实现</span>
      </div>
    </section>`;
}

function renderCollectionOrEmpty(items, template, emptyText) {
  const records = Array.isArray(items) ? items : [];
  if (records.length) {
    return records.map(template).join("");
  }
  return `<article class="workbench-empty-state" data-empty-state="true"><strong>${escapeHtml(emptyText)}</strong><span>数据可用后将在这里自动显示</span></article>`;
}

function currentOperationsPanelTemplate(currentUser = {}) {
  const empId = String(currentUser.emp_id || "");
  const tokenReady = Boolean(String(window.OMS_SESSION_TOKEN || "").trim());
  if (!["EMP003", "EMP004", "EMP008", "EMP009"].includes(empId)) {
    return `<article class="current-operation-card readonly"><header><h3>当前经营事实</h3><span>只读</span></header><p>当前岗位没有生产事实录入责任。查看不会改变经营数据。</p></article>`;
  }
  if (!tokenReady) {
    return `<article class="current-operation-card blocked"><header><h3>当前经营事实</h3><span>只读</span></header><p>当前飞书会话未取得写入授权。请重新从飞书工作台进入。</p></article>`;
  }
  if (empId === "EMP004") return financeCurrentFormTemplate();
  if (empId === "EMP003") return financeReviewTemplate();
  if (empId === "EMP008") return roomAndStayCurrentTemplate();
  return stayVerificationTemplate();
}

function financeCurrentFormTemplate() {
  return `
    <article class="current-operation-card">
      <header><div><h3>财务日结录入</h3><p>提交后等待张敬东复核，复核前不进入老板首页。</p></div><span>EMP004</span></header>
      <form data-current-operation="finance-record" class="current-operation-form">
        <label>经营日期<input name="effective_date" type="date" required></label>
        <label>收入<input name="income" type="number" min="0" step="0.01" required></label>
        <label>支出<input name="expense" type="number" min="0" step="0.01" required></label>
        <label>待收<input name="receivable" type="number" min="0" step="0.01" required></label>
        <label>待付<input name="payable" type="number" min="0" step="0.01" required></label>
        <label>当前资金余额<input name="cash_balance" type="number" min="0" step="0.01" required></label>
        <label class="full">录入原因<input name="reason" required placeholder="例如：7月11日财务日结"></label>
        <button type="submit">提交复核</button>
      </form>
      <p class="current-operation-feedback" data-current-feedback>等待录入</p>
    </article>`;
}

function financeReviewTemplate() {
  return `
    <article class="current-operation-card">
      <header><div><h3>财务 Current 复核</h3><p>只复核刘晶提交的待复核日结。</p></div><span>EMP003</span></header>
      <button type="button" class="secondary-command" data-current-load="finance-review">读取待复核记录</button>
      <div data-current-review-body class="current-review-body"><p>尚未读取</p></div>
      <p class="current-operation-feedback" data-current-feedback>等待复核</p>
    </article>`;
}

function roomAndStayCurrentTemplate() {
  return `
    <article class="current-operation-card">
      <header><div><h3>待确认入住</h3><p>核对客户、房间和实际到馆时间，确认后生成当前入住事实。</p></div><span>运营确认</span></header>
      <form data-current-operation="stay-check-in" class="current-operation-form">
        <label>入住编号<input name="stay_id" required></label>
        <label>客户姓名<input name="customer_name" required></label>
        <label>房号<input name="room_number" required></label>
        <label>实际入住时间<input name="checkin_time" type="datetime-local" required></label>
        <label>预计出馆时间<input name="expected_checkout_time" type="datetime-local"></label>
        <label class="full">确认说明<input name="reason" required placeholder="例如：客户已到馆，房间与实际入住时间已核对"></label>
        <button type="submit">确认当前入住</button>
      </form>
      <p class="current-operation-feedback" data-current-feedback>等待确认</p>
    </article>
    <article class="current-operation-card">
      <header><div><h3>出馆确认</h3><p>核对实际出馆时间，确认后客户退出当前入住，房间进入清洁中。</p></div><span>运营确认</span></header>
      <form data-current-operation="stay-check-out" class="current-operation-form">
        <label>入住编号<input name="stay_id" required></label>
        <label>实际出馆时间<input name="checkout_time" type="datetime-local" required></label>
        <label class="full">确认说明<input name="reason" required placeholder="例如：客户已完成出馆交接，实际时间已核对"></label>
        <button type="submit">确认出馆</button>
      </form>
      <p class="current-operation-feedback" data-current-feedback>等待确认</p>
    </article>
    <article class="current-operation-card">
      <header><div><h3>房态处理</h3><p>用于调房后的房态确认、清洁完成、维修和停用。</p></div><span>店总处理</span></header>
      <form data-current-operation="room-update" class="current-operation-form">
        <label>房号<input name="room_number" required></label>
        <label>房态<select name="status" required><option value="">请选择</option><option value="AVAILABLE">空房</option><option value="RESERVED">预留</option><option value="CLEANING">清洁中</option><option value="MAINTENANCE">维修中</option><option value="DISABLED">停用</option></select></label>
        <label>生效时间<input name="effective_time" type="datetime-local" required></label>
        <label class="full">处理原因<input name="reason" required placeholder="例如：清洁完成，房间恢复空房"></label>
        <label class="full">异常说明<input name="exception" placeholder="如无异常可不填"></label>
        <button type="submit">确认房态处理</button>
      </form>
      <p class="current-operation-feedback" data-current-feedback>等待处理</p>
    </article>
    <article class="current-operation-card">
      <header><div><h3>42间房首次确认</h3><p>逐房选择真实状态；所有42间完成后才能生成当前房态。</p></div><span>店总确认</span></header>
      <button type="button" class="secondary-command" data-current-load="room-form">开始确认42间房</button>
      <form data-current-operation="room-publish" class="current-operation-form room-current-form" hidden>
        <label class="full">确认时间<input name="effective_time" type="datetime-local" required></label>
        <div class="room-current-rows full" data-room-current-rows></div>
        <label class="full">确认原因<input name="reason" required placeholder="例如：Cutover逐房实地确认"></label>
        <button type="submit">生成当前房态</button>
      </form>
      <p class="current-operation-feedback" data-current-feedback>等待逐房确认</p>
    </article>
    <article class="current-operation-card">
      <header><div><h3>当前在住首次确认</h3><p>仅录入此刻真实在住，不得使用合同计划代替。</p></div><span>店总确认</span></header>
      <form data-current-operation="stay-publish" class="current-operation-form stay-current-form">
        <label class="full">确认时间<input name="effective_time" type="datetime-local" required></label>
        <div class="stay-current-rows full" data-stay-current-rows>${actualStayRowTemplate(1)}</div>
        <button type="button" class="secondary-command" data-add-stay-row>增加一条在住</button>
        <label class="full">确认原因<input name="reason" required placeholder="例如：当前在住逐人逐房确认"></label>
        <button type="submit">生成当前在住</button>
      </form>
      <p class="current-operation-feedback" data-current-feedback>等待实际入住确认</p>
    </article>`;
}

function actualStayRowTemplate(index) {
  return `<fieldset class="stay-current-row" data-stay-row><legend>在住 ${index}</legend><input data-stay-field="stay_id" placeholder="入住编号" required><input data-stay-field="customer_name" placeholder="客户姓名" required><input data-stay-field="room_number" placeholder="房号" required><input data-stay-field="checkin_time" type="datetime-local" required><input data-stay-field="expected_checkout_time" type="datetime-local"><select data-stay-field="status" required><option value="">选择状态</option><option value="IN_STAY">在住</option><option value="EXTENDED">延期在住</option></select></fieldset>`;
}

function stayVerificationTemplate() {
  return `<article class="current-operation-card"><header><div><h3>Actual Stay 服务核对</h3><p>核对店总发布的当前在住与实际服务状态。</p></div><span>EMP009</span></header><button type="button" class="secondary-command" data-current-load="stay-verify">读取当前在住</button><div data-current-review-body class="current-review-body"><p>尚未读取</p></div><p class="current-operation-feedback" data-current-feedback>等待核对</p></article>`;
}

function finalRenderSnapshotHash(snapshot) {
  return JSON.stringify({
    source: snapshot.source,
    mode: snapshot.mode,
    dom: snapshot.dom,
    contract_version: snapshot.componentTree.contract_version || "",
  });
}

function enqueueFinalRender(snapshot) {
  validateFinalRenderSnapshot(snapshot);
  FINAL_RENDER_SINK.queue = [snapshot];
  finalRenderSinkState = {
    ...finalRenderSinkState,
    status: "queued",
    queue_length: FINAL_RENDER_SINK.queue.length,
    current_version: snapshot.version,
    last_mode: snapshot.mode,
    last_error: "",
  };
  syncFinalRenderDebugState();
  commitFinalRenderQueue();
}

function commitFinalRenderQueue() {
  if (FINAL_RENDER_SINK.locked) {
    return;
  }
  const snapshot = FINAL_RENDER_SINK.queue.pop();
  FINAL_RENDER_SINK.queue = [];
  if (!snapshot) {
    return;
  }
  FINAL_RENDER_SINK.locked = true;
  finalRenderSinkState = { ...finalRenderSinkState, status: "committing", locked: true, queue_length: 0 };
  syncFinalRenderDebugState();
  try {
    const diff = diffFinalRenderSnapshot(snapshot);
    commitFinalRenderSnapshot(snapshot, diff);
    FINAL_RENDER_SINK.currentSnapshot = snapshot;
    finalRenderSinkState = {
      ...finalRenderSinkState,
      status: "committed",
      locked: false,
      committed_version: snapshot.version,
      current_version: snapshot.version,
      last_hash: snapshot.hash,
      last_diff: diff,
      last_mode: snapshot.mode,
      last_error: "",
    };
    syncFinalRenderDebugState();
  } catch (error) {
    finalRenderSinkState = { ...finalRenderSinkState, status: "blocked", locked: false, last_error: errorMessage(error) };
    syncFinalRenderDebugState();
    renderContractError(`final_render_failed:${errorMessage(error)}`);
  } finally {
    FINAL_RENDER_SINK.locked = false;
    if (FINAL_RENDER_SINK.queue.length) {
      commitFinalRenderQueue();
    }
  }
}

function validateFinalRenderSnapshot(snapshot) {
  const contract = requireLoadedContract("contract_layer_not_loaded");
  const finalContract = contract.final_render_contract || {};
  if (!snapshot || snapshot.source !== "contract.json") {
    throw new Error("final_render_snapshot_source_invalid");
  }
  for (const field of finalContract.required_snapshot_fields || ["version", "source", "mode", "componentTree", "dom", "hash"]) {
    if (!Object.prototype.hasOwnProperty.call(snapshot, field)) {
      throw new Error(`final_render_snapshot_missing_${field}`);
    }
  }
  for (const selector of finalContract.required_dom_commit_targets || FINAL_RENDER_COMMIT_TARGETS) {
    if (!snapshot.dom[selector]) {
      throw new Error(`final_render_missing_dom_target:${selector}`);
    }
  }
}

function diffFinalRenderSnapshot(snapshot) {
  const previous = FINAL_RENDER_SINK.currentSnapshot;
  if (!previous) {
    return ["initial_commit"];
  }
  const diff = [];
  for (const selector of Object.keys(snapshot.dom)) {
    const nextNode = snapshot.dom[selector] || {};
    const prevNode = (previous.dom || {})[selector] || {};
    if ((nextNode.html || "") !== (prevNode.html || "") || (nextNode.text || "") !== (prevNode.text || "") || JSON.stringify(nextNode.attrs || {}) !== JSON.stringify(prevNode.attrs || {})) {
      diff.push(selector);
    }
  }
  return diff;
}

function commitFinalRenderSnapshot(snapshot, diff) {
  prepareFullSchemaRepaint(snapshot);
  for (const [selector, patch] of Object.entries(snapshot.dom)) {
    commitFinalRenderPatch(selector, patch, snapshot);
  }
  renderClock();
  markSchemaRenderComplete(snapshot.componentTree);
  document.documentElement.dataset.omsFinalRender = "committed";
  document.documentElement.dataset.omsFinalRenderVersion = String(snapshot.version);
  document.documentElement.dataset.omsFinalRenderDiff = diff.join("|");
  if (snapshot.mode === "master_control") {
    document.documentElement.dataset.omsFinalRenderMode = "master_control";
  } else {
    document.documentElement.dataset.omsFinalRenderMode = "single_user";
  }
  renderActiveRouteIfNeeded();
}

function commitFinalRenderPatch(selector, patch, snapshot) {
  const target = $(selector);
  if (!target) {
    throw new Error(`final_render_target_missing:${selector}`);
  }
  if (Object.prototype.hasOwnProperty.call(patch, "html") && target.innerHTML !== patch.html) {
    target.innerHTML = patch.html;
  }
  if (Object.prototype.hasOwnProperty.call(patch, "text") && target.textContent !== patch.text) {
    target.textContent = patch.text;
  }
  for (const [name, value] of Object.entries(patch.attrs || {})) {
    if (target.getAttribute(name) !== String(value)) target.setAttribute(name, String(value));
  }
  target.dataset.renderSource = snapshot.source;
  target.dataset.renderState = "committed";
  target.dataset.renderVersion = String(snapshot.version);
  target.dataset.renderHash = snapshot.hash;
  if (patch.navigation) {
    target.dataset.navigationLayer = "mounted";
    target.dataset.menuTree = "ready";
    navigationState = {
      ...navigationState,
      mounted: true,
      current_menu_key: menuKeyForRoute(interactionState.current_route || navigationState.current_route),
    };
    syncNavigationDebugState();
    markActiveMenuTree();
  }
}

function syncFinalRenderDebugState() {
  window.OMS_FINAL_RENDER_STATE = { ...finalRenderSinkState };
  document.documentElement.dataset.omsFinalRender = finalRenderSinkState.status || "idle";
  document.documentElement.dataset.omsFinalRenderQueue = String(finalRenderSinkState.queue_length || 0);
  document.documentElement.dataset.omsFinalRenderLocked = finalRenderSinkState.locked ? "true" : "false";
  document.documentElement.dataset.omsFinalRenderVersion = String(finalRenderSinkState.committed_version || finalRenderSinkState.current_version || 0);
  document.documentElement.dataset.omsFinalRenderMode = finalRenderSinkState.last_mode || "";
  document.documentElement.dataset.omsFinalRenderError = finalRenderSinkState.last_error || "";
}

function requireContractMappedRuntimeHome(runtimeHome) {
  requireLoadedContract("contract_layer_not_loaded");
  const marker = runtimeHome && runtimeHome._contract_render;
  if (!marker || marker.source !== "contract.json") {
    throw new Error("contract_mapping_missing");
  }
  const diff = validateUiVsContractPayload(runtimeHome);
  if (diff.length) {
    throw new Error(`contract_ui_diff:${diff.join(",")}`);
  }
  return runtimeHome;
}

function validateUiVsContractPayload(runtimeHome) {
  const contract = requireLoadedContract("contract_layer_not_loaded");
  const renderContract = contract.ui_render_contract || {};
  const diff = [];
  for (const section of renderContract.required_home_sections || CONTRACT_REQUIRED_HOME_SECTIONS) {
    const config = (renderContract.home_sections || {})[section];
    if (!config) {
      diff.push(`missing_section:${section}`);
      continue;
    }
    for (const path of config.payload_paths || []) {
      if (!hasPath({ payload: runtimeHome }, path)) {
        diff.push(path);
      }
    }
  }
  contractLayerState = { ...contractLayerState, validation_status: diff.length ? "blocked" : "ready", diff };
  syncContractDebugState();
  return diff;
}

function prepareFullSchemaRepaint(snapshot = null) {
  document.body.classList.remove("identity-error-mode");
  clearSchemaRenderTargets();
  schemaRenderSequence += 1;
  document.documentElement.dataset.schemaRenderId = String(schemaRenderSequence);
  if (snapshot) {
    document.documentElement.dataset.schemaRenderSnapshot = String(snapshot.version);
  }
}

function clearSchemaRenderTargets() {
  for (const selector of SCHEMA_RENDER_TARGETS) {
    const target = $(selector);
    if (target) {
      target.replaceChildren();
      target.dataset.renderSource = "contract.json";
      target.dataset.renderState = "cleared_by_contract";
    }
  }
}

function renderLoading() {
  $("#homeTitle").textContent = "\u6211\u73b0\u5728\u5e94\u8be5\u505a\u4ec0\u4e48\uff1f";
  if ($("#homeSubtitle")) {
    $("#homeSubtitle").textContent = "\u6b63\u5728\u8bc6\u522b\u8eab\u4efd\uff0c\u7a0d\u7b49\u4e00\u4e0b";
  }
  $("#lockedUserName").textContent = "\u6b63\u5728\u8bc6\u522b";
  $("#lockedUserRole").textContent = "\u8eab\u4efd\u8bc6\u522b\u4e2d";
  $("#workspaceStatus").textContent = "\u51c6\u5907\u4eca\u65e5\u5de5\u4f5c";
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
    <section class="identity-error-panel" aria-label="OMS 身份认证提示">
      <p class="eyebrow">OMS</p>
      <h1>飞书身份认证失败</h1>
      <p>OMS 已识别飞书运行环境，但身份认证尚未完成，请稍后重试。</p>
      <div class="error-actions">
        <strong>认证状态：未完成</strong>
        <span>${escapeHtml(identity.userId ? "当前身份尚未分配工作台" : userFacingError())}</span>
      </div>
      <button id="retryAuthFlow" class="auth-retry-button" type="button">重新认证</button>
    </section>
  `;
  bindRetry();
}

function renderRuntimeContextBlock() {
  document.body.classList.add("identity-error-mode");
  $(".app-shell").innerHTML = `
    <section class="identity-error-panel" aria-label="OMS 飞书工作台提示">
      <p class="eyebrow">OMS</p>
      <h1>\u8bf7\u4ece\u98de\u4e66\u5de5\u4f5c\u53f0\u6253\u5f00</h1>
      <p>OMS 当前需要从飞书工作台进入，直接访问暂不可用。</p>
      <div class="error-actions">
        <strong>运行环境</strong>
        <span>未检测到飞书工作台环境</span>
      </div>
    </section>
  `;
}

function renderContractError(reason) {
  document.body.classList.add("identity-error-mode");
  contractLayerState = {
    ...contractLayerState,
    loaded: Boolean(omsContract),
    validation_status: "blocked",
    diff: [reason],
  };
  syncContractDebugState();
  $(".app-shell").innerHTML = `
    <section class="identity-error-panel" aria-label="OMS 页面加载提示">
      <p class="eyebrow">OMS</p>
      <h1>页面暂时无法加载</h1>
      <p>${escapeHtml(userFacingError())}</p>
      <div class="error-actions">
        <strong>页面状态</strong>
        <span>请稍后刷新页面</span>
      </div>
    </section>
  `;
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
  return buildFinalRenderSnapshot(runtimeHome, componentTree, "single_user");
}

function bindWorkActionFeedback() {
  if (interactionLayerBound) return;
  interactionLayerBound = true;
  document.addEventListener("click", handleWorkActionClick, true);
  document.addEventListener("click", handleWorkNavigationClick);
  document.addEventListener("click", handleBossRecordDetailClick);
  document.addEventListener("click", handleReadOnlyDetailDismiss);
  document.addEventListener("keydown", handleReadOnlyDetailKeydown);
  document.addEventListener("submit", handleCurrentOperationSubmit);
  document.addEventListener("click", handleCurrentOperationClick);
  bindMenuTreeClick();
  initializeRouter();
  markBootChainStep("event_binding", "bound");
  markBootChainStep("state_layer", "ready");
  updateUiChainStep("interaction_bound", "ready", "document_click_handlers_bound");
  updateUiChainStep("api_refresh_bridge_bound", "ready", "triggerInteractionApiBridge");
  syncInteractionDebugState();
  handleWorkRouteChange();
}

function initializeRouter() {
  if (routerInitialized) return;
  routerInitialized = true;
  window.addEventListener("hashchange", handleWorkRouteChange);
  const routeInfo = parseWorkRoute();
  navigationState = {
    ...navigationState,
    initialized: true,
    current_route: routeInfo.route || "home",
    current_menu_key: menuKeyForRoute(routeInfo.route || "home"),
    selected_target: routeInfo.target || "",
  };
  markBootChainStep("router_init", "bound");
  syncNavigationDebugState();
}

function mountMenuTree(tree = null) {
  const target = $("#sideBusinessMenu");
  if (!target) return;
  const resolvedTree = Array.isArray(tree) && tree.length ? tree : activeNavigationTree();
  target.innerHTML = resolvedTree.map(navigationMenuTemplate).join("");
  target.dataset.navigationLayer = "mounted";
  target.dataset.menuTree = "ready";
  navigationState = {
    ...navigationState,
    mounted: true,
    current_menu_key: menuKeyForRoute(interactionState.current_route || navigationState.current_route),
  };
  syncNavigationDebugState();
  markActiveMenuTree();
}

function bindMenuTreeClick() {
  if (navigationLayerBound) return;
  navigationLayerBound = true;
  document.addEventListener("click", handleNavigationMenuClick);
}

function handleNavigationMenuClick(event) {
  const trigger = event.target.closest("[data-nav-route]");
  if (!trigger) return;
  event.preventDefault();
  const route = trigger.dataset.navRoute || "home";
  const target = trigger.dataset.navTarget || trigger.textContent || route;
  const menuKey = trigger.dataset.navKey || menuKeyForRoute(route);
  navigationState = {
    ...navigationState,
    current_route: route,
    current_menu_key: menuKey,
    selected_target: target,
  };
  applyInteractionState({ action: "\u5207\u6362\u83dc\u5355", target, route, card: trigger.closest(".navigation-menu-node") });
  navigateToWorkRoute(route, target);
  renderInteractionPanel();
  markActiveMenuTree();
  syncNavigationDebugState();
}

function handleWorkActionClick(event) {
  const trigger = event.target.closest("[data-work-action]");
  if (!trigger) return;
  const card = trigger.closest("article, li, details");
  const target = trigger.dataset.workTarget || trigger.textContent || "\u5f53\u524d\u4e8b\u9879";
  const action = trigger.dataset.workAction || "\u5904\u7406";
  const route = routeForWorkTrigger(trigger, action, target, card);
  event.preventDefault();
  applyInteractionState({ action, target, route, card });
  navigateToWorkRoute(route, target);
  renderInteractionPanel();
  if (isExecutionWorkAction(action)) {
    triggerInteractionApiBridge();
  }
}

function handleBossRecordDetailClick(event) {
  const trigger = event.target.closest("[data-boss-view-record]");
  if (!trigger) return;
  event.preventDefault();
  event.stopPropagation();
  const route = normalizeBossCenterRoute(interactionState.current_route);
  const page = buildBossCenterPage(route, latestRuntimeHome || {});
  openBossRecordDetail(page, trigger.dataset.bossViewRecord || "");
}

function handleReadOnlyDetailDismiss(event) {
  const dialog = $("#bossReadOnlyDialog");
  if (!dialog || dialog.hidden) return;
  if (event.target.closest("[data-close-readonly-detail]") || event.target === dialog) {
    closeBossRecordDetail();
  }
}

function handleReadOnlyDetailKeydown(event) {
  if (event.key === "Escape") closeBossRecordDetail();
}

async function handleCurrentOperationSubmit(event) {
  const form = event.target.closest("[data-current-operation]");
  if (!form) return;
  event.preventDefault();
  const operation = form.dataset.currentOperation;
  const feedback = form.closest(".current-operation-card")?.querySelector("[data-current-feedback]");
  setCurrentOperationFeedback(feedback, "正在提交并校验身份…", "loading");
  try {
    let path = "";
    let payload = Object.fromEntries(new FormData(form).entries());
    if (operation === "finance-record") {
      path = "/api/oms/current/finance/record";
    } else if (operation === "stay-check-in") {
      path = "/api/oms/current/stays/check-in";
    } else if (operation === "stay-check-out") {
      path = "/api/oms/current/stays/check-out";
    } else if (operation === "room-update") {
      path = "/api/oms/current/rooms/update";
    } else if (operation === "room-publish") {
      path = "/api/oms/current/rooms/publish";
      payload.rooms = Array.from(form.querySelectorAll("[data-room-row]")).map((row) => ({
        room_number: row.dataset.roomNumber,
        status: row.querySelector("[data-room-status]").value,
        customer_name: row.querySelector("[data-room-customer]").value.trim(),
        exception: row.querySelector("[data-room-exception]").value.trim(),
      }));
    } else if (operation === "stay-publish") {
      path = "/api/oms/current/stays/publish";
      payload.stays = Array.from(form.querySelectorAll("[data-stay-row]")).map((row) => {
        const result = {};
        row.querySelectorAll("[data-stay-field]").forEach((field) => {
          result[field.dataset.stayField] = field.value.trim();
        });
        return result;
      });
    } else {
      throw new Error("不支持此项当前经营操作");
    }
    const result = await currentApiRequest(path, { method: "POST", payload });
    const record = result.record || result.stay_current || result.room_current || {};
    setCurrentOperationFeedback(feedback, `操作已完成${record.version ? `，当前为第 ${record.version} 版` : ""}`, "ready");
    if (operation === "finance-record") form.reset();
  } catch (error) {
    setCurrentOperationFeedback(feedback, userFacingError(), "error");
  }
}

async function handleCurrentOperationClick(event) {
  const addStay = event.target.closest("[data-add-stay-row]");
  if (addStay) {
    const rows = addStay.closest("form")?.querySelector("[data-stay-current-rows]");
    if (rows) rows.insertAdjacentHTML("beforeend", actualStayRowTemplate(rows.querySelectorAll("[data-stay-row]").length + 1));
    return;
  }
  const load = event.target.closest("[data-current-load]");
  if (load) {
    if (load.dataset.currentLoad === "room-form") await loadRoomCurrentForm(load);
    if (load.dataset.currentLoad === "finance-review") await loadFinanceCurrentReview(load);
    if (load.dataset.currentLoad === "stay-verify") await loadActualStayVerification(load);
    return;
  }
  const decision = event.target.closest("[data-current-decision]");
  if (!decision) return;
  const card = decision.closest(".current-operation-card");
  const feedback = card?.querySelector("[data-current-feedback]");
  try {
    const recordId = decision.dataset.recordId;
    const reasonInput = card?.querySelector("[data-current-review-reason]");
    const reason = String(reasonInput?.value || "").trim();
    if (!reason) throw new Error("必须填写复核原因");
    if (decision.dataset.currentDecision === "finance-approve" || decision.dataset.currentDecision === "finance-reject") {
      const approved = decision.dataset.currentDecision === "finance-approve";
      const result = await currentApiRequest("/api/oms/current/finance/review", { method: "POST", payload: { record_id: recordId, approved, reason } });
      setCurrentOperationFeedback(feedback, `财务复核完成：${chineseStatus(result.record.status)}`, "ready");
      await loadFinanceCurrentReview(card.querySelector("[data-current-load]"));
    } else if (decision.dataset.currentDecision === "stay-verify") {
      const result = await currentApiRequest("/api/oms/current/stays/verify", { method: "POST", payload: { record_id: recordId, reason } });
      setCurrentOperationFeedback(feedback, `服务核对完成：${chineseStatus(result.record.service_verification_status)}`, "ready");
      await loadActualStayVerification(card.querySelector("[data-current-load]"));
    }
  } catch (error) {
    setCurrentOperationFeedback(feedback, userFacingError(), "error");
  }
}

async function loadRoomCurrentForm(trigger) {
  const card = trigger.closest(".current-operation-card");
  const feedback = card.querySelector("[data-current-feedback]");
  setCurrentOperationFeedback(feedback, "正在读取42间房资源编号…", "loading");
  try {
    const url = new URL(omsApiEndpoint("/api/oms/room-resources"), window.location.href);
    url.searchParams.set("page", "1");
    url.searchParams.set("page_size", "100");
    const response = await fetch(url.toString(), { cache: "no-store", credentials: "include" });
    if (!response.ok) throw new Error(`房间资源读取失败 ${response.status}`);
    const data = unwrapContractPayload(await response.json(), "/api/oms/room-resources");
    const records = arrayValue(data.records);
    if (records.length !== 42) throw new Error(`房间资源必须为42间，当前${records.length}间`);
    const roomNumbers = records.map((record) => firstNonEmpty(record.room_number, record.room_no, record.room_id, record.name)).filter(Boolean);
    if (new Set(roomNumbers).size !== 42) throw new Error("42间房号不唯一，暂不能生成当前房态");
    card.querySelector("[data-room-current-rows]").innerHTML = roomNumbers.map(roomCurrentRowTemplate).join("");
    card.querySelector("[data-current-operation='room-publish']").hidden = false;
    setCurrentOperationFeedback(feedback, "已加载42个房号，请逐房确认真实状态", "ready");
  } catch (error) {
    setCurrentOperationFeedback(feedback, userFacingError(), "error");
  }
}

function roomCurrentRowTemplate(roomNumber) {
  return `<fieldset class="room-current-row" data-room-row data-room-number="${escapeHtml(roomNumber)}"><legend>${escapeHtml(roomNumber)}</legend><select data-room-status required><option value="">选择真实房态</option><option value="AVAILABLE">空房</option><option value="RESERVED">预留</option><option value="OCCUPIED">在住</option><option value="CLEANING">清洁</option><option value="MAINTENANCE">维修</option><option value="DISABLED">停用</option></select><input data-room-customer placeholder="当前客户（在住时填写）"><input data-room-exception placeholder="异常说明（如有）"></fieldset>`;
}

async function loadFinanceCurrentReview(trigger) {
  const card = trigger.closest(".current-operation-card");
  const body = card.querySelector("[data-current-review-body]");
  const summary = await currentApiRequest("/api/oms/current/summary");
  const record = summary.finance_pending;
  body.innerHTML = record
    ? `<dl><dt>经营日期</dt><dd>${escapeHtml(record.effective_time)}</dd><dt>收入</dt><dd>${escapeHtml(record.income)}</dd><dt>支出</dt><dd>${escapeHtml(record.expense)}</dd><dt>待收</dt><dd>${escapeHtml(record.receivable)}</dd><dt>待付</dt><dd>${escapeHtml(record.payable)}</dd><dt>余额</dt><dd>${escapeHtml(record.cash_balance)}</dd></dl><label>复核原因<input data-current-review-reason placeholder="填写复核依据" required></label><div class="current-decision-actions"><button type="button" data-current-decision="finance-approve" data-record-id="${escapeHtml(record.record_id)}">复核通过</button><button type="button" class="danger-command" data-current-decision="finance-reject" data-record-id="${escapeHtml(record.record_id)}">退回</button></div>`
    : "<p>当前没有待复核财务日结。</p>";
}

async function loadActualStayVerification(trigger) {
  const card = trigger.closest(".current-operation-card");
  const body = card.querySelector("[data-current-review-body]");
  const summary = await currentApiRequest("/api/oms/current/summary");
  const record = summary.actual_stay;
  body.innerHTML = record
    ? `<p>当前在住：<strong>${escapeHtml(record.resident_count)}</strong> 人</p><ul>${arrayValue(record.stays).map((stay) => `<li>${escapeHtml(stay.room_number)} · ${escapeHtml(stay.customer_name)} · ${escapeHtml(stay.status)}</li>`).join("")}</ul><label>核对原因<input data-current-review-reason placeholder="填写服务核对依据" required></label><button type="button" data-current-decision="stay-verify" data-record-id="${escapeHtml(record.record_id)}">确认服务状态一致</button>`
    : "<p>尚未生成当前在住。</p>";
}

async function currentApiRequest(path, options = {}) {
  const response = await fetch(omsApiEndpoint(path), {
    method: options.method || "GET",
    headers: omsAuthenticatedHeaders(options.payload ? { "Content-Type": "application/json" } : {}),
    credentials: "include",
    cache: "no-store",
    body: options.payload ? JSON.stringify(options.payload) : undefined,
  });
  const envelope = await response.json().catch(() => ({}));
  const payload = unwrapContractPayload(envelope, path);
  if (!response.ok) throw new Error("当前经营操作失败");
  return payload;
}

function setCurrentOperationFeedback(target, message, status) {
  if (!target) return;
  target.textContent = message;
  target.dataset.status = status;
}

function isExecutionWorkAction(action) {
  return ["处理", "审批", "执行", "开始处理", "处理事项", "处理风险", "标记处理中", "确认完成", "重新触发", "重新计算排房"].includes(String(action || ""));
}

function handleWorkNavigationClick(event) {
  const link = event.target.closest('a[href^="#"]');
  if (event.target.closest("[data-nav-route]")) return;
  if (!link || event.target.closest("[data-work-action]")) return;
  const route = routeFromAnchor(link.getAttribute("href"));
  if (!route) return;
  applyInteractionState({ action: "\u5207\u6362\u9875\u9762", target: link.textContent || route, route, card: null });
  renderInteractionPanel();
}

function handleWorkRouteChange() {
  const routeInfo = parseWorkRoute();
  if (!routeInfo.route) return;
  interactionState = {
    ...interactionState,
    current_route: routeInfo.route,
    selected_target: routeInfo.target || interactionState.selected_target,
  };
  document.documentElement.dataset.workRoute = interactionState.current_route;
  navigationState = {
    ...navigationState,
    current_route: interactionState.current_route,
    current_menu_key: menuKeyForRoute(interactionState.current_route),
    selected_target: routeInfo.target || navigationState.selected_target,
  };
  markActiveMenuTree();
  syncInteractionDebugState();
  syncNavigationDebugState();
  renderBossCenterPage(interactionState.current_route);
  renderInteractionPanel();
}

function applyInteractionState({ action, target, route, card }) {
  const selectedTarget = String(target || "\u5f53\u524d\u4e8b\u9879").trim();
  interactionState = {
    ...interactionState,
    current_route: route,
    selected_target: selectedTarget,
    selected_action: action,
    selected_task: route === "action" ? selectedTarget : interactionState.selected_task,
    current_room: route === "room" ? selectedTarget : interactionState.current_room,
    active_workflow: ["status", "business", "risk", "finance", "sales", "stay", "room", "operations", "organization", "service", "hr", "data"].includes(route) ? selectedTarget : interactionState.active_workflow,
    api_status: "ready",
    api_message: "\u5df2\u9009\u62e9\uff0c\u6b63\u5728\u51c6\u5907\u6267\u884c",
    execution_status: "pending",
    execution_message: "",
    closure_status: "",
    execution_trace_id: "",
    state_update_id: "",
    business_state_status: "",
    business_state_id: "",
    decision_summary: "",
    decision_why: "",
    retrigger_status: "",
    retrigger_message: "",
    last_error: "",
  };
  markSelectedActionCard(card);
  updateWorkspaceStatus();
  syncInteractionDebugState();
  updateUiChainInteraction(action, route, selectedTarget);
}

function updateUiChainInteraction(action, route, target) {
  uiChainState = {
    ...uiChainState,
    last_action: action || "",
    last_route: route || "",
    last_target: target || "",
  };
  syncUiChainDebugState(`action:${action || ""}|route:${route || ""}`);
}

function markSelectedActionCard(card) {
  document.querySelectorAll(".is-selected-action").forEach((node) => node.classList.remove("is-selected-action"));
  if (card) {
    card.classList.add("is-selected-action");
  }
}

function updateWorkspaceStatus() {
  const status = $("#workspaceStatus");
  if (status) {
    status.textContent = `\u5df2\u9009\u62e9\uff1a${interactionState.selected_target || "\u5f53\u524d\u4e8b\u9879"}\uff0c\u4e0b\u4e00\u6b65\uff1a${actionDisplayLabel(interactionState.selected_action)}`;
  }
}

function actionDisplayLabel(action) {
  const labels = {
    "open-action": "\u5f00\u59cb\u5904\u7406",
    "open-status": "\u67e5\u770b\u8be6\u60c5",
    "open-room": "\u67e5\u770b\u623f\u95f4",
    "trace-finance": "\u8ffd\u8e2a\u8d22\u52a1",
    "open-sales": "\u8ddf\u8fdb\u5ba2\u6237",
    "execute-task": "\u5904\u7406\u4efb\u52a1",
  };
  return labels[action] || action || "\u5904\u7406";
}

function routeForAction(action, target, card) {
  const text = [action, target, card && card.id, card && card.dataset ? card.dataset.businessDomain : ""].join(" ");
  if (/risk|\u98ce\u9669|\u5f02\u5e38|\u51b2\u7a81|\u5ef6\u8fdf|\u5904\u7406\u98ce\u9669/i.test(text)) return "risk";
  if (/open-room|room|\u623f|\u5165\u4f4f|\u51fa\u9986|\u6392\u623f/i.test(text)) return "room";
  if (/trace-finance|finance|\u8d22\u52a1|\u6536\u652f|\u6536\u6b3e|\u5bf9\u8d26/i.test(text)) return "finance";
  if (/open-sales|sales|\u9500\u552e|\u5ba2\u6237|\u7b7e\u7ea6/i.test(text)) return "sales";
  if (/\u8ffd\u8e2a|source|\u6765\u6e90|data/i.test(text)) return "data";
  if (/Action|\u5f00\u59cb|\u6267\u884c|\u5904\u7406|\u5f85\u529e|execute-task/i.test(text)) return "action";
  return "status";
}

function routeForWorkTrigger(trigger, action, target, card) {
  const explicitRoute = trigger.dataset.workRoute || (card && card.dataset ? card.dataset.workRoute : "");
  if (isSupportedWorkRoute(explicitRoute)) {
    return explicitRoute;
  }
  return routeForAction(action, target, card);
}

function isSupportedWorkRoute(route) {
  return ["home", "action", "status", "work", "business", "risk", "stay", "room", "finance", "sales", "operations", "organization", "service", "hr", "data"].includes(route);
}

function routeFromAnchor(href) {
  const routes = {
    "#homeTop": "home",
    "#todayWorkSection": "action",
    "#businessFlowSection": "status",
    "#riskExceptionSection": "risk",
    "#work": "action",
    "#business": "business",
    "#data": "data",
  };
  return routes[href] || "";
}

function navigateToWorkRoute(route, target) {
  const safeRoute = route || "status";
  const hash = `#${safeRoute}/${encodeURIComponent(target || "")}`;
  if (window.location.hash !== hash) {
    window.location.hash = hash;
  }
  handleWorkRouteChange();
  const section = sectionForWorkRoute(safeRoute);
  if (section && typeof section.scrollIntoView === "function") {
    section.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function parseWorkRoute() {
  const rawHash = String(window.location.hash || "").replace(/^#/, "");
  if (!rawHash) return { route: "", target: "" };
  const [route, ...rest] = rawHash.split("/");
  if (!isSupportedWorkRoute(route)) return { route: routeFromAnchor(`#${rawHash}`), target: "" };
  return { route, target: decodeURIComponent(rest.join("/") || "") };
}

function sectionForWorkRoute(route) {
  if (route === "action" || route === "work") return $("#todayWorkSection");
  if (route === "risk") return $("#riskExceptionSection");
  if (["sales", "finance", "stay", "operations", "organization", "room", "service", "hr", "data"].includes(route)) return ensureBossCenterPage();
  return $("#businessFlowSection");
}

function renderActiveRouteIfNeeded() {
  if (interactionState.current_route !== "home" || parseWorkRoute().route) {
    handleWorkRouteChange();
  }
}

function ensureInteractionPanel() {
  let panel = $("#interactionDetailPanel");
  if (panel) return panel;
  panel = document.createElement("section");
  panel.id = "interactionDetailPanel";
  panel.className = "interaction-detail-panel clickable-card";
  panel.setAttribute("aria-live", "polite");
  const host = $("#businessFlowSection");
  const before = $("#personalWorkspacePanels");
  if (host) {
    host.insertBefore(panel, before || null);
  }
  return panel;
}

function renderInteractionPanel() {
  const panel = ensureInteractionPanel();
  if (!panel) return;
  const route = interactionState.current_route || "home";
  if (route === "home" && !interactionState.selected_target) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  panel.dataset.route = route;
  if (identity.workspaceKey === "boss") {
    panel.innerHTML = `
      <header>
        <div>
          <span>${escapeHtml(routeLabel(route))}</span>
          <h3>${escapeHtml(interactionState.selected_target || "当前经营")}</h3>
          <p>${escapeHtml(routeDescription(route))}</p>
        </div>
      </header>
      <div class="interaction-state-grid boss-readonly-state">
        <div><span>查看模式</span><strong>只读经营判断</strong></div>
        <div><span>当前页面</span><strong>${escapeHtml(routeLabel(route))}</strong></div>
      </div>
    `;
    return;
  }
  panel.innerHTML = `
    <header>
      <div>
        <span>${escapeHtml(routeLabel(route))}</span>
        <h3>${escapeHtml(interactionState.selected_target || "\u5f53\u524d\u5de5\u4f5c")}</h3>
        <p>${escapeHtml(routeDescription(route))}</p>
      </div>
      ${workActionButton("\u5237\u65b0\u6570\u636e", "\u5237\u65b0\u6570\u636e", interactionState.selected_target || "\u5f53\u524d\u5de5\u4f5c")}
    </header>
    <div class="interaction-state-grid">
      <div><span>\u5f53\u524d\u4efb\u52a1</span><strong>${escapeHtml(interactionState.selected_task || "\u5f85\u9009\u62e9")}</strong></div>
      <div><span>\u5f53\u524d\u623f\u95f4</span><strong>${escapeHtml(interactionState.current_room || "\u5f85\u9009\u62e9")}</strong></div>
      <div><span>\u4e1a\u52a1\u6d41</span><strong>${escapeHtml(interactionState.active_workflow || "\u5f85\u9009\u62e9")}</strong></div>
      <div><span>\u6570\u636e\u72b6\u6001</span><strong>${escapeHtml(apiStatusText(interactionState))}</strong></div>
    </div>
    <div class="execution-closure-result">
      <div>
        <span>\u6267\u884c\u95ed\u73af</span>
        <strong>${escapeHtml(executionStatusText(interactionState))}</strong>
        <small>${escapeHtml(interactionState.execution_message || "\u7b49\u5f85\u6267\u884c\u52a8\u4f5c")}</small>
      </div>
      <div>
        <span>\u6267\u884c\u8bb0\u5f55</span>
        <strong>${escapeHtml(interactionState.execution_trace_id || "\u5c1a\u672a\u751f\u6210")}</strong>
        <small>${escapeHtml(interactionState.state_update_id ? `state: ${interactionState.state_update_id}` : "\u70b9\u51fb\u540e\u81ea\u52a8\u56de\u5199")}</small>
      </div>
      <div>
        <span>\u4e1a\u52a1\u72b6\u6001</span>
        <strong>${escapeHtml(businessStateText(interactionState))}</strong>
        <small>${escapeHtml(interactionState.business_state_id || "\u7b49\u5f85\u5199\u56de\u4e1a\u52a1\u72b6\u6001")}</small>
      </div>
      <div class="lifecycle-closure-panel">
        <span>\u751f\u547d\u5468\u671f\u95ed\u73af</span>
        <strong>${escapeHtml(lifecycleStatusText(interactionState))}</strong>
        <small>${escapeHtml(interactionState.lifecycle_next_action || "\u70b9\u51fb\u540e\u8bc6\u522b\u4e0b\u4e00\u4e2a\u4e1a\u52a1\u9636\u6bb5")}</small>
      </div>
    </div>
    <div class="decision-explainability-panel">
      <div>
        <span>\u4e3a\u4ec0\u4e48\u8fd9\u6837\u505a</span>
        <strong>${escapeHtml(interactionState.decision_summary || "\u70b9\u51fb\u540e\u751f\u6210\u51b3\u7b56\u8bf4\u660e")}</strong>
        <small>${escapeHtml(interactionState.decision_why || "\u7b49\u5f85\u51b3\u7b56\u94fe")}</small>
      </div>
      <div>
        <span>\u91cd\u65b0\u89e6\u53d1</span>
        <strong>${escapeHtml(retriggerStatusText(interactionState))}</strong>
        <small>${escapeHtml(interactionState.retrigger_message || "\u53ef\u4ee5\u4ece\u5f53\u524d\u7ed3\u679c\u91cd\u65b0\u8ba1\u7b97")}</small>
      </div>
    </div>
    <div class="interaction-action-row">
      ${workActionButton("\u6807\u8bb0\u5904\u7406\u4e2d", "\u6807\u8bb0\u5904\u7406\u4e2d", interactionState.selected_target || "\u5f53\u524d\u5de5\u4f5c")}
      ${workActionButton("\u786e\u8ba4\u5b8c\u6210", "\u786e\u8ba4\u5b8c\u6210", interactionState.selected_target || "\u5f53\u524d\u5de5\u4f5c")}
      ${workActionButton("\u67e5\u770b\u8ffd\u6eaf", "\u8ffd\u8e2a\u6765\u6e90", interactionState.selected_target || "\u5f53\u524d\u5de5\u4f5c")}
      ${workActionButton(retriggerActionLabel(route), retriggerActionLabel(route), interactionState.selected_target || "\u5f53\u524d\u5de5\u4f5c")}
    </div>
  `;
  restoreSelectedActionCard();
  updateWorkspaceStatus();
  syncInteractionDebugState();
}

function ensureBossCenterPage() {
  let panel = $("#bossCenterPage");
  if (panel) return panel;
  panel = document.createElement("section");
  panel.id = "bossCenterPage";
  panel.className = "boss-center-page product-home-block";
  panel.setAttribute("aria-live", "polite");
  const firstWorkSection = $("#todayWorkSection");
  const fallbackHost = $("#businessFlowSection");
  if (firstWorkSection && firstWorkSection.parentNode) {
    firstWorkSection.parentNode.insertBefore(panel, firstWorkSection);
  } else if (fallbackHost && fallbackHost.parentNode) {
    fallbackHost.parentNode.insertBefore(panel, fallbackHost.nextSibling);
  }
  return panel;
}

async function renderBossCenterPage(route) {
  const panel = ensureBossCenterPage();
  if (!panel) return;
  const normalizedRoute = normalizeBossCenterRoute(route);
  if (!isBossCenterRoute(normalizedRoute)) {
    panel.hidden = true;
    panel.replaceChildren();
    return;
  }
  if (!latestRuntimeHome) {
    panel.hidden = true;
    return;
  }
  const pendingLoad = ensureBossCenterRouteData(normalizedRoute);
  const page = buildBossCenterPage(normalizedRoute, latestRuntimeHome);
  page.loading = Boolean(pendingLoad);
  panel.hidden = false;
  panel.dataset.route = normalizedRoute;
  panel.dataset.dataSource = page.dataSource;
  panel.innerHTML = bossCenterPageTemplate(page);
  bindBossCenterControls(page);
  if (!pendingLoad) {
    return;
  }
  try {
    await pendingLoad;
    if (normalizeBossCenterRoute(interactionState.current_route) !== normalizedRoute) {
      return;
    }
    const refreshedPage = buildBossCenterPage(normalizedRoute, latestRuntimeHome);
    refreshedPage.loading = false;
    panel.dataset.dataSource = refreshedPage.dataSource;
    panel.innerHTML = bossCenterPageTemplate(refreshedPage);
    bindBossCenterControls(refreshedPage);
  } catch (error) {
    panel.insertAdjacentHTML(
      "beforeend",
      `<article class="boss-center-empty"><strong>经营数据加载失败</strong><p>${escapeHtml(userFacingError())}</p></article>`
    );
  }
}

function normalizeBossCenterRoute(route) {
  if (identity.workspaceKey === "june") return route || "home";
  if (["room", "service", "hr"].includes(route)) return "operations";
  return route || "home";
}

function isBossCenterRoute(route) {
  if (identity.workspaceKey === "june") return ["stay", "room", "allocation", "sales", "operations"].includes(route);
  return ["sales", "finance", "operations", "organization", "data"].includes(route);
}

function buildBossCenterPage(route, runtimeHome) {
  if (identity.workspaceKey === "june") return buildEmp008CenterPage(route, runtimeHome);
  if (ownerCurrentNotInitialized(runtimeHome)) return buildOwnerInitializationPage(route, runtimeHome);
  const repo = bossDataRepository(runtimeHome);
  if (route === "sales") return buildSalesCenterPage(repo);
  if (route === "finance") return buildFinanceCenterPage(repo);
  if (route === "data") return buildDataTracePage(repo);
  if (route === "organization") return buildOrganizationCenterPage(repo);
  return buildOperationsCenterPage(repo);
}

function buildEmp008CenterPage(route, runtimeHome) {
  const definitions = {
    stay: ["入住管理", "待确认入住、当前入住、入住变更与出馆确认", "当前入住尚未初始化", "只有刘芳羽确认的实际入住才进入当前入住"],
    room: ["房态管理", "42间房总览、调房、清洁、维修与停用", "当前房态尚未初始化", "42间房基础档案已保留，等待刘芳羽逐房确认"],
    allocation: ["排房管理", "未来排房总览、客户入住计划、房间调整、冲突检查与排房记录", "未来排房尚未初始化", "六月排房法当前仅采集真实规则，不进行自动排房"],
    sales: ["销售中心", "我的客户、我的签约、我的合同、我的收款状态与我的销售业绩", "个人销售事实尚未初始化", "只显示归属于刘芳羽的销售事实"],
    operations: ["运营异常", "房间冲突、入住异常、出馆异常与服务异常", "当前没有已确认的运营异常", "异常由真实运营动作产生，不从旧表格推算"],
  };
  const [title, subtitle, state, instruction] = definitions[route] || definitions.operations;
  return {
    route,
    title,
    subtitle,
    dataSource: "OMS 当前运营事实",
    emptyText: state,
    metrics: [bossCenterMetric(route === "room" ? "房间基础档案" : "初始化状态", route === "room" ? "42间待确认" : "尚未初始化", route)],
    records: [],
    pagination: null,
    endpoint: "",
    quality: { status: "NOT_INITIALIZED", snapshot_status: "NOT_INITIALIZED", snapshot_version: "NOT_INITIALIZED" },
    sourceGroups: [],
    initializationInstruction: instruction,
    operatingMode: (((runtimeHome || {}).business_dashboard || {}).operating_mode) || {},
  };
}

function ownerCurrentNotInitialized(runtimeHome) {
  return (((runtimeHome || {}).business_dashboard || {}).operating_mode || {}).current_status === "NOT_INITIALIZED";
}

function buildOwnerInitializationPage(route, runtimeHome) {
  const definitions = {
    sales: ["销售经营", "签约结果、合同与收款状态、例外审批", "销售事实尚未初始化", "由销售录入签约事实，财务确认到账后才显示"],
    finance: ["资金经营", "日结状态、待收待付与财务异常", "资金事实尚未初始化", "由出纳录入、会计复核后才显示"],
    operations: ["运营经营", "当前入住、当前房态与服务异常", "运营事实尚未初始化", "由管家提交现场资料、店总确认后才显示"],
    organization: ["组织执行", "今日责任人与未闭环事项", "执行事实尚未初始化", "各岗位开始使用工作台后自动形成"],
    data: ["审计追溯", "经营事实的来源、责任人与处理记录", "当前事实尚未产生", "历史资料已归档，不作为当前经营依据"],
  };
  const [title, subtitle, state, instruction] = definitions[route] || definitions.data;
  const mode = (((runtimeHome || {}).business_dashboard || {}).operating_mode) || {};
  return {
    route,
    title,
    subtitle,
    dataSource: "当前经营事实",
    emptyText: state,
    metrics: [bossCenterMetric("初始化状态", "尚未初始化", route)],
    records: [],
    pagination: null,
    endpoint: "",
    quality: { status: "NOT_INITIALIZED", snapshot_status: "NOT_INITIALIZED", snapshot_version: "NOT_INITIALIZED" },
    sourceGroups: [],
    initializationInstruction: instruction,
    operatingMode: mode,
  };
}

function buildOrganizationCenterPage(repo) {
  return {
    route: "organization",
    title: "组织执行",
    subtitle: "今日责任人与未闭环事项",
    dataSource: "岗位责任与执行记录",
    emptyText: "暂无已确认的组织执行事实",
    metrics: [],
    records: [],
    pagination: null,
    endpoint: "",
    quality: repo.quality,
    sourceGroups: [],
  };
}

function bossDataRepository(runtimeHome) {
  const dashboard = (runtimeHome && runtimeHome.business_dashboard) || {};
  const schema = dashboard.business_schema || {};
  const source = dashboard.source_evidence_available_data || {};
  const master = (runtimeHome && runtimeHome.master_control) || {};
  const globalView = master.global_view || {};
  const workspaces = master.business_workspaces || {};
  const salesQuery = bossCenterQuery("sales");
  const financeQuery = bossCenterQuery("finance");
  const operationsQuery = bossCenterQuery("operations");
  const operationsEndpoint = operationsEndpointForTarget();
  return {
    schema,
    source,
    master,
    globalView,
    workspaces,
    paged: {
      sales: cachedBossCenterRecords("sales", salesQuery),
      contracts: cachedBossCenterRecords("contracts", { ...salesQuery, page: 1, pageSize: 1 }),
      finance: cachedBossCenterRecords("finance", financeQuery),
      rooms: operationsEndpoint === "rooms" ? cachedBossCenterRecords("rooms", operationsQuery) : [],
      stays: operationsEndpoint === "stays" ? cachedBossCenterRecords("stays", operationsQuery) : [],
      traceSales: cachedBossCenterRecords("sales", { page: 1, pageSize: 20, includeTrace: true }),
      traceContracts: cachedBossCenterRecords("contracts", { page: 1, pageSize: 20, includeTrace: true }),
      traceFinance: cachedBossCenterRecords("finance", { page: 1, pageSize: 20, includeTrace: true }),
      traceRooms: cachedBossCenterRecords("rooms", { page: 1, pageSize: 20, includeTrace: true }),
      traceStays: cachedBossCenterRecords("stays", { page: 1, pageSize: 20, includeTrace: true }),
    },
    totals: {
      sales: cachedBossCenterTotal("sales", salesQuery),
      contracts: cachedBossCenterTotal("contracts", { ...salesQuery, page: 1, pageSize: 1 }),
      finance: cachedBossCenterTotal("finance", financeQuery),
      rooms: Number((((dashboard.metrics || {}).room_status_records) || 0)),
      stays: Number(((dashboard.truth_source || {}).counts || {}).stay_records || 0),
    },
    quality: dashboard.data_quality || {},
    operationsEndpoint,
    sourceRoot: ((dashboard.runtime_source || {}).truth_root) || ((dashboard.truth_source || {}).root) || "OMS_TRUTH_SOURCE",
  };
}

function buildSalesCenterPage(repo) {
  const sales = repo.schema.sales_schema || {};
  const records = dedupeVisibleRecords(arrayValue(repo.paged.sales));
  const query = bossCenterQuery("sales");
  return {
    route: "sales",
    title: "销售中心",
    subtitle: "签约客户、合同、收款状态与销售结果",
    dataSource: "OMS_TRUTH_SOURCE/sales.json + /api/oms/sales + /api/oms/contracts",
    emptyText: "正在读取真实销售数据",
    metrics: [
      bossCenterMetric("签约客户", humanWorkCount(firstPositive(repo.totals.sales, sales.signed_customers), "条", "暂无签约客户"), "sales"),
      bossCenterMetric("合同记录", humanWorkCount(repo.totals.contracts, "条", "暂无合同记录"), "sales"),
      bossCenterMetric("合同金额", formatMoney(sales.sales_amount || 0), "sales"),
      bossCenterMetric("销售结果", humanWorkCount(sales.sales_results || 0, "条已完成", "暂无完成记录"), "sales"),
    ],
    records,
    pagination: { ...query, total: repo.totals.sales },
    endpoint: "sales",
    quality: repo.quality,
    sourceGroups: [sourceEvidenceGroup("销售真实数据", records.slice(0, 6))],
  };
}

function buildFinanceCenterPage(repo) {
  const finance = repo.schema.finance_schema || {};
  const records = dedupeVisibleRecords(arrayValue(repo.paged.finance));
  const query = bossCenterQuery("finance");
  return {
    route: "finance",
    title: "财务中心",
    subtitle: "收款、待收待付、支出和对账追溯",
    dataSource: "OMS_TRUTH_SOURCE/finance.json + /api/oms/finance",
    emptyText: "正在读取真实财务数据",
    metrics: [
      bossCenterMetric("财务流水", humanWorkCount(repo.totals.finance, "条", "暂无财务流水"), "finance"),
      bossCenterMetric("收入", formatMoney(finance.income || 0), "finance"),
      bossCenterMetric("支出", formatMoney(finance.expenses || 0), "finance"),
      bossCenterMetric("利润", formatMoney(finance.profit || 0), "finance"),
      bossCenterMetric("待收", formatMoney(finance.receivable || 0), "finance"),
      bossCenterMetric("待付", formatMoney(finance.pending_payment_amount || 0), "finance"),
    ],
    records,
    pagination: { ...query, total: repo.totals.finance },
    endpoint: "finance",
    quality: repo.quality,
    sourceGroups: [sourceEvidenceGroup("财务真实数据", records.slice(0, 6))],
  };
}

function buildOperationsCenterPage(repo) {
  const resident = repo.schema.resident_flow_schema || {};
  const service = repo.schema.service_schema || {};
  const hr = repo.schema.hr_schema || {};
  const roomFlow = ((repo.globalView.business_flows || {}).room_flow) || {};
  const serviceFlow = ((repo.globalView.business_flows || {}).service_flow) || {};
  const hrFlow = ((repo.globalView.business_flows || {}).hr_flow) || {};
  const records = dedupeVisibleRecords(repo.operationsEndpoint === "stays" ? repo.paged.stays : repo.paged.rooms);
  const query = bossCenterQuery("operations");
  const total = repo.operationsEndpoint === "stays" ? repo.totals.stays : repo.totals.rooms;
  return {
    route: "operations",
    title: "运营中心",
    subtitle: "入住、房态、照护师和服务执行",
    dataSource: "OMS_TRUTH_SOURCE/room.json + OMS_TRUTH_SOURCE/stay.json + /api/oms/rooms + /api/oms/stays",
    emptyText: "正在读取真实运营数据",
    metrics: [
      bossCenterMetric("在住", humanWorkCount(resident.resident_count || 0, "个在住", "暂无在住"), "operations"),
      bossCenterMetric("房态记录", humanWorkCount(firstPositive(repo.totals.rooms, resident.room_status_records, roomFlow.task_count), "条", "暂无房态"), "operations"),
      bossCenterMetric("入住记录", humanWorkCount(repo.totals.stays, "条", "暂无入住记录"), "operations"),
      bossCenterMetric("照护师", hr.on_duty_staff ? humanWorkCount(hr.on_duty_staff, "人在岗", "") : "暂无结构化生产数据", "operations"),
    ],
    records,
    pagination: { ...query, total },
    endpoint: repo.operationsEndpoint,
    quality: repo.quality,
    sourceGroups: [sourceEvidenceGroup("运营真实数据", records.slice(0, 6))],
  };
}

function buildDataTracePage(repo) {
  const traceRecords = {
    sales: arrayValue(repo.paged.traceSales),
    contracts: arrayValue(repo.paged.traceContracts),
    finance: arrayValue(repo.paged.traceFinance),
    rooms: arrayValue(repo.paged.traceRooms),
    stays: arrayValue(repo.paged.traceStays),
  };
  const groups = [
    sourceEvidenceGroup("销售来源", traceRecords.sales.slice(0, 6)),
    sourceEvidenceGroup("合同来源", traceRecords.contracts.slice(0, 6)),
    sourceEvidenceGroup("财务来源", traceRecords.finance.slice(0, 6)),
    sourceEvidenceGroup("房态来源", traceRecords.rooms.slice(0, 6)),
    sourceEvidenceGroup("入住来源", traceRecords.stays.slice(0, 6)),
  ].filter((group) => group.records.length);
  const records = dedupeVisibleRecords(groups.flatMap((group) => group.records));
  return {
    route: "data",
    title: "数据追溯",
    subtitle: "来源、处理链路和执行记录",
    dataSource: "OMS_TRUTH_SOURCE/*.json + include_trace=1",
    emptyText: "正在读取真实追溯数据",
    metrics: [
      bossCenterMetric("来源分组", humanWorkCount(groups.length, "组来源", "暂无来源"), "data"),
      bossCenterMetric("可追溯记录", humanWorkCount(records.length, "条记录", "暂无记录"), "data"),
      bossCenterMetric("明细接口", humanWorkCount(5, "个接口", "暂无接口"), "data"),
      bossCenterMetric("按需追溯", "已启用", "data"),
    ],
    records: records.slice(0, 12),
    endpoint: "sales",
    quality: repo.quality,
    sourceGroups: groups.length ? groups : [sourceEvidenceGroup("真实来源", [])],
  };
}

function domainRecords(records, domain) {
  return arrayValue(records).filter((record) => {
    const text = [record.business_domain, record.event_type, record.event_action, record.title, record.role, record.workspace]
      .map((value) => String(value || ""))
      .join(" ");
    if (domain === "sales") return /sales|销售|签约|客户|合同/i.test(text);
    if (domain === "finance") return /finance|财务|收款|付款|收入|支出|对账/i.test(text);
    if (domain === "room") return /room|房|入住|出馆|排房/i.test(text);
    if (domain === "service") return /service|服务|护理|管家|照护|人效|hr/i.test(text);
    return false;
  });
}

function bossCenterMetric(label, value, domain) {
  return { label, value, domain };
}

function bossCenterPageTemplate(page) {
  const records = page.records.length
    ? page.records.map(bossCenterRecordTemplate).join("")
    : bossCenterEmptyTemplate(page.loading ? "正在读取经营数据" : page.emptyText, page.initializationInstruction);
  return `
    <header class="boss-center-header">
      <div>
        <span>${escapeHtml(page.title)}</span>
        <h2>${escapeHtml(page.subtitle)}</h2>
      </div>
      <div class="boss-center-health">
        <small>${escapeHtml(page.dataSource)}</small>
        ${bossDataHealthTemplate(page.quality)}
      </div>
    </header>
    <div class="boss-center-metrics">
      ${page.metrics.map(bossCenterMetricTemplate).join("")}
    </div>
    ${page.pagination ? bossCenterFilterTemplate(page) : ""}
    <div class="boss-center-layout">
      <section class="boss-center-records" aria-label="${escapeHtml(page.title)}记录">
        <div class="section-title">
          <h2>${page.operatingMode ? "初始化状态" : "当前经营记录"}</h2>
          <span>${escapeHtml(page.records.length ? `${page.records.length} 条可见记录` : page.emptyText)}</span>
        </div>
        ${records}
        ${page.pagination ? bossCenterPaginationTemplate(page) : ""}
      </section>
      ${page.sourceGroups.length ? `<aside class="boss-center-sources" aria-label="${escapeHtml(page.title)}数据来源">
        <h3>数据来源</h3>
        ${page.sourceGroups.map(sourceEvidenceGroupTemplate).join("")}
      </aside>` : ""}
    </div>
  `;
}

function bossCenterMetricTemplate(item) {
  const route = routeForProductItem(item);
  return `
    <article class="boss-center-metric tone-${escapeHtml(toneForBossCenterDomain(item.domain))}" data-work-action="${escapeHtml(actionForBossCenterDomain(item.domain))}" data-work-target="${escapeHtml(item.label)}" data-work-route="${escapeHtml(route)}">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
      <small>${item.value === "尚未初始化" ? "等待岗位操作产生事实" : "当前经营数据"}</small>
    </article>
  `;
}

function bossCenterRecordTemplate(record) {
  const title = record.title || record.name || record.summary || record.work_item_id || record.event_id || "真实业务记录";
  const fields = Array.isArray(record.display_fields) ? record.display_fields.slice(0, 3) : visibleDisplayFields(record).slice(0, 3);
  const evidence = record.source_evidence || {};
  const fieldText = fields.map((field) => `${friendlyFieldLabel(field.label)}：${field.value}`).join(" / ");
  const sourceLine = [
    basename(evidence.source_file || ""),
    evidence.row_number ? `第 ${evidence.row_number} 行` : "",
    record.status ? `状态：${record.status}` : "",
  ].filter(Boolean).join(" / ");
  const recordId = record.record_id || record.domain_id || record.work_item_id || record.contract_id || record.tx_id || record.room_id || record.stay_id || "";
  return `
    <article class="boss-center-record" data-record-id="${escapeHtml(recordId)}">
      <header>
        <strong>${escapeHtml(title)}</strong>
        <b class="confidence-label confidence-${escapeHtml(record.data_confidence || "uncalibrated_warning")}">${escapeHtml(confidenceLabel(record.data_confidence))}</b>
      </header>
      <p>${escapeHtml(fieldText || sourceLine || "真实记录已进入 OMS")}</p>
      <small>${escapeHtml(sourceLine || "来源待进一步结构化")}</small>
      <button class="daily-action-button boss-view-detail" type="button" data-boss-view-record="${escapeHtml(recordId)}">查看详情</button>
    </article>
  `;
}

function bossCenterFilterTemplate(page) {
  const query = page.pagination || {};
  return `
    <form class="boss-center-filter" data-boss-query-form="${escapeHtml(page.route)}">
      <label><span>搜索</span><input name="keyword" value="${escapeHtml(query.keyword || "")}" placeholder="姓名、合同、房号或记录号"></label>
      <label><span>状态</span><input name="status" value="${escapeHtml(query.status || "")}" placeholder="例如：已签约、已收入、已占用"></label>
      <label><span>开始日期</span><input name="startDate" type="date" value="${escapeHtml(query.startDate || "")}"></label>
      <label><span>结束日期</span><input name="endDate" type="date" value="${escapeHtml(query.endDate || "")}"></label>
      <button class="daily-action-button" type="submit">查询</button>
      <button class="daily-action-button secondary" type="button" data-boss-query-reset="${escapeHtml(page.route)}">重置</button>
    </form>
  `;
}

function bossCenterPaginationTemplate(page) {
  const query = page.pagination || {};
  const total = Number(query.total || 0);
  const pageSize = Number(query.pageSize || 20);
  const currentPage = Number(query.page || 1);
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  return `
    <nav class="boss-pagination" aria-label="${escapeHtml(page.title)}分页">
      <button type="button" data-boss-page="${currentPage - 1}" ${currentPage <= 1 ? "disabled" : ""}>上一页</button>
      <span>第 ${currentPage} / ${pageCount} 页，共 ${total} 条</span>
      <button type="button" data-boss-page="${currentPage + 1}" ${currentPage >= pageCount ? "disabled" : ""}>下一页</button>
    </nav>
  `;
}

function bossDataHealthTemplate(quality = {}) {
  const score = quality.score === undefined ? "待计算" : `${quality.score}/100`;
  const status = quality.snapshot_status || quality.status || "WARNING";
  const snapshot = quality.snapshot_version || "PENDING_DQ_SNAPSHOT";
  if (status === "NOT_INITIALIZED") {
    return `<div class="data-health-line"><span>当前经营</span><strong>尚未初始化</strong><span>等待真实业务动作</span></div>`;
  }
  return `<div class="data-health-line"><span>当前经营</span><strong>${escapeHtml(chineseStatus(status))}</strong><span>数据健康 ${escapeHtml(score)}</span><span>数据版本 ${escapeHtml(chineseStatus(snapshot))}</span></div>`;
}

function bindBossCenterControls(page) {
  const panel = document.querySelector("#bossCenterPage");
  if (!panel) return;
  const form = panel.querySelector("[data-boss-query-form]");
  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      bossCenterQueryState[page.route] = {
        ...bossCenterQuery(page.route),
        page: 1,
        keyword: String(formData.get("keyword") || "").trim(),
        status: String(formData.get("status") || "").trim(),
        startDate: String(formData.get("startDate") || "").trim(),
        endDate: String(formData.get("endDate") || "").trim(),
      };
      renderBossCenterPage(page.route);
    });
  }
  panel.querySelector("[data-boss-query-reset]")?.addEventListener("click", () => {
    bossCenterQueryState[page.route] = { page: 1, pageSize: 20, keyword: "", status: "", startDate: "", endDate: "" };
    renderBossCenterPage(page.route);
  });
  panel.querySelectorAll("[data-boss-page]").forEach((button) => {
    button.addEventListener("click", () => {
      bossCenterQueryState[page.route] = { ...bossCenterQuery(page.route), page: Number(button.dataset.bossPage || 1) };
      renderBossCenterPage(page.route);
    });
  });
}

async function openBossRecordDetail(page, recordId) {
  if (!recordId) return;
  const detail = ensureBossReadOnlyDialog();
  detail.hidden = false;
  document.body.classList.add("readonly-detail-open");
  detail.querySelector("[data-readonly-detail-body]").innerHTML = "<strong>正在读取来源与详情</strong>";
  detail.querySelector("[data-close-readonly-detail]")?.focus();
  try {
    const payload = await fetchBossCenterRecords(page.endpoint, { page: 1, pageSize: 1, recordId, includeTrace: true });
    const record = arrayValue(payload.records)[0];
    detail.querySelector("[data-readonly-detail-body]").innerHTML = record ? bossReadOnlyDetailTemplate(record) : "<strong>未找到该记录</strong>";
  } catch (error) {
    detail.querySelector("[data-readonly-detail-body]").innerHTML = `<strong>详情读取失败</strong><p>${escapeHtml(userFacingError())}</p>`;
  }
}

function ensureBossReadOnlyDialog() {
  let dialog = $("#bossReadOnlyDialog");
  if (dialog) return dialog;
  dialog = document.createElement("section");
  dialog.id = "bossReadOnlyDialog";
  dialog.className = "readonly-detail-dialog";
  dialog.hidden = true;
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-labelledby", "bossReadOnlyDialogTitle");
  dialog.innerHTML = `
    <article class="readonly-detail-sheet">
      <header class="readonly-detail-toolbar">
        <div><span>只读查看</span><h2 id="bossReadOnlyDialogTitle">业务详情与来源</h2></div>
        <button type="button" data-close-readonly-detail aria-label="关闭详情">关闭</button>
      </header>
      <div class="readonly-detail-body" data-readonly-detail-body aria-live="polite"></div>
      <footer>此窗口仅查看，不会修改状态或触发执行。</footer>
    </article>`;
  document.body.appendChild(dialog);
  return dialog;
}

function closeBossRecordDetail() {
  const dialog = $("#bossReadOnlyDialog");
  if (!dialog || dialog.hidden) return;
  dialog.hidden = true;
  document.body.classList.remove("readonly-detail-open");
}

function bossReadOnlyDetailTemplate(record) {
  const evidence = record.source_evidence || {};
  const fields = arrayValue(record.display_fields);
  const sourceFields = arrayValue(evidence.source_columns).join("、") || evidence.column_number || "未结构化";
  return `
    <header><div><span>只读详情 · 追踪来源</span><h3>${escapeHtml(record.title || record.record_id || "业务记录")}</h3></div><strong>${escapeHtml(chineseStatus(record.quality_status || "WARNING"))}</strong></header>
    <dl class="trace-chain">
      ${fields.map((field) => traceChainRow(friendlyFieldLabel(field.label), field.value)).join("")}
      ${traceRequiredRow("文件", evidence.source_file_name || basename(evidence.source_file || ""))}
      ${traceRequiredRow("工作表", evidence.source_sheet)}
      ${traceRequiredRow("行", evidence.row_number)}
      ${traceRequiredRow("字段", sourceFields)}
      ${traceRequiredRow("版本", evidence.source_version)}
      ${traceRequiredRow("数据快照", chineseStatus((latestRuntimeHome?.business_dashboard?.data_quality || {}).snapshot_version))}
      ${traceRequiredRow("数据健康", (latestRuntimeHome?.business_dashboard?.data_quality || {}).score)}
      ${traceRequiredRow("质量状态", chineseStatus(record.quality_status || (latestRuntimeHome?.business_dashboard?.data_quality || {}).snapshot_status))}
    </dl>
  `;
}

function bossCenterEmptyTemplate(text, instruction = "") {
  return `<article class="boss-center-empty"><strong>${escapeHtml(text)}</strong><p>${escapeHtml(instruction || "真实业务动作产生后将在这里显示。")}</p></article>`;
}

function toneForBossCenterDomain(domain) {
  if (domain === "finance") return "red";
  if (domain === "sales") return "green";
  if (domain === "operations") return "blue";
  return "purple";
}

function actionForBossCenterDomain(domain) {
  if (domain === "finance") return "trace-finance";
  if (domain === "sales") return "open-sales";
  if (domain === "operations") return "open-room";
  return "open-status";
}

function actionForRecord(record) {
  const domain = classifyVisibleDomain(record);
  if (domain === "finance_data") return "trace-finance";
  if (domain === "sales_contract_data") return "open-sales";
  if (domain === "room_status_data" || domain === "resident_data") return "open-room";
  return "execute-task";
}

function restoreSelectedActionCard() {
  const target = interactionState.selected_target;
  if (!target) return;
  document.querySelectorAll(".is-selected-action").forEach((node) => node.classList.remove("is-selected-action"));
  const candidates = Array.from(document.querySelectorAll(".clickable-card[data-work-target]"));
  const selected = candidates.find((node) => node.dataset.workTarget === target);
  if (selected) {
    selected.classList.add("is-selected-action");
  }
}

function routeLabel(route) {
  const labels = {
    action: "今日工作",
    status: "经营状态",
    risk: "风险异常",
    finance: "\u8d22\u52a1\u8ffd\u8e2a",
    sales: "\u9500\u552e\u4e2d\u5fc3",
    stay: "入住管理",
    room: "房态管理",
    allocation: "排房管理",
    operations: "\u8fd0\u8425\u4e2d\u5fc3",
    organization: "组织执行",
    data: "\u6765\u6e90\u8ffd\u6eaf",
  };
  return labels[route] || "首页";
}

function routeDescription(route) {
  const descriptions = {
    action: "\u8fd9\u91cc\u5904\u7406\u4eca\u5929\u8981\u505a\u7684\u4e8b",
    status: "\u8fd9\u91cc\u67e5\u770b\u6b63\u5728\u53d1\u751f\u4ec0\u4e48",
    risk: "\u8fd9\u91cc\u4e0b\u94bb\u9700\u8981\u5173\u6ce8\u7684\u95ee\u9898",
    finance: "\u8fd9\u91cc\u8ffd\u8e2a\u6536\u652f\u548c\u5bf9\u8d26",
    sales: "\u8fd9\u91cc\u67e5\u770b\u7b7e\u7ea6\u5ba2\u6237\u3001\u5408\u540c\u3001\u6536\u6b3e\u72b6\u6001\u548c\u9500\u552e\u7ed3\u679c",
    stay: "这里确认实际入住、记录入住变更并确认出馆",
    room: "这里确认42间房的真实状态并处理调房、清洁、维修和停用",
    allocation: "这里查看未来排房、客户入住计划、房间调整、冲突和排房记录",
    operations: "\u8fd9\u91cc\u67e5\u770b\u5165\u4f4f\u3001\u623f\u6001\u3001\u7167\u62a4\u5e08\u548c\u670d\u52a1\u6267\u884c",
    organization: "这里查看今日责任人与尚未闭环的事项",
    data: "\u8fd9\u91cc\u67e5\u770b\u6570\u636e\u6765\u6e90\u548c\u5904\u7406\u8bb0\u5f55",
  };
  return descriptions[route] || "\u4eca\u5929\u5148\u770b\u8981\u505a\u4ec0\u4e48";
}

function apiStatusText(state) {
  if (state.api_status === "loading") return "\u6b63\u5728\u5237\u65b0";
  if (state.api_status === "synced") return "\u5df2\u66f4\u65b0";
  if (state.api_status === "failed") return `\u5237\u65b0\u5931\u8d25\uff1a${state.last_error}`;
  return state.api_message || "\u7b49\u5f85\u70b9\u51fb";
}

function executionStatusText(state) {
  const status = state.execution_status || "idle";
  if (status === "executing") return "\u6b63\u5728\u6267\u884c";
  if (status === "closed" || status === "completed") return "\u5df2\u6267\u884c\u5e76\u56de\u5199";
  if (status === "blocked") return "\u5df2\u963b\u65ad";
  if (status === "failed") return "\u6267\u884c\u5931\u8d25";
  if (status === "pending") return "\u5f85\u6267\u884c";
  return state.closure_status || "\u7b49\u5f85\u70b9\u51fb";
}

function businessStateText(state) {
  if (state.business_state_status === "applied") return "\u5df2\u5199\u56de\u771f\u5b9e\u4e1a\u52a1\u72b6\u6001";
  if (state.execution_status === "blocked") return "\u5199\u56de\u963b\u65ad";
  if (state.execution_status === "failed") return "\u5199\u56de\u5931\u8d25";
  return "\u5f85\u5199\u56de";
}

function retriggerActionLabel(route) {
  return route === "room" ? "\u91cd\u65b0\u8ba1\u7b97\u6392\u623f" : "\u91cd\u65b0\u89e6\u53d1";
}

function retriggerStatusText(state) {
  if (state.retrigger_status === "completed") return "\u5df2\u91cd\u65b0\u89e6\u53d1";
  if (state.retrigger_status === "not_requested") return "\u672a\u91cd\u65b0\u89e6\u53d1";
  if (state.retrigger_status) return state.retrigger_status;
  return "\u5f85\u91cd\u65b0\u89e6\u53d1";
}

function lifecycleStatusText(state) {
  const stage = state.lifecycle_stage || "";
  const status = state.lifecycle_status || "";
  if (status === "closed") return stage ? `\u5df2\u95ed\u73af\uff1a${stage}` : "\u5df2\u95ed\u73af";
  if (status === "open") return stage ? `\u672a\u95ed\u73af\uff1a${stage}` : "\u672a\u95ed\u73af";
  return "\u5f85\u8bc6\u522b";
}

async function triggerInteractionApiBridge() {
  if (identity.bindingStatus !== "ready") {
    interactionState = { ...interactionState, api_status: "failed", execution_status: "blocked", last_error: "\u8eab\u4efd\u672a\u5c31\u7eea" };
    syncInteractionDebugState();
    renderInteractionPanel();
    return;
  }
  const config = authConfig();
  if (!config.homeEndpoint || !config.executeEndpoint) {
    interactionState = { ...interactionState, api_status: "failed", execution_status: "blocked", last_error: "\u672a\u914d\u7f6e\u6267\u884c\u63a5\u53e3" };
    syncInteractionDebugState();
    renderInteractionPanel();
    return;
  }
  interactionState = {
    ...interactionState,
    api_status: "loading",
    api_message: "\u6b63\u5728\u6267\u884c\u5e76\u56de\u5199 OMS",
    execution_status: "executing",
    execution_message: "\u6267\u884c\u4e2d",
    closure_status: "",
    execution_trace_id: "",
    state_update_id: "",
    lifecycle_stage: "",
    lifecycle_status: "",
    lifecycle_next_action: "",
    last_error: "",
  };
  syncInteractionDebugState();
  renderInteractionPanel();
  try {
    const execution = await executeBusinessAction(config.executeEndpoint, identity);
    const traceChain = execution.trace_chain || {};
    const businessStateWriteback = execution.business_state_writeback || {};
    const decisionChain = execution.decision_chain || {};
    const retriggerClosure = execution.retrigger_closure || {};
    const lifecycleClosure = execution.lifecycle_closure || {};
    const lifecycleDetection = lifecycleClosure.closure_detection || {};
    const whyItems = Array.isArray(decisionChain.why) ? decisionChain.why : [];
    interactionState = {
      ...interactionState,
      api_status: "loading",
      api_message: "\u52a8\u4f5c\u5df2\u6267\u884c\uff0c\u6b63\u5728\u5237\u65b0\u754c\u9762",
      execution_status: execution.closure_status || execution.status || "completed",
      execution_message: ((execution.ui_reflect || {}).message) || "\u4e1a\u52a1\u52a8\u4f5c\u5df2\u6267\u884c",
      closure_status: execution.closure_status || "",
      execution_trace_id: traceChain.execution_result_id || "",
      state_update_id: traceChain.state_update_id || "",
      business_state_status: businessStateWriteback.status || "",
      business_state_id: businessStateWriteback.business_state_id || "",
      decision_summary: decisionChain.decision_summary || "",
      decision_why: whyItems.slice(0, 3).join(" / "),
      retrigger_status: retriggerClosure.status || "",
      retrigger_message: retriggerClosure.message || "",
      lifecycle_stage: lifecycleClosure.current_stage_label || lifecycleClosure.current_stage || "",
      lifecycle_status: lifecycleDetection.status || "",
      lifecycle_next_action: lifecycleClosure.next_action || "",
      last_error: "",
    };
    syncInteractionDebugState();
    renderInteractionPanel();
    const runtimeHome = await fetchRuntimeHome(config.homeEndpoint, identity);
    interactionState = {
      ...interactionState,
      api_status: "synced",
      api_message: "\u5df2\u6267\u884c\u5e76\u5237\u65b0 OMS \u6570\u636e",
      last_error: "",
    };
    syncInteractionDebugState();
    render(runtimeHome);
    renderInteractionPanel();
  } catch (error) {
    interactionState = {
      ...interactionState,
      api_status: "failed",
      execution_status: interactionState.execution_status === "executing" ? "failed" : interactionState.execution_status,
      last_error: errorMessage(error),
    };
    syncInteractionDebugState();
    renderInteractionPanel();
  }
}

function isMasterControlHome(runtimeHome) {
  return Boolean(runtimeHome && runtimeHome.entry === "master_control_dashboard" && runtimeHome.master_control);
}

function renderMasterControlOS(runtimeHome) {
  const componentTree = masterControlLayerRenderer(runtimeHome);
  return buildFinalRenderSnapshot(runtimeHome, componentTree, "master_control");
}

function masterControlLayerRenderer(runtimeHome) {
  if (ownerCurrentNotInitialized(runtimeHome)) {
    return dailyWorkbenchLogicLayerRenderer(runtimeHome);
  }
  const master = runtimeHome.master_control || {};
  const globalView = master.global_view || {};
  const businessFlows = globalView.business_flows || {};
  const risk = globalView.risk_register || {};
  const execution = globalView.execution_status || {};
  const workspaces = master.business_workspaces || {};
  const schema = requireBusinessSchema(runtimeHome);
  const sourceEvidence = requireSourceEvidenceVerifiedData(runtimeHome);
  const visibleData = requireVisibleBusinessData(runtimeHome, sourceEvidence, runtimeSections(runtimeHome));
  return applyContractRenderMetadata({
    source: "master_control_layer_renderer",
    pipeline: "boss_master_control -> business_workspaces -> execution_layer -> ui",
    scoreboard: masterControlScoreboard(globalView, risk, execution, businessFlows, workspaces),
    businessFlows: masterControlBusinessFlows(businessFlows, schema, visibleData),
    taskMenu: masterControlMenu(globalView, risk, businessFlows, visibleData),
    navigationTree: contractNavigationTree(),
    riskCards: masterControlRiskCards(globalView, risk),
    workspacePanels: masterControlWorkspacePanels(workspaces, schema),
    sourceEvidence: dailyWritebackLog(visibleData),
    dataStrip: productDataStrip(visibleData, schema),
  }, runtimeHome);
}

function masterControlScoreboard(globalView, risk, execution, businessFlows, workspaces) {
  const actionCount = firstPositive(globalView.unfinished_task_count, execution.unfinished, globalView.task_count, execution.total);
  const riskCount = risk.risk_count || 0;
  const quality = (latestRuntimeHome?.business_dashboard?.data_quality) || {};
  return [
    scoreMetric("今日事项", humanWorkCount(actionCount, "件待处理", "今日暂无必做"), "需要本人处理的事项", actionCount ? "查看事项" : "无需处理", "red", actionCount),
    scoreMetric("经营风险", humanRiskCount(riskCount), "当前需要关注的问题", riskCount ? "立即查看" : "暂无异常", "orange", riskCount),
    scoreMetric("数据健康", quality.score === undefined ? "待验收" : String(quality.score) + "/100", "Current 数据可信度", quality.snapshot_status || quality.status || "WARNING", "green", Number(quality.score || 0)),
  ];
}

function masterControlBusinessFlows(businessFlows, schema, visibleData) {
  const entries = Object.entries(businessFlows);
  if (!entries.length) {
    return dailyBusinessFlows(schema, visibleData);
  }
  return entries.map(([key, flow]) => ({
    type: "business_flow_progress",
    key,
    userLabel: flow.label || key,
    value: humanWorkCount(flow.unfinished_count || flow.task_count || 0, "\u4ef6\u8fdb\u884c\u4e2d", "\u7b49\u5f85\u89e6\u53d1"),
    count: Number(flow.unfinished_count || flow.task_count || 0),
    currentStep: "全局流转",
    nextAction: "查看未完成事项",
    riskNote: humanRiskCount(flow.risk_count || 0),
    tone: masterToneForFlow(key),
  }));
}

function masterControlMenu(globalView, risk, businessFlows, visibleData) {
  return [
    { key: "home", label: "首页", value: "\u9996", caption: "经营入口", tone: "red" },
    { key: "action", label: "今日工作", value: "\u505a", caption: "要做什么", tone: "orange" },
    { key: "status", label: "经营状态", value: "\u770b", caption: "现在发生什么", tone: "green" },
    { key: "risk", label: "风险异常", value: "\u9632", caption: "哪里有问题", tone: "purple" },
  ];
}

function masterControlRiskCards(globalView, risk) {
  const quality = (latestRuntimeHome?.business_dashboard?.data_quality) || {};
  const qualityRisk = (quality.snapshot_status || quality.status) === "PASS" ? 0 : 1;
  return [
    dailyRiskCard("经营风险", risk.risk_count || 0, "查看风险明细", risk.risk_count ? "需要关注" : "暂无异常", "red"),
    dailyRiskCard("数据质量", qualityRisk, "查看数据健康与版本", qualityRisk ? "等待正式快照" : "数据健康", "purple"),
    dailyRiskCard("财务异常", risk.finance_count || 0, "核对待收待付", risk.finance_count ? "需要核对" : "暂无异常", "orange"),
    dailyRiskCard("房态异常", risk.room_count || 0, "核对房态与入住", risk.room_count ? "需要核对" : "暂无异常", "blue"),
  ];
}

function masterControlWorkspacePanels(workspaces, schema) {
  const entries = Object.entries(workspaces);
  if (!entries.length) {
    const metrics = schemaMetrics(schema);
    return [
      workspacePanel("销售中心", { count: metrics.sales_leads, items: [] }, "客户与签约", "green"),
      workspacePanel("财务中心", { count: metrics.finance_records, items: [] }, "收款与对账", "red"),
      workspacePanel("运营中心", { count: metrics.room_status_records, items: [] }, "入住与房态", "blue"),
    ];
  }
  return entries.map(([key, workspace]) => workspacePanel(
    workspace.name || key,
    {
      count: workspace.unfinished_count || workspace.task_count || 0,
      items: [
        {
          title: workspace.workspace || key,
          data_confidence: "source_verified",
          display_fields: [
            { label: "任务", value: humanWorkCount(workspace.task_count || 0, "\u4ef6\u5de5\u4f5c", "\u6682\u65e0\u4efb\u52a1") },
            { label: "未完成", value: humanWorkCount(workspace.unfinished_count || 0, "\u4ef6\u5f85\u5904\u7406", "\u5df2\u6e05\u7a7a") },
            { label: "风险", value: humanRiskCount(workspace.risk_count || 0) },
          ],
        },
      ],
    },
    workspace.role || "工作台",
    roleTone(key),
  ));
}

function masterControlOverview(globalView, risk, execution, businessFlows, workspaces) {
  return [
    overviewGroup("石磊今天先看", [
      metric("\u4eca\u5929\u8981\u505a", humanWorkCount(globalView.task_count || 0, "\u4ef6\u8981\u505a", "\u6682\u65e0\u5fc5\u505a")),
      metric("\u9700\u5173\u6ce8\u98ce\u9669", humanRiskCount(risk.risk_count || 0)),
      metric("\u8fd8\u8981\u63a8\u8fdb", humanWorkCount(globalView.unfinished_task_count || 0, "\u4ef6\u5f85\u63a8\u8fdb", "\u5df2\u6e05\u7a7a")),
    ]),
    overviewGroup("\u8c01\u5728\u5e72\u6d3b", [
      metric("\u8c01\u5728\u5904\u7406", humanWorkCount(Object.keys(workspaces).length || 0, "\u4eba\u5728\u5904\u7406", "\u7b49\u5f85\u5206\u914d")),
      metric("\u6b63\u5728\u53d1\u751f", humanWorkCount(Object.keys(businessFlows).length || 0, "\u6761\u4e1a\u52a1\u6d41", "\u7b49\u5f85\u4e1a\u52a1")),
    ]),
    overviewGroup("\u6267\u884c\u8fdb\u5ea6", Object.entries(execution.by_status || {}).map(([status, count]) => metric(status, humanWorkCount(count, "\u4ef6", "\u6682\u65e0")))),
  ];
}

function masterToneForFlow(key) {
  if (key.includes("finance")) return "red";
  if (key.includes("room")) return "blue";
  if (key.includes("sales")) return "green";
  if (key.includes("service")) return "orange";
  return "purple";
}

function markSchemaRenderComplete(componentTree) {
  for (const selector of SCHEMA_RENDER_TARGETS) {
    const target = $(selector);
    if (target) {
      target.dataset.renderSource = componentTree.source;
      target.dataset.renderState = "mounted";
      target.dataset.renderPipeline = componentTree.pipeline;
      target.dataset.renderId = String(schemaRenderSequence);
      target.dataset.contractVersion = componentTree.contract_version || "";
    }
  }
  document.documentElement.dataset.omsContractRender = componentTree.source === "contract.json" ? "mounted" : "blocked";
  document.documentElement.dataset.omsContractPipeline = componentTree.pipeline || "";
  updateUiChainStep("component_tree_built", "ready", componentTree.source);
  validateEndToEndUiChain(componentTree);
}

function dailyWorkbenchLogicLayerRenderer(runtimeHome) {
  const schema = requireBusinessSchema(runtimeHome);
  const truthLock = requireDataTruthLock(runtimeHome);
  const sourceEvidence = requireSourceEvidenceVerifiedData(runtimeHome);
  const sections = runtimeSections(runtimeHome);
  const visibleData = requireVisibleBusinessData(runtimeHome, sourceEvidence, sections);
  const productSections = ensureVisibleSections(sections, visibleData);
  const componentTree = dailyWorkbenchLogicLayer(schema, truthLock, visibleData, productSections);
  const operatingMode = ((runtimeHome.business_dashboard || {}).operating_mode) || {};
  if (operatingMode.current_status === "NOT_INITIALIZED") {
    applyNotInitializedWorkspace(componentTree);
  }
  return applyContractRenderMetadata(componentTree, runtimeHome);
}

function applyNotInitializedWorkspace(componentTree) {
  if (identity.workspaceKey === "june") {
    componentTree.scoreboard = [
      emp008EmptyAction("今日入住与出馆确认", "尚未产生待确认的入住或出馆事实", "入住管理", "blue"),
      emp008EmptyAction("待确认房态", "42间房等待首次现场确认", "房态管理", "green"),
      emp008EmptyAction("运营异常", "当前没有已确认的运营异常", "运营异常", "purple"),
    ];
    componentTree.businessFlows = [
      emp008EmptyFlow("入住管理", "运营事实确认", "确认实际入住后生成当前入住", "blue"),
      emp008EmptyFlow("房态管理", "42间房基础档案", "逐房确认后生成当前房态", "green"),
      emp008EmptyFlow("排房管理", "未来排房基础", "先记录真实排房，再沉淀六月排房规则", "purple"),
      emp008EmptyFlow("销售中心", "刘芳羽个人销售", "只显示本人客户、签约、合同、收款和业绩", "orange"),
    ];
    componentTree.dataStrip = [{ type: "data_pill", label: "当前运营", value: "尚未初始化", caption: "旧数据不会进入当前运营", tone: "blue" }];
    componentTree.sourceEvidence = [];
    componentTree.riskCards = [{
      type: "daily_risk_card", label: "初始化提醒", value: "待处理", count: 1,
      nextAction: "先确认42间房，再确认实际入住", riskNote: "不得使用合同计划代替实际在住", tone: "orange",
    }];
    componentTree.workspacePanels = [];
    return;
  }
  componentTree.scoreboard = [{
      type: "daily_empty_action",
      rank: 0,
      label: "当前没有可执行的经营决策",
      value: "尚未初始化",
      caption: "今日决策",
      delta: "尚未产生经营事实",
      currentStep: "工作台设计",
      nextAction: "等待岗位工作台启用",
      actionLabel: "查看经营状态",
      riskNote: "旧数据已归档",
      tone: "green",
    }];
    componentTree.businessFlows = [{
      key: "operating_initialization",
      type: "business_flow_progress",
      label: "当前经营",
      userLabel: "当前经营",
      value: "尚未初始化",
      count: 0,
      currentStep: "十一人工作台设计",
      nextAction: "定义谁看、谁录、谁产生数据",
      riskNote: "旧表格数据已隔离",
      status: "NOT_INITIALIZED",
      tone: "blue",
      source: "operating_mode",
    }];
    componentTree.dataStrip = [{
      type: "data_pill",
      label: "当前状态",
      value: "尚未初始化",
      caption: "旧经营数据已归档",
      tone: "blue",
    }];
    componentTree.sourceEvidence = [];
    componentTree.riskCards = [{
      type: "daily_risk_card",
      label: "经营基线",
      value: "尚未初始化",
      count: 0,
      nextAction: "等待真实岗位操作产生数据",
      riskNote: "旧数据不会进入当前经营",
      tone: "purple",
    }];
    componentTree.workspacePanels = [];
}

function emp008EmptyAction(label, detail, routeLabel, tone) {
  return {
    type: "daily_empty_action", rank: 0, label, value: "尚未初始化", caption: "今日运营",
    delta: detail, currentStep: "等待真实操作", nextAction: `进入${routeLabel}`,
    actionLabel: "查看详情", riskNote: "旧数据已隔离", tone,
  };
}

function emp008EmptyFlow(label, currentStep, nextAction, tone) {
  return {
    key: label, type: "business_flow_progress", label, userLabel: label, value: "尚未初始化", count: 0,
    currentStep, nextAction, riskNote: "仅由刘芳羽确认产生当前事实", status: "NOT_INITIALIZED", tone, source: "operating_mode",
  };
}

function dailyWorkbenchLogicLayer(schema, truthLock, visibleData, sections) {
  return {
    source: "daily_workbench_logic_layer",
    pipeline: "single_entry_home -> today_work -> business_flow -> risk_exception",
    scoreboard: dailyTodayTasks(schema, sections, visibleData),
    businessFlows: dailyBusinessFlows(schema, visibleData),
    taskMenu: dailyTaskMenu(schema, sections, visibleData),
    navigationTree: contractNavigationTree(),
    riskCards: dailyRiskExceptions(schema, sections, visibleData),
    workspacePanels: dailyWorkspacePanels(sections),
    sourceEvidence: dailyWritebackLog(visibleData),
    dataStrip: productDataStrip(visibleData, schema),
    truthLock,
  };
}

function contractNavigationTree() {
  if (identity.workspaceKey === "boss") {
    return emp001NavigationTree();
  }
  if (identity.workspaceKey === "june") {
    return emp008NavigationTree();
  }
  const contract = requireLoadedContract("contract_layer_not_loaded");
  const tree = ((contract.ui_render_contract || {}).navigation_tree) || [];
  if (!Array.isArray(tree) || !tree.length) {
    throw new Error("contract_navigation_tree_missing");
  }
  const profiles = ((contract.ui_render_contract || {}).workspace_menu_profiles) || {};
  const profile = profiles[identity.workspaceKey] || profiles.boss;
  const allowedKeys = new Set((profile && profile.menu_keys) || []);
  if (!allowedKeys.size) {
    throw new Error(`workspace_menu_profile_missing:${identity.workspaceKey || "unknown"}`);
  }
  return tree.filter((node) => allowedKeys.has(node.key));
}

function emp008NavigationTree() {
  const child = (key, label, route, tone) => ({ key, label, route, target: label, tone });
  return [
    {
      key: "store_home", label: "首页", route: "home", target: "今日运营", tone: "red",
      children: [
        child("store_today_stay", "今日入住与出馆", "action", "orange"),
        child("store_room_pending", "待确认房态", "action", "blue"),
        child("store_home_exception", "运营异常", "operations", "purple"),
      ],
    },
    {
      key: "store_stay", label: "入住管理", route: "stay", target: "入住管理", tone: "blue",
      children: [
        child("store_stay_pending", "待确认入住", "stay", "blue"),
        child("store_stay_current", "当前入住", "stay", "green"),
        child("store_stay_change", "入住变更", "stay", "teal"),
        child("store_stay_checkout", "出馆确认", "stay", "orange"),
      ],
    },
    {
      key: "store_room", label: "房态管理", route: "room", target: "房态管理", tone: "green",
      children: [
        child("store_room_overview", "房间总览", "room", "green"),
        child("store_room_transfer", "调房", "room", "blue"),
        child("store_room_clean", "清洁状态", "room", "teal"),
        child("store_room_maintenance", "维修状态", "room", "orange"),
        child("store_room_disabled", "停用管理", "room", "red"),
      ],
    },
    {
      key: "store_allocation", label: "排房管理", route: "allocation", target: "排房管理", tone: "purple",
      children: [
        child("store_allocation_overview", "未来排房总览", "allocation", "blue"),
        child("store_june_method", "六月排房法", "allocation", "purple"),
        child("store_customer_plan", "客户入住计划", "allocation", "green"),
        child("store_room_adjustment", "房间调整", "allocation", "orange"),
        child("store_allocation_conflict", "冲突检查", "allocation", "red"),
        child("store_allocation_records", "排房记录", "allocation", "teal"),
      ],
    },
    {
      key: "store_sales", label: "销售中心", route: "sales", target: "我的销售", tone: "orange",
      children: [
        child("store_my_customers", "我的客户", "sales", "blue"),
        child("store_my_signings", "我的签约", "sales", "green"),
        child("store_my_contracts", "我的合同", "sales", "purple"),
        child("store_my_payments", "我的收款状态", "sales", "orange"),
        child("store_my_performance", "我的销售业绩", "sales", "red"),
      ],
    },
    {
      key: "store_exception", label: "运营异常", route: "operations", target: "运营异常", tone: "purple",
      children: [
        child("store_room_conflict", "房间冲突", "operations", "red"),
        child("store_stay_exception", "入住异常", "operations", "orange"),
        child("store_checkout_exception", "出馆异常", "operations", "purple"),
        child("store_service_exception", "服务异常", "operations", "blue"),
      ],
    },
  ];
}

function emp001NavigationTree() {
  const child = (key, label, route, tone) => ({ key, label, route, target: label, tone });
  return [
    {
      key: "owner_home", label: "首页", route: "home", target: "经营入口", tone: "red",
      children: [
        child("owner_decisions", "今日决策", "action", "orange"),
        child("owner_status", "经营状态", "status", "green"),
        child("owner_risks", "经营风险", "risk", "purple"),
      ],
    },
    {
      key: "owner_sales", label: "销售经营", route: "sales", target: "销售经营", tone: "green",
      children: [
        child("owner_sales_results", "签约结果", "sales", "green"),
        child("owner_sales_payment", "合同与收款状态", "sales", "blue"),
        child("owner_sales_exception", "例外审批", "sales", "orange"),
      ],
    },
    {
      key: "owner_finance", label: "资金经营", route: "finance", target: "资金经营", tone: "red",
      children: [
        child("owner_finance_close", "日结状态", "finance", "green"),
        child("owner_finance_pending", "待收待付", "finance", "orange"),
        child("owner_finance_risk", "财务异常", "finance", "red"),
      ],
    },
    {
      key: "owner_operations", label: "运营经营", route: "operations", target: "运营经营", tone: "blue",
      children: [
        child("owner_actual_stay", "当前入住", "operations", "blue"),
        child("owner_room", "当前房态", "operations", "green"),
        child("owner_service_risk", "服务异常", "operations", "orange"),
      ],
    },
    {
      key: "owner_organization", label: "组织执行", route: "organization", target: "组织执行", tone: "purple",
      children: [
        child("owner_responsible_today", "今日责任人", "organization", "blue"),
        child("owner_open_work", "未闭环事项", "organization", "orange"),
      ],
    },
    {
      key: "owner_audit", label: "审计追溯", route: "data", target: "审计追溯", tone: "purple",
      children: [
        child("owner_source", "事实来源", "data", "blue"),
        child("owner_audit_records", "处理记录", "data", "green"),
        child("owner_history", "历史档案", "data", "purple"),
      ],
    },
  ];
}

function activeNavigationTree() {
  if (!omsContract || identity.bindingStatus !== "ready") {
    return NAVIGATION_MENU_TREE;
  }
  return contractNavigationTree();
}

function applyContractRenderMetadata(componentTree, runtimeHome) {
  const contract = requireLoadedContract("contract_layer_not_loaded");
  const renderContract = contract.ui_render_contract || {};
  const diff = validateComponentTreeAgainstContract(componentTree, renderContract, runtimeHome);
  if (diff.length && ((renderContract.validation || {}).ui_vs_contract_diff_check)) {
    throw new Error(`contract_component_diff:${diff.join(",")}`);
  }
  return {
    ...componentTree,
    source: "contract.json",
    pipeline: renderContract.render_pipeline || "contract.json -> UI render engine -> DOM",
    contract_version: contract.schema_version,
    contract_sections: renderContract.required_home_sections || CONTRACT_REQUIRED_HOME_SECTIONS,
    contract_diff: diff,
    contract_render_source: renderContract.render_source,
  };
}

function validateComponentTreeAgainstContract(componentTree, renderContract, runtimeHome) {
  const diff = [];
  const homeSections = renderContract.home_sections || {};
  for (const section of renderContract.required_home_sections || CONTRACT_REQUIRED_HOME_SECTIONS) {
    const config = homeSections[section];
    if (!config) {
      diff.push(`missing_render_section:${section}`);
      continue;
    }
    const key = config.component_tree_key;
    if (!key || !Array.isArray(componentTree[key])) {
      diff.push(`missing_component:${section}:${key}`);
    }
    for (const path of config.payload_paths || []) {
      if (!hasPath({ payload: runtimeHome }, path)) {
        diff.push(`missing_payload:${path}`);
      }
    }
  }
  return diff;
}

function validateEndToEndUiChain(componentTree) {
  const contract = requireLoadedContract("contract_layer_not_loaded");
  const chainContract = contract.e2e_ui_chain_contract || {};
  const diff = [];
  if (componentTree.source !== "contract.json") {
    diff.push("component_tree_not_contract_source");
  }
  for (const selector of chainContract.required_dom_targets || SCHEMA_RENDER_TARGETS) {
    const target = $(selector);
    if (!target) {
      diff.push(`missing_dom:${selector}`);
      continue;
    }
    if (!String(target.innerHTML || "").trim()) {
      diff.push(`empty_dom:${selector}`);
    }
    if (target.dataset.renderSource !== "contract.json") {
      diff.push(`wrong_render_source:${selector}`);
    }
  }
  for (const selector of chainContract.required_interaction_selectors || ["[data-work-action]", "[data-nav-route]"]) {
    if (!document.querySelector(selector)) {
      diff.push(`missing_interaction:${selector}`);
    }
  }
  for (const section of (chainContract.display_validation || {}).required_sections_visible || CONTRACT_REQUIRED_HOME_SECTIONS) {
    const config = (((contract.ui_render_contract || {}).home_sections || {})[section]);
    const targets = (config && config.dom_targets) || [];
    if (!targets.some((selector) => {
      const target = $(selector);
      return target && String(target.textContent || "").trim();
    })) {
      diff.push(`section_not_visible:${section}`);
    }
  }
  uiChainState = {
    ...uiChainState,
    status: diff.length ? "blocked" : "ready",
    diff,
    last_render_id: String(schemaRenderSequence),
  };
  if (diff.length) {
    updateUiChainStep("dom_rendered", "blocked", diff.join("|"));
  } else {
    updateUiChainStep("dom_rendered", "ready", String(schemaRenderSequence));
  }
  syncUiChainDebugState(diff.join("|"));
  if (diff.length && ((chainContract.display_validation || {}).empty_dom_blocks_chain)) {
    throw new Error(`ui_chain_diff:${diff.join(",")}`);
  }
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
    finance_pending_payment: finance.pending_payment_amount || 0,
    finance_records: finance.event_records || 0,
    sales_signed_customers: sales.signed_customers || 0,
    sales_contracts: sales.contracts || 0,
    sales_results: sales.sales_results || 0,
    sales_amount: sales.sales_amount || 0,
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
    sourceEvidenceGroup("\u5728\u4f4f", sourceEvidence.resident_data),
    sourceEvidenceGroup("\u623f\u6001", sourceEvidence.room_status_data),
    sourceEvidenceGroup("\u5ba2\u6237", sourceEvidence.sales_contract_data),
    sourceEvidenceGroup("\u8d22\u52a1", sourceEvidence.finance_data),
    sourceEvidenceGroup("\u670d\u52a1", sourceEvidence.service_data),
    sourceEvidenceGroup("\u6536\u652f", sourceEvidence.financial_events),
    sourceEvidenceGroup("\u4e1a\u52a1\u53d8\u5316", sourceEvidence.business_event_flow),
    sourceEvidenceGroup("\u4eba\u5458\u5904\u7406", sourceEvidence.hr_execution_flow),
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
  const records = actionableDailyRecords(sections, visibleData).sort((left, right) => dailyTaskPriority(right) - dailyTaskPriority(left));
  const targetCount = Math.min(7, records.length);
  const tasks = records.slice(0, targetCount).map((record, index) => dailyTaskFromRecord(record, index));
  return tasks.length ? tasks : [{
    type: "daily_empty_action",
    rank: 0,
    label: "今天暂无待处理事项",
    value: "已清空",
    caption: "今日工作",
    delta: "仅显示真实待办",
    currentStep: "无需处理",
    nextAction: "查看经营状态",
    actionLabel: "查看状态",
    riskNote: "经营数据已归入当前状态",
    tone: "green",
  }];
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
      value: identity.workspaceKey === "boss"
        ? humanWorkCount(count, "\u6761\u5f53\u524d\u8bb0\u5f55", "\u6682\u65e0\u6570\u636e")
        : humanWorkCount(count, "\u4ef6\u8fdb\u884c\u4e2d", "\u7b49\u5f85\u89e6\u53d1"),
      count,
      currentStep: identity.workspaceKey === "boss" ? "\u5f53\u524d\u7ecf\u8425" : state.currentStep,
      nextAction: identity.workspaceKey === "boss" ? "\u67e5\u770b\u4e1a\u52a1\u660e\u7ec6" : state.nextAction,
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
    home: Math.min(7, Math.max(3, records.length)),
    action: firstPositive((sections.my_todos || {}).count, metrics.today_todos, records.length),
    status: firstPositive((sections.my_tasks || {}).count, (sections.role_home || {}).count, visible.current),
    risk: firstPositive(metrics.risk_alerts, metrics.service_exceptions),
  };
  const captions = {
    home: "\u552f\u4e00\u9996\u9875",
    action: "\u8981\u505a\u4ec0\u4e48",
    status: "\u73b0\u5728\u53d1\u751f\u4ec0\u4e48",
    risk: "\u54ea\u91cc\u6709\u95ee\u9898",
  };
  return DAILY_WORKBENCH_MENU.map((item) => ({
    ...item,
    type: "daily_menu",
    value: dailyMenuBadge(item.key),
    count: counts[item.key] || 0,
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

function productDataStrip(visibleData, schema) {
  const visible = visibleCounts(visibleData);
  const metrics = schema && schema.schema_version ? schemaMetrics(schema) : {};
  return [
    dataPill("当前在住", humanWorkCount(firstPositive(metrics.resident_count, visible.resident), "位客户", "暂无在住"), "入住经营状态", "open-room"),
    dataPill("房态", humanWorkCount(firstPositive(metrics.room_status_records, visible.room), "间房", "暂无房态"), "占用 / 预留 / 空房", "open-room"),
    dataPill("销售", humanWorkCount(firstPositive(metrics.sales_signed_customers, metrics.sales_contracts, visible.sales), "条签约", "暂无签约记录"), "签约客户与合同", "open-sales"),
    dataPill("实收", formatMoney(metrics.finance_collected || metrics.finance_income || 0), "资金状态", "trace-finance"),
    dataPill("待收", formatMoney(metrics.finance_receivable || 0), "需要关注", "trace-finance"),
    dataPill("待付", formatMoney(metrics.finance_pending_payment || 0), "付款安排", "trace-finance"),
    dataPill("风险", humanRiskCount(metrics.risk_alerts || 0), "当前异常", "open-risk"),
  ];
}

function dataPill(label, value, caption, action = "open-status") {
  const quality = (latestRuntimeHome?.business_dashboard?.data_quality) || {};
  return {
    label,
    value: String(value || "\u6682\u65e0"),
    caption,
    action,
    currentStatus: "Current",
    healthStatus: quality.snapshot_status || quality.status || "WARNING",
    snapshotVersion: quality.snapshot_version || "PENDING_DQ_SNAPSHOT",
  };
}

function dailyWorkbenchSummary(schema, sections, visibleData) {
  const metrics = schemaMetrics(schema);
  const visible = visibleCounts(visibleData);
  return [
    overviewGroup("\u4eca\u65e5", [
      metric("\u5fc5\u505a\u4efb\u52a1", humanWorkCount(Math.min(7, Math.max(3, allDailyRecords(sections, visibleData).length)), "\u4ef6\u5148\u505a", "\u6682\u65e0\u5fc5\u505a")),
      metric("\u4eca\u65e5\u5165\u4f4f", humanWorkCount(firstPositive(metrics.today_checkins, visible.resident), "\u95f4\u623f\u8981\u5904\u7406", "\u6682\u65e0\u5165\u4f4f")),
      metric("\u4eca\u65e5\u51fa\u9986", humanWorkCount(metrics.today_checkouts, "\u95f4\u623f\u8981\u51fa\u9986", "\u6682\u65e0\u51fa\u9986")),
      metric("\u5f85\u5904\u7406", humanWorkCount(firstPositive(metrics.today_todos, visible.current), "\u4ef6\u5f85\u5904\u7406", "\u5df2\u6e05\u7a7a")),
    ]),
    overviewGroup("\u5f85\u529e", [
      metric("\u6211\u7684\u5f85\u529e", humanWorkCount(firstPositive((sections.my_todos || {}).count, metrics.today_todos), "\u4ef6\u5f85\u529e", "\u6682\u65e0\u5f85\u529e")),
      metric("\u6211\u7684\u5ba1\u6279", humanWorkCount((sections.my_approvals || {}).count || 0, "\u4ef6\u8981\u786e\u8ba4", "\u6682\u65e0\u5ba1\u6279")),
      metric("\u6211\u7684\u4efb\u52a1", humanWorkCount((sections.my_tasks || {}).count || 0, "\u4ef6\u4efb\u52a1", "\u6682\u65e0\u4efb\u52a1")),
      metric("\u6211\u7684\u4e1a\u52a1", humanWorkCount((sections.role_home || {}).count || 0, "\u4ef6\u4e1a\u52a1", "\u6682\u65e0\u4e1a\u52a1")),
    ]),
    overviewGroup("\u8fdb\u884c\u4e2d", [
      metric("\u5165\u4f4f/\u51fa\u9986", humanWorkCount(firstPositive(metrics.active_stays, visible.resident), "\u95f4\u623f\u6b63\u5728\u5904\u7406", "\u6682\u65e0\u623f\u95f4\u5f85\u5904\u7406")),
      metric("\u6536\u6b3e/\u5bf9\u8d26", humanWorkCount(firstPositive(metrics.finance_records, visible.finance), "\u7b14\u6536\u652f\u8981\u8ddf", "\u6682\u65e0\u8d22\u52a1\u5f85\u529e")),
      metric("\u7b7e\u7ea6/\u8f6c\u5316", humanWorkCount(firstPositive(metrics.sales_contracts, visible.sales), "\u4e2a\u5ba2\u6237\u8981\u8ddf", "\u6682\u65e0\u5ba2\u6237\u5f85\u8ddf")),
      metric("\u5165\u4f4f/\u62a4\u7406", humanWorkCount(firstPositive(metrics.service_progress, visible.service), "\u9879\u670d\u52a1\u8981\u8ddf", "\u6682\u65e0\u670d\u52a1\u5f85\u529e")),
    ]),
    overviewGroup("\u98ce\u9669", [
      metric("\u5ef6\u8fdf", humanRiskCount(allDailyRecords(sections, visibleData).filter((record) => /\u5ef6\u8fdf|\u903e\u671f|delay|overdue|late/i.test(dailyRecordText(record))).length)),
      metric("\u5f02\u5e38", humanRiskCount(firstPositive(metrics.risk_alerts, metrics.service_exceptions))),
      metric("\u672a\u5b8c\u6210", humanWorkCount(firstPositive(metrics.today_todos, visible.current), "\u4ef6\u672a\u5b8c\u6210", "\u5df2\u6e05\u7a7a")),
      metric("\u672a\u6821\u9a8c\u6570\u636e", humanWorkCount((visibleData.current_user_visible_data || []).filter((item) => item.data_confidence !== "source_verified").length, "\u6761\u8981\u590d\u6838", "\u6682\u65e0")),
    ]),
    overviewGroup("\u6570\u636e", [
      metric("\u53ef\u89c1\u8bb0\u5f55", humanWorkCount(visible.finance + visible.room + visible.resident + visible.sales + visible.service, "\u6761\u53ef\u67e5", "\u6682\u65e0")),
      metric("\u5728\u4f4f", humanWorkCount(firstPositive(metrics.resident_count, visible.resident), "\u95f4\u623f", "\u6682\u65e0")),
      metric("\u6536\u652f", humanWorkCount(firstPositive(metrics.finance_records, visible.finance), "\u7b14\u53ef\u8ffd\u8e2a", "\u6682\u65e0")),
      metric("\u5ba2\u6237", humanWorkCount(firstPositive(metrics.sales_leads + metrics.sales_contracts, visible.sales), "\u4e2a\u53ef\u8ddf", "\u6682\u65e0")),
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

function actionableDailyRecords(sections, visibleData) {
  return allDailyRecords(sections, visibleData).filter((record) => {
    const text = dailyRecordText(record);
    const status = String(record.status || record.execution_status || record.approval_status || "").toLowerCase();
    const actionableStatus = /pending|todo|open|blocked|warning|error|waiting|approval|confirm|risk|exception|待办|待处理|待审批|待确认|风险|异常/.test(status);
    const actionableText = /今日任务|待办|待处理|待审批|待确认|审批|确认|风险|异常|冲突|延迟|逾期|today task|todo|approval|confirm|risk|exception|blocked|overdue/i.test(text);
    return actionableStatus || actionableText;
  });
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
  const count = Number(value || 0);
  return {
    type: "daily_risk_card",
    label,
    value: humanRiskCount(count),
    count,
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
    room_flow: firstPositive(metrics.room_status_records, visible.room),
    finance_flow: firstPositive(metrics.finance_records, visible.finance),
    sales_flow: firstPositive(metrics.sales_signed_customers, metrics.sales_contracts, visible.sales),
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
    if (metrics.sales_results) return "\u9500\u552e\u7ed3\u679c";
    if (metrics.sales_contracts || metrics.sales_signed_customers) return "\u7b7e\u7ea6\u5ba2\u6237";
    return "\u7b7e\u7ea6\u5ba2\u6237";
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

function scoreMetric(label, value, caption, delta, tone, count = 0) {
  return { label, value, caption, delta, tone, count };
}

function overviewGroup(title, metrics) {
  return { title, metrics };
}

function metric(label, value) {
  return { label, value };
}

function dailyMenuBadge(key) {
  const badges = { home: "\u9996", action: "\u505a", status: "\u770b", risk: "\u9632" };
  return badges[key] || "\u770b";
}

function humanWorkCount(value, unit, emptyText) {
  const count = Number(value || 0);
  if (!count) return emptyText;
  return `${count}${unit}`;
}

function humanRiskCount(value) {
  const count = Number(value || 0);
  if (!count) return "\u6682\u65e0\u98ce\u9669";
  if (count > 99) return "\u98ce\u9669\u8f83\u591a\uff0c\u5148\u5904\u7406\u7ea2\u8272\u9879";
  return `${count}\u4e2a\u9700\u5173\u6ce8`;
}

function humanPanelCount(value) {
  const count = Number(value || 0);
  if (!count) return "\u6682\u65e0";
  if (count > 99) return "\u5df2\u6709\u5de5\u4f5c\uff0c\u5148\u770b\u91cd\u70b9";
  return `${count}\u4ef6`;
}

function workActionButton(label, action, target, route = "") {
  const routeAttribute = isSupportedWorkRoute(route) ? ` data-work-route="${escapeHtml(route)}"` : "";
  return `<button class="daily-action-button work-action-button" type="button" data-work-action="${escapeHtml(action)}" data-work-target="${escapeHtml(target || label)}"${routeAttribute}>${escapeHtml(label)}</button>`;
}

function scoreCardTemplate(item) {
  if (item.type === "daily_task") {
    return dailyTaskCardTemplate(item);
  }
  const route = routeForProductItem(item);
  const action = identity.workspaceKey === "boss" ? "查看详情" : "开始处理";
  return `
    <article class="score-card clickable-card tone-${escapeHtml(item.tone)}" data-work-action="${escapeHtml(action)}" data-work-target="${escapeHtml(item.label)}" data-work-route="${escapeHtml(route)}">
      <span class="score-icon" aria-hidden="true"></span>
      <h2>${escapeHtml(item.label)}</h2>
      <strong>${escapeHtml(item.value)}</strong>
      <p><span>${escapeHtml(item.caption)}</span><b>${escapeHtml(item.delta)}</b></p>
      <div class="sparkline" aria-hidden="true"></div>
      ${workActionButton(action, action, item.label, route)}
    </article>
  `;
}

function priorityCardTemplate(item) {
  if (item.type === "business_flow_progress") {
    return dailyBusinessFlowCardTemplate(item);
  }
  const route = routeForProductItem(item);
  return `
    <article class="priority-card clickable-card tone-${escapeHtml(item.tone)}" data-work-action="open-status" data-work-target="${escapeHtml(item.label)}" data-work-route="${escapeHtml(route)}">
      <span class="score-icon" aria-hidden="true"></span>
      <strong>${escapeHtml(item.value)}</strong>
      <div>
        <h3>${escapeHtml(item.label)}</h3>
        <p>${escapeHtml(item.delta)}</p>
        ${workActionButton("查看详情", "查看详情", item.label, route)}
      </div>
    </article>
  `;
}

function sideBusinessMenuTemplate(item) {
  const hrefs = {
    home: "#homeTop",
    action: "#todayWorkSection",
    status: "#businessFlowSection",
    risk: "#riskExceptionSection",
  };
  return `<a href="${hrefs[item.key] || "#homeTop"}"><span class="rank-badge tone-${escapeHtml(item.tone)}">${escapeHtml(item.value || item.label.slice(0, 1))}</span>${escapeHtml(item.label)}<small>${escapeHtml(item.caption || "")}</small></a>`;
}

function navigationMenuTemplate(item) {
  const children = Array.isArray(item.children) ? item.children : [];
  return `
    <section class="navigation-menu-node" data-nav-node="${escapeHtml(item.key)}">
      ${navigationMenuLinkTemplate(item, "parent")}
      ${children.length ? `<div class="navigation-submenu">${children.map((child) => navigationMenuLinkTemplate(child, "child")).join("")}</div>` : ""}
    </section>
  `;
}

function navigationMenuLinkTemplate(item, level) {
  const route = item.route || "home";
  const target = item.target || item.label || route;
  const hash = `#${route}/${encodeURIComponent(target)}`;
  return `
    <a href="${escapeHtml(hash)}" class="navigation-menu-link navigation-${escapeHtml(level)}" data-nav-route="${escapeHtml(route)}" data-nav-key="${escapeHtml(item.key)}" data-nav-target="${escapeHtml(target)}">
      <span class="rank-badge tone-${escapeHtml(item.tone || "blue")}">${escapeHtml(item.label.slice(0, 1))}</span>
      <span>${escapeHtml(item.label)}</span>
    </a>
  `;
}

function menuKeyForRoute(route) {
  const normalizedRoute = route || "home";
  for (const node of activeNavigationTree()) {
    if (node.route === normalizedRoute || node.key === normalizedRoute) {
      return node.key;
    }
    const child = (node.children || []).find((item) => item.route === normalizedRoute || item.key === normalizedRoute);
    if (child) {
      return child.key;
    }
  }
  return "home";
}

function compactNavigationTemplate(tree) {
  return (Array.isArray(tree) ? tree : []).map((item) => {
    const route = item.route || "home";
    const target = item.target || item.label || route;
    return `<a href="#${escapeHtml(route)}/${encodeURIComponent(target)}" data-nav-route="${escapeHtml(route)}" data-nav-key="${escapeHtml(item.key)}" data-nav-target="${escapeHtml(target)}">${escapeHtml(item.label)}</a>`;
  }).join("");
}

function routeForProductItem(item = {}) {
  const text = [
    item.key,
    item.label,
    item.caption,
    item.delta,
    item.action,
    item.actionLabel,
    item.userLabel,
    item.domain,
    item.source,
    item.nextAction,
  ].map((value) => String(value || "")).join(" ");
  if (/finance|财务|收款|待收|待付|收入|支出|对账/i.test(text)) return "finance";
  if (/sales|销售|客户|签约|合同|收款状态|销售结果/i.test(text)) return "sales";
  if (/room|resident|stay|入住|出馆|房态|房间|排房|服务|照护|人效|护理|运营/i.test(text)) return "operations";
  if (/risk|风险|异常|冲突|延迟/i.test(text)) return "risk";
  if (/trace|source|data|来源|数据|追溯|历史/i.test(text)) return "data";
  if (/Action|任务|待办|处理|执行/i.test(text)) return "action";
  return "status";
}

function markActiveMenuTree() {
  const key = navigationState.current_menu_key || menuKeyForRoute(interactionState.current_route);
  document.querySelectorAll(".navigation-menu-node.active").forEach((node) => node.classList.remove("active"));
  let activeNode = null;
  document.querySelectorAll("[data-nav-key]").forEach((node) => {
    const isActive = node.dataset.navKey === key || node.dataset.navRoute === interactionState.current_route;
    node.classList.toggle("active", isActive);
    if (isActive && !activeNode) {
      activeNode = node;
    }
  });
  if (activeNode) {
    activeNode.closest(".navigation-menu-node")?.classList.add("active");
  }
}

function dataPillTemplate(item) {
  const route = routeForProductItem(item);
  const qualityMeta = [item.currentStatus, item.healthStatus, item.snapshotVersion]
    .filter((value) => value !== undefined && value !== null && String(value).trim() !== "")
    .map(chineseStatus)
    .join(" · ");
  return `
    <article class="data-pill clickable-card" data-work-action="${escapeHtml(item.action || "open-status")}" data-work-target="${escapeHtml(item.label)}" data-work-route="${escapeHtml(route)}">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
      <small>${escapeHtml(item.caption)}</small>
      ${qualityMeta ? `<em class="metric-quality-meta">${escapeHtml(qualityMeta)}</em>` : ""}
      ${workActionButton("查看", "查看详情", item.label, route)}
    </article>
  `;
}

function businessMenuCardTemplate(item) {
  if (item.type === "daily_risk_card") {
    return dailyRiskCardTemplate(item);
  }
  const route = routeForProductItem(item);
  return `
    <article class="business-menu-card clickable-card tone-${escapeHtml(item.tone)}" data-business-domain="${escapeHtml(item.key)}" data-schema-source="${escapeHtml(item.source)}" data-work-action="open-status" data-work-target="${escapeHtml(item.label)}" data-work-route="${escapeHtml(route)}">
      <header>
        <span class="score-icon" aria-hidden="true"></span>
        <strong>${escapeHtml(item.label)}</strong>
      </header>
      <b>${escapeHtml(item.value)}</b>
      <p>${escapeHtml(item.caption)}</p>
      <small>${item.available ? "可操作" : "等待数据"}</small>
      ${workActionButton(item.available ? "进入处理" : "查看", item.available ? "进入处理" : "查看详情", item.label, route)}
    </article>
  `;
}

function dailyTaskCardTemplate(item) {
  const route = routeForProductItem(item);
  return `
    <article class="score-card daily-task-card clickable-card tone-${escapeHtml(item.tone)}" data-work-action="${escapeHtml(item.actionLabel)}" data-work-target="${escapeHtml(item.label)}" data-work-route="${escapeHtml(route)}">
      <div class="daily-card-head">
        <span class="daily-rank">${escapeHtml(item.value)}</span>
        <span class="daily-flow-label">${escapeHtml(item.caption)}</span>
      </div>
      <h2>${escapeHtml(item.label)}</h2>
      <strong>${escapeHtml(item.nextAction)}</strong>
      <p><span>${escapeHtml(item.caption)}</span><b>${escapeHtml(item.delta)}</b></p>
      <small class="daily-warning">${escapeHtml("\u63d0\u9192\uff1a")}${escapeHtml(item.riskNote)}</small>
      ${workActionButton(item.actionLabel, item.actionLabel, item.label, route)}
    </article>
  `;
}

function dailyBusinessFlowCardTemplate(item) {
  const route = routeForProductItem(item);
  const stateLabel = identity.workspaceKey === "boss" ? "口径" : "进行中";
  const nextLabel = identity.workspaceKey === "boss" ? "入口" : "下一步动作";
  return `
    <article class="priority-card daily-flow-card clickable-card tone-${escapeHtml(item.tone)}" data-work-action="查看详情" data-work-target="${escapeHtml(item.userLabel)}" data-work-route="${escapeHtml(route)}">
      <span class="score-icon" aria-hidden="true"></span>
      <strong>${escapeHtml(item.value)}</strong>
      <div>
        <h3>${escapeHtml(item.userLabel)}</h3>
        <p>${escapeHtml(stateLabel + "：")}${escapeHtml(item.currentStep)}</p>
        <small>${escapeHtml(nextLabel + "：")}${escapeHtml(item.nextAction)}</small>
        <em>${escapeHtml("\u98ce\u9669\uff1a")}${escapeHtml(item.riskNote)}</em>
        ${workActionButton("查看详情", "查看详情", item.userLabel, route)}
      </div>
    </article>
  `;
}

function dailyRiskCardTemplate(item) {
  const canProcess = identity.workspaceKey !== "boss" && Number(item.count);
  const actionLabel = canProcess ? "处理风险" : "查看详情";
  return `
    <article class="business-menu-card daily-risk-card clickable-card tone-${escapeHtml(item.tone)}" data-work-action="${escapeHtml(actionLabel)}" data-work-target="${escapeHtml(item.label)}">
      <header>
        <span class="score-icon" aria-hidden="true"></span>
        <strong>${escapeHtml(item.label)}</strong>
      </header>
      <b>${escapeHtml(item.value)}</b>
      <div class="daily-risk-list">
        <span><em>${escapeHtml("\u4e0b\u4e00\u6b65")}</em><strong>${escapeHtml(item.nextAction)}</strong></span>
        <span><em>${escapeHtml("\u72b6\u6001")}</em><strong>${escapeHtml(item.riskNote)}</strong></span>
      </div>
      <small>${Number(item.count) ? "\u9700\u5173\u6ce8" : "\u6682\u65e0\u5f02\u5e38"}</small>
      ${workActionButton(actionLabel, actionLabel, item.label)}
    </article>
  `;
}

function personalWorkspacePanelTemplate(panel) {
  const items = panel.items.length
    ? panel.items.map((item) => {
        const fields = Array.isArray(item.display_fields) ? item.display_fields.slice(0, 3) : [];
        const fieldText = fields.map((field) => `${field.label}:${field.value}`).join(" / ");
        return `
          <li class="clickable-card" data-work-action="处理事项" data-work-target="${escapeHtml(item.title || item.name || item.summary || item.id || "\u5f85\u5904\u7406\u4e8b\u9879")}">
            <strong>${escapeHtml(item.title || item.name || item.summary || item.id || "\u5f85\u5904\u7406\u4e8b\u9879")}</strong>
            <b class="confidence-label confidence-${escapeHtml(item.data_confidence || "uncalibrated_warning")}">${escapeHtml(confidenceLabel(item.data_confidence))}</b>
            ${item.source_summary ? `<small>${escapeHtml(item.source_summary)}</small>` : ""}
            ${fieldText ? `<em>${escapeHtml(fieldText)}</em>` : ""}
            ${workActionButton("处理", "处理事项", item.title || item.name || item.summary || item.id || "\u5f85\u5904\u7406\u4e8b\u9879")}
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
        <strong>${escapeHtml(humanPanelCount(panel.count))}</strong>
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
  const chain = record.trace_chain || record.event_chain || {};
  const completion = record.completion_log || {};
  const sourceFile = basename(evidence.source_file || "");
  const fields = Array.isArray(record.display_fields) ? record.display_fields.slice(0, 4) : [];
  const fieldText = fields.map((field) => `${friendlyFieldLabel(field.label)}:${field.value}`).join(" / ");
  const rowNumber = evidence.row_number || evidence.row_id || chain.row_id || chain.source_row || "";
  const currentStatus = record.status || completion.completion_status || chain.trace_status || confidenceLabel(record.data_confidence);
  const owner = record.role || record.workspace || chain.owner || "";
  const quality = (latestRuntimeHome?.business_dashboard?.data_quality) || {};
  const sourceFields = arrayValue(evidence.source_columns).join("、") || evidence.column_number || "未结构化";
  const sourceLine = [
    evidence.truth_source,
    evidence.source_type || record.business_domain,
    sourceFile,
    rowNumber ? `\u7b2c ${rowNumber} \u884c` : "",
  ].filter(Boolean).join(" / ");
  const statusLine = [
    currentStatus ? `\u72b6\u6001\uff1a${currentStatus}` : "",
    owner ? `\u8d1f\u8d23\u4eba\uff1a${owner}` : "",
  ].filter(Boolean).join(" / ");
  return `
    <details class="source-record clickable-card">
      <summary>
        <strong>${escapeHtml(record.title || record.name || record.summary || "\u6765\u6e90\u8bb0\u5f55")}</strong>
        <b class="confidence-label confidence-${escapeHtml(record.data_confidence || "uncalibrated_warning")}">${escapeHtml(confidenceLabel(record.data_confidence))}</b>
      </summary>
      <span>${escapeHtml(sourceLine || "\u6682\u65e0\u6765\u6e90\u660e\u7ec6")}</span>
      <small>${escapeHtml(statusLine || "\u72b6\u6001\uff1a\u5f85\u786e\u8ba4")}</small>
      ${fieldText ? `<em>${escapeHtml(fieldText)}</em>` : ""}
      <dl class="trace-chain">
        ${traceRequiredRow("\u6765\u6e90\u6587\u4ef6", evidence.source_file || chain.source_file)}
        ${traceRequiredRow("工作表", evidence.source_sheet)}
        ${traceRequiredRow("\u8868\u683c\u884c", rowNumber)}
        ${traceRequiredRow("字段", sourceFields)}
        ${traceRequiredRow("版本", evidence.source_version)}
        ${traceRequiredRow("数据快照", chineseStatus(quality.snapshot_version))}
        ${traceRequiredRow("数据健康", quality.score === undefined ? "待计算" : String(quality.score) + "/100")}
        ${traceRequiredRow("质量状态", chineseStatus(record.quality_status || quality.snapshot_status || quality.status))}
        ${traceChainRow("\u5f53\u524d\u72b6\u6001", currentStatus)}
        ${traceChainRow("\u8d1f\u8d23\u4eba", owner)}
        ${traceChainRow("\u5b8c\u6210\u65f6\u95f4", completion.completed_at)}
      </dl>
    </details>
  `;
}

function chineseStatus(value) {
  const normalized = String(value || "").trim();
  const labels = {
    PASS: "通过",
    WARNING: "警告",
    FAIL: "失败",
    NOT_INITIALIZED: "尚未初始化",
    ARCHIVED: "已归档",
    ARCHIVED_LEGACY: "历史版本已归档",
    PENDING: "待处理",
    APPROVED: "已批准",
    REJECTED: "已驳回",
    OPEN: "待处理",
    RESOLVED: "已解决",
    OCCUPIED: "已占用",
    AVAILABLE: "可用",
    RESERVED: "已预留",
    CLEANING: "清洁中",
    MAINTENANCE: "维修中",
    DISABLED: "已停用",
    IN_STAY: "在住",
  };
  if (labels[normalized]) return labels[normalized];
  if (/^TS-|^OB-|^PENDING_DQ_SNAPSHOT$/i.test(normalized)) return normalized === "PENDING_DQ_SNAPSHOT" ? "等待生成" : "历史版本";
  return normalized || "尚未确认";
}

function friendlyFieldLabel(label) {
  const labels = {
    source_file: "\u6765\u6e90\u6587\u4ef6",
    row_id: "\u8868\u683c\u884c",
    row_number: "\u8868\u683c\u884c",
    ingestion_event_id: "\u63a5\u6536\u8bb0\u5f55",
    business_event_id: "\u4e1a\u52a1\u53d8\u5316",
    workflow_task_id: "\u5f85\u5904\u7406\u52a8\u4f5c",
    hr_execution_id: "\u8d1f\u8d23\u4eba\u5904\u7406",
    completion_status: "\u5b8c\u6210\u72b6\u6001",
    completed_at: "\u5b8c\u6210\u65f6\u95f4",
    trace_status: "\u5f53\u524d\u72b6\u6001",
    event_id: "\u4e1a\u52a1\u53d8\u5316",
    work_item_id: "\u5f85\u5904\u7406\u52a8\u4f5c",
    business_domain: "\u7c7b\u522b",
  };
  return labels[String(label || "")] || String(label || "");
}

function traceChainRow(label, value) {
  if (!value) return "";
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`;
}

function traceRequiredRow(label, value) {
  const resolved = value === undefined || value === null || String(value).trim() === "" ? "源文件未提供" : value;
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(resolved)}</dd></div>`;
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
  markBootChainStep("app_mount", "starting");
  renderLoading();
  await ensureContractLayerLoaded();
  identity = await bootstrapIdentity();
  currentWorkspace = identity.bindingStatus === "ready" ? workspaceData[identity.workspaceKey] : null;
  if (identity.bindingStatus === "ready" && !currentWorkspace) {
    identity = identityBindingError("workspace_route_not_found_after_auth", identity.userId, identity.runtimeContext);
    currentWorkspace = null;
  }
  if (identity.bindingStatus !== "ready") {
    markBootChainStep("app_mount", "blocked", identity.errorType || "identity_blocked");
    render();
    return;
  }
  try {
    const runtimeHome = await fetchRuntimeHome(authConfig().homeEndpoint, identity);
    render(runtimeHome);
    markBootChainStep("app_mount", "ready");
  } catch (error) {
    markBootChainStep("app_mount", "failed", errorMessage(error));
    renderContractError(`contract_runtime_fetch_failed:${errorMessage(error)}`);
  }
}

function markBootChainStep(step, status, detail = "") {
  if (!OMS_BOOT_CHAIN_STEPS.includes(step)) return;
  bootChainState = { ...bootChainState, [step]: status, last_error: detail || bootChainState.last_error };
  window.OMS_BOOT_STATE = { ...bootChainState };
  document.documentElement.dataset.omsJsBoot = bootChainState.js_entry;
  document.documentElement.dataset.omsDomMount = bootChainState.dom_ready;
  document.documentElement.dataset.omsEventBinding = bootChainState.event_binding;
  document.documentElement.dataset.omsRouter = bootChainState.router_init;
  document.documentElement.dataset.omsStateLayer = bootChainState.state_layer;
  document.documentElement.dataset.omsAppMount = bootChainState.app_mount;
  if (window.console && typeof window.console.info === "function") {
    window.console.info(`[OMS boot] ${step}: ${status}`, detail || "");
  }
}

function syncInteractionDebugState() {
  window.OMS_INTERACTION_STATE = { ...interactionState };
  document.documentElement.dataset.omsSelectedTask = interactionState.selected_task || "";
  document.documentElement.dataset.omsCurrentRoom = interactionState.current_room || "";
  document.documentElement.dataset.omsActiveWorkflow = interactionState.active_workflow || "";
  document.documentElement.dataset.omsApiStatus = interactionState.api_status || "idle";
  document.documentElement.dataset.omsExecutionStatus = interactionState.execution_status || "idle";
  document.documentElement.dataset.omsClosureStatus = interactionState.closure_status || "";
  document.documentElement.dataset.omsBusinessStateStatus = interactionState.business_state_status || "";
  document.documentElement.dataset.omsDecisionSummary = interactionState.decision_summary || "";
  document.documentElement.dataset.omsRetriggerStatus = interactionState.retrigger_status || "";
  document.documentElement.dataset.omsLifecycleStage = interactionState.lifecycle_stage || "";
  document.documentElement.dataset.omsLifecycleStatus = interactionState.lifecycle_status || "";
}

function syncNavigationDebugState() {
  window.OMS_NAVIGATION_STATE = { ...navigationState };
  document.documentElement.dataset.omsNavigation = navigationState.mounted ? "mounted" : "pending";
  document.documentElement.dataset.omsNavigationRoute = navigationState.current_route || "home";
  document.documentElement.dataset.omsNavigationMenu = navigationState.current_menu_key || "home";
}

const PRODUCTION_VIEW_CONFIG = Object.freeze({
  sales: {
    dataset: "sales",
    title: "销售数据",
    subtitle: "来自 2026年销售明细表，可按销售和月份核对",
    route: "sales",
    filters: ["search", "salesperson_name", "month"],
  },
  finance: {
    dataset: "finance",
    title: "财务数据",
    subtitle: "来自 2026年财务报表，含收入、支出、待收、待付",
    route: "finance",
    filters: ["search", "type", "month"],
  },
  rooms: {
    dataset: "rooms",
    title: "房态明细",
    subtitle: "来自凰家房态表，显示真实房间和缺房号异常",
    route: "operations",
    filters: ["search", "status", "room_flag"],
  },
  contracts: {
    dataset: "contracts",
    title: "签约客户",
    subtitle: "来自凰家签约客户一览表，合同与入住计划逐条核对",
    route: "sales",
    filters: ["search", "salesperson_name", "month", "status"],
  },
});
const productionDatasetCache = {};
const productionDatasetLoading = {};

function selectedProductionView(route) {
  const normalizedRoute = normalizeBossCenterRoute(route);
  const target = String(interactionState.selected_target || "").trim();
  if (normalizedRoute === "finance") return PRODUCTION_VIEW_CONFIG.finance;
  if (normalizedRoute === "operations") return PRODUCTION_VIEW_CONFIG.rooms;
  if (normalizedRoute === "sales" && /签约客户|合同客户|客户明细/.test(target)) return PRODUCTION_VIEW_CONFIG.contracts;
  if (normalizedRoute === "sales") return PRODUCTION_VIEW_CONFIG.sales;
  return null;
}

function buildBossCenterPage(route, runtimeHome) {
  const view = selectedProductionView(route);
  if (view) {
    const cached = productionDatasetCache[view.dataset];
    if (!cached) {
      requestProductionDataset(view.dataset);
      return productionLoadingPage(view);
    }
    return productionDatasetPage(view, cached);
  }
  const repo = bossDataRepository(runtimeHome);
  if (route === "data") return buildDataTracePage(repo);
  return buildOperationsCenterPage(repo);
}

function renderBossCenterPage(route) {
  const panel = ensureBossCenterPage();
  if (!panel) return;
  const normalizedRoute = normalizeBossCenterRoute(route);
  if (!isBossCenterRoute(normalizedRoute)) {
    panel.hidden = true;
    panel.replaceChildren();
    return;
  }
  if (!latestRuntimeHome) {
    panel.hidden = true;
    return;
  }
  const page = buildBossCenterPage(normalizedRoute, latestRuntimeHome);
  panel.hidden = false;
  panel.dataset.route = normalizedRoute;
  panel.dataset.dataSource = page.dataSource || page.dataset || "";
  panel.innerHTML = page.productionDataset ? productionPageTemplate(page) : bossCenterPageTemplate(page);
  if (page.productionDataset) {
    hydrateProductionFilters(panel);
  }
}

function requestProductionDataset(dataset) {
  if (productionDatasetCache[dataset] || productionDatasetLoading[dataset]) return;
  productionDatasetLoading[dataset] = true;
  fetchProductionDataset(dataset)
    .then((payload) => {
      productionDatasetCache[dataset] = payload;
      window.OMS_PRODUCTION_DATASETS = { ...productionDatasetCache };
      renderBossCenterPage(interactionState.current_route || navigationState.current_route || "sales");
    })
    .catch((error) => {
      productionDatasetCache[dataset] = {
        dataset,
        title: dataset,
        records: [],
        columns: [],
        metrics: {},
        error: errorMessage(error),
      };
      renderBossCenterPage(interactionState.current_route || navigationState.current_route || "sales");
    })
    .finally(() => {
      productionDatasetLoading[dataset] = false;
    });
}

async function fetchProductionDataset(dataset) {
  const endpoint = String(window.OMS_PRODUCTION_ENDPOINT || "http://127.0.0.1:8787/api/oms/production").replace(/\/$/, "");
  const response = await fetch(`${endpoint}/${encodeURIComponent(dataset)}`, {
    method: "GET",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
  });
  const envelope = unwrapContractPayload(await response.json(), `/api/oms/production/${dataset}`);
  if (!response.ok || envelope.status === "failed" || envelope.error) {
    throw new Error(envelope.error || `production_dataset_${dataset}_failed`);
  }
  return envelope;
}

function productionLoadingPage(view) {
  return {
    productionDataset: true,
    route: view.route,
    dataset: view.dataset,
    title: view.title,
    subtitle: view.subtitle,
    dataSource: "OMS_TRUTH_SOURCE -> Production Adapter -> API -> 飞书页面",
    metrics: [],
    columns: [],
    records: [],
    filters: view.filters,
    source: {},
    emptyText: "正在读取生产事实源；没有使用 mock 数据。",
  };
}

function productionDatasetPage(view, payload) {
  const rows = arrayValue(payload.records);
  return {
    productionDataset: true,
    route: view.route,
    dataset: payload.dataset || view.dataset,
    title: view.title,
    subtitle: view.subtitle,
    dataSource: "Truth Source -> Adapter -> Domain -> API Contract -> 飞书页面",
    metrics: productionMetricCards(payload.metrics || {}),
    columns: arrayValue(payload.columns),
    records: rows,
    filters: view.filters,
    source: payload.source || {},
    updatedAt: ((payload.source || {}).updated_at) || "",
    emptyText: payload.error || "暂无生产数据",
    error: payload.error || "",
  };
}

function productionMetricCards(metrics) {
  return Object.entries(metrics || {}).map(([key, value]) => ({
    key,
    label: productionMetricLabel(key),
    value: typeof value === "number" ? formatMetricNumber(key, value) : String(value || "0"),
  }));
}

function productionMetricLabel(key) {
  const labels = {
    record_count: "记录数",
    financial_event_count: "收支明细",
    settlement_record_count: "待收待付",
    contract_amount_total: "合同金额",
    collected_amount_total: "已收金额",
    unpaid_amount_total: "未收尾款",
    income_total: "收入合计",
    expense_total: "支出合计",
    profit: "利润",
    receivable_total: "待收金额",
    pending_payment_total: "待付金额",
    room_count: "房间数",
    occupied_count: "占用",
    reserved_count: "预留",
    available_count: "空房",
    maintenance_or_disabled_count: "维修停用",
    missing_room_number_count: "缺房号",
    checked_in_count: "已入住",
    reconciliation_required_count: "需核对",
  };
  return labels[key] || key;
}

function formatMetricNumber(key, value) {
  if (/amount|income|expense|profit|receivable|payment|unpaid|collected/.test(key)) {
    return formatMoney(value);
  }
  return String(value);
}

function productionPageTemplate(page) {
  const source = page.source || {};
  return `
    <header class="boss-center-header production-header">
      <div>
        <span>${escapeHtml(page.title)}</span>
        <h2>${escapeHtml(page.subtitle)}</h2>
        <p>${escapeHtml(page.dataSource)}</p>
      </div>
      <small>${escapeHtml(source.source_file_name || "")}<br>${escapeHtml(page.updatedAt || "更新时间待读取")}</small>
    </header>
    <div class="boss-center-metrics production-metrics">
      ${page.metrics.map(productionMetricTemplate).join("")}
    </div>
    ${productionFilterBarTemplate(page)}
    ${productionTableTemplate(page)}
    <aside class="production-source-box">
      <strong>来源追溯</strong>
      <span>${escapeHtml(source.source_file_name || "-")}</span>
      <span>${escapeHtml(source.source_version || "-")}</span>
      <span>${escapeHtml(source.truth_source_path || "-")}</span>
      <span>Mock：禁止 / legacy_runtime：禁止 / 页面手工数据：禁止</span>
    </aside>
  `;
}

function productionMetricTemplate(item) {
  return `
    <article class="boss-center-metric tone-blue">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
      <small>Excel核对指标</small>
    </article>
  `;
}

function productionFilterBarTemplate(page) {
  const records = arrayValue(page.records);
  const filterControls = (page.filters || []).map((filter) => {
    if (filter === "search") {
      return `<label><span>搜索</span><input class="production-filter" data-filter-key="search" type="search" placeholder="客户/事项/房号/来源" /></label>`;
    }
    const values = uniqueFilterValues(records, filter);
    return `
      <label>
        <span>${escapeHtml(productionColumnLabel(filter))}</span>
        <select class="production-filter" data-filter-key="${escapeHtml(filter)}">
          <option value="">全部</option>
          ${values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}
        </select>
      </label>
    `;
  }).join("");
  return `
    <section class="production-filter-bar" data-production-dataset="${escapeHtml(page.dataset)}">
      ${filterControls}
      <div><span>当前显示</span><strong data-production-visible-count>${records.length}</strong></div>
      <div><span>总记录</span><strong>${records.length}</strong></div>
    </section>
  `;
}

function productionTableTemplate(page) {
  if (!page.records.length) {
    return `<article class="boss-center-empty"><strong>${escapeHtml(page.emptyText)}</strong><p>页面不会用模拟数据补空。</p></article>`;
  }
  const columns = page.columns.length ? page.columns : productionFallbackColumns(page.records[0]);
  return `
    <section class="production-table-wrap">
      <table class="production-table" data-production-table="${escapeHtml(page.dataset)}">
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column.label || productionColumnLabel(column.key))}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${page.records.map((record) => productionRowTemplate(record, columns)).join("")}
        </tbody>
      </table>
    </section>
  `;
}

function productionRowTemplate(record, columns) {
  const searchText = JSON.stringify(record || {}).toLowerCase();
  const attrs = [
    `data-row-search="${escapeHtml(searchText)}"`,
    `data-salesperson_name="${escapeHtml(record.salesperson_name || "")}"`,
    `data-month="${escapeHtml(record.month || "")}"`,
    `data-type="${escapeHtml(record.type || "")}"`,
    `data-status="${escapeHtml(record.status || "")}"`,
    `data-room_flag="${escapeHtml(record.room_flag || "")}"`,
  ].join(" ");
  return `
    <tr ${attrs}>
      ${columns.map((column, index) => `<td>${productionCellTemplate(record, column.key, index === 0)}</td>`).join("")}
    </tr>
  `;
}

function productionCellTemplate(record, key, primary) {
  const value = record[key];
  if (primary) {
    return `
      <details class="production-row-detail">
        <summary>${escapeHtml(formatProductionCell(value))}</summary>
        <div>
          <span>来源：${escapeHtml(record.source_line || "-")}</span>
          <span>Trace：${escapeHtml(record.trace_id || "-")}</span>
          <span>ID：${escapeHtml(record.id || record.contract_id || "")}</span>
        </div>
      </details>
    `;
  }
  return escapeHtml(formatProductionCell(value));
}

function formatProductionCell(value) {
  if (typeof value === "number") return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  return String(value ?? "");
}

function productionFallbackColumns(record) {
  return Object.keys(record || {})
    .filter((key) => !["source_evidence", "trace_id"].includes(key))
    .slice(0, 10)
    .map((key) => ({ key, label: productionColumnLabel(key) }));
}

function productionColumnLabel(key) {
  const labels = {
    salesperson_name: "销售人员",
    month: "月份",
    type: "类型",
    status: "状态",
    room_flag: "房态",
  };
  return labels[key] || key;
}

function uniqueFilterValues(records, key) {
  return [...new Set(records.map((record) => String(record[key] || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "zh-CN"));
}

function hydrateProductionFilters(panel) {
  panel.querySelectorAll(".production-filter").forEach((control) => {
    control.addEventListener("input", () => applyProductionFilters(panel));
    control.addEventListener("change", () => applyProductionFilters(panel));
  });
  applyProductionFilters(panel);
}

function applyProductionFilters(panel = document) {
  const controls = [...panel.querySelectorAll(".production-filter")];
  const rows = [...panel.querySelectorAll(".production-table tbody tr")];
  let visible = 0;
  for (const row of rows) {
    const matched = controls.every((control) => {
      const key = control.dataset.filterKey || "";
      const value = String(control.value || "").trim().toLowerCase();
      if (!value) return true;
      if (key === "search") return String(row.dataset.rowSearch || "").includes(value);
      return String(row.dataset[key] || "").toLowerCase() === value;
    });
    row.hidden = !matched;
    if (matched) visible += 1;
  }
  const counter = panel.querySelector("[data-production-visible-count]");
  if (counter) counter.textContent = String(visible);
}

function bootOmsFrontend() {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountOmsFrontend, { once: true });
    return;
  }
  mountOmsFrontend();
}

async function mountOmsFrontend() {
  try {
    markBootChainStep("dom_ready", "ready");
    bindWorkActionFeedback();
    await startOmsApp();
  } catch (error) {
    markBootChainStep("app_mount", "failed", errorMessage(error));
    renderContractError(`contract_boot_failed:${errorMessage(error)}`);
  }
}

bootOmsFrontend();
