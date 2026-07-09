# OMS AI 治理设计

## 阶段边界

P26 AI Governance Layer 建立凰家大脑 AI 输出治理框架。
本阶段只管理 AI 建议的生命周期，不增强 AI 能力，不执行 AI 建议，不修改业务数据。

本阶段禁止：

- 自动执行
- 自动审批
- 修改业务数据
- 调用真实 AI API
- 接 UI

## 一、AIRecommendationRecord

AIRecommendationRecord 是一条 AI 建议进入治理层后的正式记录。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `record_id` | 是 | 治理记录 ID |
| `recommendation_id` | 是 | AI 建议 ID |
| `proposer_emp_id` | 是 | 提出 AI 建议的 EMP |
| `source_reasoning` | 是 | 来源推理结果或推理摘要 |
| `evidence_sources` | 是 | 建议依据来源 |
| `confidence` | 是 | 置信度 |
| `generated_at` | 是 | 建议生成时间 |
| `recommendation_text` | 否 | 建议正文 |
| `status` | 是 | 治理状态 |
| `metadata` | 否 | 扩展信息 |

初始状态固定为：

```text
PENDING_REVIEW
```

## 二、AIReview

AIReview 表示一次人工审核结果。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `review_id` | 是 | 审核 ID |
| `recommendation_id` | 是 | 被审核建议 ID |
| `reviewer_emp_id` | 是 | 审核人 EMP |
| `review_status` | 是 | 审核状态 |
| `reason` | 是 | 审核原因 |
| `reviewed_at` | 是 | 审核时间 |
| `execution_flow_allowed` | 是 | 是否允许进入后续执行流程 |
| `policy_id` | 否 | 使用的治理策略 |
| `correlation_id` | 否 | 链路 ID |

审核状态：

```text
PENDING_REVIEW
APPROVED
REJECTED
EXPIRED
```

规则：

- `APPROVED` 只能表示人工通过。
- `execution_flow_allowed = true` 只代表允许进入后续执行流程，不代表已经执行。
- `REJECTED` / `EXPIRED` 必须禁止进入执行流程。

## 三、AIGovernancePolicy

AIGovernancePolicy 定义 AI 建议进入治理链路后的审核规则。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `policy_id` | 是 | 策略 ID |
| `name` | 是 | 策略名称 |
| `requires_human_review` | 是 | 是否需要人工审核 |
| `allowed_reviewer_emp_ids` | 是 | 允许审核的 EMP 列表 |
| `allow_execution_flow` | 是 | 审核通过后是否允许进入执行流程 |
| `expires_after_hours` | 否 | 审核有效期 |

治理策略只判断权限和生命周期，不自动批准。

## 四、AIGovernanceEngine

AIGovernanceEngine 是 AI 建议治理编排层。

流程：

```text
AIRecommendationRecord
-> governance policy check
-> review request
-> human review
-> review completed
-> execution flow authorization flag
```

职责：

- 保存建议治理记录
- 创建人工审核请求
- 校验审核人权限
- 记录审核状态
- 记录责任链
- 写 Audit
- 发布 Event

禁止：

- 执行业务动作
- 自动审批
- 修改业务数据
- 调用真实 AI API

## 五、责任链

治理层必须记录：

- AI 建议 ID
- 来源推理
- 证据来源
- 建议提出人
- 审核人
- 审核时间
- 审核结果
- 是否允许进入执行流程

责任链只做治理记录，不做执行。

## 六、Audit

审核请求必须写入：

```text
ai.governance.review.request
```

审核完成必须写入：

```text
ai.governance.review.completed
```

Audit metadata 必须包含：

- `record_id`
- `recommendation_id`
- `policy_id`
- `review_status`
- `reviewer_emp_id`
- `execution_flow_allowed`
- `mutates_business_state = false`
- `auto_executes = false`
- `auto_approves = false`
- `external_ai_called = false`

## 七、Event

审核完成必须发布：

```text
ai.governance.review.completed
```

Event payload 必须包含：

- `record_id`
- `recommendation_id`
- `review_id`
- `review_status`
- `reviewer_emp_id`
- `execution_flow_allowed`
- `mutates_business_state = false`
- `auto_executes = false`
- `auto_approves = false`
- `external_ai_called = false`

## 八、安全边界

AI Governance Layer 只管理建议生命周期。

明确禁止：

- 自动执行建议
- 自动审批建议
- 修改业务数据
- 直接进入执行引擎
- 绕过人工审核
- 绕过 Audit
- 接真实 AI API
- 接 UI
