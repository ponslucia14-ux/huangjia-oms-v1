const SOURCE_OF_TRUTH = "凰家运营中心（OMS）V1.1";
const SINGLE_IDENTITY_POLICY = "feishu_user_id_only";
const DEFAULT_FEISHU_APP_ID = "cli_aaac7e6da2b95cfc";

const workspaceData = {
  boss: workspace("主理办（你）", "总览 | 决策 | 授权", "主理办工作台", "经营总览", ["经营总览", "财务总览", "客户总览（防遗忘）"], 3, 1, 2),
  huanhuan: workspace("欢欢", "销售", "销售工作台", "销售流程", ["销售签约", "意向客户", "销售分析"], 2, 1, 0),
  june: workspace("六月", "店总 + 销售", "店总工作台", "经营事务", ["今日经营目标", "销售下房", "排房协同"], 4, 1, 1),
  liujie: workspace("刘姐", "出纳", "财务工作台", "财务流程", ["待收款", "日结管理", "收支台账"], 3, 1, 2),
  zhangjie: workspace("张姐", "财务总监/会计", "财务总监工作台", "财务复核", ["财务总览", "现金流水", "财务审核"], 3, 1, 1),
  nana: workspace("娜娜", "管家", "管家工作台", "服务流程", ["今日入住", "在住妈妈", "CRM客户管理"], 4, 1, 1),
  chenchangyi: workspace("陈昌辉", "产护部总监", "产护工作台", "产护流程", ["今日入住", "在住产护一览", "套餐信息"], 2, 1, 1),
  zhouchen: workspace("周厨", "厨师长", "料理工作台", "餐饮流程", ["今日入住", "在住饮食一览", "特殊餐管理"], 2, 1, 1),
  yaowei: workspace("维维", "行政采购 + 照护师工资决算", "行政采购工作台", "行政采购流程", ["行政采购", "报销", "照护师工资决算"], 2, 1, 1),
  songxue: workspace("宗惠", "人事行政", "人事行政工作台", "人事行政流程", ["考勤管理", "工资管理", "人事审批"], 2, 1, 1),
  yuchun: workspace("子渝", "食材采购 + 销售", "食材采购 + 销售工作台", "食材采购流程", ["食材采购", "销售工作台"], 2, 1, 1),
};

const trustedWorkspaceKeys = {
  boss: "boss",
  huanhuan: "huanhuan",
  june: "june",
  liujie: "liujie",
  zhangjie: "zhangjie",
  nana: "nana",
  chenchangyi: "chenchangyi",
  zhouchen: "zhouchen",
  yaowei: "yaowei",
  songxue: "songxue",
  yuchun: "yuchun",
};

const $ = (selector) => document.querySelector(selector);
const initialShell = document.querySelector(".app-shell").innerHTML;
let identity = identityBindingError("identity_bootstrap_not_started", "");
let currentWorkspace = null;

function workspace(name, role, title, flowName, flowItems, todoCount, taskCount, approvalCount) {
  return {
    current_user: { name, role, home_title: title },
    home_title: title,
    source_of_truth: SOURCE_OF_TRUTH,
    sections: {
      my_todos: section("我的待办", makeItems(todoCount, `${flowName}待办`, "待处理", true), "暂无待办"),
      my_tasks: section("我的任务", makeItems(taskCount, `${flowName}任务`, "已就绪", false), "暂无任务"),
      my_approvals: section("我的审批", makeItems(approvalCount, `${flowName}审批`, "需确认", false, true), "暂无审批"),
      my_flow: section("我的流程", flowItems.map((item, index) => flowItem(item, index)), "暂无流程"),
    },
    sync_status: {
      state: todoCount ? "待同步" : "正常",
      pending_count: todoCount,
    },
  };
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

function isFeishuContainer() {
  return isFeishuWorkbenchContainer();
}

function feishuRuntimeContext() {
  const userAgent = String(window.navigator && window.navigator.userAgent ? window.navigator.userAgent : "");
  const hasSdk = Boolean(window.h5sdk && window.tt);
  const hasAuthApi = Boolean(
    window.tt && (typeof window.tt.requestAccess === "function" || typeof window.tt.requestAuthCode === "function")
  );
  const isFeishuClient = /Feishu|Lark/i.test(userAgent);
  const isLarkWebview = hasSdk || /Lark/i.test(userAgent);
  const isWorkbenchContainer = Boolean(window.h5sdk && window.tt && hasAuthApi);
  return {
    is_feishu_client: isFeishuClient,
    is_lark_webview: isLarkWebview,
    is_feishu_workbench_container: isWorkbenchContainer,
    has_h5sdk: Boolean(window.h5sdk),
    has_tt: Boolean(window.tt),
    has_auth_api: hasAuthApi,
    user_agent: userAgent,
  };
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

function authConfig() {
  return {
    appId: String(window.OMS_FEISHU_APP_ID || DEFAULT_FEISHU_APP_ID).trim(),
    endpoint: String(window.OMS_AUTH_ENDPOINT || "/api/feishu/identity").trim(),
  };
}

async function bootstrapIdentity() {
  const runtime = feishuRuntimeContext();
  if (!runtime.is_feishu_workbench_container) {
    return identityBindingError("not_feishu_runtime_context", "", runtime);
  }
  if (hasInjectedIdentity()) {
    const injectedIdentity = resolveLockedIdentity();
    injectedIdentity.runtimeContext = runtime;
    return injectedIdentity;
  }
  const config = authConfig();
  if (!config.appId) {
    return identityBindingError("missing_feishu_app_id", "");
  }
  if (!config.endpoint) {
    return identityBindingError("missing_oms_auth_endpoint", "");
  }
  try {
    await waitForFeishuReady();
    const code = await requestFeishuAuthCode(config.appId);
    const payload = await exchangeFeishuAuthCode(config.endpoint, code);
    window.OMS_USER_CONTEXT = payload;
    const authenticatedIdentity = resolveLockedIdentity();
    authenticatedIdentity.runtimeContext = runtime;
    if (authenticatedIdentity.bindingStatus !== "ready") {
      return authenticatedIdentity;
    }
    return authenticatedIdentity;
  } catch (error) {
    return identityBindingError(`feishu_auth_failed:${errorMessage(error)}`, "", runtime);
  }
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

function requestFeishuAuthCode(appId) {
  return new Promise((resolve, reject) => {
    const success = (res) => (res && res.code ? resolve(res.code) : reject(new Error("empty_auth_code")));
    const fail = (error) => reject(error);
    if (window.tt && typeof window.tt.requestAccess === "function") {
      window.tt.requestAccess({
        appID: appId,
        scopeList: [],
        state: `oms_${Date.now()}`,
        success,
        fail: (error) => {
          if (error && error.errno === 103) {
            requestLegacyAuthCode(appId).then(resolve).catch(reject);
            return;
          }
          fail(error);
        },
      });
      return;
    }
    requestLegacyAuthCode(appId).then(resolve).catch(reject);
  });
}

function requestLegacyAuthCode(appId) {
  return new Promise((resolve, reject) => {
    if (!window.tt || typeof window.tt.requestAuthCode !== "function") {
      reject(new Error("feishu_auth_api_unavailable"));
      return;
    }
    window.tt.requestAuthCode({
      appId,
      success: (res) => (res && res.code ? resolve(res.code) : reject(new Error("empty_auth_code"))),
      fail: (error) => reject(error),
    });
  });
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

function errorMessage(error) {
  if (!error) {
    return "unknown";
  }
  if (error.message) {
    return String(error.message);
  }
  if (error.errString) {
    return String(error.errString);
  }
  if (error.errMsg) {
    return String(error.errMsg);
  }
  return String(error);
}

function section(title, items, emptyText) {
  return { title, items, count: items.length, empty_text: items.length ? "" : emptyText };
}

function makeItems(count, title, status, fallback, confirmation = false) {
  return Array.from({ length: count }, (_, index) => ({
    id: `${title}-${index + 1}`,
    title: `${title} #${index + 1}`,
    action: fallback ? "已进入 pending_outbox，不阻断主流程。" : "请在 OMS 内确认处理结果。",
    status,
    fallback,
    needs_confirmation: confirmation,
  }));
}

function flowItem(title, index) {
  return {
    id: `flow-${index + 1}`,
    title,
    action: "仅显示当前用户负责的流程。",
    status: "当前流程",
    fallback: false,
    needs_confirmation: false,
  };
}

function render() {
  if (identity.bindingStatus === "error") {
    renderIdentityError();
    return;
  }
  restoreWorkspaceShell();
  const data = currentWorkspace;
  $("#homeTitle").textContent = data.home_title;
  $("#lockedUserName").textContent = data.current_user.name;
  $("#lockedUserRole").textContent = `${data.current_user.role} / ${identity.source}`;
  $("#workspaceStatus").textContent = data.sync_status.state;
  $("#todoCount").textContent = data.sections.my_todos.count;
  $("#taskCount").textContent = data.sections.my_tasks.count;
  $("#approvalCount").textContent = data.sections.my_approvals.count;
  $("#pendingCount").textContent = data.sync_status.pending_count;
  renderList("#todoList", data.sections.my_todos);
  renderList("#taskList", data.sections.my_tasks);
  renderList("#approvalList", data.sections.my_approvals);
  renderList("#flowList", data.sections.my_flow);
}

function restoreWorkspaceShell() {
  document.body.classList.remove("identity-error-mode");
  const shell = $(".app-shell");
  if (!$("#homeTitle")) {
    shell.innerHTML = initialShell;
  }
}

function renderLoading() {
  $("#homeTitle").textContent = "OMS";
  $("#lockedUserName").textContent = "Feishu";
  $("#lockedUserRole").textContent = "identity authenticating";
  $("#workspaceStatus").textContent = "authenticating";
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
      <h1>\u98de\u4e66\u8eab\u4efd\u8ba4\u8bc1\u5931\u8d25</h1>
      <p>OMS \u5df2\u8bc6\u522b\u98de\u4e66\u8fd0\u884c\u5bb9\u5668\uff0c\u4f46\u672a\u83b7\u53d6\u5230\u6709\u6548\u7684 user_id / open_id / union_id\u3002</p>
      <div class="error-actions">
        <strong>\u8ba4\u8bc1\u72b6\u6001</strong>
        <span>${identity.userId ? "\u672a\u6620\u5c04\u5230\u8fd0\u8425\u4e2d\u5fc3\u5c97\u4f4d" : identity.errorType}</span>
      </div>
    </section>
  `;
}

function renderRuntimeContextBlock() {
  document.body.classList.add("identity-error-mode");
  $(".app-shell").innerHTML = `
    <section class="identity-error-panel" aria-label="OMS Feishu runtime context required">
      <p class="eyebrow">OMS</p>
      <h1>\u8bf7\u4ece\u98de\u4e66\u5de5\u4f5c\u53f0\u6253\u5f00</h1>
      <p>OMS \u53ea\u80fd\u5728 Feishu Workbench / H5 Runtime Context \u5185\u8fd0\u884c\u3002\u76f4\u63a5 URL \u8bbf\u95ee\u5df2\u88ab\u963b\u6b62\u3002</p>
      <div class="error-actions">
        <strong>runtime context</strong>
        <span>is_feishu_workbench_container=false</span>
      </div>
    </section>
  `;
}

function renderList(selector, sectionData) {
  const container = $(selector);
  if (!sectionData.items.length) {
    container.innerHTML = `<p class="empty">${sectionData.empty_text}</p>`;
    return;
  }
  container.innerHTML = sectionData.items.map(itemTemplate).join("");
}

function itemTemplate(item) {
  const fallback = item.fallback ? `<span class="badge warning">pending_outbox</span>` : "";
  const approval = item.needs_confirmation ? `<span class="badge danger">需确认</span>` : "";
  return `
    <article class="work-item">
      <strong>${escapeHtml(item.title)}</strong>
      <p>${escapeHtml(item.action)}</p>
      <footer>
        <span class="badge">${escapeHtml(item.status)}</span>
        ${fallback}
        ${approval}
      </footer>
    </article>
  `;
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
  render();
}

startOmsApp();
