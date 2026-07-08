# OMS 调度审批设计

## 阶段边界

P14 Scheduling Approval Engine 建立在 P13 Scheduling Decision Engine 之后。

本阶段只建立审批确认链：

```text
推荐结果 -> 审批请求 -> 审批决定 -> 执行授权
```

P14 不执行调度，不修改业务状态。

禁止：

- 自动执行排房
- 自动修改 Room
- 自动修改 Stay
- 自动修改 Caregiver
- 接 UI
- 接数据库

## 审批模型

### ApprovalRequest

ApprovalRequest 表示对一个调度推荐结果发起审批。

字段：

- `approval_id`
- `decision_id`
- `requester_emp_id`
- `approver_emp_id`
- `reason`
- `decision_status`
- `timestamp`
- `correlation_id`
- `source_decision_status`
- `metadata`

创建审批请求时：

- `decision_status = PENDING`
- `execution_authorized = false`
- 必须写 Audit
- 必须发布 Event

### ApprovalDecision

ApprovalDecision 表示审批人对审批请求做出的决定。

字段：

- `approval_id`
- `decision_id`
- `requester_emp_id`
- `approver_emp_id`
- `reason`
- `decision_status`
- `timestamp`
- `correlation_id`
- `execution_authorized`
- `metadata`

规则：

- `APPROVED` 才能产生 `execution_authorized = true`
- `REJECTED` 必须保持 `execution_authorized = false`
- `EXPIRED` 必须保持 `execution_authorized = false`

### ApprovalWorkflow

ApprovalWorkflow 表示一次调度审批的完整链路。

字段：

- `request`
- `current_status`
- `decisions`
- `approval_id`
- `decision_id`
- `execution_authorized`
- `decision_chain`
- `mutates_business_state`
- `audit_records`
- `events`

`mutates_business_state` 固定为 `false`。

## 状态流转

支持状态：

- `PENDING`
- `APPROVED`
- `REJECTED`
- `EXPIRED`

合法流转：

```text
PENDING -> APPROVED
PENDING -> REJECTED
PENDING -> EXPIRED
```

终态不可再次审批。

## SchedulingApprovalEngine

职责：

- 创建审批请求
- 记录审批决定
- 标记执行授权
- 写入 Audit Log
- 发布 Event
- 保留决策链

不得：

- 修改房间状态
- 修改入住状态
- 修改照护师状态
- 执行排房
- 写数据库
- 接 UI

## Event

必须发布：

- `scheduling.approval.requested`
- `scheduling.approval.approved`
- `scheduling.approval.rejected`

扩展支持：

- `scheduling.approval.expired`

Event 必须包含：

- `approval_id`
- `decision_id`
- `requester_emp_id`
- `approver_emp_id`
- `decision_status`
- `execution_authorized`
- `mutates_business_state=false`

## Audit

必须写入：

- `approval.request`
- `approval.approve`
- `approval.reject`

扩展支持：

- `approval.expire`

Audit 必须记录：

- actor EMP
- actor name
- reason
- result
- approval_id
- decision_id
- execution_authorized
- mutates_business_state=false

## 决策链保留

P14 必须保留完整链路：

```text
system_recommendation
approval_request
approval_decision
execution_authorization
```

审批通过只代表未来执行阶段获得授权。

审批通过不等于执行。

## 输出

SchedulingApprovalEngine 输出 ApprovalWorkflow。

输出必须包含：

- 当前审批状态
- 审批决定
- 执行授权标记
- Event
- Audit
- 决策链
