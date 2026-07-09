# OMS 知识检索设计

## 阶段边界

P23 Knowledge Retrieval Foundation 建立凰家大脑知识检索基础层。

本阶段只建立检索模型和 rule-based / keyword-based 检索框架。

本阶段不是：

- 向量数据库
- 搜索页面
- UI
- 外部搜索
- 自动执行

本阶段禁止：

- 修改知识内容
- 修改业务数据
- 接真实向量数据库
- 接外部搜索服务
- 接 UI

## 一、KnowledgeQuery

KnowledgeQuery 表示一次知识检索请求。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `query_id` | 是 | 检索请求唯一 ID |
| `actor_emp_id` | 是 | 发起检索的 EMP |
| `query` | 是 | 检索问题或关键词 |
| `category` | 否 | 限定知识分类 |
| `related_domain` | 否 | 限定业务域 |
| `context_scope` | 否 | 上下文范围 |
| `correlation_id` | 否 | 上下游追踪 ID |

要求：

- `query` 不允许为空
- `category` 如传入，必须来自 P22 固定知识分类
- `actor_emp_id` 必须来自 OMS Master Data

## 二、KnowledgeMatch

KnowledgeMatch 表示一条命中的知识结果。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `knowledge_id` | 是 | 命中的知识 ID |
| `title` | 是 | 知识标题 |
| `category` | 是 | 知识分类 |
| `relevance_score` | 是 | 匹配分数 |
| `source` | 是 | 知识来源 |
| `version` | 是 | 知识版本 |
| `related_domains` | 是 | 关联业务域 |
| `matched_terms` | 是 | 命中关键词 |
| `content_preview` | 否 | 内容摘要 |

要求：

- 每条结果必须可追溯到 `knowledge_id`
- 每条结果必须保留 `source`
- 每条结果必须保留 `version`

## 三、KnowledgeRetriever

KnowledgeRetriever 是纯检索器。

职责：

- 读取 KnowledgeEntry 列表
- 按 query / category / related_domain / context_scope 匹配
- 计算 relevance_score
- 返回排序后的 KnowledgeMatch

禁止：

- 写 Audit
- 发 Event
- 修改知识
- 修改业务数据
- 调用向量数据库
- 调用外部搜索

## 四、KnowledgeRetrievalEngine

KnowledgeRetrievalEngine 是检索编排层。

流程：

```text
KnowledgeQuery
→ read KnowledgeRepository
→ KnowledgeRetriever keyword match
→ KnowledgeMatch list
→ Audit
→ Event
→ AI Context reference
```

职责：

- 校验 actor_emp_id
- 执行检索
- 写 Audit
- 发布 Event
- 输出可进入 AI Context 的只读引用

## 五、匹配逻辑

第一阶段采用 rule-based / keyword-based retrieval。

匹配范围：

- title
- content
- source
- category
- related_domain
- context_scope

排序规则：

1. 标题命中优先
2. 内容命中其次
3. 分类过滤加权
4. 业务域过滤加权
5. 分数相同时按 `knowledge_id` 稳定排序

## 六、AI Context 关联方式

检索结果必须能进入 AI Context。

标准输出：

```text
KnowledgeMatch
→ ai_context_reference
→ AI Assistant context source
```

AI Context reference 必须包含：

- `knowledge_entries`
- `source_domains`
- `categories`
- `versions`
- `matched_knowledge_ids`
- `mutates_business_state = false`
- `external_vector_db_called = false`
- `external_search_called = false`

## 七、Audit

每次检索必须写入：

```text
knowledge.query
knowledge.retrieve
```

Audit 必须包含：

- actor EMP
- query_id
- query
- category
- related_domain
- context_scope
- match_count
- correlation_id

## 八、Event

每次检索完成必须发布：

```text
knowledge.retrieval.completed
```

Event payload 必须包含：

- `query_id`
- `match_count`
- `matched_knowledge_ids`
- `category`
- `related_domain`
- `mutates_business_state = false`
- `external_vector_db_called = false`
- `external_search_called = false`

## 九、边界确认

P23 只建立知识检索基础层。

不提供：

- 搜索 UI
- 向量数据库
- 外部搜索
- 业务写入
- 知识内容修改

检索结果只读、可追溯、可进入 AI Context。
