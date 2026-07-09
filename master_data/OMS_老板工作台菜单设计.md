# OMS 老板工作台菜单设计

阶段：P0.5 OMS 老板工作台落地

目标：老板打开 OMS 后，可以直接查看经营、销售、财务、运营数据，并从左侧菜单进入常用页面。

## 一、菜单原则

- 入口对象：老板 / 石磊 / `user_id=a2c82cb4`
- 首页定位：老板日常经营工作台
- 菜单结构：一级菜单 + 二级菜单
- 数据来源：只读取 OMS 真实运行数据，不使用 mock 数据
- 页面要求：所有页面必须有真实数据、可点击记录、可追溯来源

## 二、一级菜单

| 一级菜单 | 路由 | 定位 | 对应 Domain | 数据来源 |
|---|---|---|---|---|
| 首页工作台 | `home` | 今日工作、当前状态、风险异常 | `task`, `room`, `finance`, `sales` | `/api/oms/home`、`business_dashboard`、`sections` |
| 销售中心 | `sales` | 销售签约、客户跟进、转化状态 | `sales` | `OMS_TRUTH_SOURCE/sales.json`、`source_evidence_available_data.sales_contract_data`、`sales_schema` |
| 财务中心 | `finance` | 收款、待收、支出、对账 | `finance` | `OMS_TRUTH_SOURCE/finance.json`、`source_evidence_available_data.finance_data`、`financial_events`、`finance_schema` |
| 运营中心 | `operations` | 入住、房态、照护师、服务执行 | `room`, `stay`, `caregiver`, `task` | `OMS_TRUTH_SOURCE/room.json`、`resident_data`、`room_status_data`、`service_data`、`hr_execution_flow` |
| 数据追溯 | `data` | 来源文件、行号、处理链路 | `task`, `room`, `finance`, `sales` | `source_evidence`、`trace_chain`、`business_event_flow` |

## 三、二级菜单

### 1. 首页工作台

| 二级菜单 | 路由 | 展示内容 | 对应 Domain | 数据来源 |
|---|---|---|---|---|
| 今日工作 | `action` | 今日必须处理任务 | `task` | `sections.my_todos`、`sections.event_execution_flow` |
| 当前状态 | `status` | 房态、财务、销售、服务、人效状态 | `room`, `finance`, `sales`, `task` | `business_schema`、`master_control.global_view` |
| 风险异常 | `risk` | 未完成、延迟、财务异常、房态冲突 | `task`, `finance`, `room` | `master_control.global_view.risk_register`、`semantic_status` |

### 2. 销售中心

| 二级菜单 | 路由 | 展示内容 | 对应 Domain | 数据来源 |
|---|---|---|---|---|
| 签约客户 | `sales` | 客户、合同、签约记录 | `sales` | `sales_contract_data` |
| 销售跟进 | `sales` | 跟进任务、负责人、下一步动作 | `sales`, `task` | `business_event_flow`、`workflow_distribution` |
| 转化指标 | `sales` | 线索数、签约数、转化率 | `sales` | `sales_schema`、`Metrics` |

### 3. 财务中心

| 二级菜单 | 路由 | 展示内容 | 对应 Domain | 数据来源 |
|---|---|---|---|---|
| 收款记录 | `finance` | 收入、收款、到账记录 | `finance` | `finance_data`、`financial_events` |
| 待收待付 | `finance` | 应收、待收、待付款 | `finance` | `finance_schema`、`financial_events` |
| 对账追溯 | `finance` | 来源文件、行号、处理链 | `finance` | `source_evidence`、`trace_chain` |

### 4. 运营中心

| 二级菜单 | 路由 | 展示内容 | 对应 Domain | 数据来源 |
|---|---|---|---|---|
| 入住管理 | `operations` | 在住、入住、出馆 | `stay`, `room` | `resident_data`、`resident_flow_schema` |
| 房态管理 | `operations` | 房态记录、排房任务、房间状态 | `room` | `room_status_data`、`room_flow` |
| 照护师 | `operations` | 照护师状态、人效执行 | `caregiver`, `task` | `hr_schema`、`hr_execution_flow` |
| 服务执行 | `operations` | 管家、产护、服务事项 | `task` | `service_data`、`service_schema` |

### 5. 数据追溯

| 二级菜单 | 路由 | 展示内容 | 对应 Domain | 数据来源 |
|---|---|---|---|---|
| 来源追溯 | `data` | 文件、行号、来源类型 | `task` | `source_evidence` |
| 处理链路 | `data` | ingestion、business_event、workflow、hr_execution | `task` | `trace_chain` |
| 历史查询 | `data` | 按需历史回放 | `task` | `/api/oms/history` |

## 四、老板常用页面

| 页面 | 路由 | 必须显示 | 数据来源 |
|---|---|---|---|
| 首页工作台 | `home` | Action / Status / Risk | `/api/oms/home` |
| 销售中心 | `sales` | 销售指标、签约客户、销售任务 | `sales_schema`、`sales_contract_data` |
| 财务中心 | `finance` | 收入、待收、支出、财务事件 | `finance_schema`、`finance_data`、`financial_events` |
| 运营中心 | `operations` | 在住、房态、服务、人效 | `resident_flow_schema`、`room_status_data`、`service_data`、`hr_execution_flow` |

## 五、禁止项

- 禁止空页面
- 禁止只展示框架
- 禁止 mock 数据冒充真实数据
- 禁止前端自行创造经营事实
- 禁止绕过 `/api/oms/home` 与 `OMS_TRUTH_SOURCE`

## 六、验收标准

```text
Left Menu = 完整老板工作台菜单
Home = 今日经营入口
Sales Center = 可见真实销售数据
Finance Center = 可见真实财务数据
Operations Center = 可见真实入住 / 房态 / 照护师 / 服务数据
Data Source = OMS_TRUTH_SOURCE + /api/oms/home
AI Capability = unchanged
```
