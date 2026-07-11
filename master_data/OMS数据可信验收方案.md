# OMS 数据可信验收方案

阶段：P0.13.3 OMS Data Trust Acceptance

状态：上线前验收方案

## 一、验收目标

本方案用于证明：OMS 中每一个经营数字和每一条当前经营记录，都可以回溯到经确认的 Excel 原始来源，并且在 Data Quality、Truth Source、Adapter、Domain、API 和老板端之间没有数量、金额、状态或语义漂移。

验收链路：

```text
Excel 原始文件与单元格
  -> Data Quality Layer 分析与准入
  -> versioned OMS_TRUTH_SOURCE
  -> Production Data Adapter
  -> Domain
  -> API Contract
  -> 老板端经营数字或明细
```

本次验收不假设：

- Excel 内容正确。
- 第一个 Sheet 就是生产数据。
- Adapter 映射正确。
- 汇总行等于基础事实之和。
- Truth Source 记录数正确。
- 页面显示值等于 API 或 Domain 值。

验收必须用独立计算和原始证据证明一致性。

## 二、上线 Gate

在以下四个数据域全部达到 `PASS` 前，OMS 不得进入正式上线：

1. 销售。
2. 财务。
3. 房态。
4. 签约客户。

`WARNING` 不等于通过，只允许继续治理和复验；`FAIL` 必须阻断生产发布。

```text
production_release_allowed =
  sales_health == PASS
  AND finance_health == PASS
  AND room_health == PASS
  AND contract_customer_health == PASS
  AND overall_trace_coverage == 100%
```

## 三、验收范围与候选基线

当前系统观察值只作为待核对候选，不作为真值：

| 数据域 | 候选来源 | 当前候选基线 | 正式验收要求 |
|---|---|---:|---|
| 销售 | 最新经批准销售 Excel | 销售记录数及销售总额待独立重算 | 总额一致，抽查 20 条 |
| 财务 | 最新经批准财务 Excel | 收入、支出、利润待独立重算 | 收入、支出、利润一致，抽查 20 条 |
| 房态 | 最新经批准房态 Excel | 42 个房间 | 42 房一致，抽查 10 条 |
| 签约客户 | 最新经批准签约客户 Excel | 148 条 | 148 条一致，抽查 20 条 |

验收开始前必须冻结每个来源的：

- 文件完整名称与路径。
- 文件 SHA-256。
- 文件版本与最后修改时间。
- 全部 Sheet 清单。
- 被批准用于生产的 Sheet。
- Data Quality Report ID。
- Adapter ID 与 mapping version。
- Truth Source snapshot version。

验收过程中来源文件发生变化时，本轮验收立即失效，必须基于新哈希重新开始。

## 四、验收证据模型

### 4.1 单条记录证据链

每条被抽查或进入当前经营口径的记录，必须具备：

```text
display_value / metric_value
  -> api_field
  -> domain_record_id
  -> truth_source_record_id
  -> adapter_result_id
  -> quality_import_id
  -> source_file_hash
  -> source_sheet
  -> source_row
  -> source_columns / source_cells
```

最低追溯字段：

| 字段 | 必填 | 说明 |
|---|---:|---|
| `record_id` | 是 | 稳定记录 ID |
| `source_file` | 是 | Excel 文件名 |
| `source_file_hash` | 是 | 文件哈希 |
| `source_sheet` | 是 | 实际 Sheet 名 |
| `source_row` | 是 | 原始行号 |
| `source_columns` | 是 | 使用的原始列名 |
| `source_cells` | 是 | 关键值对应单元格地址 |
| `source_version` | 是 | 来源版本 |
| `quality_report_id` | 是 | 数据质量报告 |
| `admission_status` | 是 | 当前或历史准入结论 |
| `adapter_id` | 是 | Adapter 标识 |
| `mapping_version` | 是 | 映射版本 |
| `domain_record_id` | 是 | Domain 记录 ID |
| `api_contract_version` | 是 | API 契约版本 |

任何当前经营记录缺少上述关键追溯字段，所在数据域直接判定为 `FAIL`。

### 4.2 指标证据链

每个经营指标必须保存：

- 指标名称与业务定义。
- 纳入条件与排除条件。
- 计算公式。
- 计算时间与业务时区。
- Truth Source snapshot version。
- 参与计算的 record_id 列表或可重放查询条件。
- 原始 Excel 独立重算值。
- Domain/API 计算值。
- 页面显示值。
- 三者差异。

页面不得只显示最终数字而无法展开参与计算的记录。

## 五、验收环境与独立性

### 5.1 三份独立结果

每个总量必须至少生成三份独立结果：

1. Excel 基准值：由验收工具直接读取已冻结原始文件全部批准 Sheet 计算。
2. Truth Source/Domain 值：从已准入 snapshot 计算。
3. API/页面值：从生产 API 返回并核对老板端显示。

Adapter 自己生成的汇总不能作为 Excel 独立基准，否则属于用同一逻辑证明自己。

### 5.2 只读原则

验收过程：

- 不修改原始 Excel。
- 不修改 Truth Source。
- 不修正 Adapter 输出。
- 不手工补页面数字。
- 不删除异常记录。
- 只读取、计算、比对和记录问题。

发现差异后生成 Issue，等待统一修复与复验。

## 六、全 Sheet 前置验收

四个数据域进入业务对账前，必须先通过 Excel 全 Sheet 检查：

1. Sheet 实际数量等于 Data Quality Report 中数量。
2. 每个 Sheet 均有行数、列数、字段、时间范围和用途分类。
3. 生产 Sheet 明确标记为 `CURRENT_PRODUCTION`。
4. 历史、汇总、辅助计算、备注 Sheet 均未混入当前口径。
5. 隐藏 Sheet 已分析。
6. 合计行、标题行、空白格式行未被当作基础记录。
7. 未确认用途的 Sheet 进入当前 Truth Source 数量为 0。

任何一项不满足，对应数据域不得继续判定为 PASS。

## 七、销售可信验收

### 7.1 业务口径

销售总额定义为：在验收业务时点仍属于销售统计口径的有效销售/合同记录金额之和。

必须明确：

- 当前有效合同是否计入。
- 历史成交是否仅进入历史分析。
- 退款金额如何冲减。
- 已结束或作废客户是否排除。
- 重复合同如何识别。
- 空金额和负金额如何处理。

上述规则必须由销售负责人、财务复核和主理人确认后冻结为验收公式，禁止验收人员临时解释。

### 7.2 总额对账

分别计算：

```text
excel_sales_total
truth_source_sales_total
domain_sales_total
api_sales_total
page_sales_total
```

同时计算：

- Excel 符合口径的记录数。
- Truth Source 当前销售记录数。
- Domain 销售记录数。
- API 返回 `total`。
- 页面显示总数。

验收条件：

- 五层销售总额精确到人民币分一致。
- 五层记录数一致。
- 退款、作废、结束和重复记录的排除清单一致。
- 参与总额的每条记录可追溯到 Excel 单元格。

### 7.3 抽查 20 条

采用固定随机种子进行分层随机抽样，抽样名单必须在读取 OMS 结果前生成并固化。

建议分层：

- 当前有效合同 10 条。
- 历史成交 4 条。
- 退款/结束/作废 3 条；不足时全部抽取并补到当前有效合同。
- 高金额前 10% 中抽 3 条。

每条核对：

- 客户姓名或稳定客户 ID。
- 合同号。
- 签约日期。
- 合同金额。
- 销售人员。
- 销售/合同状态。
- 是否计入销售总额。
- Excel 文件、Sheet、行号、关键单元格。
- Truth Source、Domain、API 和页面值。

20 条关键字段必须全部一致；任一金额、合同号、状态或归属错误即为 `FAIL`。

## 八、财务可信验收

### 8.1 业务口径

财务验收必须独立区分：

- 收入。
- 支出。
- 利润。
- 待收。
- 待付。
- 历史流水。
- 当前资金状态。

利润计算公式必须冻结。基础验收默认：

```text
profit = confirmed_income - confirmed_expense
```

若存在税费、退款、内部划转、押金或非经营性收支，必须在公式中显式列出，不能临时归类。

### 8.2 总额对账

分别计算：

```text
excel_income / truth_income / domain_income / api_income / page_income
excel_expense / truth_expense / domain_expense / api_expense / page_expense
excel_profit / truth_profit / domain_profit / api_profit / page_profit
```

同时对账：

- 财务基础流水数量。
- 收入记录数量。
- 支出记录数量。
- 待收记录与金额。
- 待付记录与金额。
- 退款和内部划转排除/归类清单。

验收条件：

- 收入、支出、利润精确到人民币分一致。
- 各分类记录数一致。
- 利润可由已确认收入与支出重算。
- 汇总 Sheet 只作交叉校验，不替代基础流水。
- 不存在同一流水重复计入。

### 8.3 抽查 20 条

采用固定随机种子分层抽样：

- 收入 8 条。
- 支出 8 条。
- 待收 2 条。
- 待付 2 条。

若某类不足，则全部抽取并从收入/支出补足，但必须在报告中说明。

每条核对：

- financial_event_id / tx_id。
- 发生日期。
- 收支方向。
- 金额。
- 对方或业务对象。
- 支付/确认状态。
- 关联客户、合同或费用依据。
- 是否参与收入、支出、利润、待收或待付指标。
- Excel 文件、Sheet、行号和关键单元格。
- Truth Source、Domain、API 与页面值。

20 条中任一方向、金额、状态或重复性错误即为 `FAIL`。

## 九、房态可信验收

### 9.1 数量与唯一性

验收基准：42 个房间。

必须证明：

- Excel 房间主数据中存在 42 个唯一房号。
- Truth Source 当前 Room 有 42 个唯一 `room_id`。
- Domain 有 42 个当前 Room。
- API `total=42`。
- 老板端显示 42，并可访问全部 42 条。

房间数量一致还不够，必须同时验证：

- 每个房号唯一。
- 每个房间只有一个 `is_current=true` 状态。
- 状态属于 Room 生命周期允许值。
- `OCCUPIED` 与当前 Stay 一致。
- `RESERVED` 有有效预订或入住计划依据。

### 9.2 抽查 10 条

采用状态分层随机抽样：

- OCCUPIED 至少 3 条。
- RESERVED 至少 2 条。
- AVAILABLE 至少 2 条。
- CLEANING / MAINTENANCE / DISABLED 如存在至少各 1 条。
- 不足部分从其他状态随机补齐到 10 条。

每条核对：

- 房号。
- 房型。
- 当前状态。
- 当前客户。
- 关联 Stay。
- 入住/预计出馆时间。
- `is_current`。
- Excel 文件、Sheet、行号和关键单元格。
- Truth Source、Domain、API 和页面值。

任何房号缺失、重复、状态错误或占用关系不一致即为 `FAIL`。

## 十、签约客户可信验收

### 10.1 数量与分类

验收基准：148 条签约客户记录。

必须先明确这 148 条的口径：

- 当前客户数量。
- 历史客户数量。
- 入住计划数量。
- 已结束客户数量。
- 是否一名客户可有多份合同。
- 客户记录数与合同记录数是否不同。

验收条件：

- Excel 按冻结口径重算为 148 条。
- Truth Source 中对应准入记录为 148 条。
- Domain、API `total` 与页面可访问记录均为 148 条。
- 当前与历史分类合计等于 148，且分类互斥或有明确多标签规则。
- 客户与合同、入住计划的关联可追溯。

若 Excel 独立重算不等于 148，不能为满足目标而修改筛选条件；必须判定差异并进入 Issue。

### 10.2 抽查 20 条

采用分类分层随机抽样：

- 当前有效客户 8 条。
- 入住计划 4 条。
- 历史客户 4 条。
- 已结束/退款客户 4 条。

不足类别全部抽取后，从当前有效客户补足。

每条核对：

- customer_id。
- 客户姓名。
- contract_id。
- 合同状态与金额。
- 客户状态。
- 预计入住日期/预产期。
- 实际 Stay 关联（如适用）。
- 是否属于当前经营口径。
- Excel 文件、Sheet、行号和关键单元格。
- Truth Source、Domain、API 和页面值。

20 条关键字段、分类和关联必须全部一致。

## 十一、抽样控制

### 11.1 可复现抽样

每次抽样必须记录：

- `acceptance_run_id`。
- 数据源文件哈希。
- 候选记录 ID 排序规则。
- 随机算法。
- 固定 seed。
- 分层规则。
- 生成时间。
- 抽样人 EMP。

禁止人工挑选“看起来正确”的记录。

### 11.2 抽样不替代全量校验

以下项目必须全量检查，不能只抽样：

- 记录数。
- 金额汇总。
- record_id 唯一性。
- 当前记录追溯字段完整率。
- 当前/历史分类。
- 重复与冲突。
- `is_current` 唯一性。

抽样用于验证字段映射与人工可读证据链，不替代全量机器对账。

## 十二、数据健康状态

### 12.1 单项状态

| 状态 | 判定标准 | 生产影响 |
|---|---|---|
| `PASS` | 数量、金额、分类、关键字段、抽样和追溯全部通过；关键追溯覆盖率 100% | 该数据域具备上线资格 |
| `WARNING` | 总量和金额一致，关键记录可追溯，但存在不影响经营口径的可选字段缺失、接近过期或非关键说明问题 | 允许治理和复验，不计入正式上线通过 |
| `FAIL` | 数量/金额不一致、关键字段错误、当前/历史混用、抽样关键项失败、任何当前记录不可追溯、来源或映射未确认 | 阻断上线 |

### 12.2 直接 FAIL 条件

出现任一情况直接 `FAIL`：

- Excel 文件或 Sheet 未冻结。
- 有 Sheet 未分析或用途未确认却进入生产。
- 销售总额不一致。
- 财务收入、支出或利润任一不一致。
- 房间不是 42 个唯一当前房间。
- 签约客户按冻结口径不是 148 条或链路中数量不一致。
- 抽样记录关键字段不一致。
- 当前经营记录无法定位 Excel 文件、Sheet、行和关键单元格。
- Adapter 丢失、重复或改变业务含义。
- 页面值与 API 值不一致。
- Conflict 记录进入当前经营口径。

### 12.3 总体状态

总体状态采用最差项原则：

```text
任何数据域 FAIL -> overall FAIL
无 FAIL 但存在 WARNING -> overall WARNING
全部 PASS -> overall PASS
```

正式上线要求 `overall=PASS`。

### 12.4 Data Health Score

除离散健康状态外，每个数据域和全局必须生成 `0-100` 的 Data Health Score，供老板首页查看整体数据健康。

| 维度 | 权重 | 计算依据 |
|---|---:|---|
| 完整性 | 25 | 必填字段完整率、全 Sheet 分析覆盖率、当前记录必要元数据完整率 |
| 一致性 | 30 | Excel、Truth Source、Domain、API、页面的数量、金额、状态和关联一致率 |
| 时效性 | 15 | 距离最近成功导入时间是否满足该数据源 update_frequency / SLA |
| 追溯性 | 25 | 当前记录可回到文件、Sheet、行、关键单元格的完整率 |
| 异常数量 | 5 | 未解决 WARNING、FAIL、MISSING、CONFLICT 的数量与严重度 |

计算公式：

```text
data_health_score =
  completeness_score
  + consistency_score
  + timeliness_score
  + traceability_score
  + anomaly_score
```

各维度得分不得超过对应权重，保留两位小数。评分明细必须保存分子、分母、扣分项和计算时间，禁止只保存最终总分。

异常分初始为 5 分，按未关闭异常扣减：

- Critical：每条扣 5 分。
- High：每条扣 2 分。
- Medium：每条扣 0.5 分。
- Low：每条扣 0.1 分。
- 最低为 0 分。

分数与状态映射：

| 分数 | 候选状态 | 附加条件 |
|---:|---|---|
| `95-100` | PASS | 不存在直接 FAIL 条件，且关键追溯覆盖率 100% |
| `80-94.99` | WARNING | 不存在直接 FAIL 条件 |
| `<80` | FAIL | 阻断上线 |

硬性规则优先于评分：任何“直接 FAIL 条件”成立时，即使计算分数高于 95，也必须将状态强制为 `FAIL`，并记录 `hard_fail_override=true`。

全局分数采用四个数据域等权平均：

```text
overall_data_health_score =
  (sales_score + finance_score + room_score + contract_customer_score) / 4
```

全局状态仍采用最差项原则，不能用平均分掩盖单一数据域失败。

老板首页应显示：总分、总体状态、四域分数、最近计算时间、当前生效的 Truth Source Snapshot Version 和未关闭异常数量。

### 12.5 Truth Source 验收快照版本

每次正式数据可信验收必须生成不可变 Truth Source Snapshot Version：

```text
TS-YYYYMMDD-Vn
```

其中 `YYYYMMDD` 为验收业务日期，`Vn` 为当天从 1 开始递增的验收版本。例如：`TS-20260710-V1`。

每个快照必须记录：

| 字段 | 说明 |
|---|---|
| `snapshot_version` | `TS-YYYYMMDD-Vn` |
| `acceptance_run_id` | 对应正式验收批次 |
| `created_at` | 快照生成时间 |
| `created_by_emp_id` | 生成快照的真实 EMP |
| `source_files` | 文件名、文件版本、SHA-256、修改时间 |
| `source_sheets` | 获准使用的 Sheet 与分类 |
| `import_ids` | 对应 Data Quality 导入批次 |
| `imported_at` | 各来源导入时间 |
| `quality_report_ids` | 对应数据质量报告 |
| `quality_results` | 各数据域质量结论与问题数量 |
| `adapter_versions` | Adapter ID、source version、mapping version |
| `truth_source_record_counts` | 当前、历史、隔离记录数量 |
| `metric_values` | 本轮验收的销售、财务、房态、签约客户关键指标 |
| `data_health_scores` | 各域与全局五维评分 |
| `acceptance_result` | PASS / WARNING / FAIL |
| `hard_fail_reasons` | 直接失败原因 |
| `previous_snapshot_version` | 上一快照版本 |
| `activated_for_production` | 是否成为生产当前版本 |

正式验收无论通过或失败都生成快照，以保留当时证据。只有 `acceptance_result=PASS` 的快照允许设置 `activated_for_production=true`。

快照一旦生成：

- 禁止原地修改。
- 禁止复用版本号。
- 禁止删除失败快照。
- 原始来源变化后必须生成新快照。
- 页面指标和追溯结果必须携带当前生效快照版本。

上线后可通过快照证明：某个时间点老板看到的是哪一批文件、哪次导入、哪组质量结果和哪组经营指标。

## 十三、老板端数据来源追溯入口

### 13.1 入口位置

老板端必须提供两级只读追溯入口：

1. 指标追溯：在首页经营数字和中心汇总数字旁提供“查看来源”。
2. 记录追溯：在销售、财务、房态、签约客户每条明细提供“来源与处理链”。

追溯入口是数据可信验收的必要条件，不是新增录入页面。

### 13.2 指标追溯内容

点击经营数字后显示：

- 指标业务定义。
- 当前显示值。
- 计算公式。
- 统计时点。
- Truth Source snapshot version。
- 纳入记录数量。
- 排除记录数量及原因。
- Data Quality 状态。
- 最近验收状态与时间。
- 可下钻的参与记录列表。

### 13.3 记录追溯内容

点击单条记录后显示：

```text
页面记录
  -> API 字段
  -> Domain 记录
  -> Truth Source 版本
  -> Adapter 与 mapping version
  -> Data Quality Report
  -> Excel 文件
  -> Sheet
  -> 行号
  -> 关键单元格和值
```

同时显示：

- 当前/历史状态。
- NEW / CHANGED / MISSING / CONFLICT 状态。
- 责任 Owner、Reviewer、Publisher 的 EMP。
- Audit correlation_id。

### 13.4 权限与安全

- 追溯入口只读。
- 老板可查看全域来源。
- 普通角色只查看授权 Domain 与记录。
- 原始 Excel 只提供受控预览，不允许从追溯页修改。
- 敏感身份和财务字段按权限脱敏。
- 每次追溯查询写 Audit。

## 十四、验收操作顺序

### 场景 0：来源冻结

1. 登记四类来源文件。
2. 计算 SHA-256。
3. 导出全部 Sheet 清单。
4. 锁定 Data Quality Report 与 mapping version。
5. 创建 `acceptance_run_id`。
6. 预分配本次 `TS-YYYYMMDD-Vn` 快照版本。

### 场景 1：全量结构与追溯检查

1. 验证全部 Sheet 分析完成。
2. 验证当前/历史/隔离分类。
3. 验证记录唯一性。
4. 验证当前记录追溯字段完整率为 100%。

### 场景 2：四域总量对账

1. 销售总额与记录数五层对账。
2. 财务收入、支出、利润与分类数量五层对账。
3. 房态 42 房五层对账。
4. 签约客户 148 条五层对账。

### 场景 3：分层随机抽查

1. 固化随机 seed 与样本名单。
2. 销售抽查 20 条。
3. 财务抽查 20 条。
4. 房态抽查 10 条。
5. 签约客户抽查 20 条。
6. 保存 Excel 单元格与 OMS 各层对照证据。

### 场景 4：老板端追溯

1. 从首页每个经营数字进入指标追溯。
2. 从四个数据域各打开至少 3 条记录追溯。
3. 验证能到达 Excel 文件、Sheet、行和关键单元格。
4. 验证页面只读和权限正确。

### 场景 5：健康状态与发布决定

1. 计算每个数据域 PASS/WARNING/FAIL。
2. 计算每个数据域五维 Data Health Score。
3. 汇总所有差异和 Issue。
4. 按四域等权平均计算全局分数，按最差项规则计算总体状态。
5. 生成不可变 Truth Source 验收快照。
6. 只有总体 PASS 才激活快照并签署上线许可。

## 十五、验收输出

正式执行后必须生成：

```text
《OMS数据可信验收报告》
```

附件至少包含：

- 来源文件清单与哈希。
- 全 Sheet 分析结果。
- 四域总量对账表。
- 销售 20 条抽查表。
- 财务 20 条抽查表。
- 房态 10 条抽查表。
- 签约客户 20 条抽查表。
- Trace Coverage 报告。
- 差异与 Issue 清单。
- 老板端追溯截图或验收证据。
- 各数据域健康状态。
- 各数据域与全局 Data Health Score 及五维评分明细。
- Truth Source Snapshot Version 与快照 manifest。
- 总体上线结论。

每个差异 Issue 必须包含：

- issue_id。
- 数据域。
- 发现层级。
- Excel 值。
- OMS 值。
- 差异。
- 来源证据。
- 责任 Owner。
- 风险等级。
- 当前状态。

## 十六、责任签署

| 数据域 | 数据 Owner | 复核人 | 质量检查人 | 最终验收人 |
|---|---|---|---|---|
| 销售 | 销售负责人 | 财务复核金额口径 | 销售质量责任人 | 主理人 |
| 财务 | 财务经办 | 财务复核 | 财务质量责任人 | 主理人 |
| 房态 | 店总 | 店总或授权第二复核人 | 店总 | 主理人 |
| 签约客户 | 销售负责人 | 财务复核金额、店总复核入住计划 | 销售质量责任人 | 主理人 |

所有签署必须使用真实 EMP 和有效 user_id，禁止姓名文本代替身份确认。

## 十七、验收标准汇总

| 验收项 | 标准 |
|---|---|
| 销售 | 总额与记录数五层一致；20/20 抽查通过；追溯覆盖 100% |
| 财务 | 收入、支出、利润与分类数量五层一致；20/20 抽查通过；追溯覆盖 100% |
| 房态 | 42 个唯一当前房间五层一致；10/10 抽查通过；状态与 Stay 一致 |
| 签约客户 | 148 条五层一致；20/20 抽查通过；客户、合同、入住计划关联正确 |
| 数据健康 | 四域均为 PASS |
| 健康评分 | 四域均不低于 95，整体分数不低于 95，且无硬失败覆盖 |
| 验收快照 | 生成不可变 `TS-YYYYMMDD-Vn`；仅 PASS 快照可激活生产 |
| 老板端追溯 | 每个指标和明细可下钻到 Excel 单元格 |
| 上线 Gate | overall=PASS，Blocking Issue=0 |

## 十八、结论

OMS 数据可信不以“页面有数字”或“API 返回成功”为依据，只以可重放、可对账、可追溯的证据链为依据。

```text
Excel 原始证据一致
  + Data Quality 准入正确
  + Truth Source 完整
  + Adapter 映射无漂移
  + Domain/API/Page 数值一致
  + 老板端可追溯
  = OMS 数据可信 PASS
```

在四个数据域全部 PASS 之前，OMS 保持上线阻断状态。
