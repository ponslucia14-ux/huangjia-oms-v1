const workspaceData = {
  boss: workspace("BOSS", "BOSS", "BOSS工作台", "经营总览", ["经营总览", "风险提醒", "今日全局事项"], 3, 1, 2),
  june: workspace("六月", "六月", "六月工作台", "房态流程", ["排房", "调房", "房态确认"], 4, 1, 1),
  liujie: workspace("刘姐", "刘姐", "刘姐工作台", "财务流程", ["收款确认", "日结", "对账", "审批"], 3, 1, 2),
  sales: workspace("销售", "销售", "销售工作台", "销售流程", ["签约", "客户", "提报"], 2, 1, 0),
  huanhuan: workspace("欢欢", "销售", "欢欢工作台", "销售流程", ["签约", "客户", "提报"], 2, 1, 0),
  nana: workspace("娜娜", "娜娜", "娜娜工作台", "服务流程", ["入住准备", "服务安排", "出馆流程"], 4, 1, 1),
  admin: workspace("行政", "行政", "行政工作台", "行政流程", ["行政支持", "制度", "日常协同"], 1, 1, 0),
  procurement: workspace("采购", "采购", "采购工作台", "采购流程", ["采购申请", "物资补给", "消耗品补充"], 2, 1, 1),
  maternity_care: workspace("产护", "产护", "产护工作台", "产护流程", ["人员调度", "护理资源", "临时支援"], 2, 1, 1),
  kitchen: workspace("厨房", "厨房", "厨房工作台", "餐饮流程", ["餐食准备", "特殊餐需求", "备餐计划"], 2, 1, 1),
  logistics: workspace("后勤", "后勤", "后勤工作台", "后勤流程", ["房间清理", "设备维护", "物资配送"], 2, 1, 1),
};

const trustedWorkspaceMap = {
  BOSS: "boss",
  boss: "boss",
  六月: "june",
  june: "june",
  刘姐: "liujie",
  liujie: "liujie",
  销售: "sales",
  sales: "sales",
  欢欢: "huanhuan",
  huanhuan: "huanhuan",
  娜娜: "nana",
  nana: "nana",
  行政: "admin",
  admin: "admin",
  采购: "procurement",
  procurement: "procurement",
  产护: "maternity_care",
  maternity_care: "maternity_care",
  厨房: "kitchen",
  kitchen: "kitchen",
  后勤: "logistics",
  logistics: "logistics",
};

const $ = (selector) => document.querySelector(selector);
const identity = resolveLockedIdentity();
const currentWorkspace = workspaceData[identity.workspaceKey] || workspaceData.boss;

function workspace(name, role, title, flowName, flowItems, todoCount, taskCount, approvalCount) {
  return {
    current_user: { name, role, home_title: title },
    home_title: title,
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
  const trustedUserId = String(window.OMS_CURRENT_USER_ID || trustedContext.user_id || "").trim();
  const mappedWorkspace = trustedUserId ? trustedUserMap[trustedUserId] : "";
  const suppliedWorkspace = String(trustedContext.workspace_key || trustedContext.workspace || mappedWorkspace || "boss").trim();
  const workspaceKey = trustedWorkspaceMap[suppliedWorkspace] || "boss";
  return {
    userId: trustedUserId || workspaceKey,
    workspaceKey,
    source: trustedUserId ? "飞书身份" : "系统身份",
  };
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

render();
