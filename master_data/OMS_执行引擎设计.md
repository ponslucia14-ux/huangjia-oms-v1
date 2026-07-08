# OMS 执行引擎设计

## 阶段边界

P15 Execution Engine 建立在 P13 调度决策和 P14 调度审批之后。

本阶段只建立授权后的执行框架。

本阶段不是：

- 自动排房
- 自动分配照护师
- 修改真实业务状态
- UI
- 数据库

第一阶段只支持模拟执行。

## 执行链路

```text
Decision Result
-> Approval Workflow
-> Execution Request
-> Execution Command
-> Execution Result
```

执行必须同时满足：

1. Decision Result 存在。
2. Approval Status = APPROVED。
3. `execution_authorized = true`。

任何条件不满足，执行结果必须为 failed，并记录失败原因。

## 执行模型

### ExecutionRequest

字段：

- `request_id`
- `decision_result`
- `approval_workflow`
- `requester_emp_id`
- `reason`
- `command_type`
- `correlation_id`
- `timestamp`
- `metadata`

### ExecutionCommand

字段：

- `command_id`
- `request_id`
- `decision_id`
- `approval_id`
- `command_type`
- `target_type`
- `payload`
- `simulation_only`
- `mutates_business_state`
- `timestamp`

约束：

- `simulation_only = true`
- `mutates_business_state = false`

### ExecutionResult

字段：

- `result_id`
- `request`
- `command`
- `status`
- `execution_authorized`
- `simulated_actions`
- `failure_reasons`
- `warnings`
- `mutates_business_state`
- `audit_records`
- `events`

约束：

- 成功状态：`completed`
- 失败状态：`failed`
- `mutates_business_state = false`

## ExecutionEngine

职责：

- 校验 Decision Result 是否存在
- 校验 Approval 是否通过
- 校验 execution_authorized 是否为 true
- 生成 ExecutionCommand
- 生成 ExecutionResult
- 写 Audit
- 发布 Event
- 记录失败原因

不得：

- 修改 Room
- 修改 Stay
- 修改 Caregiver
- 执行排房
- 分配照护师
- 接 UI
- 写数据库

## Event

必须发布：

- `execution.requested`
- `execution.completed`
- `execution.failed`

Event 必须包含：

- request_id
- decision_id
- approval_id
- execution_authorized
- simulation_only
- mutates_business_state=false

## Audit

必须写入：

- `execution.request`
- `execution.complete`
- `execution.fail`

Audit 必须记录：

- requester_emp_id
- reason
- result
- decision_id
- approval_id
- execution_authorized
- simulation_only
- mutates_business_state=false

## 模拟执行说明

P15 的 execute() 只记录已授权推荐结果的模拟执行。

即使审批通过，P15 也不写入真实房态、入住、照护师状态。

真实业务状态修改留给未来执行落地阶段。
