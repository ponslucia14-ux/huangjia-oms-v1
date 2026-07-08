# OMS 通知集成设计

## 阶段边界

P16 Notification & Integration Foundation 建立 OMS 对外通知和集成基础层。

本阶段只建立 Notification Layer。

本阶段禁止：

- 直接接业务模块
- 直接修改业务状态
- 接 UI
- 接真实飞书 API
- 实现复杂机器人

第一阶段只支持：

- `internal_log`
- `feishu_mock`

`feishu_mock` 只记录模拟投递，不调用飞书真实接口。

## 通知链路

```text
事件产生
-> 通知路由
-> 发送目标
-> 投递状态记录
```

通知必须关联：

- `event_id`
- `correlation_id`
- `receiver_emp_id`

## 通知模型

### NotificationEvent

通知输入事件。

字段：

- `notification_event_id`
- `event_id`
- `event_type`
- `correlation_id`
- `receiver_emp_id`
- `reason`
- `payload`
- `source_module`
- `timestamp`

### NotificationMessage

通知路由后的消息对象。

字段：

- `message_id`
- `notification_event`
- `receiver_emp_id`
- `title`
- `body`
- `channel`
- `delivery_status`
- `event_id`
- `correlation_id`
- `timestamp`
- `metadata`

### NotificationChannel

通知通道抽象。

支持通道：

- `internal_log`
- `feishu_mock`

通道职责：

- 接收 NotificationMessage
- 生成 NotificationDelivery
- 记录 delivery_status

### NotificationRouter

通知路由器。

职责：

- 校验接收人 EMP
- 生成 NotificationMessage
- 路由到目标 channel
- 写 Audit
- 发布 Event
- 汇总 delivery_status

不得：

- 调用真实飞书 API
- 修改业务状态
- 触发业务模块执行

## 状态流转

支持状态：

- `PENDING`
- `SENT`
- `FAILED`
- `RETRY`

流转：

```text
PENDING -> SENT
PENDING -> FAILED
PENDING -> RETRY
```

说明：

- 全部通道成功：`SENT`
- 全部通道失败：`FAILED`
- 部分成功部分失败：`RETRY`

## Event

必须发布：

- `notification.requested`
- `notification.sent`
- `notification.failed`

Event 必须包含：

- `event_id`
- `correlation_id`
- `receiver_emp_id`
- `delivery_status`
- `mutates_business_state=false`

## Audit

必须写入：

- `notification.request`
- `notification.sent`
- `notification.fail`

Audit 必须记录：

- event_id
- correlation_id
- receiver_emp_id
- delivery_status
- channel
- reason
- mutates_business_state=false

## 集成边界

P16 只建立基础接口。

后续阶段可以在 NotificationChannel 下新增真实外部通道，但必须通过独立阶段验收。
