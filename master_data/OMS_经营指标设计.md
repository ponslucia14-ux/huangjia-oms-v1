# OMS 经营指标设计

## 阶段边界

P18 Metrics & Dashboard Foundation 建立老板驾驶舱的数据基础。

本阶段只建立经营指标模型。

本阶段不是：

- UI
- 网页
- 图表
- 业务修改
- 外部 BI

## 指标链路

```text
Domain Data
-> MetricDefinition
-> MetricsEngine
-> MetricSnapshot
-> DashboardDataset
```

所有指标必须：

- 有定义
- 有计算方式
- 有来源 Domain
- 可生成 Snapshot
- 可追踪 Audit

## 指标模型

### MetricDefinition

字段：

- `metric_id`
- `name`
- `category`
- `source_domain`
- `calculation_method`
- `unit`
- `description`

### MetricSnapshot

字段：

- `snapshot_id`
- `metric_id`
- `name`
- `category`
- `source_domain`
- `calculation_method`
- `value`
- `unit`
- `generated_at`

### DashboardDataset

字段：

- `dataset_id`
- `snapshots`
- `source_summary`
- `audit_record`
- `mutates_business_state`
- `generated_at`

`DashboardDataset` 是数据集，不是 UI。

## 第一批指标

### 销售

#### 今日接待数

- 来源 Domain：Customer
- 计算方式：统计 `sales_records` 中 `event_type = reception`

#### 今日签约数

- 来源 Domain：Contract
- 计算方式：统计 `sales_records` 中 `event_type = contract_signed`

#### 成交金额

- 来源 Domain：Contract
- 计算方式：汇总已签约销售记录金额

#### 转化率

- 来源 Domain：Customer
- 计算方式：今日签约数 / 今日接待数

### 资金

#### 今日收款

- 来源 Domain：Payment
- 计算方式：汇总 `finance_records` 中 `type = received`

#### 待收金额

- 来源 Domain：Payment
- 计算方式：汇总 `finance_records` 中 `type = receivable`

#### 待付款金额

- 来源 Domain：Expense
- 计算方式：汇总 `finance_records` 中 `type = payable`

### 经营

#### 在住人数

- 来源 Domain：Stay
- 计算方式：统计 `stay_records` 中 `status = in_house`

#### 房间利用率

- 来源 Domain：Room
- 计算方式：OCCUPIED 房间数 / 非 DISABLED 房间数

#### 照护师状态数量

- 来源 Domain：Caregiver
- 计算方式：按 `caregiver_records.status` 分组计数

## Audit

每次生成 Dataset 必须写入：

- `metrics.snapshot`

Audit metadata 必须包含：

- metric_count
- source_summary
- mutates_business_state=false

## 边界

禁止：

- 修改业务数据
- 接 UI
- 生成图表
- 接外部 BI
- 写入生产业务状态

P18 仅输出可被未来驾驶舱使用的数据基础。
