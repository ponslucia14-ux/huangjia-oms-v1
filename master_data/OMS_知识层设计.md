# OMS 知识层设计

## 阶段边界

P22 Knowledge Layer 建立凰家大脑知识资产基础层。

本阶段只建立知识模型、知识分类、知识版本、知识读取，以及与 AI Context 的只读关联。

本阶段禁止：

- 修改业务数据
- 自动执行业务动作
- 自动审批
- 接真实向量数据库
- 接 UI
- 建搜索产品

## 一、Knowledge Model

### KnowledgeDocument

KnowledgeDocument 表示一份知识来源文件或资料。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `document_id` | 是 | 知识文档唯一 ID |
| `title` | 是 | 文档标题 |
| `category` | 是 | 知识分类 |
| `source` | 是 | 来源类型或来源说明 |
| `content` | 是 | 文档内容摘要或正文 |
| `related_domain` | 是 | 关联业务域 |
| `version` | 是 | 文档版本 |
| `created_at` | 是 | 创建时间 |

### KnowledgeEntry

KnowledgeEntry 表示可被 OMS 和 AI Context 引用的一条知识。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `knowledge_id` | 是 | 知识条目唯一 ID |
| `title` | 是 | 知识标题 |
| `category` | 是 | 知识分类 |
| `source` | 是 | 知识来源 |
| `content` | 是 | 知识内容 |
| `related_domain` | 是 | 关联业务域 |
| `version` | 是 | 知识版本 |
| `created_at` | 是 | 创建时间 |

### KnowledgeCategory

KnowledgeCategory 定义知识分类。

第一阶段固定分类：

| 分类 ID | 名称 | 来源 |
| --- | --- | --- |
| `policy` | 制度文件 | 制度文件 |
| `sop` | SOP | SOP |
| `business_rule` | 业务规则 | 业务规则 |
| `operating_experience` | 运营经验 | 运营经验 |
| `retrospective` | 历史复盘 | 历史复盘 |
| `training` | 培训资料 | 培训资料 |

禁止系统运行时临时生成分类。

### KnowledgeContext

KnowledgeContext 是给 AI Context 使用的知识上下文引用。

包含：

- `entries`
- `source_domains`
- `categories`
- `versions`

要求：

- 只读
- 不修改原始知识
- 不修改业务状态
- 不调用外部 AI 或向量数据库

## 二、知识读取与分类

Knowledge Layer 支持：

- 按 `knowledge_id` 读取
- 按 `category` 分类读取
- 按 `related_domain` 读取
- 读取知识版本历史
- 生成 KnowledgeContext

所有读取操作只读，不写业务数据。

## 三、知识版本

知识更新必须保留版本历史。

更新规则：

- 更新后生成新版本
- 原版本进入历史记录
- 新版本保留同一个 `knowledge_id`
- 必须记录更新原因

## 四、AI Context 关联方式

AI Assistant 不直接读取散落文件。

标准链路：

```text
KnowledgeEntry
→ KnowledgeContext
→ AI Context reference
→ AI Response source
```

AI 可读取的知识内容必须经过 KnowledgeContext 裁剪。

AI 禁止：

- 绕过 KnowledgeContext 直接读取外部知识源
- 修改 KnowledgeEntry
- 修改业务数据
- 自动执行

## 五、Audit

知识创建必须写入：

```text
knowledge.created
```

知识更新必须写入：

```text
knowledge.updated
```

Audit 必须包含：

- actor EMP
- actor name
- reason
- target_type = `knowledge`
- target_id = `knowledge_id`
- correlation_id
- version
- category
- related_domain

## 六、Event

知识创建或更新后必须发布：

```text
knowledge.available
```

Event payload 必须包含：

- `knowledge_id`
- `title`
- `category`
- `source`
- `related_domain`
- `version`
- `action`
- `mutates_business_state = false`
- `external_vector_db_called = false`

## 七、边界确认

P22 Knowledge Layer 是知识资产基础层，不是知识库产品。

本阶段只提供：

- 模型
- 分类
- 版本
- 读取
- AI 只读关联
- Audit
- Event

不提供：

- 搜索页面
- 向量数据库
- 自动执行
- 业务状态修改
- UI
