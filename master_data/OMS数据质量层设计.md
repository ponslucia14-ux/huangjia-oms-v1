# OMS 数据质量层设计

阶段：P0.12 OMS Data Quality Layer

状态：设计冻结候选

## 一、目标与边界

Data Quality Layer 是外部 Excel 进入 OMS 初始化迁移快照或后续批量导入流程之前的唯一质量与准入关口。它回答四个问题：

1. 这份数据表达什么业务事实。
2. 这份数据是否可信、完整且可追溯。
3. 这份数据属于当前状态还是历史记录。
4. 这份数据是否具备进入 `OMS_TRUTH_SOURCE` 的资格。

生产数据链路统一为：

```text
Excel
  -> Workbook Inventory
  -> Sheet Analysis
  -> Data Classification
  -> Record Quality Evaluation
  -> Current/Historical Resolution
  -> Change Detection
  -> Production Admission Decision
  -> OMS_TRUTH_SOURCE
  -> Production Data Adapter
  -> Domain
  -> API Contract
  -> Page / AI Context
```

禁止以下链路：

```text
Excel -> Adapter -> Page
Excel -> Truth Source（未经质量判定）
Excel -> AI Context（未经质量判定）
UI -> 自行判断当前或历史
新文件 -> 覆盖上一批数据
```

本阶段只定义数据质量层，不修改页面，不新增业务模块，不改变既有 Domain Engine。

## 二、核心模型

### 2.1 DataQualityImport

一次 Excel 质量分析批次。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `import_id` | string | 是 | 导入批次唯一 ID |
| `source_file` | string | 是 | 原始文件完整名称 |
| `source_file_hash` | string | 是 | 原文件内容哈希，用于去重与防篡改 |
| `source_version` | string | 是 | 文件版本或导入版本 |
| `file_modified_time` | datetime | 是 | 文件最后修改时间 |
| `imported_at` | datetime | 是 | OMS 接收时间 |
| `imported_by_emp_id` | string | 是 | 导入人 EMP ID |
| `workbook_sheet_count` | integer | 是 | 工作簿 Sheet 总数 |
| `quality_status` | enum | 是 | `ANALYZING / REVIEW_REQUIRED / ADMISSIBLE / PARTIALLY_ADMISSIBLE / REJECTED` |
| `report_id` | string | 是 | 对应数据质量报告 ID |
| `correlation_id` | string | 是 | Audit/Event 关联 ID |

同一 `source_file_hash` 不重复生成生产记录，只记录重复导入事实。

### 2.2 SheetProfile

每个 Sheet 必须生成一条完整分析记录，不能跳过隐藏 Sheet、空白 Sheet 或非首个 Sheet。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `sheet_profile_id` | string | 是 | Sheet 分析 ID |
| `import_id` | string | 是 | 所属导入批次 |
| `source_file` | string | 是 | 文件名 |
| `source_sheet` | string | 是 | Sheet 原始名称 |
| `sheet_index` | integer | 是 | Sheet 顺序 |
| `visibility` | enum | 是 | `VISIBLE / HIDDEN / VERY_HIDDEN` |
| `row_count` | integer | 是 | 有效数据行数，不含纯格式空行 |
| `column_count` | integer | 是 | 有效列数 |
| `header_row` | integer/null | 是 | 识别出的表头行；无法确认时为空 |
| `fields` | array | 是 | 原始字段名、标准字段候选及置信度 |
| `time_range_start` | date/null | 是 | 最早业务时间 |
| `time_range_end` | date/null | 是 | 最晚业务时间 |
| `business_purpose` | string/null | 是 | 销售、财务、房态、签约客户等业务用途 |
| `usage_class` | enum | 是 | Sheet 用途分类 |
| `classification_confidence` | number | 是 | `0-1`，只表达判定可信度 |
| `classification_evidence` | array | 是 | 字段、内容、公式、时间范围等判定证据 |
| `admission_status` | enum | 是 | Sheet 生产准入结果 |
| `issues` | array | 是 | 质量问题列表 |

### 2.3 Sheet 用途分类

每个 Sheet 必须且只能归入以下一种主分类：

| 分类 | 含义 | 生产准入 |
|---|---|---|
| `CURRENT_PRODUCTION` | 描述当前有效业务状态 | 可进入当前 Truth Source，仍须通过记录级校验 |
| `HISTORICAL` | 描述过去已结束或已被新版本替代的事实 | 只进入历史区，不进入首页当前口径 |
| `SUMMARY` | 汇总、透视、报表合计 | 不作为基础事实；可作校验对账证据 |
| `AUXILIARY_CALCULATION` | 公式中间表、辅助映射、计算底稿 | 不直接进入 Truth Source 实体 |
| `NOTES` | 备注、说明、口径、模板 | 不进入生产事实源 |

无法确定用途时：

```text
usage_class = UNCONFIRMED
admission_status = REVIEW_REQUIRED
```

`UNCONFIRMED` 数据不得进入生产 Truth Source。

### 2.4 QualityRecord

每条候选生产记录统一增加：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `record_id` | string | 是 | OMS 稳定记录 ID；不能使用易变行号作为唯一业务键 |
| `source_file` | string | 是 | 来源文件 |
| `source_sheet` | string | 是 | 来源 Sheet |
| `source_row` | integer | 是 | 来源行号 |
| `source_version` | string | 是 | 来源版本 |
| `source_file_hash` | string | 是 | 来源文件哈希 |
| `record_fingerprint` | string | 是 | 标准化业务字段指纹 |
| `created_time` | datetime | 是 | 业务记录首次出现时间 |
| `effective_time` | datetime/date | 是 | 业务事实生效时间 |
| `expire_time` | datetime/date/null | 是 | 业务事实失效时间 |
| `status` | string | 是 | Domain 认可的业务状态 |
| `is_current` | boolean | 是 | 是否属于当前有效事实 |
| `change_type` | enum | 是 | `NEW / CHANGED / UNCHANGED / MISSING / CONFLICT` |
| `quality_score` | number | 是 | `0-100` 数据质量评分 |
| `quality_issues` | array | 是 | 缺失、格式、冲突、时效等问题 |
| `admission_status` | enum | 是 | 记录级生产准入状态 |
| `supersedes_record_id` | string/null | 是 | 替代的上一版本记录 |
| `import_id` | string | 是 | 导入批次 ID |

`record_id` 由稳定业务键生成；`source_row` 只用于追溯，不能作为跨版本身份的唯一依据。

## 三、Excel 全 Sheet 分析

### 3.1 强制扫描规则

每次导入必须：

1. 打开工作簿并枚举全部 Sheet。
2. 记录 Sheet 顺序与可见性。
3. 识别实际数据区域，排除纯格式空行空列。
4. 识别表头候选、合并单元格、公式、隐藏行列和重复表头。
5. 提取全部字段及标准字段候选。
6. 扫描日期字段并形成业务时间范围。
7. 基于结构和数据内容判断用途，禁止仅根据文件名判断。
8. 输出每个 Sheet 的分类证据、置信度和准入结论。

禁止：

- 默认只读第一个 Sheet。
- 因 Sheet 隐藏而跳过分析。
- 根据文件名直接认定 Domain。
- 将合计行、标题行、备注行当成业务记录。
- 将公式结果和原始事实混为一条记录。

### 3.2 用途判定证据

用途判定至少综合以下证据：

- 字段组合，例如合同号、客户、金额、房号、入住日期。
- 数据类型与值域。
- 日期范围及是否覆盖当前业务日。
- 状态字段及生命周期终态比例。
- 公式密度、合计行、透视结构。
- 与上一版本 Sheet 的结构相似度。
- 与已登记 Data Adapter Version 的映射兼容度。
- 业务 owner 已确认的 Sheet Registry。

文件名和 Sheet 名只作为辅助证据，不得单独决定准入。

### 3.3 Sheet Registry

经确认的 Sheet 用途登记到 `Sheet Registry`：

| 字段 | 说明 |
|---|---|
| `source_system` | 来源系统或维护团队 |
| `workbook_pattern` | 工作簿标识，不作为唯一判断 |
| `sheet_signature` | 字段与结构签名 |
| `approved_usage_class` | 已确认用途 |
| `target_truth_source` | 目标事实源 |
| `owner_emp_id` | 数据 owner |
| `mapping_version` | 对应映射版本 |
| `approved_at` | 确认时间 |

结构签名发生变化时，原登记不能静默沿用，必须进入 `REVIEW_REQUIRED`。

## 四、Current 与 Historical 分离

### 4.1 当前事实判定

`is_current=true` 必须同时满足：

1. 来源 Sheet 为 `CURRENT_PRODUCTION`。
2. 记录已通过必填、类型、值域、关联与时间校验。
3. `effective_time` 已生效。
4. `expire_time` 为空或晚于当前业务时间。
5. 状态不是该 Domain 的结束、退款、失效或归档状态。
6. 不存在更新且已获准生效的同业务键版本。
7. 不处于 `CONFLICT` 或 `REVIEW_REQUIRED`。

任何条件不满足时，不得由页面或 Adapter 自行推定为当前数据。

### 4.2 存储分区

Truth Source 内必须区分：

```text
current_records     # 仅 admission_status=ADMITTED 且 is_current=true
historical_records  # 已失效、已结束或被替代的可追溯事实
quarantine_records  # 未确认、异常、冲突、被拒绝记录
```

首页、经营指标和实时 AI Context 只读取 `current_records`。

历史查询读取 `historical_records`，并明确历史版本与有效时间。

`quarantine_records` 只能进入数据治理报告和授权审核视图，不能进入生产经营页面、Metrics 或 AI Context。

### 4.3 版本替代

记录发生有效修改时：

1. 原记录保留，设置 `is_current=false` 与 `expire_time`。
2. 新记录生成新版本，保留稳定业务 `record_id` 或业务主键关联。
3. 新记录通过质量门槛后设置 `is_current=true`。
4. 使用 `supersedes_record_id` 保留版本链。
5. 禁止原地覆盖导致历史丢失。

## 五、四大核心数据质量规则

### 5.1 销售

销售记录必须分类为：

- 当前有效合同。
- 历史成交。
- 退款。
- 结束客户。

核心校验：

| 规则 | 说明 |
|---|---|
| 合同唯一性 | 合同号或稳定业务组合不能产生两个当前版本 |
| 客户身份 | 客户标识、姓名及联系方式不得形成明显冲突 |
| 金额一致性 | 合同金额、退款金额、已收与未收关系必须可解释 |
| 生命周期 | 线索、签约、成交、退款、结束状态必须符合顺序 |
| 当前判定 | 退款完成、合同结束、客户结束不得继续作为当前有效合同 |
| 来源完整 | 必须保留文件、Sheet、行号和版本 |

销售 Truth Source 只接收通过校验的当前合同和合规历史记录；退款不能被当作新增成交。

### 5.2 财务

财务记录必须分类为：

- 当前资金状态。
- 历史流水。
- 收入。
- 支出。
- 待收。
- 待付。

核心校验：

| 规则 | 说明 |
|---|---|
| 流水唯一性 | 日期、金额、方向、对方、凭证等稳定组合不得重复入账 |
| 借贷方向 | 收入与支出、应收与应付不得混淆 |
| 金额有效 | 金额必须为有效数值，负数必须有明确业务语义 |
| 状态闭环 | 待收转已收、待付转已付必须形成版本或关联链 |
| 汇总隔离 | 日报合计、月度合计只用于对账，不生成基础流水 |
| 余额校验 | 期初、流入、流出、期末差异超阈值时进入冲突区 |

当前资金状态是可重建的当前视图；历史流水保留原始不可变事实。两者不可混作同一记录集合。

### 5.3 房态

房态记录必须区分：

- 当前房态。
- 历史房态变化。

核心校验：

| 规则 | 说明 |
|---|---|
| 房间主数据 | 房号必须存在于 Room Master Data |
| 当前唯一 | 每个房间只能有一个 `is_current=true` 状态 |
| 状态值域 | 只允许 Room 生命周期定义状态 |
| 占用关联 | `OCCUPIED` 必须关联有效 Stay 和客户 |
| 预留关联 | `RESERVED` 必须关联计划或预订依据 |
| 资源冲突 | 同一时间段不能分配给多个互斥 Stay |
| 变化留痕 | 状态变化生成历史版本，不覆盖前态 |

当前房态进入首页；房态变化进入历史轨迹与异常检测。

### 5.4 签约客户

签约客户记录必须分类为：

- 当前客户。
- 历史客户。
- 入住计划。
- 已结束客户。

核心校验：

| 规则 | 说明 |
|---|---|
| 客户去重 | 同一客户的稳定身份不能重复形成当前客户 |
| 合同关联 | 签约客户必须关联有效销售合同或明确例外原因 |
| 入住计划 | 预计入住、预产期、套餐等时间关系需合理 |
| Stay 关联 | 已入住客户必须关联 Stay；已结束 Stay 不得继续标记当前在住 |
| 结束判定 | 出馆、合同结束或退款完成后转历史或结束状态 |
| 来源完整 | 保留来源文件、Sheet、行号、版本及关联合同 |

签约客户事实不等于当前在住；只有满足 Stay 当前规则的记录才能进入首页在住口径。

## 六、人工 Excel 变化处理

### 6.1 稳定匹配键

变化检测优先使用 Domain 业务主键：合同号、流水号、房号、Stay ID、客户 ID。无显式主键时，只能使用经批准的复合键，并记录匹配规则版本。

禁止使用 Excel 行号作为跨版本唯一匹配键，因为员工插入、排序或删除行会改变行号。

### 6.2 变化类型

| 类型 | 判定 | 处理 |
|---|---|---|
| `NEW` | 新业务键首次出现 | 通过质量校验后新增当前或历史记录 |
| `CHANGED` | 同业务键内容指纹变化 | 保留旧版本，生成候选新版本；通过后替代 |
| `UNCHANGED` | 业务键和内容指纹均未变化 | 不重复写入，只更新导入观测记录 |
| `MISSING` | 上批当前记录本批未出现 | 不自动删除；进入待确认区 |
| `CONFLICT` | 同批或跨来源给出互斥事实 | 隔离，不进入当前 Truth Source |

### 6.3 Missing 处理

Excel 中消失不等于业务删除。`MISSING` 记录必须：

1. 保持原当前状态，或按已批准的来源策略标记待确认。
2. 生成缺失异常。
3. 等待数据 owner 确认是删除、结束、迁移还是漏录。
4. 确认后再设置 `expire_time` 和 `is_current=false`。

禁止因某一批文件缺行而自动删除生产事实。

### 6.4 Conflict 处理

发生以下情况之一视为冲突：

- 同一合同存在互斥金额或状态。
- 同一流水在两个来源中方向不同。
- 同一房间同一时间存在多个当前占用。
- 同一客户同时被标为在住与已结束。
- 新文件结构与已批准映射不兼容。

冲突记录进入 `quarantine_records`，并生成质量报告与 Audit，不进入生产页面。

## 七、生产准入机制

### 7.1 准入状态

| 状态 | 含义 |
|---|---|
| `ADMITTED_CURRENT` | 允许写入当前事实区 |
| `ADMITTED_HISTORICAL` | 允许写入历史事实区 |
| `EXCLUDED_SUMMARY` | 汇总数据，仅用于对账 |
| `EXCLUDED_AUXILIARY` | 辅助计算，不作为事实 |
| `EXCLUDED_NOTES` | 说明性内容 |
| `REVIEW_REQUIRED` | 用途或时效无法确认 |
| `QUARANTINED` | 存在异常或冲突 |
| `REJECTED` | 不符合生产质量规则 |

### 7.2 准入门槛

进入 `OMS_TRUTH_SOURCE` 前必须满足：

- 全 Sheet 分析完成，数量与工作簿一致。
- Sheet 用途已确认，不是 `UNCONFIRMED`。
- 来源元数据完整。
- 必填字段、类型、值域和业务关联通过。
- Current/Historical 判定完成。
- 增改删冲突检测完成。
- Adapter 与 mapping version 已登记且兼容。
- 质量报告已生成。
- Audit 与 Event 已写入。

质量评分不能替代硬性门槛。关键字段缺失、业务冲突或用途未确认时，即使总分较高也不能准入。

### 7.3 原子发布

生产事实源更新采用批次原子发布：

```text
candidate build
  -> quality validation
  -> diff review
  -> admission decision
  -> versioned snapshot
  -> atomic activate
```

失败批次不得部分覆盖当前 Truth Source。上一已生效版本必须保留并可回滚。

## 八、数据质量报告

每次 Excel 导入必须生成：

```text
《<原文件名>数据质量报告》
```

报告至少包含：

1. 文件身份：文件名、哈希、版本、修改时间、导入时间、导入人。
2. Sheet 清单：Sheet 名、可见性、行数、列数、字段、时间范围。
3. Sheet 用途：分类、业务用途、判定证据、置信度。
4. 字段检查：缺失字段、重复字段、类型和值域异常。
5. 当前/历史判断：当前数、历史数、无法判断数。
6. 变化检测：新增、修改、未变化、缺失、冲突数量。
7. 异常记录：记录 ID、来源行、问题、风险等级。
8. 排除记录：汇总、辅助、备注、拒绝和隔离数量及原因。
9. Truth Source 准入：当前准入数、历史准入数、隔离数、拒绝数。
10. 版本信息：Adapter ID、source version、mapping version、目标 Domain。
11. 审核结论：`ADMISSIBLE / PARTIALLY_ADMISSIBLE / REVIEW_REQUIRED / REJECTED`。

报告必须可从 Truth Source 批次、Domain 记录和页面追溯入口反向定位。

## 九、Audit 与 Event

### 9.1 Audit

必须记录：

- `data_quality.import.request`
- `data_quality.sheet.analyzed`
- `data_quality.record.evaluated`
- `data_quality.change.detected`
- `data_quality.admission.completed`
- `data_quality.admission.rejected`

Audit 至少包含：`actor_emp_id`、`import_id`、`source_file_hash`、`source_sheet`、`record_id`、`quality_status`、`admission_status`、`reason`、`correlation_id`。

### 9.2 Event

必须发布：

- `data_quality.analysis.completed`
- `data_quality.review.required`
- `data_quality.conflict.detected`
- `data_quality.truth_source.admitted`
- `data_quality.truth_source.rejected`

Event 只表达质量事实，不自动修改业务状态、不触发业务执行。

## 十、与既有系统的职责边界

| 层 | 职责 | 禁止 |
|---|---|---|
| Data Quality Layer | 识别、分类、时效判断、变化检测、准入 | 不映射页面，不执行业务 |
| Truth Source | 保存已准入的当前、历史及隔离版本 | 不接受未审数据 |
| Production Data Adapter | 将已准入事实映射为 Domain Contract | 不重新判断数据真假或当前性 |
| Domain | 表达标准业务实体和规则 | 不读取原始 Excel |
| API | 只读输出 Domain 与查询结果 | 不拼接未准入原始数据 |
| Page | 展示与查询 | 不计算事实、不推断当前状态 |
| AI Context | 读取授权且已准入的数据 | 不读取隔离、未确认或原始 Excel |

Data Adapter Version 管理继续保留：

- `adapter_id`
- `source_system`
- `source_version`
- `target_domain`
- `mapping_version`
- `last_sync_time`

新增要求：只有与已批准 Sheet 结构签名兼容的 Adapter 版本，才能消费已准入批次。

## 十一、页面与 AI 准入规则

以下入口只允许读取 `ADMITTED_CURRENT` 且 `is_current=true` 的 Domain 数据：

- 首页工作台。
- 销售中心当前经营视图。
- 财务中心当前资金视图。
- 运营中心当前入住和房态视图。
- 实时 Metrics 与 Dashboard Query。
- 实时 AI Context。

历史页面只允许读取 `ADMITTED_HISTORICAL`，并显示有效时间、来源版本及替代链。

以下数据全部禁止进入页面和 AI Context：

- `UNCONFIRMED` Sheet。
- `REVIEW_REQUIRED` 记录。
- `QUARANTINED` 冲突记录。
- 汇总表冒充基础事实。
- 辅助计算表。
- 备注说明表。
- 未生成数据质量报告的导入批次。

## 十二、失败与恢复策略

- 单个 Sheet 分析失败：整个工作簿不得标记为完全准入；允许其他独立 Sheet 形成候选结果，但必须标记 `PARTIALLY_ADMISSIBLE`。
- 质量报告生成失败：批次不得发布。
- Truth Source 写入失败：保留上一生效版本，不允许半写入。
- Adapter 版本不兼容：批次进入 `REVIEW_REQUIRED`。
- 冲突未解决：相关记录保持隔离，不影响上一已确认当前事实。
- 原始文件必须只读保存，禁止在质量处理过程中修改。

## 十三、验收标准

P0.12 后续实现必须满足：

1. 任意 Excel 的全部 Sheet 均有分析记录。
2. 每个 Sheet 均有行列数、字段、时间范围、用途与分类。
3. 未确认用途的数据进入生产 Truth Source 数量为 0。
4. 每条准入记录具备完整来源、时间、状态和 `is_current`。
5. 首页只消费 `is_current=true` 数据。
6. 历史记录可查询且不会污染实时指标。
7. 新增、修改、缺失和冲突可被稳定识别。
8. Missing 不触发自动删除，Changed 不覆盖历史。
9. 每批导入均生成数据质量报告、Audit 和 Event。
10. 未经 Data Quality Layer 的数据无法进入页面、Metrics 或 AI Context。

## 十四、设计结论

P0.12 将 OMS 的生产链路冻结为：

```text
Excel
-> Data Quality Layer
-> versioned OMS_TRUTH_SOURCE
-> Production Data Adapter
-> Domain
-> API Contract
-> Page / AI Context
```

核心原则：

```text
先识别，再校验；
先区分当前与历史，再准入；
变化留痕，不覆盖；
用途未确认，不进入生产。
```
