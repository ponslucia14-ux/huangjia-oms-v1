# OMS V1.0 生产事实源设计

Generated At: 2026-07-09 23:35 (Asia/Shanghai)

## 一、Truth Source 定义

OMS V1.0 唯一事实源为：

```text
OMS_TRUTH_SOURCE
```

所有生产页面必须只读取：

```text
Truth Source
→ Adapter
→ Domain
→ API Contract
→ UI
```

禁止绕过 Domain 和 API Contract 直接展示原始表格、legacy runtime、截图、临时快照或 mock 数据。

### 1. 销售事实源

| 项目 | 定义 |
|---|---|
| truth_source_key | `sales_truth_source` |
| domain | `Sales` |
| 目标文件 | `OMS_TRUTH_SOURCE/sales.json` |
| 原始来源 | 销售明细表、签约客户表、合同记录 |
| 业务含义 | 线索、签约、客户、成交金额、转化阶段 |
| 页面使用 | 首页工作台、销售中心、数据追溯 |

### 2. 财务事实源

| 项目 | 定义 |
|---|---|
| truth_source_key | `finance_truth_source` |
| domain | `Finance` / `Payment` / `Settlement` |
| 目标文件 | `OMS_TRUTH_SOURCE/finance.json` |
| 原始来源 | 财务日报、银行流水、收款记录、待收待付表 |
| 业务含义 | 收款、应收、应付、支出、余额、对账状态 |
| 页面使用 | 首页工作台、财务中心、数据追溯 |

### 3. Stay 事实源

| 项目 | 定义 |
|---|---|
| truth_source_key | `stay_truth_source` |
| domain | `Stay` |
| 目标文件 | `OMS_TRUTH_SOURCE/stay.json` 或 `OMS_TRUTH_SOURCE/room.json.stays` |
| 原始来源 | 入住登记表、在住表、实际入住记录 |
| 业务含义 | 客户入住周期、入住日期、出馆日期、当前在住状态 |
| 页面使用 | 首页工作台、运营中心、数据追溯 |

### 4. Room 事实源

| 项目 | 定义 |
|---|---|
| truth_source_key | `room_truth_source` |
| domain | `Room` |
| 目标文件 | `OMS_TRUTH_SOURCE/room.json` |
| 原始来源 | 房态表、排房记录、实际房间状态 |
| 业务含义 | 房间资源、房态、可用/占用/清洁/维修/停用 |
| 页面使用 | 首页工作台、运营中心、数据追溯 |

### 5. Caregiver 事实源

| 项目 | 定义 |
|---|---|
| truth_source_key | `caregiver_truth_source` |
| domain | `Caregiver` |
| 目标文件 | `OMS_TRUTH_SOURCE/caregiver.json` 或 `OMS_TRUTH_SOURCE/room.json.caregivers` |
| 原始来源 | 照护师排班、照护师分配记录、实际在岗记录 |
| 业务含义 | 照护师状态、分配关系、在岗/空闲/服务中 |
| 页面使用 | 首页工作台、运营中心、数据追溯 |

## 二、每个事实源字段定义

每个事实源必须在 manifest 中登记以下字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `source_file` | string | 是 | 原始业务文件或系统来源路径 |
| `source_version` | string | 是 | 原始来源版本，例如文件日期、系统版本、导入批次 |
| `owner` | string | 是 | 业务负责人或数据 owner |
| `update_frequency` | string | 是 | 更新频率：daily / hourly / realtime / manual |
| `adapter` | string | 是 | 使用的 Adapter ID |
| `domain` | string | 是 | 进入的 OMS Domain |

### 1. 销售事实源字段

```json
{
  "source_file": "销售明细表 / 签约客户表",
  "source_version": "YYYY-MM-DD 或业务批次号",
  "owner": "销售负责人",
  "update_frequency": "daily",
  "adapter": "sales_adapter_v1",
  "domain": "Sales"
}
```

销售 Domain 最低字段：

| 字段 | 说明 |
|---|---|
| `contract_id` | 合同或签约记录 ID |
| `customer_name` | 客户姓名 |
| `contract_date` | 签约日期 |
| `expected_checkin_date` | 预产期/预计入住 |
| `package_name` | 套餐 |
| `amount` | 成交金额 |
| `salesperson_id` | 销售负责人 |
| `stage` | 线索 / 跟进 / 签约 / 转化 / 流失 |
| `source_file` | 来源文件 |
| `row_id` | 来源行 |

### 2. 财务事实源字段

```json
{
  "source_file": "财务日报 / 银行流水 / 收款记录",
  "source_version": "YYYY-MM-DD 或对账批次号",
  "owner": "财务负责人",
  "update_frequency": "daily",
  "adapter": "finance_adapter_v1",
  "domain": "Finance"
}
```

财务 Domain 最低字段：

| 字段 | 说明 |
|---|---|
| `tx_id` | 财务流水 ID |
| `tx_date` | 发生日期 |
| `type` | 收入 / 支出 / 应收 / 应付 |
| `amount` | 金额 |
| `counterparty` | 客户/供应商/员工 |
| `related_customer` | 关联客户 |
| `related_room` | 关联房间 |
| `payment_status` | 已收 / 待收 / 待付 / 已付 / 已对账 |
| `source_file` | 来源文件 |
| `row_id` | 来源行 |

### 3. Stay 事实源字段

```json
{
  "source_file": "入住登记表 / 在住表",
  "source_version": "YYYY-MM-DD 或入住批次号",
  "owner": "运营负责人",
  "update_frequency": "daily",
  "adapter": "stay_adapter_v1",
  "domain": "Stay"
}
```

Stay Domain 最低字段：

| 字段 | 说明 |
|---|---|
| `stay_id` | 入住记录 ID |
| `guest_name` | 客户姓名 |
| `room_id` | 房间号 |
| `checkin_date` | 入住日期 |
| `checkout_date` | 出馆日期 |
| `stay_status` | 即将入住 / 在住 / 出馆 / 已完成 |
| `butler_id` | 管家 |
| `caregiver_id` | 照护师 |
| `package_name` | 套餐 |
| `source_file` | 来源文件 |
| `row_id` | 来源行 |

### 4. Room 事实源字段

```json
{
  "source_file": "房态表 / 排房记录",
  "source_version": "YYYY-MM-DD 或房态批次号",
  "owner": "房态负责人",
  "update_frequency": "daily",
  "adapter": "room_adapter_v1",
  "domain": "Room"
}
```

Room Domain 最低字段：

| 字段 | 说明 |
|---|---|
| `room_id` | 房间号 |
| `room_type` | 房型 |
| `status` | AVAILABLE / RESERVED / OCCUPIED / CLEANING / MAINTENANCE / DISABLED |
| `guest_id` | 当前入住客户 |
| `stay_id` | 关联入住记录 |
| `checkin_date` | 入住日期 |
| `checkout_date` | 出馆日期 |
| `assigned_staff` | 管家/照护师 |
| `source_file` | 来源文件 |
| `row_id` | 来源行 |

### 5. Caregiver 事实源字段

```json
{
  "source_file": "照护师排班 / 分配记录",
  "source_version": "YYYY-MM-DD 或排班批次号",
  "owner": "照护负责人",
  "update_frequency": "daily",
  "adapter": "caregiver_adapter_v1",
  "domain": "Caregiver"
}
```

Caregiver Domain 最低字段：

| 字段 | 说明 |
|---|---|
| `caregiver_id` | 照护师 ID |
| `name` | 照护师姓名 |
| `status` | ON_DUTY / OFF_DUTY / ASSIGNED / RESTING / DISABLED |
| `assigned_stay_id` | 当前服务入住记录 |
| `assigned_room_id` | 当前服务房间 |
| `shift_date` | 班次日期 |
| `shift_type` | 白班 / 夜班 / 全天 |
| `source_file` | 来源文件 |
| `row_id` | 来源行 |

## 三、Domain 映射

### 1. 总映射链路

```text
Truth Source
↓
Adapter
↓
Domain
↓
Metrics / Dashboard / API Contract
↓
页面
```

### 2. 映射表

| Truth Source | Adapter | Domain | 输出文件 | 页面 |
|---|---|---|---|---|
| 销售明细 / 签约表 | `sales_adapter_v1` | `Sales` | `sales.json` | 销售中心 |
| 财务日报 / 银行流水 | `finance_adapter_v1` | `Finance` / `Payment` | `finance.json` | 财务中心 |
| 入住登记 / 在住表 | `stay_adapter_v1` | `Stay` | `stay.json` 或 `room.json.stays` | 运营中心 |
| 房态表 / 排房记录 | `room_adapter_v1` | `Room` | `room.json` | 运营中心 |
| 照护师排班 / 分配 | `caregiver_adapter_v1` | `Caregiver` | `caregiver.json` 或 `room.json.caregivers` | 运营中心 |

### 3. 映射要求

每条 Domain 记录必须保留：

```text
source_file
source_version
row_id
adapter_id
mapping_version
domain_id
created_at
```

不能只有汇总数字。

不能只有业务事件。

不能只有执行任务。

## 四、API Contract

### 1. 首页工作台需要字段

API:

```text
/api/oms/home
```

首页必须返回：

| 字段 | 来源 Domain | 说明 |
|---|---|---|
| `today_actions` | Task / Alert / Workflow | 今天要处理的 3-7 件事 |
| `current_resident_count` | Stay | 当前在住人数 |
| `available_room_count` | Room | 当前可用房 |
| `occupied_room_count` | Room | 当前在住房 |
| `today_income` | Finance / Payment | 今日收款 |
| `receivable_amount` | Finance / Payment | 待收金额 |
| `pending_payment_amount` | Finance / Payment | 待付金额 |
| `new_contract_count` | Sales | 新签约数 |
| `sales_amount` | Sales | 成交金额 |
| `caregiver_on_duty_count` | Caregiver | 在岗照护师 |
| `risk_items` | Alert | 风险/异常 |

### 2. 销售中心需要字段

API Contract payload:

| 字段 | 说明 |
|---|---|
| `contracts` | 签约列表 |
| `leads` | 线索列表 |
| `conversion_rate` | 转化率 |
| `sales_amount` | 成交金额 |
| `stage_summary` | 各阶段数量 |
| `records[].source_file` | 来源文件 |
| `records[].row_id` | 来源行 |
| `records[].adapter_id` | Adapter |
| `records[].data_status` | verified / warning / rejected |

### 3. 财务中心需要字段

API Contract payload:

| 字段 | 说明 |
|---|---|
| `today_income` | 今日收款 |
| `receivable_amount` | 待收金额 |
| `pending_payment_amount` | 待付金额 |
| `expense_amount` | 支出金额 |
| `balance` | 余额 |
| `transactions` | 财务流水 |
| `transactions[].payment_status` | 收款/对账状态 |
| `transactions[].source_file` | 来源文件 |
| `transactions[].row_id` | 来源行 |

### 4. 运营中心需要字段

运营中心必须由 Stay / Room / Caregiver 三个 Domain 驱动。

#### Stay payload

| 字段 | 说明 |
|---|---|
| `active_stays` | 当前在住列表 |
| `today_checkins` | 今日入住 |
| `today_checkouts` | 今日出馆 |
| `upcoming_checkins` | 即将入住 |
| `stay_records[].room_id` | 房间 |
| `stay_records[].caregiver_id` | 照护师 |
| `stay_records[].source_file` | 来源 |

#### Room payload

| 字段 | 说明 |
|---|---|
| `rooms` | 房间列表 |
| `room_status_summary` | 房态统计 |
| `available_count` | 可用房 |
| `occupied_count` | 占用房 |
| `cleaning_count` | 清洁中 |
| `maintenance_count` | 维修 |
| `disabled_count` | 停用 |

#### Caregiver payload

| 字段 | 说明 |
|---|---|
| `caregivers` | 照护师列表 |
| `on_duty_count` | 在岗人数 |
| `assigned_count` | 已分配 |
| `available_count` | 可分配 |
| `caregivers[].assigned_stay_id` | 当前服务对象 |
| `caregivers[].source_file` | 来源 |

## 五、禁止

### 1. 禁止 legacy_runtime

禁止生产页面直接展示：

```text
migration_source = legacy_runtime
```

legacy_runtime 只能作为迁移输入，不得作为 V1.0 生产事实。

### 2. 禁止 mock 数据

禁止：

- mock 记录；
- demo state；
- fallback data；
- UI 生成的假指标；
- 空数据自动补正常。

### 3. 禁止临时快照冒充生产数据

禁止将以下内容作为生产事实：

- 截图；
- OCR 结果；
- 临时 JSON；
- 浏览器缓存；
- old runtime snapshot；
- event_flow 汇总数字。

### 4. 禁止事件流替代 Domain

以下只能用于追溯，不得替代业务事实：

- `business_event_flow`;
- `workflow_distribution`;
- `hr_execution_flow`;
- `events.jsonl`;
- execution log。

运营中心必须直接来自：

```text
Stay + Room + Caregiver
```

## 六、V1.0 事实源冻结验收标准

| 验收项 | 标准 |
|---|---|
| 唯一事实源 | 所有页面只读 `OMS_TRUTH_SOURCE` |
| 销售 | 不再显示 legacy_runtime，记录可追溯到 source_file/row_id |
| 财务 | 金额口径统一，待收/待付/收款来自 Finance/Payment |
| Stay | active_stays 不为 0，且有来源 |
| Room | room entities 不为 0，且有状态 |
| Caregiver | caregiver entities 不为 0，且有状态/分配 |
| API Contract | 首页/销售/财务/运营字段固定 |
| 禁止项 | 无 mock、无 legacy_runtime 直出、无临时快照冒充 |

## 七、当前结论

```text
P0.8 目标 = 冻结 V1.0 唯一生产事实源定义
当前动作 = 仅设计
代码修改 = 无
下一步 = 按本设计进入代码修复
```
