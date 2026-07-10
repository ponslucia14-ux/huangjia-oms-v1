# OMS 十一人岗位菜单规范

Date: 2026-07-10
Status: P0.11 Menu Freeze
Owner: 石磊
Executor: 张照南

---

## 一、冻结原则

本文件只冻结 11 人岗位菜单规范，不开发页面，不新增业务模块，不 Commit。

飞书端 OMS 后续页面必须按本文件开发：

```text
EMP
-> user_id / open_id / union_id
-> role_code
-> workspace
-> 一级菜单
-> 二级菜单
-> 页面
-> API
-> Domain / Engine
-> Truth Source
-> Audit
```

规则：

1. 所有身份以 `OMS_组织主数据.md` 与 `OMS_飞书身份映射.md` 为唯一来源。
2. 所有页面不得使用 Mock、legacy_runtime、临时快照作为生产数据。
3. 没有生产数据时显示“暂无生产数据”。
4. 删除权限默认禁止；业务撤销必须通过取消、作废、禁用、出馆、关闭等状态动作完成，并写 Audit。
5. 只读岗位不得出现新增、修改、审批、删除按钮。
6. 管家岗位不得显示合同金额。
7. 杨欢欢岗位不得出现签约前客户跟进页面。
8. 宗惠岗位不启用培训管理和排班管理。

---

## 二、API 与 Truth Source 口径

| 类型 | 当前 API | 用途 |
|---|---|---|
| 身份入口 | `/api/feishu/identity` | 飞书身份交换，返回 EMP / user_id / workspace |
| 工作台读取 | `/api/oms/home` | 读取当前人员首页、菜单、Domain 数据、Metrics |
| 动作执行 | `/api/oms/execute` | 表单提交、状态变更、审批动作、写 Audit |
| 数据追溯 | `/api/oms/history` | 按 EMP、模块、时间、对象追溯 |
| 本地恢复 | `/api/oms/local-owner-access` | 仅石磊在飞书认证异常时受控恢复 |

| Truth Source | 覆盖范围 |
|---|---|
| `D:\凰家大脑\brain\03_organization\oms\OMS_组织主数据.md` | EMP、正式姓名、部门、岗位、role_code |
| `D:\凰家大脑\brain\03_organization\oms\OMS_飞书身份映射.md` | user_id、open_id、union_id |
| `OMS_TRUTH_SOURCE/sales.json` | Customer / Contract / 销售结果 |
| `OMS_TRUTH_SOURCE/finance.json` | Payment / Finance / Settlement / 待收待付 |
| `OMS_TRUTH_SOURCE/room.json` | Stay / Room / Caregiver 当前生产运营数据 |
| `OMS_TRUTH_SOURCE/events.jsonl` | Event / Task / Execution 追溯 |
| `live_runtime/audit_center/audit_events.jsonl` | Audit Log |

---

## 三、权限标记

| 标记 | 含义 |
|---|---|
| 查看 | 页面可见、可读取真实生产数据 |
| 新增 | 可新建业务记录 |
| 修改 | 可更新业务状态或字段 |
| 审批 | 可对他人提交的动作做批准、驳回、确认 |
| 删除 | 是否允许物理删除；本规范全部为“否” |

---

## 四、EMP001 石磊

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP001 |
| 正式姓名 | 石磊 |
| role_code | ROLE_OWNER |
| workspace | 主理办工作台 |

### 一级菜单

今日工作、销售驾驶舱、资金驾驶舱、经营驾驶舱、风险异常、待我审批、决策与授权、数据追溯、AI经营助手。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 今日工作 | 我的待办 | Task / Approval / Alert | `/api/oms/home` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 是 | 是 | 否 | 可处理待办和异常，不直接改原始数据 |
| 销售驾驶舱 | 签约客户 | Customer / Contract | `/api/oms/home` | `OMS_TRUTH_SOURCE/sales.json` | 是 | 否 | 否 | 否 | 否 | 主理办只读销售全局 |
| 销售驾驶舱 | 成交金额与转化 | Contract / Metrics | `/api/oms/home` | `OMS_TRUTH_SOURCE/sales.json` | 是 | 否 | 否 | 否 | 否 | 指标只读 |
| 资金驾驶舱 | 今日收款 | Payment / Finance | `/api/oms/home` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 否 | 否 | 否 | 否 | 资金总览只读 |
| 资金驾驶舱 | 待收待付 | Payment / Expense | `/api/oms/home` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 否 | 否 | 否 | 否 | 金额口径来自 Finance Adapter |
| 经营驾驶舱 | 在住总览 | Stay | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 经营查看 |
| 经营驾驶舱 | 房态总览 | Room | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 经营查看 |
| 经营驾驶舱 | 照护师总览 | Caregiver | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 经营查看 |
| 风险异常 | 超卖 / 倒房 / 到账异常 | Alert / Room / Payment | `/api/oms/home` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 是 | 是 | 否 | 处理结果写 Audit |
| 待我审批 | 审批列表 | Approval | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 是 | 是 | 否 | 审批通过/驳回 |
| 决策与授权 | 授权动作 | Approval / Decision | `/api/oms/execute` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 是 | 是 | 否 | 授权必须写 reason |
| 数据追溯 | 审计查询 | Audit | `/api/oms/history` | `live_runtime/audit_center/audit_events.jsonl` | 是 | 否 | 否 | 否 | 否 | 只读追溯 |
| AI经营助手 | 经营问答 | Knowledge / Metrics | `/api/oms/home` | Domain 汇总 | 是 | 否 | 否 | 否 | 否 | P2，当前只保留菜单规范 |

### 只读页面

销售驾驶舱、资金驾驶舱、经营驾驶舱、数据追溯、AI经营助手。

---

## 五、EMP002 宗惠

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP002 |
| 正式姓名 | 宗惠 |
| role_code | ROLE_HR |
| workspace | 人事行政工作台 |

### 一级菜单

员工花名册、考勤导入、工资表、工资核算结果、待处理事项。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 员工花名册 | 正式员工列表 | Employee | `/api/oms/home` | `OMS_组织主数据.md` | 是 | 否 | 否 | 否 | 否 | 只读组织主数据 |
| 员工花名册 | 飞书身份状态 | Employee | `/api/oms/home` | `OMS_飞书身份映射.md` | 是 | 否 | 否 | 否 | 否 | 只读 user_id 状态 |
| 考勤导入 | 考勤文件上传 | Employee / Task | `/api/oms/execute` | 待建 HR Truth Source | 是 | 是 | 是 | 否 | 否 | 无数据时显示暂无生产数据 |
| 工资表 | 工资表上传 | Employee / Payment | `/api/oms/execute` | 待建 HR Truth Source | 是 | 是 | 是 | 否 | 否 | 仅上传和核对 |
| 工资核算结果 | 员工工资结果 | Employee / Payment | `/api/oms/home` | 待建 HR Truth Source | 是 | 否 | 否 | 否 | 否 | 只读核算结果 |
| 待处理事项 | HR 待办 | Task | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 是 | 否 | 否 | 处理本人 HR 事项 |

### 只读页面

正式员工列表、飞书身份状态、工资核算结果。

禁用页面：

培训管理、排班管理。

---

## 六、EMP003 张敬东

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP003 |
| 正式姓名 | 张敬东 |
| role_code | ROLE_ACCOUNTANT |
| workspace | 财务总监工作台 |

### 一级菜单

月度入账、现金账、实入账、财务报表、对账追溯。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 月度入账 | 月度入账表 | Payment / Finance | `/api/oms/home` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 是 | 是 | 否 | 否 | 会计可补录入账口径 |
| 现金账 | 现金流水 | Payment / Finance | `/api/oms/home` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 是 | 是 | 否 | 否 | 现金账调整写 Audit |
| 实入账 | 实入账核对 | Payment / Finance | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 否 | 是 | 是 | 否 | 可确认核对结果 |
| 财务报表 | 月度财务报表 | Metrics / Payment / Expense | `/api/oms/home` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 否 | 否 | 否 | 否 | 只读报表 |
| 对账追溯 | 财务审计链 | Audit / Payment | `/api/oms/history` | `live_runtime/audit_center/audit_events.jsonl` | 是 | 否 | 否 | 否 | 否 | 只读追溯 |

### 只读页面

财务报表、对账追溯。

---

## 七、EMP004 刘晶

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP004 |
| 正式姓名 | 刘晶 |
| role_code | ROLE_CASHIER |
| workspace | 财务工作台 |

### 一级菜单

今日收款、销售明细、日结、待付录入、转账执行、到账确认。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 今日收款 | 收款列表 | Payment | `/api/oms/home` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 否 | 是 | 否 | 否 | 可标记到账状态 |
| 销售明细 | 本日销售收款关联 | Contract / Payment | `/api/oms/home` | `OMS_TRUTH_SOURCE/sales.json` + `finance.json` | 是 | 否 | 否 | 否 | 否 | 只读销售明细 |
| 日结 | 日结录入 | Payment / Task | `/api/oms/execute` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 是 | 是 | 否 | 否 | 提交日结结果 |
| 待付录入 | 待付款项 | Expense / Payment | `/api/oms/execute` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 是 | 是 | 否 | 否 | 待付不可直接删除 |
| 转账执行 | 转账任务 | Payment / Task | `/api/oms/execute` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 否 | 是 | 否 | 否 | 记录执行结果 |
| 到账确认 | 到账确认表 | Payment | `/api/oms/execute` | `OMS_TRUTH_SOURCE/finance.json` | 是 | 否 | 是 | 是 | 否 | 到账确认必须留痕 |

### 只读页面

销售明细。

---

## 八、EMP005 石昊昕

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP005 |
| 正式姓名 | 石昊昕 |
| role_code | ROLE_ADMIN |
| workspace | 行政采购工作台 |

### 一级菜单

行政采购报销、截图/凭证上传、自动分类结果、报销审核、照护师工资决算。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 行政采购报销 | 报销录入 | Expense | `/api/oms/execute` | 待建 Expense Truth Source | 是 | 是 | 是 | 否 | 否 | 行政采购支出 |
| 截图/凭证上传 | 凭证上传 | Expense / Task | `/api/oms/execute` | 待建 Expense Truth Source | 是 | 是 | 是 | 否 | 否 | 凭证不可物理删除 |
| 自动分类结果 | 分类结果 | Expense / Metrics | `/api/oms/home` | 待建 Expense Truth Source | 是 | 否 | 是 | 否 | 否 | 可修正分类 |
| 报销审核 | 报销审核列表 | Approval / Expense | `/api/oms/execute` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 是 | 是 | 否 | 仅授权范围审核 |
| 照护师工资决算 | 工资决算表 | Caregiver / Payment | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` + 待建工资 Truth Source | 是 | 是 | 是 | 否 | 否 | 不接考勤工资外模块 |

### 只读页面

自动分类结果可查看；工资决算结果提交后对历史记录只读。

---

## 九、EMP006 杨欢欢

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP006 |
| 正式姓名 | 杨欢欢 |
| role_code | ROLE_SALES |
| workspace | 销售工作台 |

### 一级菜单

签约客户录入、合同手写字段录入、合同照片、到账确认后的提交、本人销售结果。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 签约客户录入 | 签约客户表单 | Customer / Contract | `/api/oms/execute` | `OMS_TRUTH_SOURCE/sales.json` | 是 | 是 | 是 | 否 | 否 | 只录入已签约客户 |
| 合同手写字段录入 | 合同字段表 | Contract | `/api/oms/execute` | `OMS_TRUTH_SOURCE/sales.json` | 是 | 是 | 是 | 否 | 否 | 必须关联合同编号 |
| 合同照片 | 合同照片上传 | Contract / Task | `/api/oms/execute` | `OMS_TRUTH_SOURCE/sales.json` | 是 | 是 | 是 | 否 | 否 | 照片需 source_evidence |
| 到账确认后的提交 | 待提交合同 | Contract / Payment | `/api/oms/execute` | `OMS_TRUTH_SOURCE/sales.json` + `finance.json` | 是 | 否 | 是 | 否 | 否 | 只有到账后可提交 |
| 本人销售结果 | 我的销售结果 | Contract / Metrics | `/api/oms/home` | `OMS_TRUTH_SOURCE/sales.json` | 是 | 否 | 否 | 否 | 否 | 只看本人 |

### 只读页面

本人销售结果。

禁用页面：

签约前客户跟进。

---

## 十、EMP007 薛子渝

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP007 |
| 正式姓名 | 薛子渝 |
| role_code | ROLE_SALES |
| workspace | 食材采购 + 销售工作台 |

### 一级菜单

食材采购报销、截图/凭证上传、自动分类结果、报销审核、销售签约录入。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 食材采购报销 | 食材采购录入 | Expense | `/api/oms/execute` | 待建 Expense Truth Source | 是 | 是 | 是 | 否 | 否 | 食材采购支出 |
| 截图/凭证上传 | 凭证上传 | Expense / Task | `/api/oms/execute` | 待建 Expense Truth Source | 是 | 是 | 是 | 否 | 否 | 凭证不可物理删除 |
| 自动分类结果 | 分类结果 | Expense / Metrics | `/api/oms/home` | 待建 Expense Truth Source | 是 | 否 | 是 | 否 | 否 | 可修正本人提交 |
| 报销审核 | 报销状态 | Approval / Expense | `/api/oms/home` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 否 | 否 | 否 | 只看审核状态 |
| 销售签约录入 | 签约客户表单 | Customer / Contract | `/api/oms/execute` | `OMS_TRUTH_SOURCE/sales.json` | 是 | 是 | 是 | 否 | 否 | 与销售规则一致 |

### 只读页面

报销状态、本人销售结果。

---

## 十一、EMP008 刘芳羽

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP008 |
| 正式姓名 | 刘芳羽 |
| role_code | ROLE_STORE_MANAGER |
| workspace | 店总工作台 |

### 一级菜单

在住总览、排房表、空房、超卖风险、倒房期、已生未入住、入住/出馆安排、销售签约录入。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 在住总览 | 当前在住 | Stay | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 经营只读 |
| 排房表 | 排房计划 | Room / Stay / Scheduling | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 是 | 是 | 是 | 否 | 排房动作必须写 reason |
| 空房 | 可用房 | Room | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 只读房态 |
| 超卖风险 | 超卖列表 | Alert / Room / Stay | `/api/oms/home` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 是 | 是 | 否 | 处理风险不删记录 |
| 倒房期 | 倒房安排 | Room / Stay / Scheduling | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 是 | 是 | 是 | 否 | 形成调度记录 |
| 已生未入住 | 待入住客户 | Stay / Contract | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` + `sales.json` | 是 | 否 | 是 | 否 | 否 | 可安排入住 |
| 入住/出馆安排 | 安排表 | Stay | `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 是 | 是 | 否 | 否 | 办理安排，不直接结算金额 |
| 销售签约录入 | 签约客户表单 | Customer / Contract | `/api/oms/execute` | `OMS_TRUTH_SOURCE/sales.json` | 是 | 是 | 是 | 否 | 否 | 店总兼销售 |

### 只读页面

在住总览、空房。

---

## 十二、EMP009 尚丽娜

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP009 |
| 正式姓名 | 尚丽娜 |
| role_code | ROLE_BUTLER |
| workspace | 管家工作台 |

### 一级菜单

在住信息录入、入住评估、房号、客户与宝宝信息、照护师对应关系、离馆录入。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 在住信息录入 | 在住信息表 | Stay / Customer | `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 是 | 是 | 否 | 否 | 不显示合同金额 |
| 入住评估 | 入住评估表 | Stay / Task | `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 是 | 是 | 否 | 否 | 评估记录写 Audit |
| 房号 | 房号信息 | Room / Stay | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 是 | 否 | 否 | 仅维护授权字段 |
| 客户与宝宝信息 | 基础信息 | Customer / Stay | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 是 | 是 | 否 | 否 | 隐藏合同金额 |
| 照护师对应关系 | 对应关系 | Caregiver / Stay | `/api/oms/home` + `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 是 | 是 | 否 | 否 | 可维护对应关系 |
| 离馆录入 | 离馆表 | Stay | `/api/oms/execute` | `OMS_TRUTH_SOURCE/room.json` | 是 | 是 | 是 | 否 | 否 | 离馆为状态变更 |

### 只读页面

房号当前状态、照护师当前状态。

禁用页面：

合同金额、客户关怀、交接事项、服务记录模块。

---

## 十三、EMP010 陈晶辉

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP010 |
| 正式姓名 | 陈晶辉 |
| role_code | ROLE_NURSING_DIRECTOR |
| workspace | 产护工作台 |

### 一级菜单

在住客户、套餐与入住/出馆信息、产康套餐、照护安排、换照护师原因月报。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 在住客户 | 在住客户列表 | Stay / Customer | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 只读 |
| 套餐与入住/出馆信息 | 套餐与日期 | Stay / Contract | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` + `sales.json` | 是 | 否 | 否 | 否 | 否 | 不显示金额 |
| 产康套餐 | 产康套餐内容 | Stay / Task | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 只读 |
| 照护安排 | 照护安排表 | Caregiver / Stay | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 只读为主 |
| 换照护师原因月报 | 月报 | Caregiver / Metrics | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 月报只读 |

### 只读页面

全部页面只读。

---

## 十四、EMP011 周志朋

身份：

| 字段 | 值 |
|---|---|
| EMP | EMP011 |
| 正式姓名 | 周志朋 |
| role_code | ROLE_KITCHEN_DIRECTOR |
| workspace | 料理工作台 |

### 一级菜单

在住客户、套餐、入住/出馆日期、忌口、料理相关提醒。

### 页面规范

| 一级菜单 | 二级菜单 / 页面 | 来源 Domain | 来源 API | Truth Source | 查看 | 新增 | 修改 | 审批 | 删除 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|
| 在住客户 | 在住客户列表 | Stay / Customer | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 只读 |
| 套餐 | 套餐信息 | Stay / Contract | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` + `sales.json` | 是 | 否 | 否 | 否 | 否 | 不显示金额 |
| 入住/出馆日期 | 日期表 | Stay | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 只读 |
| 忌口 | 忌口信息 | Stay / Task | `/api/oms/home` | `OMS_TRUTH_SOURCE/room.json` | 是 | 否 | 否 | 否 | 否 | 只读 |
| 料理相关提醒 | 料理提醒 | Notification / Task | `/api/oms/home` | `OMS_TRUTH_SOURCE/events.jsonl` | 是 | 否 | 否 | 否 | 否 | 只读提醒 |

### 只读页面

全部页面只读。

---

## 十五、删除与审计统一规则

| 规则 | 说明 |
|---|---|
| 物理删除 | 全员禁止 |
| 业务取消 | 使用 `cancel` / `void` / `disabled` / `checked_out` 等状态 |
| 修改原因 | 所有新增、修改、审批动作必须填写 reason |
| 审计日志 | 所有动作必须写 Audit |
| 事件发布 | 所有关键动作必须发布 Event |
| 未授权动作 | 返回权限不足，不得默认进入石磊工作台 |

---

## 十六、后续开发顺序

确认本规范后，后续开发顺序应为：

1. 按 11 人生成飞书工作台菜单入口。
2. 先实现只读真实数据页面。
3. 再实现 P0 操作表单。
4. 每个表单接 `/api/oms/execute`、Domain、Truth Source、Audit。
5. 最后做飞书实机逐人截图验收。

