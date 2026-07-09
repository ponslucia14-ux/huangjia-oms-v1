# OMS AI 推理设计

## 阶段边界

P24 AI Reasoning Layer 建立凰家大脑可解释分析能力。

本阶段只建立推理框架，不接真实 AI API，不训练模型，不自动决策。

本阶段禁止：

- 修改业务数据
- 自动执行
- 自动审批
- 调用真实模型 API
- 接 UI

## 一、ReasoningContext

ReasoningContext 是一次 AI 推理的输入上下文。

输入来源：

- AI Context
- Knowledge Retrieval Result
- Metrics
- Alerts
- Domain Data

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `context_id` | 是 | 推理上下文 ID |
| `actor_emp_id` | 是 | 发起推理的 EMP |
| `question` | 是 | 本次推理问题 |
| `ai_context` | 否 | P21 AI Context |
| `knowledge_retrieval_result` | 否 | P23 知识检索结果 |
| `metrics` | 否 | 指标证据 |
| `alerts` | 否 | 异常证据 |
| `domain_data` | 否 | Domain 证据 |
| `correlation_id` | 否 | 上下游追踪 ID |

要求：

- 输入只读
- 推理过程不得修改任何输入
- 输入缺失时允许返回低置信度或证据不足结果

## 二、ReasoningStep

ReasoningStep 表示一段可解释推理步骤。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `step_id` | 是 | 推理步骤 ID |
| `order` | 是 | 步骤顺序 |
| `description` | 是 | 推理动作说明 |
| `input_sources` | 是 | 使用的证据来源 ID |
| `output` | 是 | 本步骤输出 |
| `confidence` | 是 | 本步骤置信度 |

要求：

- 每一步必须说明使用了哪些来源
- 每一步必须有输出

## 三、ReasoningChain

ReasoningChain 表示完整推理链。

包含：

- `chain_id`
- `context_id`
- `steps`
- `evidence_sources`
- `generated_at`

要求：

- 推理链必须可回放
- 推理链必须能追溯到证据来源

## 四、ReasoningResult

ReasoningResult 表示推理输出。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `result_id` | 是 | 推理结果 ID |
| `reasoning_chain` | 是 | 推理链 |
| `conclusions` | 是 | 结论列表 |
| `evidence_sources` | 是 | 证据来源 |
| `confidence` | 是 | 总体置信度 |
| `uncertainty` | 是 | 不确定性说明 |
| `generated_at` | 是 | 生成时间 |

每个结论必须包含：

- `conclusion_id`
- `statement`
- `source_ids`
- `reasoning_step_ids`
- `confidence`

要求：

- 每个结论必须有来源
- 每个结论必须引用推理步骤
- 不允许无来源结论

## 五、AIReasoningEngine

AIReasoningEngine 是推理编排层。

流程：

```text
ReasoningContext
→ collect evidence
→ build reasoning steps
→ generate conclusions
→ calculate confidence
→ write Audit
→ publish Event
```

职责：

- 校验 actor EMP
- 汇总证据来源
- 生成推理链
- 生成结论
- 输出不确定性
- 写 Audit
- 发 Event

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

- `knowledge`
- `metric`
- `alert`
- `domain_data`
- `ai_context`

知识来源必须保留：

- `knowledge_id`
- `source`
- `version`

指标来源必须保留：

- `metric_id`
- `source_domain`

异常来源必须保留：

- `alert_id`
- `severity`
- `status`

## 七、Audit

推理请求必须写入：

```text
ai.reasoning.request
```

推理完成必须写入：

```text
ai.reasoning.completed
```

Audit metadata 必须包含：

- `context_id`
- `result_id`
- `evidence_count`
- `conclusion_count`
- `confidence`
- `correlation_id`
- `external_ai_called = false`
- `mutates_business_state = false`

## 八、Event

推理完成必须发布：

```text
ai.reasoning.completed
```

Event payload 必须包含：

- `context_id`
- `result_id`
- `confidence`
- `evidence_count`
- `conclusion_count`
- `external_ai_called = false`
- `mutates_business_state = false`

## 九、安全边界

AI Reasoning Layer 只做解释性分析。

禁止：

- 修改业务数据
- 自动执行
- 自动审批
- 自动下发任务
- 调用真实外部模型
- 绕过权限
- 绕过 Audit
