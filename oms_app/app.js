const appData = {
  june: userState("六月", "六月", "六月工作台", "我的房态", 5, 0, 0, "每日排房", "房态流"),
  liujie: userState("刘姐", "刘姐", "刘姐工作台", "我的财务", 0, 0, 0, "", "财务流"),
  sales: userState("销售", "销售", "销售工作台", "我的客户", 0, 0, 0, "", "销售流"),
  nana: userState("娜娜", "娜娜", "娜娜工作台", "我的服务", 5, 0, 0, "每日入住/服务", "服务流"),
  boss: bossState(),
  huanhuan: userState("欢欢", "销售", "销售工作台", "我的客户", 0, 0, 0, "", "销售流"),
};

const flowDefs = [
  { key: "sales", title: "销售流", owner: "销售 / 欢欢", desc: "签约、客户、提报" },
  { key: "liujie", title: "财务流", owner: "刘姐", desc: "收款、对账、审批" },
  { key: "june", title: "房态流", owner: "六月", desc: "排房、调房、房态确认" },
  { key: "nana", title: "服务流", owner: "娜娜", desc: "入住、服务、产护协同" },
];

const state = {
  userId: localStorage.getItem("oms.native.user") || "boss",
  tab: "workbench",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function userState(name, role, homeTitle, rolePanelTitle, todoCount, taskCount, approvalCount, taskTitle, flowName) {
  const todos = makeItems(todoCount, taskTitle, "待外部同步", true);
  return {
    current_user: { name, role, home_title: homeTitle },
    home_title: homeTitle,
    sections: {
      my_todos: section("我的待办", todos, "暂无待办"),
      my_tasks: section("我的任务", makeItems(taskCount, "执行任务", "已就绪", false), "暂无任务"),
      my_approvals: section("我的审批", makeItems(approvalCount, "审批确认", "需关注", false, true), "暂无审批"),
      role_home: section(rolePanelTitle, todos, rolePanelTitle.replace("我的", "暂无") + "待处理事项"),
    },
    sync_status: syncStatus(22),
    decision_assist: {
      messages: todoCount ? [`有 ${todoCount} 个事项等待外部同步，不影响继续处理。`] : ["当前首页暂无系统提醒。"],
    },
    flowName,
  };
}

function bossState() {
  const todos = [
    ...makeItems(5, "每日排房", "待外部同步", true),
    ...makeItems(5, "每日入住/服务", "待外部同步", true),
    ...makeItems(5, "每日经营判断", "需关注", false, true),
    ...makeItems(8, "跨岗位协同", "待外部同步", true),
  ];
  const approvals = makeItems(5, "每日经营判断", "需关注", false, true);
  return {
    current_user: { name: "BOSS", role: "BOSS", home_title: "BOSS工作台" },
    home_title: "BOSS工作台",
    sections: {
      my_todos: section("我的待办", todos, "暂无待办"),
      my_tasks: section("我的任务", [], "暂无任务"),
      my_approvals: section("我的审批", approvals, "暂无审批"),
      role_home: section("经营总览", todos, "暂无全局待处理事项"),
    },
    sync_status: syncStatus(22),
    decision_assist: {
      messages: ["有 5 个事项需要确认。", "有 18 个事项等待外部同步，不影响继续处理。"],
    },
    flowName: "经营总览",
  };
}

function section(title, items, emptyText) {
  return { title, count: items.length, items, empty_text: items.length ? "" : emptyText };
}

function makeItems(count, title, status, fallback, confirmation = false) {
  if (!count) return [];
  return Array.from({ length: count }, (_, index) => ({
    id: `${title}-${index + 1}`,
    title,
    action: fallback ? "在 OMS 中确认同步结果；不要回到 Excel/微信群重复操作。" : "在 OMS 中查看并确认处理结果。",
    status,
    needs_confirmation: confirmation,
    fallback,
  }));
}

function syncStatus(pendingCount) {
  return {
    title: "外部同步",
    state: pendingCount ? "待同步" : "正常",
    pending_count: pendingCount,
    failed_count: 0,
  };
}

function render() {
  const data = appData[state.userId] || appData.boss;
  $("#userSelect").value = state.userId;
  $("#homeTitle").textContent = data.home_title;
  $("#todayTodos").textContent = data.sections.my_todos.count;
  $("#todayApprovals").textContent = data.sections.my_approvals.count;
  $("#pendingSync").textContent = data.sync_status.pending_count;
  $("#syncState").textContent = data.sync_status.state;
  $("#profileName").textContent = data.current_user.name;
  $("#profileRole").textContent = `${data.current_user.role} / ${data.home_title}`;
  $("#avatar").textContent = data.current_user.name.slice(0, 1).toUpperCase();

  renderList("#todoList", data.sections.my_todos);
  renderList("#taskList", data.sections.my_tasks);
  renderList("#todayList", data.sections.role_home);
  renderList("#approvalList", data.sections.my_approvals);
  renderHistory(data);
  renderFlows();
  renderBossPanel();
}

function renderList(selector, sectionData) {
  const container = $(selector);
  if (!sectionData.items.length) {
    container.innerHTML = `<p class="empty">${sectionData.empty_text}</p>`;
    return;
  }
  container.innerHTML = sectionData.items.slice(0, 6).map(itemTemplate).join("");
  if (sectionData.items.length > 6) {
    container.insertAdjacentHTML("beforeend", `<p class="empty">还有 ${sectionData.items.length - 6} 条</p>`);
  }
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

function renderHistory(data) {
  const items = data.sections.role_home.items.map((item, index) => ({
    ...item,
    title: `${item.title} #${index + 1}`,
    status: item.fallback ? "已进入待同步" : item.status,
  }));
  renderList("#historyList", section("我的历史记录", items, "暂无历史记录"));
}

function renderFlows() {
  const activeData = appData[state.userId] || appData.boss;
  $("#flowGrid").innerHTML = flowDefs.map((flow) => {
    const data = appData[flow.key];
    const count = data.sections.role_home.count;
    const active = activeData.flowName === flow.title ? "badge warning" : "badge";
    return `
      <article class="flow-card">
        <span class="${active}">${flow.owner}</span>
        <h3>${flow.title}</h3>
        <div class="count">${count}</div>
        <p>${flow.desc}</p>
      </article>
    `;
  }).join("");
}

function renderBossPanel() {
  const boss = appData.boss;
  renderList("#riskList", section("风险提醒", boss.sections.my_approvals.items, "暂无风险提醒"));
  renderList("#globalList", section("今日全局事项", boss.sections.role_home.items, "暂无全局事项"));
}

function activateTab(tab) {
  state.tab = tab;
  $$(".tab-button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  $$(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === tab));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

$("#userSelect").addEventListener("change", (event) => {
  state.userId = event.target.value;
  localStorage.setItem("oms.native.user", state.userId);
  render();
});

$$(".tab-button").forEach((button) => button.addEventListener("click", () => activateTab(button.dataset.tab)));

$("#bossEntry").addEventListener("click", () => {
  $("#bossPanel").hidden = false;
});

$("#closeBoss").addEventListener("click", () => {
  $("#bossPanel").hidden = true;
});

render();
