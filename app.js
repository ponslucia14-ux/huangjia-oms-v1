const peopleModel = [
  {
    key: "boss",
    order: "1",
    name: "王梦为",
    role: "总控",
    title: "经营总览",
    badge: "总览｜决策｜验收",
    tone: "red",
    tasks: ["经营总览", "财务日报", "客户总览（隐藏）", "房态总览", "风险管理", "数据分析中心", "我的待办"],
    metrics: { todos: 5, approvals: 5, pending: 3 },
  },
  {
    key: "huanhuan",
    order: "2",
    name: "欢欢",
    role: "销售",
    title: "销售工作台",
    badge: "销售工作台",
    tone: "green",
    tasks: ["新增签约", "意向客户", "销售分析"],
    metrics: { todos: 3, approvals: 0, pending: 0 },
  },
  {
    key: "june",
    order: "3",
    name: "六月",
    role: "店长 + 销售",
    title: "店总工作台",
    badge: "经营事务",
    tone: "green",
    tasks: ["今日经营目标", "销售下房", "明天开会", "今日加急定房", "未30天预产期", "已客户跟踪", "房型/客源盘整", "运营事务提醒"],
    metrics: { todos: 8, approvals: 0, pending: 2 },
  },
  {
    key: "lingling",
    order: "4",
    name: "刘姐",
    role: "出纳",
    title: "财务工作台",
    badge: "财务管理",
    tone: "orange",
    tasks: ["待收款", "待付款", "日结管理", "收支台账", "财务报表"],
    metrics: { todos: 5, approvals: 4, pending: 1 },
  },
  {
    key: "zhangjue",
    order: "5",
    name: "张姐",
    role: "财务总监/会计",
    title: "财务总监工作台",
    badge: "财务复核",
    tone: "blue",
    tasks: ["财务总览", "现金流水", "利润报表", "成本分析", "预算管理", "财务审核"],
    metrics: { todos: 6, approvals: 6, pending: 1 },
  },
  {
    key: "wensao",
    order: "6",
    name: "娜娜",
    role: "管家",
    title: "管家工作台",
    badge: "服务一线",
    tone: "teal",
    tasks: ["今日入住", "在住妈妈", "CRM客户管理"],
    metrics: { todos: 3, approvals: 0, pending: 2 },
  },
  {
    key: "chenchen",
    order: "7",
    name: "陈昌伊",
    role: "产护总监",
    title: "产护工作台",
    badge: "产护服务",
    tone: "purple",
    tasks: ["今日入住", "在住产妇一览", "案例登记", "入住/出馆日期", "产康项目符合", "待排护理需求"],
    metrics: { todos: 6, approvals: 0, pending: 1 },
  },
  {
    key: "shuaishuai",
    order: "8",
    name: "周辰",
    role: "厨师长",
    title: "月厨工作台",
    badge: "厨房餐饮",
    tone: "orange",
    tasks: ["今日入住", "在住饮食一览", "餐后管理", "特殊餐管理", "加餐管理"],
    metrics: { todos: 5, approvals: 0, pending: 1 },
  },
  {
    key: "yajie",
    order: "9",
    name: "尧维",
    role: "行政采购 + 后勤",
    title: "后勤采购工作台",
    badge: "行政后勤",
    tone: "green",
    tasks: ["行品采购", "装修", "园区员工餐具", "园区后勤工具"],
    metrics: { todos: 4, approvals: 0, pending: 2 },
  },
  {
    key: "songxue",
    order: "10",
    name: "宋雪",
    role: "人事行政",
    title: "人事行政工作台",
    badge: "人事行政",
    tone: "blue",
    tasks: ["考勤管理", "工资管理", "员工档案", "人事审批"],
    metrics: { todos: 4, approvals: 2, pending: 0 },
  },
  {
    key: "yuhe",
    order: "11",
    name: "于淳",
    role: "食材采购 + 销售",
    title: "食材采购 + 销售工作台",
    badge: "采购销售",
    tone: "purple",
    tasks: ["食材采购", "销售工作台"],
    metrics: { todos: 2, approvals: 0, pending: 1 },
  },
];

const trustedWorkspaceMap = {
  boss: "boss",
  BOSS: "boss",
  june: "june",
  liujie: "lingling",
  lingling: "lingling",
  huanhuan: "huanhuan",
  nana: "wensao",
  wensao: "wensao",
};

const $ = (selector) => document.querySelector(selector);
const today = new Date();
const identity = resolveLockedIdentity();
const currentPerson = peopleModel.find((person) => person.key === identity.workspaceKey) || peopleModel[0];

function resolveLockedIdentity() {
  const trustedContext = window.OMS_USER_CONTEXT || {};
  const trustedUserMap = window.OMS_FEISHU_USER_WORKSPACE_MAP || {};
  const trustedUserId = String(window.OMS_CURRENT_USER_ID || trustedContext.user_id || "").trim();
  const mappedWorkspace = trustedUserId ? trustedUserMap[trustedUserId] : "";
  const suppliedWorkspace = String(trustedContext.workspace_key || trustedContext.workspace || mappedWorkspace || "boss").trim();
  const workspaceKey = trustedWorkspaceMap[suppliedWorkspace] || suppliedWorkspace;
  const resolved = peopleModel.some((person) => person.key === workspaceKey) ? workspaceKey : "boss";
  return {
    userId: trustedUserId || resolved,
    workspaceKey: resolved,
    source: trustedUserId ? "飞书身份" : "系统身份",
  };
}

function render() {
  const isBoss = currentPerson.key === "boss";
  const visiblePeople = isBoss ? peopleModel : [currentPerson];
  $("#pageTitle").textContent = isBoss ? "凰家运营中心" : `${currentPerson.name}工作台`;
  $("#pageSubtitle").textContent = isBoss
    ? "11个人，每人一个工作台，最后拼成一个运营中心"
    : "您只能查看和处理自己的工作内容";
  $("#lockedUserName").textContent = currentPerson.name;
  $("#lockedUserRole").textContent = `${currentPerson.role} / ${identity.source}`;
  $("#todayText").textContent = formatToday(today);
  $("#operatingCenter").classList.toggle("single-workspace", !isBoss);
  $("#unifiedOverview").hidden = !isBoss;
  $("#operatingCenter").innerHTML = visiblePeople.map(workspaceCard).join("");
  if (isBoss) renderOverview();
}

function workspaceCard(person) {
  const taskItems = person.tasks.map((task) => `<li>${escapeHtml(task)}</li>`).join("");
  return `
    <article class="workspace-card tone-${person.tone}">
      <header>
        <div>
          <span class="order">${person.order}. ${escapeHtml(person.name)}</span>
          <h2>${escapeHtml(person.role)}</h2>
          <p>${escapeHtml(person.title)}</p>
        </div>
        <span class="role-badge">${escapeHtml(person.badge)}</span>
      </header>
      <ul>${taskItems}</ul>
      <footer>
        <span>待办 ${person.metrics.todos}</span>
        <span>审批 ${person.metrics.approvals}</span>
        <span>同步 ${person.metrics.pending}</span>
      </footer>
    </article>
  `;
}

function renderOverview() {
  const totals = peopleModel.reduce(
    (acc, person) => {
      acc.todos += person.metrics.todos;
      acc.approvals += person.metrics.approvals;
      acc.pending += person.metrics.pending;
      return acc;
    },
    { todos: 0, approvals: 0, pending: 0 }
  );
  $("#metricRevenue").textContent = "¥156,600";
  $("#metricRoom").textContent = "12 / 28";
  $("#metricFinance").textContent = `${totals.approvals}`;
  $("#metricPeople").textContent = "11人";
  $("#metricPending").textContent = `${totals.pending}`;
}

function formatToday(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(value);
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
