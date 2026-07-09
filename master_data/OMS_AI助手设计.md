# OMS AI 助手设计

## 阶段边界

P21 AI Assistant Foundation 建立 OMS AI 助手基础层。

本阶段只定义架构设计，不写代码，不接模型，不接 UI，不接外部 AI 服务。

AI 助手只允许读取授权范围内的 OMS 信息，并基于已有数据回答经营问题。

AI 助手禁止：

- 修改业务数据
- 自动审批
- 自动执行
- 绕过权限
- 绕过 Audit
- 生成未经授权的数据结论

## 一、AI Context Layer

AI Context Layer 定义 AI 可以读取的 OMS 上下文范围。

允许读取的来源：

- Domain
- Metrics
- Dashboard Query
- Alert
- Audit
- Event

### Domain Context

可读取内容：

- 已定义的 Domain 对象摘要
- Domain 状态
- Domain ID
- Domain 来源

边界：

- 只读
- 不允许修改 Domain
- 不允许绕过 Domain 权限

### Metrics Context

可读取内容：

- MetricDefinition
- MetricSnapshot
- DashboardDataset
- 指标值
- 指标来源 Domain
- 指标生成时间

边界：

- AI 只能解释指标
- 不允许重新写入指标
- 不允许自行生成经营指标作为事实

### Dashboard Query Context

可读取内容：

- DashboardQuery
- DashboardFilter
- DashboardView
- 销售驾驶舱
- 资金驾驶舱
- 经营驾驶舱

边界：

- 必须沿用 Dashboard Query Layer 权限
- 不能绕过驾驶舱查询权限

### Alert Context

可读取内容：

- AlertDefinition
- AlertContext 摘要
- AlertResult
- alert status
- alert severity
- alert evidence

边界：

- AI 可以解释异常原因
- AI 可以提示处理建议
- AI 不允许自动 acknowledge / resolve / ignore

### Audit Context

可读取内容：

- 授权范围内的 Audit 记录
- 操作人
- 操作模块
- 操作原因
- 操作结果
- correlation_id

边界：

- Audit 只读
- AI 查询本身必须写入 Audit
- 不允许隐藏 AI 查询记录

### Event Context

可读取内容：

- Event 类型
- source_module
- payload 摘要
- correlation_id
- event timestamp

边界：

- Event 只读
- AI 不允许发布业务事件
- AI 查询流程自身可以发布 AI 事件

## 二、AI Query Model

### AIQuery

AIQuery 是一次 AI 问答请求。

字段：

- `query_id`
- `actor_emp_id`
- `question`
- `context_scope`
- `correlation_id`

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `query_id` | 是 | AI 查询唯一 ID |
| `actor_emp_id` | 是 | 发起人 EMP |
| `question` | 是 | 用户问题原文 |
| `context_scope` | 是 | 本次允许读取的上下文范围 |
| `correlation_id` | 否 | 与上下游 Audit / Event 关联 |

`context_scope` 可包含：

- `domain`
- `metrics`
- `dashboard_query`
- `alert`
- `audit`
- `event`

要求：

- `actor_emp_id` 必须来自 OMS Master Data
- `question` 不允许为空
- `context_scope` 必须经过权限裁剪

## 三、AI Response Model

### AIResponse

AIResponse 是 AI 对查询的回答结果。

字段：

- `response_id`
- `answer`
- `source_domains`
- `related_metrics`
- `related_alerts`
- `confidence`
- `generated_at`

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `response_id` | 是 | AI 响应唯一 ID |
| `answer` | 是 | AI 回答内容 |
| `source_domains` | 是 | 回答引用的 Domain 来源 |
| `related_metrics` | 否 | 回答涉及的指标 ID |
| `related_alerts` | 否 | 回答涉及的异常 ID |
| `confidence` | 是 | 回答可信度 |
| `generated_at` | 是 | 生成时间 |

`confidence` 支持：

- `high`
- `medium`
- `low`
- `insufficient_context`

回答要求：

- 必须说明引用来源
- 缺少上下文时必须降级为 `insufficient_context`
- 不允许把推测当作事实

## 四、权限边界

AI 权限必须继承 OMS 现有角色权限。

### 石磊

权限：

- 可查询全部经营数据
- 可查询全部 Metrics
- 可查询全部 Dashboard Query
- 可查询全部 Alert
- 可查询授权范围内 Audit / Event

限制：

- 仍不允许通过 AI 修改业务状态
- 仍不允许通过 AI 自动审批
- 仍不允许通过 AI 自动执行

### 财务角色

权限：

- 可查询资金驾驶舱
- 可查询财务相关 Metrics
- 可查询财务相关 Alert
- 可查询自己权限范围内的财务 Audit / Event

限制：

- 不允许查询非授权房态、销售、人效明细

### 销售角色

权限：

- 可查询销售驾驶舱
- 可查询销售相关 Metrics
- 可查询销售相关 Alert
- 可查询自己权限范围内的销售 Audit / Event

限制：

- 不允许查询资金明细
- 不允许查询非授权人效数据

### 店长 / 房态角色

权限：

- 可查询经营驾驶舱中房态相关内容
- 可查询房态相关 Alert
- 可查询授权范围内 Room / Stay / Event

限制：

- 不允许查询非授权财务明细

### 其他角色

权限：

- 只允许查询本人工作范围内的数据
- 只允许查询本人相关 Audit / Event 摘要

限制：

- 不允许查询全局经营数据
- 不允许查询其他人的个人执行明细

## 五、审计要求

所有 AI 查询必须写 Audit。

必须写入：

- `ai.query`
- `ai.response`

### ai.query

记录内容：

- `query_id`
- `actor_emp_id`
- `question`
- `context_scope`
- `correlation_id`
- `permission_result`
- `mutates_business_state=false`

### ai.response

记录内容：

- `query_id`
- `response_id`
- `source_domains`
- `related_metrics`
- `related_alerts`
- `confidence`
- `correlation_id`
- `mutates_business_state=false`

## 六、Event

AI 查询流程必须发布事件。

事件：

- `ai.query.requested`
- `ai.response.generated`

### ai.query.requested

Payload：

- `query_id`
- `actor_emp_id`
- `context_scope`
- `correlation_id`
- `mutates_business_state=false`

### ai.response.generated

Payload：

- `query_id`
- `response_id`
- `source_domains`
- `related_metrics`
- `related_alerts`
- `confidence`
- `correlation_id`
- `mutates_business_state=false`

## 七、明确禁止

AI 不允许：

- 修改业务数据
- 自动审批
- 自动执行
- 绕过权限
- 绕过 Audit
- 绕过 Event
- 直接调用业务 Engine 修改状态
- 直接调用 Execution Engine
- 直接调用 Approval Engine
- 将未授权数据暴露给无权限角色
- 将低可信度推测伪装成事实

## P21 目标状态

P21 完成后，OMS 将具备 AI 助手基础契约：

```text
AIQuery
-> Permission Check
-> AI Context Layer
-> AIResponse
-> Audit
-> Event
```

AI 助手是只读解释层，不是执行层。
