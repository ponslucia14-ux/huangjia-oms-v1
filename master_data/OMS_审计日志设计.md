# OMS 审计日志设计

## 目标

OMS Audit Log 是全系统唯一审计日志框架。

OMS 不允许无痕修改。所有关键动作未来必须写入 Audit Log。

本阶段只建立基础框架，不接入业务模块。

## 组成

Audit Event

定义单条审计事件，记录谁、在什么模块、对什么对象、做了什么、结果是什么。

Audit Storage

负责 append-only JSONL 存储。只允许追加，不允许覆盖、删除、清空。

Audit Writer

统一写入入口。业务模块未来只能通过 Writer 写审计事件。

Audit Reader

统一读取和查询入口。支持按时间排序、按 EMP 查询、按模块查询、按动作查询。

Audit Engine

统一门面，组合 Writer、Reader、Storage，作为后续系统接入点。

## 字段

| 字段 | 说明 |
|------|------|
| audit_id | 审计事件唯一 ID |
| schema_version | 审计事件 schema 版本 |
| timestamp | 事件发生时间 |
| emp_id | 操作人 EMP 编号 |
| actor_name | 操作人正式姓名 |
| module | OMS 模块 |
| action | 动作名称 |
| reason | 本次动作原因 |
| action_type | 动作类型 |
| target_type | 被操作对象类型 |
| target_id | 被操作对象 ID |
| result | 动作结果 |
| severity | 级别 |
| source | 来源 |
| correlation_id | 关联链路 ID |
| request_id | 请求 ID |
| before_hash | 变更前摘要 |
| after_hash | 变更后摘要 |
| metadata | 扩展元数据 |

## Reason 规则

reason 是审计事件必填字段。

关键修改类动作 reason 不允许为空。

关键修改类动作包括但不限于：

- create
- update
- modify
- delete
- write
- approve
- reject
- confirm
- assign
- sync
- import
- export
- close
- open

只读查询类动作也应记录 reason，用于说明查询目的。

## 存储方式

默认路径：

```text
live_runtime/audit_center/audit_events.jsonl
```

存储格式：

```text
一行一个 JSON 对象
只追加
不覆盖
不删除
不清空
```

## 查询能力

Audit Reader 支持：

- 查询全部事件
- 按时间排序
- 按 EMP 查询
- 按模块查询
- 按动作查询

## 当前边界

本阶段只建立审计日志中心基础能力。

暂不接入：

- 销售模块
- 财务模块
- 房态模块
- 服务模块
- 飞书同步
- 审批流

后续接入业务模块时，所有关键写入必须先生成 Audit Event，再执行实际业务动作。
