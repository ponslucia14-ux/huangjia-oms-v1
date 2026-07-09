# OMS 生产数据迁移报告

Generated At: 2026-07-09 23:35 (Asia/Shanghai)

## 一、迁移目标

P0.9 第一阶段目标：

```text
销售 Truth Source -> Sales Adapter -> Contract Domain -> 销售中心
财务 Truth Source -> Finance Adapter -> Payment Domain -> 财务中心
```

本阶段只迁移销售中心与财务中心页面数据口径，禁止使用：

- `legacy_runtime` 作为页面展示口径
- 临时快照
- mock 数据
- UI 自行拼接生产指标

## 二、原数据来源

| 页面 | 原数据来源 | 原问题 |
|---|---|---|
| 销售中心 | `source_evidence_available_data.sales_contract_data`，由 `sales.json.work_items` / event / workflow 混合补充 | `sales.json.work_items` 中无完整 source evidence，页面可能展示 legacy 任务而不是 Contract Domain |
| 财务中心 | `finance_data` + `financial_events` + event / workflow 混合补充 | 全量 `financial_events` 中存在大量无 source evidence 记录，页面口径会混入未校准历史数据 |

## 三、新 Truth Source

| Domain | Truth Source | 当前记录 | 可作为页面生产数据 | 排除记录 |
|---|---|---:|---:|---:|
| Sales | `OMS_TRUTH_SOURCE/sales.json` | `entities=1758` | `contract_records=500` | `unverified=1258` |
| Finance / Payment | `OMS_TRUTH_SOURCE/finance.json` | `financial_events=3170`, `settlement_records=3170` | `payment_records=500`, `financial_event_records=500` | `unverified_events=2670`, `unverified_settlements=2670` |

生产页面只展示满足以下条件的记录：

```text
source_file exists
row_id / row_number exists
record_id exists
adapter_id exists
mapping_version exists
```

## 四、Adapter

### 1. Sales Adapter

| 字段 | 值 |
|---|---|
| adapter_id | `sales_adapter_v1` |
| source_system | `OMS_TRUTH_SOURCE/sales.json` |
| target_domain | `Sales` |
| mapping_version | `p0.9.production_truth.v1` |
| 输入 | `sales.entities` |
| 输出 | `sales_contract_data` |

### 2. Finance Adapter

| 字段 | 值 |
|---|---|
| adapter_id | `finance_adapter_v1` |
| source_system | `OMS_TRUTH_SOURCE/finance.json` |
| target_domain | `Payment` / `Finance` |
| mapping_version | `p0.9.production_truth.v1` |
| 输入 | `settlement_records`, `financial_events` |
| 输出 | `finance_data`, `financial_events` |

## 五、Domain 映射

### 销售

```text
OMS_TRUTH_SOURCE/sales.json
  -> sales_adapter_v1
  -> Sales Contract Domain
  -> /api/oms/home.business_dashboard.source_evidence_available_data.sales_contract_data
  -> 销售中心
```

映射字段：

| 页面字段 | Domain 字段 | 来源 |
|---|---|---|
| 客户 | `customer_name` / `guest_name` | `Sales.entity.guest_name` |
| 合同 | `contract_id` | `Sales.entity.contract_id` |
| 金额 | `amount` | `Sales.entity.amount` |
| 阶段 | `stage` | `Sales.entity.stage` |
| 来源文件 | `source_file` | `source_evidence.source_file` |
| 来源行 | `row_id` | `source_evidence.row_number` |
| Adapter | `adapter_id` | `sales_adapter_v1` |
| 数据状态 | `data_status` | `verified` |

当前指标输出：

| 指标 | 值 |
|---|---:|
| 线索记录 | 500 |
| 签约/转化记录 | 494 |
| 转化率 | 98.8% |
| 成交金额 | 27,718,244.00 |

### 财务

```text
OMS_TRUTH_SOURCE/finance.json
  -> finance_adapter_v1
  -> Payment / Finance Domain
  -> /api/oms/home.business_dashboard.source_evidence_available_data.finance_data
  -> /api/oms/home.business_dashboard.source_evidence_available_data.financial_events
  -> 财务中心
```

映射字段：

| 页面字段 | Domain 字段 | 来源 |
|---|---|---|
| 交易 ID | `tx_id` | `settlement_id` / `financial_event_id` |
| 金额 | `income_amount` / `amount` | `financial_event` / `settlement_record` |
| 支出 | `expense_amount` | `financial_event` |
| 状态 | `payment_status` | `settlement.status` |
| 财务事件 | `financial_event_id` | `financial_event_id` |
| 来源文件 | `source_file` | `source_evidence.source_file` |
| 来源行 | `row_id` | `source_evidence.row_number` |
| Adapter | `adapter_id` | `finance_adapter_v1` |
| 数据状态 | `data_status` | `verified` |

当前指标输出：

| 指标 | 值 |
|---|---:|
| 可追溯支付记录 | 500 |
| 可追溯财务事件 | 500 |
| 收入 | 15,572,712.00 |
| 已收 / 实收 | 15,572,712.00 |
| 待收金额 | 15,572,712.00 |
| 支出 | 368.00 |
| 利润 | 15,572,344.00 |

## 六、页面字段映射

| 页面 | API 字段 | 数据来源 |
|---|---|---|
| 首页工作台 | `business_dashboard.metrics.sales_contracts` | Sales Adapter |
| 首页工作台 | `business_dashboard.metrics.finance_records` | Finance Adapter |
| 销售中心 | `business_schema.sales_schema` | Sales Adapter metrics |
| 销售中心 | `source_evidence_available_data.sales_contract_data` | Sales Adapter records |
| 财务中心 | `business_schema.finance_schema` | Finance Adapter metrics |
| 财务中心 | `source_evidence_available_data.finance_data` | Payment records |
| 财务中心 | `source_evidence_available_data.financial_events` | Finance event records |
| 数据追溯 | `trace_chain` / `source_evidence` | Adapter records |

## 七、差异

| 项目 | 迁移前 | 迁移后 |
|---|---|---|
| 销售中心记录口径 | work_items / event / workflow 混合 | `sales.entities` 中带来源证据的 Contract Domain |
| 财务中心记录口径 | work_items / all financial_events 混合 | `settlement_records` + `financial_events` 中带来源证据的 Payment/Finance Domain |
| 无来源记录 | 可进入页面 | 不进入销售/财务页面生产口径 |
| 页面指标 | 可能由 UI 混合数据推导 | 后端 Adapter 统一输出 |
| 追溯字段 | 不稳定 | `source_file + row_id + adapter_id + mapping_version` 固定 |

## 八、当前验收结果

| 验收项 | 结果 |
|---|---|
| 销售中心数据可信 | PASS |
| 财务中心数据可信 | PASS |
| legacy_runtime 直出页面 | 已阻断 |
| Mock 数据冒充真实数据 | 未发现 |
| UI 自行拼生产数据 | 已收敛到 `/api/oms/home` Adapter 输出 |

## 九、保留风险

| 风险 | 等级 | 说明 |
|---|---|---|
| 财务日报截图数据未结构化入 Finance Truth Source | 中 | 当前财务中心只展示已具备 source evidence 的 Payment/Finance 记录；截图/OCR 不进入生产页面口径 |
| `sales.json` / `finance.json` 顶层仍保留 `migration_source=legacy_runtime` 审计字段 | 中 | 该字段仅作迁移审计，不作为页面数据来源 |
| Stay / Room / Caregiver 尚未进入 P0.9 第一阶段迁移 | 中 | 本阶段只完成 Sales / Finance |

## 十、结论

```text
P0.9 第一阶段 = PASS
Sales Center = Truth Source Adapter Driven
Finance Center = Truth Source Adapter Driven
页面生产口径 = 不再使用 legacy_runtime / mock / 临时快照
```

## 十一、飞书端 OMS 内测结果

### 1. 测试环境

| 项目 | 状态 |
|---|---|
| 飞书客户端 | 已运行 |
| 客户端路径 | `D:\Feishu\app.20260709-131213-663Z\Feishu.exe` |
| OMS API | `http://127.0.0.1:8787` |
| OMS 页面标题 | `OMS 每日工作台` |
| 当前身份 | `主理办（你）` |
| 当前入口 | 飞书客户端内 OMS 页面 |

### 2. API 实测结果

`/api/oms/home?user_id=a2c82cb4` 返回：

| 字段 | 结果 |
|---|---:|
| status | `ready` |
| entry | `master_control_dashboard` |
| sales_contract_data | 500 |
| finance_data | 500 |
| financial_events | 500 |
| sales_amount | 27,718,244.00 |
| finance_income | 15,572,712.00 |
| finance_collected | 15,572,712.00 |
| sales_adapter | `sales_adapter_v1` |
| finance_adapter | `finance_adapter_v1` |

### 3. 浏览器 / GitHub 入口复测

| 页面 | 结果 |
|---|---|
| 首页工作台 | PASS |
| 销售中心 | PASS |
| 财务中心 | PASS |
| 销售记录来源 | `2026年销售明细表（经验为王7.4）.xlsx`，可见 `source_file` / `row_id` |
| 财务记录来源 | `2026年销售明细表（经验为王7.4）.xlsx`，可见 `source_file` / `row_id` |
| 旧销售未校验记录 | 未在销售中心出现 |
| 旧财务未校验记录 | 未在财务中心出现 |

复测时发现：

```text
首次浏览器页面仍显示旧销售/财务数据。
根因：本机 OMS API 进程未重启，仍加载旧代码。
处理：重启 8787 API 后，销售/财务中心切换为 P0.9 Adapter 数据。
```

### 4. 飞书客户端实机结果

| 验收项 | 结果 |
|---|---|
| 飞书客户端打开 OMS | PASS |
| 首页工作台可见 | PASS |
| Owner 身份显示 | PASS |
| Action / Status / Risk 首屏可见 | PASS |
| 销售卡片可见 | PASS |
| 财务卡片可见 | PASS |
| 点击销售卡片进入销售中心详情 | FAIL |
| 点击后显示 P0.9 销售详情 | 未完成 |
| 飞书客户端内财务中心详情验证 | 未完成 |

实际现象：

```text
飞书客户端内 OMS 首页可以进入。
点击首页销售卡片的“查看”按钮后，按钮有响应状态，但页面未进入销售中心详情。
向下滚动后仍停留在首页 Action / Risk 工作卡片区域。
```

### 5. 新增问题

| Issue | 等级 | 状态 | 说明 |
|---|---|---|---|
| P0.9-FEISHU-001 | 中 | OPEN | 飞书客户端首页可见，但销售/财务详情入口未成功下钻；浏览器入口详情页正常 |
| P0.9-RUNTIME-001 | 中 | 已处理 | API 未重启会导致页面继续显示旧数据；重启 8787 后恢复 |

### 6. 合并结论

```text
P0.9 Data Adapter Migration = PASS
Backend / API = PASS
Browser Sales Center = PASS
Browser Finance Center = PASS
Feishu Client Home = PASS
Feishu Client Sales / Finance Detail Navigation = FAIL / OPEN ISSUE
```

当前判断：

```text
销售/财务数据迁移本身通过。
飞书端 OMS 能打开首页，但还不能证明老板在飞书客户端内可稳定进入销售/财务详情页。
P0.9 可进入验收候选，但需保留 P0.9-FEISHU-001。
```

## 十二、P0.9-FEISHU-001 修复复测记录

### 1. 修复范围

| 项目 | 处理 |
|---|---|
| 飞书 WebView hash route | 已改为设置 hash 后立即执行 `handleWorkRouteChange()` |
| 首页销售/财务卡片 | 已增加显式 `data-work-route` |
| 销售详情可见记录 | 本地前端已调整为 500 条 |
| 财务详情可见记录 | 本地前端已调整为 500 条 |
| API source evidence 输出 | 已调整为 500 条可见上限 |
| 数据链 | 未修改 Adapter / Domain / Metrics 链路 |

### 2. 本机 API 复测

`/api/oms/home?user_id=a2c82cb4` 当前返回：

| 字段 | 结果 |
|---|---:|
| status | `ready` |
| entry | `master_control_dashboard` |
| sales_contract_data | 500 |
| finance_data | 500 |
| financial_events | 500 |
| source_visible_limit | 500 |
| source_payload_limit | 500 |

### 3. 本机浏览器复测

| 链路 | 结果 |
|---|---|
| 首页 → 点击销售 → 销售中心 | PASS |
| 销售中心真实记录数 | 500 |
| 首页 → 点击财务 → 财务中心 | PASS |
| 财务中心真实记录数 | 500 |
| 销售来源显示 | `2026年销售明细表（经验为王7.4）.xlsx / 第 2 行` |
| 财务来源显示 | `2026年销售明细表（经验为王7.4）.xlsx / 第 2 行` |

### 4. 飞书客户端实机复测

| 链路 | 结果 |
|---|---|
| 飞书客户端首页 | PASS |
| 首页 → 点击销售 | PASS（可进入销售中心） |
| 销售详情记录数 | FAIL：仍显示 12 条 |
| 首页 → 点击财务 | 未关闭：需生产静态入口更新后复测 |

实际定位：

```text
飞书客户端当前加载的是 GitHub Pages 旧静态入口。
远端 index.html 仍引用：
app.js?v=p05-owner-workbench-v3-20260709-55ddc9e

远端 app.js 不包含：
- routeForWorkTrigger
- data-work-route
- records.slice(0, 500)
```

### 5. 当前状态

| Issue | 状态 | 说明 |
|---|---|---|
| P0.9-FEISHU-001 | FIXED LOCALLY / PENDING DEPLOY | 本地代码和本机浏览器已通过；飞书生产入口仍使用 GitHub Pages 旧静态文件 |

### 6. 当前结论

```text
P0.9 数据链 = PASS
本机 API = PASS
本机浏览器销售/财务详情 = PASS
飞书客户端首页 = PASS
飞书客户端生产详情 = PENDING DEPLOY

阻塞点不是数据链，也不是本机前端路由。
唯一剩余阻塞点：GitHub Pages / 飞书入口静态前端未发布到最新版本。
```
