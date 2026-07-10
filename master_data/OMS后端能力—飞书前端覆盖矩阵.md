# OMS 后端能力 - 飞书前端覆盖矩阵

Date: 2026-07-10
Status: P0.10 Coverage Check
Owner: 石磊
Executor: 张照南

---

## 一、检查结论

本轮只做覆盖检查，不新增后端模块，不新增 AI 能力，不扩版本文档，不 Commit，不 Push。

当前 OMS 后端能力已经较多，但飞书前端显化不足。真实交付状态不能按“后端是否存在”判断，必须按以下链路判断：

飞书员工点击
-> 飞书前端页面
-> API Contract
-> Domain / Engine
-> Truth Source / Persistence
-> 返回结果
-> 页面刷新
-> Audit 留痕

当前飞书前端主要可见入口：

| 前端区域 | 当前能力 |
|---|---|
| 首页工作台 | 统一 Action / Status / Risk / 人员卡片 |
| 销售中心 | 销售汇总与真实数据列表，尚未形成销售录入表单 |
| 财务中心 | 财务汇总与真实数据列表，尚未形成岗位级收款/日结/待付表单 |
| 运营中心 | Stay / Room / Caregiver 已进入 Truth Source + Adapter + API + 页面显示 |
| 数据追溯 | `/api/oms/history` 可输出历史链路，前端为通用追溯页 |

当前 API Contract：

| API | 状态 | 说明 |
|---|---|---|
| `/api/oms/home` | 已存在 | 返回个人工作台、业务看板、真实数据摘要 |
| `/api/oms/execute` | 已存在 | 通用执行闭环，能写 action/event/state/lifecycle，但不是岗位专用业务表单 |
| `/api/oms/history` | 已存在 | 通用追溯查询 |
| `/api/feishu/identity` | 已存在 | 飞书身份交换依赖飞书授权可用性 |
| `/api/oms/local-owner-access` | 已存在 | 仅本机老板恢复入口，不是飞书生产验收入口 |

核心风险：

1. 权威身份源已有 11 人真实 EMP -> user_id / open_id / union_id 映射，但当前运行时工作台解析函数仍只解析出 5 人，尚未把正式 Master Data 作为第一身份源。
2. 现有前端菜单仍偏“中心页”，未按 11 人岗位建立完整一级/二级菜单。
3. 大量后端 Engine 已存在，但没有岗位级页面、表单、按钮、审批流和结果页。
4. `/api/oms/execute` 是通用执行闭环，不等于每项业务已经有真实业务表单闭环。
5. 飞书实机验收尚未完成；本地浏览器和 GitHub Pages 只能作为调试证据。

---

## 二、后端能力覆盖矩阵

| 能力 | 后端是否已存在 | API 是否已输出 | 飞书前端菜单位置 | 页面是否已实现 | 数据是否真实 | 操作是否可执行 | 角色可见 | 当前状态 | 缺口和修复动作 |
|---|---|---|---|---|---|---|---|---|---|
| Customer | 已存在于 Domain；部分由 Sales/历史数据承载 | `/api/oms/home` 可间接输出销售/客户类记录 | 销售中心、数据追溯 | 部分实现 | 当前真实客户数据不完整 | 无岗位级客户录入表单 | 石磊、杨欢欢、刘芳羽 | 部分接入 | 建立销售签约录入页时同步形成客户主记录；不要增加签约前客户跟进页 |
| Contract | 已存在 `contract_payment.py`、Domain、Metrics | `/api/oms/home` 可输出 sales_contract_data；`/api/oms/execute` 通用执行 | 销售中心 | 部分实现 | 取决于 `OMS_TRUTH_SOURCE/sales.json` | 无合同手写字段/照片/提交表单 | 石磊、杨欢欢、刘芳羽、张敬东 | 部分接入 | P0 建立签约客户录入、合同手写字段、合同照片、到账确认后提交 |
| Payment | 已存在 `PaymentService`、Domain、Metrics | `/api/oms/home` 可输出 finance_data / financial_events | 财务中心、资金驾驶舱 | 部分实现 | 取决于 `OMS_TRUTH_SOURCE/finance.json` | 无出纳岗位级今日收款/到账确认/日结表单 | 石磊、刘晶、张敬东 | 部分接入 | P0 建立刘晶收款、到账确认、日结、待付录入、转账执行 |
| Expense | 已存在 Domain、Metrics 支持 Expense 指标 | 无专用 API 输出；可能被 finance_data 间接承载 | 财务中心暂未拆分；行政/食材采购菜单未实现 | 未实现 | 无岗位级报销真实数据页 | 不可执行 | 石昊昕、薛子渝、张敬东、刘晶、石磊 | 未接入 | P0 建立报销录入、凭证上传、自动分类结果、报销审核、付款状态 |
| Stay | 已存在 `stay_engine.py`、Domain、Metrics、Production Adapter | `/api/oms/home` 已输出 `stay_data/resident_data` | 运营中心 | 部分实现 | 当前已由 `OMS_TRUTH_SOURCE/room.json.stay_records` 输出 | 通用执行按钮可写闭环；缺岗位表单 | 石磊、刘芳羽、尚丽娜、陈晶辉、周志朋 | 部分接入 | P0 为尚丽娜建立在住信息录入/离馆录入；为刘芳羽建立入住/出馆安排 |
| Room | 已存在 `room_engine.py`、RoomAllocation、Domain、Production Adapter | `/api/oms/home` 已输出 `room_status_data` | 运营中心 | 部分实现 | 当前已由 `OMS_TRUTH_SOURCE/room.json.room_records` 输出 | 通用执行按钮可写闭环；缺排房表操作页 | 石磊、刘芳羽、尚丽娜、陈晶辉 | 部分接入 | P0 建立排房表、空房、超卖风险、倒房期、房号维护 |
| Caregiver 相关工资与服务记录 | 已存在 `caregiver_engine.py`、Domain、Production Adapter；工资决算仅在岗位定义中出现 | `/api/oms/home` 已输出 `caregiver_data/service_data` | 运营中心；行政采购工作台未专门实现 | 部分实现 | 当前照护师服务记录已真实显示；工资决算未接入真实数据 | 服务记录只读/通用执行；工资决算不可执行 | 石磊、尚丽娜、陈晶辉、石昊昕 | 部分接入 | P0 建立照护师对应关系、换照护师原因月报、石昊昕照护师工资决算 |
| Approval | 已存在 `scheduling_approval.py`、`feishu_approval.py`、Domain | `/api/oms/execute` 通用；飞书审批接口存在权限问题记录 | 首页待我审批/风险异常未岗位化 | 部分实现 | 真实飞书审批未完全可用 | 通用执行，不是飞书审批闭环 | 石磊、张敬东、刘晶、刘芳羽 | 部分接入 | P1 打通真实飞书审批权限；岗位待审批列表和审批按钮 |
| Task | 已存在 `operational_core.py`、`business_execution_closure.py`、Domain | `/api/oms/home`、`/api/oms/execute` | 首页今日工作、人员工作台 | 部分实现 | 有执行流/工作项；岗位真实任务需继续映射 | 通用执行可写闭环 | 11 人 | 部分接入 | P1 把每个二级菜单动作映射为明确任务类型，不再只用通用按钮 |
| Notification | 已存在 `notification.py` | 未形成飞书前端通知中心；Feishu mock 通道存在 | 无正式菜单 | 未实现 | 无真实飞书通知送达验收 | 不可执行 | 11 人 | 未接入 | P1 接真实飞书通知/待办；禁止 mock 作为生产结果 |
| Audit | 已存在 append-only `audit_log.py`；入口/执行可写日志 | API 响应可带 trace；无专门 Audit 页面 | 数据追溯可间接查看；无审计中心菜单 | 部分实现 | Audit 日志真实存在 | 用户不可直接按业务查询审计 | 石磊、张敬东 | 部分接入 | P1 建立审计查询入口、按 EMP/模块/时间筛选 |
| Metrics | 已存在 `metrics.py`、Production Adapter metrics | `/api/oms/home` business_dashboard 输出 | 首页、销售/财务/运营中心 | 部分实现 | 运营指标当前真实；销售/财务取决于 Truth Source | 只读 | 石磊及相关岗位 | 部分接入 | P0 老板三大驾驶舱按销售/资金/经营重组；岗位只看授权指标 |
| Dashboard | 已存在 `dashboard_query.py`、首页 master_control | `/api/oms/home` 输出 | 首页、中心页 | 部分实现 | 数据覆盖不均 | 查询/筛选不足 | 石磊 | 部分接入 | P0 建立销售驾驶舱、资金驾驶舱、经营驾驶舱真实页 |
| Alert | 已存在 `alert_engine.py` | 未作为独立 API 输出；风险区只显示摘要 | 风险异常 | 部分实现 | 当前风险更多为摘要/状态 | 无异常处理闭环 | 石磊、刘芳羽、刘晶 | 部分接入 | P1 将 AlertEngine 结果接入风险异常列表和处理按钮 |
| Scheduling | 已存在 `scheduler.py`、`scheduling_decision.py`、`scheduling_approval.py`、RoomAllocation | 未作为岗位专用 API 输出 | 运营中心/排房相关菜单未完整 | 部分实现 | 可读取 Stay/Room/Caregiver 但自动建议未进页面 | 不可作为排房流程执行 | 刘芳羽、石磊 | 部分接入 | P0/P1 将调度建议显化为排房表、超卖、倒房期、审批 |
| Decision | 已存在 `decision_engine.py`、`decision_explainability.py`、AI decision | `/api/oms/execute` 会返回 decision_chain | 执行结果面板 | 部分实现 | 真实解释来自执行闭环 | 缺岗位级决策确认页 | 石磊、刘芳羽、刘晶 | 部分接入 | P1 在关键操作后显示原因、可追溯、重新触发 |
| Execution | 已存在 `execution_engine.py`、`business_execution_closure.py` | `/api/oms/execute` 已输出完整 closure | 所有通用按钮 | 部分实现 | 能写 runtime 结果 | 不是业务专用动作 | 11 人 | 部分接入 | P0/P1 把每个业务按钮从“查看处理”改为明确动作和表单 |
| Knowledge | 已存在 `knowledge.py`、`knowledge_retrieval.py` | 未形成飞书知识页 API | 数据追溯/AI 未正式显化 | 未实现 | 无飞书端生产验收 | 不可执行 | 石磊为主 | 未接入 | P2 后置，暂停扩展 |
| AI Assistant | 已存在 `ai_assistant.py` 等 | 未形成飞书 AI 经营助手真实闭环 | AI经营助手菜单未落地 | 未实现 | 无飞书端生产验收 | 不可执行 | 石磊 | 未接入 | P2 后置，先完成业务闭环 |

---

## 三、已经在飞书可用的能力

严格按“有飞书前端入口 + 有 API + 有真实数据或真实执行结果”判断，当前可算部分可用：

1. 正式身份源 `OMS_飞书身份映射.md` 已提供 11/11 EMP -> user_id / open_id / union_id。
2. 当前运行时工作台解析函数可解析 5/11：石磊、刘芳羽、刘晶、尚丽娜、石昊昕。
3. 首页工作台可显示个人身份、基础菜单、Action / Status / Risk。
4. 运营中心可显示 Stay / Room / Caregiver 真实数据。
5. 数据追溯可通过 `/api/oms/history` 返回历史链路。
6. 通用按钮可触发 `/api/oms/execute`，写入执行闭环和状态更新。

注意：以上仍未等同于 11 人飞书实机通过，因为当前证据来自本机运行时和浏览器调试，尚未逐人在飞书环境完成截图验收。P0.10 早前把“运行时快照 5/11”误写成“身份源只有 5/11”，该结论已由 `OMS十一人飞书身份源对账报告.md` 修正。

---

## 四、后端有但飞书前端没有的能力

P0 相关：

| 能力 | 后端现状 | 前端缺口 |
|---|---|---|
| 合同签约 | ContractService / PaymentService 已有 | 无签约客户录入、手写字段、合同照片、到账后提交 |
| 收款日结 | Payment / Finance 数据能力已有 | 无刘晶今日收款、日结、待付、转账执行、到账确认表单 |
| 报销 | Expense Domain 有 | 无石昊昕/薛子渝报销录入、凭证上传、自动分类、审核 |
| 照护师工资决算 | 岗位定义有，Caregiver 基础有 | 无工资决算数据页和计算结果页 |
| 老板驾驶舱 | Metrics / Dashboard 有 | 未拆成销售驾驶舱、资金驾驶舱、经营驾驶舱 |

P1 相关：

| 能力 | 后端现状 | 前端缺口 |
|---|---|---|
| 审批 | SchedulingApproval / FeishuApproval 有 | 真实飞书审批权限未通；待我审批页未闭环 |
| 通知 | NotificationRouter 有 | 真实飞书通知/待办未接；mock 不可验收 |
| Alert | AlertEngine 有 | 风险异常列表未接真实 AlertResult |
| Audit | AuditEngine 有 | 无审计查询页 |
| Scheduling | Scheduler / Decision 有 | 无排房建议、超卖、倒房期可操作页 |

P2 相关：

| 能力 | 后端现状 | 前端缺口 |
|---|---|---|
| Knowledge | KnowledgeRepository / Retrieval 有 | 无飞书知识入口 |
| AI Assistant | AI Assistant/Reasoning/Recommendation 有 | 无 AI 经营助手生产页 |

---

## 五、前端有菜单但没有真实数据的能力

| 菜单 | 当前问题 | 修复动作 |
|---|---|---|
| 签约客户 | 有中心入口，但没有岗位级录入表单和合同附件 | P0 建 Sales Contract 表单 |
| 客户跟进 | 当前存在菜单，但石磊明确不允许杨欢欢增加签约前客户跟进页 | 对杨欢欢隐藏/停用该二级菜单 |
| 转化指标 | 有指标框架，真实销售数据覆盖不完整 | 接 `OMS_TRUTH_SOURCE/sales.json` 正式销售事实 |
| 收款记录 | 有财务中心，但无刘晶真实录入表单 | P0 建今日收款/到账确认 |
| 待收待付 | 有财务摘要，无岗位操作 | P0 建待付录入/转账执行 |
| 对账追溯 | 有 history API，但未按张敬东/刘晶拆权限 | P1 建财务追溯视图 |
| 入住管理 | 真实 Stay 数据已显示，但尚丽娜录入表单未实现 | P0 建在住信息录入 |
| 房态管理 | 真实 Room 数据已显示，但刘芳羽排房操作未实现 | P0 建排房表/空房/倒房期 |
| 照护师 | 真实 Caregiver 记录已显示，但照护师工资决算未实现 | P0 建工资决算 |
| 服务执行 | 当前为通用执行，不是岗位服务记录 | 尚丽娜不启用服务记录模块；陈晶辉只读照护安排 |

---

## 六、前端有页面但没有操作闭环的能力

| 页面 | 当前闭环情况 | 判断 |
|---|---|---|
| 销售中心 | 可看数据；无录入/照片/提交表单 | 部分接入 |
| 财务中心 | 可看数据；无收款/日结/待付/转账表单 | 部分接入 |
| 运营中心 | 可看 Stay/Room/Caregiver；按钮为通用执行 | 部分接入 |
| 数据追溯 | 可查询；无岗位筛选和审计式验收 | 部分接入 |
| 首页 Action/Status/Risk | 可触发通用执行；不是具体业务动作 | 部分接入 |

---

## 七、按经营重要性排序的修复清单

### P0

1. 完成 11 人飞书 `user_id -> workspace_key` 映射，不允许共用老板页面。
2. 重建 11 人一级/二级菜单，按真实岗位显示，不按通用中心页显示。
3. 销售签约闭环：签约录入、合同手写字段、合同照片、到账确认后提交。
4. 财务闭环：今日收款、销售明细、日结、待付录入、转账执行、到账确认。
5. 运营闭环：在住录入、房号、宝宝信息、照护师关系、离馆、排房、空房、超卖、倒房期。
6. 报销闭环：行政采购/食材采购凭证上传、自动分类、审核、付款状态。
7. 老板三大驾驶舱：销售、资金、经营，全部只读真实数据。

### P1

1. 飞书真实审批。
2. 飞书真实通知和待办。
3. 风险异常接 AlertEngine。
4. 数据追溯按角色授权。
5. 月报和经营分析。

### P2

1. AI 经营助手。
2. Knowledge / AI 建议 / AI 推理。

---

## 八、当前阻塞项

| 阻塞项 | 影响 | 等级 |
|---|---|---|
| 运行时解析未使用正式身份源作为第一入口 | 权威身份 11/11 已存在，但当前工作台解析仍只能识别 5/11 | P0 |
| 飞书实机未逐人验收 | 不能宣布生产交付 | P0 |
| 前端菜单不是岗位级 | 员工看到的不是自己的真实工作台 | P0 |
| 关键业务缺表单 | 后端能力无法转成日常工作 | P0 |
| 真实飞书审批/通知权限未完全打通 | 审批通知不能验收 | P1 |
