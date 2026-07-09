# OMS AI 记忆设计

## 阶段边界

P27 AI Memory & Learning Layer 建立凰家大脑经验沉淀闭环。
本阶段不是模型训练，不自动优化模型，不自动执行，只建立经验记录与反馈框架。

本阶段禁止：

- 自动训练模型
- 自动修改 AI 规则
- 自动执行
- 修改业务数据
- 调用真实模型 API
- 接 UI

## 一、AIExperienceRecord

AIExperienceRecord 表示一条 AI 建议进入经验沉淀层后的原始经验记录。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `memory_id` | 是 | 经验记录 ID |
| `recommendation_id` | 是 | AI 建议 ID |
| `context` | 是 | 生成建议时的上下文 |
| `reasoning_source` | 是 | 来源推理结果或推理摘要 |
| `decision_result` | 是 | 人工审核或治理结果 |
| `created_at` | 是 | 经验创建时间 |
| `related_domain` | 否 | 关联业务域 |
| `metadata` | 否 | 扩展信息 |

要求：

- 必须能追溯建议来源。
- 必须保留上下文、推理来源、决策结果。
- 不允许修改业务状态。

## 二、AILearningFeedback

AILearningFeedback 表示建议被采纳或拒绝后的人工反馈。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `feedback_id` | 是 | 反馈 ID |
| `recommendation_id` | 是 | AI 建议 ID |
| `actor_emp_id` | 是 | 反馈人 EMP |
| `adopted` | 是 | 是否采纳 |
| `rejected` | 是 | 是否拒绝 |
| `outcome` | 是 | 结果描述 |
| `impact` | 是 | 影响描述 |
| `created_at` | 是 | 反馈时间 |
| `evidence_sources` | 否 | 反馈依据 |

规则：

- `adopted` 与 `rejected` 必须二选一。
- 反馈只记录结果，不触发执行。

## 三、AIOutcomeRecord

AIOutcomeRecord 表示沉淀后的经验结果。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `outcome_id` | 是 | 结果记录 ID |
| `recommendation_id` | 是 | AI 建议 ID |
| `outcome_type` | 是 | 成功经验 / 失败经验 / 历史案例 |
| `outcome` | 是 | 结果 |
| `impact` | 是 | 影响 |
| `lessons` | 是 | 经验总结 |
| `evidence_sources` | 否 | 结果依据 |
| `recorded_at` | 是 | 记录时间 |

结果类型：

```text
SUCCESS
FAILURE
HISTORICAL_CASE
```

## 四、AIMemoryEngine

AIMemoryEngine 是 AI 经验沉淀编排层。

流程：

```text
AI recommendation
-> experience record
-> feedback
-> outcome record
-> memory context
```

职责：

- 创建建议经验记录。
- 记录采纳或拒绝反馈。
- 沉淀成功经验、失败经验、历史案例。
- 输出可供 AI Context 读取的历史经验。
- 写 Audit。
- 发布 Event。

禁止：

- 自动训练模型。
- 自动修改 AI 规则。
- 自动执行建议。
- 修改业务数据。
- 调用真实模型 API。

## 五、AI Context 关联方式

AI Context 可以读取：

- experience_records
- feedback_records
- outcome_records
- success_cases
- failure_cases
- historical_cases

输出必须标记：

```text
mutates_business_state = false
trains_model = false
auto_optimizes_rules = false
external_ai_called = false
```

## 六、Audit

创建经验记录必须写入：

```text
ai.memory.created
```

更新反馈或结果必须写入：

```text
ai.memory.updated
```

Audit metadata 必须包含：

- `memory_id`
- `recommendation_id`
- `feedback_id`
- `outcome_id`
- `outcome_type`
- `mutates_business_state = false`
- `trains_model = false`
- `auto_optimizes_rules = false`
- `auto_executes = false`
- `external_ai_called = false`

## 七、Event

经验可用时发布：

```text
ai.memory.available
```

Event payload 必须包含：

- `memory_id`
- `recommendation_id`
- `action`
- `feedback_count`
- `outcome_count`
- `mutates_business_state = false`
- `trains_model = false`
- `auto_optimizes_rules = false`
- `auto_executes = false`
- `external_ai_called = false`

## 八、安全边界

AI Memory Layer 只沉淀经验。

明确禁止：

- 自动训练模型
- 自动调整规则
- 自动执行建议
- 修改业务数据
- 绕过 Audit
- 调用真实模型 API
- 接 UI
