# OMS 异常预警设计

## 阶段边界

P20 Alert & Exception Engine 建立 OMS 主动发现问题的能力。

本阶段负责：

- 发现异常
- 判断异常
- 生成异常结果
- 写 Audit
- 发布 Event
- 输出可被 Notification Layer 消费的事件

本阶段不做：

- 通知发送
- 自动修改业务状态
- 自动执行动作
- UI
- BI

## 异常链路

```text
AlertContext
-> AlertDefinition
-> ExceptionEngine
-> AlertResult
-> Audit
-> Event
```

异常引擎只读输入上下文，不修改业务对象。

## AlertDefinition

字段：

- `alert_code`
- `name`
- `domain`
- `severity`
- `description`
- `evaluator`

`evaluator` 只判断是否触发异常，不写业务数据。

## AlertContext

字段：

- `actor_emp_id`
- `reason`
- `room_records`
- `stay_records`
- `finance_records`
- `approval_records`
- `health_items`
- `thresholds`
- `correlation_id`

上下文是一次异常评估的只读快照。

## AlertResult

字段：

- `alert_id`
- `alert_code`
- `name`
- `domain`
- `severity`
- `status`
- `reason`
- `evidence`
- `receiver_emp_ids`
- `source_context`
- `created_at`
- `acknowledged_at`
- `resolved_at`
- `ignored_at`
- `audit_records`
- `events`
- `mutates_business_state`

状态：

- `OPEN`
- `ACKNOWLEDGED`
- `RESOLVED`
- `IGNORED`

## 第一批异常规则

### 经营

#### 房间资源不足

触发条件：

- 可用房间数低于 `required_available_rooms`

输出：

- domain: `operations`
- severity: `high`

#### 入住冲突

触发条件：

- 同一房间存在多个进行中的入住记录

输出：

- domain: `operations`
- severity: `critical`

### 财务

#### 待收异常

触发条件：

- 待收金额大于等于 `receivable_threshold`

输出：

- domain: `finance`
- severity: `high`

#### 待付款异常

触发条件：

- 待付款金额大于等于 `payable_threshold`

输出：

- domain: `finance`
- severity: `medium`

### 审批

#### 审批超时

触发条件：

- 审批状态为 `PENDING`
- `age_hours` 大于等于 `approval_timeout_hours`

输出：

- domain: `approval`
- severity: `high`

### 系统

#### Health Check Warning

触发条件：

- Health Check item 状态为 `warning` 或 `fail`

输出：

- domain: `system`
- severity: `warning`

## Event

异常生命周期必须发布：

- `alert.created`
- `alert.acknowledged`
- `alert.resolved`

Event payload 必须包含：

- `alert_id`
- `alert_code`
- `domain`
- `severity`
- `status`
- `reason`
- `receiver_emp_ids`
- `notification_consumable=true`
- `mutates_business_state=false`

Notification Layer 可以通过 Event payload 构造 NotificationEvent。

## Audit

异常生命周期必须写入：

- `alert.create`
- `alert.acknowledge`
- `alert.resolve`
- `alert.ignore`

Audit metadata 必须包含：

- `alert_id`
- `alert_code`
- `domain`
- `severity`
- `status`
- `receiver_emp_ids`
- `mutates_business_state=false`

## 状态流转

```text
OPEN -> ACKNOWLEDGED
OPEN -> RESOLVED
ACKNOWLEDGED -> RESOLVED
OPEN -> IGNORED
ACKNOWLEDGED -> IGNORED
```

禁止：

- `RESOLVED` 后再次变更状态
- `IGNORED` 后再次变更状态
- 未知 alert_id 状态变更

## 边界

Exception Engine 禁止：

- 自动修改业务状态
- 自动执行动作
- 调用 NotificationRouter
- 调用外部 API
- 接 UI
- 接 BI

P20 只负责异常发现与异常事件生成。
