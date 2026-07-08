# OMS 事件总线设计

## 目标

OMS Event Bus 是全系统统一事件中心。

本阶段只建立事件框架，不接入销售、财务、审批等业务模块。

## 组成

OMSEvent

统一事件定义，描述系统内发生了什么。

Event Registry

统一登记事件类型和订阅者。

Event Publisher

统一发布入口。

Event Subscriber

统一订阅者定义，记录监听模块、监听事件类型和处理函数。

Event Bus

负责接收事件、找到订阅者、分发事件、记录分发结果。

## 事件字段

| 字段 | 说明 |
|------|------|
| event_id | 事件唯一 ID |
| schema_version | 事件 schema 版本 |
| timestamp | 事件发生时间 |
| event_type | 事件类型 |
| source_module | 事件来源模块 |
| subject | 事件主题 |
| action | 事件动作 |
| emp_id | 相关操作人 EMP |
| actor_name | 相关操作人正式姓名 |
| correlation_id | 关联链路 ID |
| payload | 事件载荷 |
| metadata | 扩展元数据 |

## 发布与订阅

发布流程：

1. 模块创建 OMSEvent。
2. Event Publisher 发布事件。
3. Event Bus 查询 Event Registry。
4. Event Bus 将事件分发给所有匹配订阅者。
5. Event Bus 返回 dispatch 结果。

订阅方式：

- 按指定 event_type 订阅。
- 使用 `*` 订阅全部事件。

## 示例事件

```json
{
  "event_type": "oms.bootstrap.ready",
  "source_module": "bootstrap",
  "subject": "startup",
  "action": "ready",
  "emp_id": "EMP001",
  "actor_name": "石磊",
  "payload": {
    "ready": true
  }
}
```

## 与 Audit Log 的关系

Audit Log 后续可以作为 Event Subscriber 监听事件。

例如：

- 监听 `*`
- 将收到的事件转换为 Audit Event
- 写入 append-only Audit Log

本阶段只证明 Audit Log 可以监听事件，不正式接入业务事件。

## 当前边界

本阶段不接入：

- 销售模块
- 财务模块
- 审批流
- 飞书同步
- 业务执行动作

Event Bus 当前为进程内同步分发框架。

后续如需要跨进程、持久化、重试、死信队列，应在不改变 OMSEvent 和 Event Registry 基础契约的前提下扩展。
