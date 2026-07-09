# OMS AI 建议设计

## 阶段边界

P25 AI Recommendation Layer 建立凰家大脑基于分析结果生成经营建议的能力。

本阶段只生成可解释建议，不执行、不审批、不修改业务状态。

本阶段禁止：

- 自动执行
- 自动审批
- 修改业务数据
- 调用真实 AI API
- 接 UI

## 一、RecommendationContext

RecommendationContext 是一次建议生成请求的输入上下文。

输入来源：

- AI Reasoning Result
- Metrics
- Alerts
- Knowledge Context

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `context_id` | 是 | 建议上下文 ID |
| `actor_emp_id` | 是 | 发起建议生成的 EMP |
| `objective` | 是 | 本次建议目标 |
| `reasoning_result` | 否 | P24 推理结果 |
| `metrics` | 否 | 指标证据 |
| `alerts` | 否 | 异常证据 |
| `knowledge_context` | 否 | 知识上下文 |
| `correlation_id` | 否 | 上下游追踪 ID |

要求：

- 输入只读
- 不允许修改推理结果
- 不允许修改指标、异常或知识

## 二、RecommendationItem

RecommendationItem 表示一条可解释经营建议。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `recommendation_id` | 是 | 建议 ID |
| `recommendation` | 是 | 建议正文 |
| `priority` | 是 | 优先级 |
| `expected_impact` | 是 | 预期影响 |
| `evidence_sources` | 是 | 证据来源 ID |
| `confidence` | 是 | 置信度 |
| `risks` | 是 | 风险提示 |
| `basis` | 是 | 建议依据 |
| `related_domain` | 否 | 关联业务域 |

优先级：

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

每条建议必须满足：

- 有依据
- 有来源
- 有置信度
- 有风险提示

## 三、RecommendationResult

RecommendationResult 表示一次建议生成结果。

包含：

- `result_id`
- `context_id`
- `recommendations`
- `evidence_sources`
- `confidence`
- `generated_at`

要求：

- 结果必须可追溯
- 所有建议必须只读
- 所有建议必须由证据来源支撑

## 四、AIRecommendationEngine

AIRecommendationEngine 是建议生成编排层。

流程：

```text
RecommendationContext
→ collect evidence
→ generate recommendation items
→ calculate priority / confidence / risk
→ write Audit
→ publish Event
```

职责：

- 校验 actor EMP
- 汇总推理、指标、异常、知识证据
- 生成建议
- 绑定来源
- 输出风险提示
- 写 Audit
- 发 Event

## 五、生成逻辑

第一阶段采用 rule-based 生成逻辑。

建议来源：

1. Alert evidence
   - OPEN / HIGH / CRITICAL 异常生成高优先级建议

2. Reasoning conclusion
   - 将 P24 推理结论转换为人工可审阅建议

3. Metric evidence
   - 指标异常或关键经营指标生成观察建议

4. Knowledge evidence
   - 将知识检索结果转换为参考建议

禁止：

- 把建议当作自动决策
- 把建议直接发送到执行层
- 自动审批

## 六、来源追踪

证据来源统一格式：

```text
source_id
source_type
domain
version
title
```

支持来源：

- `reasoning_conclusion`
- `knowledge`
- `metric`
- `alert`
- `domain_data`

每条建议必须引用：

- `evidence_sources`
- `basis`

## 七、Audit

建议请求必须写入：

```text
ai.recommendation.request
```

建议生成必须写入：

```text
ai.recommendation.generated
```

Audit metadata 必须包含：

- `context_id`
- `result_id`
- `recommendation_count`
- `evidence_count`
- `confidence`
- `correlation_id`
- `external_ai_called = false`
- `mutates_business_state = false`
- `auto_executes = false`
- `auto_approves = false`

## 八、Event

建议生成必须发布：

```text
ai.recommendation.generated
```

Event payload 必须包含：

- `context_id`
- `result_id`
- `recommendation_count`
- `confidence`
- `external_ai_called = false`
- `mutates_business_state = false`
- `auto_executes = false`
- `auto_approves = false`

## 九、安全边界

AI Recommendation Layer 只生成建议。

禁止：

- 修改业务数据
- 自动执行
- 自动审批
- 调用真实 AI API
- 接 UI
- 跳过 Audit
