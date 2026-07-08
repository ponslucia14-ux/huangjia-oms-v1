# OMS 驾驶舱查询设计

## 阶段边界

P19 Dashboard Query Layer 建立经营驾驶舱查询基础。

本阶段只做查询层，不做：

- UI
- 网页
- 图表
- 前端
- 外部 BI
- 业务数据修改
- 业务动作生成

## 查询链路

```text
DashboardDataset
-> DashboardQuery
-> DashboardFilter
-> DashboardQueryEngine
-> DashboardView
```

查询层只读取 P18 生成的指标快照，不重新计算业务，不写业务状态。

## 查询模型

### DashboardFilter

字段：

- `time_scope`
- `dashboard_category`
- `metric_ids`
- `source_domains`

`time_scope` 支持：

- `today`
- `week`
- `month`

业务口径：

- 今日
- 本周
- 本月

`dashboard_category` 支持：

- `sales_dashboard`：销售驾驶舱
- `funds_dashboard`：资金驾驶舱
- `operations_dashboard`：经营驾驶舱

### DashboardQuery

字段：

- `query_id`
- `actor_emp_id`
- `reason`
- `dataset`
- `filter`
- `correlation_id`
- `requested_at`

要求：

- `actor_emp_id` 必填
- `reason` 必填
- `dataset` 必填
- 查询必须只读

### DashboardView

返回字段：

- `view_id`
- `query`
- `dashboard_category`
- `dashboard_label`
- `time_scope`
- `metric_count`
- `metrics`
- `generated_time`
- `source_domains`
- `data_status`
- `audit_record`
- `event`
- `mutates_business_state`

`metrics` 中每个指标包含：

- `metric_id`
- `name`
- `category`
- `source_domain`
- `calculation_method`
- `value`
- `unit`
- `generated_time`
- `data_status`

`data_status`：

- `READY`：查询到指标
- `EMPTY`：没有符合条件的指标

## 驾驶舱分类

### 销售驾驶舱

来源指标类别：

- `sales`

返回第一批指标：

- 今日接待数
- 今日签约数
- 成交金额
- 转化率

### 资金驾驶舱

来源指标类别：

- `funds`

返回第一批指标：

- 今日收款
- 待收金额
- 待付款金额

### 经营驾驶舱

来源指标类别：

- `operations`

返回第一批指标：

- 在住人数
- 房间利用率
- 照护师状态数量

## 权限控制

查询前必须基于组织主数据校验 `actor_emp_id`。

权限规则：

- 销售驾驶舱：`ROLE_OWNER`、`ROLE_STORE_MANAGER`、`ROLE_SALES`
- 资金驾驶舱：`ROLE_OWNER`、`ROLE_ACCOUNTANT`、`ROLE_CASHIER`
- 经营驾驶舱：`ROLE_OWNER`、`ROLE_STORE_MANAGER`、`ROLE_BUTLER`、`ROLE_NURSING_DIRECTOR`、`ROLE_HR`

未授权角色不能读取对应驾驶舱。

## Audit

每次成功查询必须写入：

- `dashboard.query`

Audit metadata 必须包含：

- `query_id`
- `dataset_id`
- `time_scope`
- `dashboard_category`
- `dashboard_label`
- `metric_count`
- `source_domains`
- `data_status`
- `mutates_business_state=false`

## Event

每次成功查询必须发布：

- `dashboard.query.executed`

Event payload 必须包含：

- `query_id`
- `dataset_id`
- `time_scope`
- `dashboard_category`
- `dashboard_label`
- `metric_count`
- `source_domains`
- `data_status`
- `mutates_business_state=false`

## 只读约束

Dashboard Query Layer 禁止：

- 修改业务数据
- 写 Room
- 写 Stay
- 写 Caregiver
- 写 Finance
- 写 Sales
- 生成业务动作
- 接 UI
- 接图表
- 接外部 BI

P19 只输出可被未来驾驶舱使用的标准查询结果。
