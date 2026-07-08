# OMS 调度决策设计

## 阶段边界

P13 Scheduling Decision Engine 建立在 P12 Scheduler Foundation 之上，只负责对调度候选资源进行判断、排序、拒绝与解释。

本阶段仍然禁止：

- 自动排房
- 自动分配照护师
- 修改 Room 状态
- 修改 Stay 状态
- 修改 Caregiver 状态
- 执行任何业务写入

调度决策链必须保留：

```text
系统推荐 -> 人工确认 -> 执行
```

P13 只完成“系统推荐”阶段，并返回可供人工确认的决策结果。

## 决策模型

### DecisionContext

DecisionContext 是调度决策引擎的只读输入上下文。

字段：

- `request_id`: 调度决策请求 ID
- `actor_emp_id`: 发起决策分析的 EMP
- `reason`: 决策分析原因
- `scheduling_context`: P12 SchedulingContext
- `candidate_resources`: 候选资源集合
- `business_rule_results`: Business Rules Engine 输出
- `correlation_id`: 上游调度请求或业务事件 ID
- `metadata`: 附加只读上下文

### DecisionRule

DecisionRule 是只读决策规则。

字段：

- `rule_id`
- `name`
- `description`
- `priority`
- `enabled`
- `evaluator`

规则只能返回：

- `PASS`
- `WARNING`
- `REJECT`

规则不得修改任何业务状态。

### DecisionResult

DecisionResult 是 P13 的唯一输出。

字段：

- `ranked_recommendations`: 排序后的建议方案
- `decision_status`: `PENDING | RECOMMENDED | APPROVED | REJECTED | EXECUTED`
- `decision_reason`: 决策原因
- `warnings`: 警告信息
- `rejected_options`: 被拒绝方案
- `business_rule_trace`: 业务规则追踪
- `decision_chain`: `system_recommendation -> human_confirmation -> execution`
- `mutates_business_state`: 固定为 `false`
- `audit_records`
- `events`

P13 默认只会产出：

- `RECOMMENDED`
- `REJECTED`

`APPROVED` 和 `EXECUTED` 仅为未来人工确认与执行阶段保留。

## 输入

SchedulingDecisionEngine 输入：

- Scheduling Context
- Business Rules Result
- Candidate Resources

候选资源可以包含：

- room candidate
- caregiver candidate
- room + caregiver 组合候选

## 输出

SchedulingDecisionEngine 输出：

- ranked recommendations
- decision_status
- decision_reason
- warnings
- rejected_options
- business_rule_trace

所有输出均为只读建议，不代表执行结果。

## 第一批决策规则

### 1. 房间可用性优先级

目标：

- `AVAILABLE` 房间优先级最高
- `RESERVED` 房间保留为人工复核候选，并附加 warning
- 其他状态不加可用性分

### 2. 房间状态限制

目标：

- 明确拒绝无法作为候选的房态
- `OCCUPIED`
- `CLEANING`
- `UNKNOWN`

### 3. 维修 / 停用排除

目标：

- `MAINTENANCE` 必须排除
- `DISABLED` 必须排除

### 4. 照护师状态限制

目标：

- `AVAILABLE` 可推荐
- `RESERVED` 可进入人工复核，但附加 warning
- `ASSIGNED`
- `ON_LEAVE`
- `OFF_DUTY`
- `DISABLED`

以上状态必须拒绝。

### 5. 权限授权判断

目标：

只有被授权角色可以发起调度决策推荐。

允许角色：

- `ROLE_OWNER`
- `ROLE_STORE_MANAGER`
- `ROLE_NURSING_DIRECTOR`
- `ROLE_HR`

未授权角色只能得到 `REJECTED` 决策结果。

## Event

P13 至少发布：

- `scheduling.decision.requested`
- `scheduling.decision.completed`
- `scheduling.decision.failed`

Event 必须包含：

- request_id
- decision_status
- mutates_business_state=false
- reason
- correlation_id

## Audit

P13 必须写入 Audit Log。

Audit action：

- `scheduling_decision.request`
- `scheduling_decision.complete`
- `scheduling_decision.fail`

Audit 必须记录：

- actor_emp_id
- actor_name
- reason
- result
- decision_status
- candidate_count
- recommendation_count
- rejected_option_count

## 系统边界

SchedulingDecisionEngine 只能分析和返回结果。

它不得调用：

- RoomService 状态变更方法
- Stay 状态变更方法
- CaregiverService 状态变更方法
- 自动排房执行方法

调度执行必须留给未来阶段。
