# OMS P0.18.4阻塞项重新评估报告

评估时间：2026-07-11  
评估原则：OMS聚焦现在和未来，Historical异常保留但不阻塞Cutover。

## 一、新的数据治理原则

### Historical与Plan

目标：

- 保留原始事实与原始错误。
- 支持查询和追溯。
- 对异常记录Warning或Quarantine。
- 不因低风险历史录入错误阻塞上线。

Historical或Plan中的编号重复、字段缺失、格式错误，只要不被用于当前经营决策，即作为历史质量Warning处理。

### Current

目标：

- 数据准确。
- 责任人明确。
- 来源和操作可追溯。
- 可以支撑当日经营决策。

Current缺失、冲突或无法确认时，才构成Cutover阻塞。

## 二、P0.18.4原阻塞项重新分类

### 2.1 Sales合同号冲突

`NSEKI94131081`对应郝梓涵和王雪两条历史录入记录。

新处理：

- 两条原始记录完整保留。
- 标记`HISTORICAL_WARNING / DUPLICATE_IDENTIFIER`。
- 不合并，不覆盖，不强制Correction。
- Business Correction提案`-A/-B`保留，未来需要按合同号执行Current业务时再确认应用。
- Sales Current由OMS后续签约或确认动作产生，不从该冲突倒推。

重新评估：`NON_BLOCKING_WARNING`。

### 2.2 Finance Historical

- 470条作为Finance Historical迁移。
- Finance Current保持`NOT_INITIALIZED`。
- 历史迁移本身PASS。

重新评估：Historical迁移`NON_BLOCKING / PASS`。

但Finance Current属于当前经营事实，必须由EMP004刘晶在OMS录入，并由EMP003张敬东复核。

### 2.3 Contract Stay Plan字段缺失

- 1319条进入Plan准入集。
- 7条字段不完整记录保留来源、Sheet和行号。
- 7条标记`PLAN_WARNING / REQUIRED_FIELDS_MISSING`。
- 不补写，不推算，不生成Actual Stay。

重新评估：`NON_BLOCKING_WARNING`。

### 2.4 Actual Stay历史快照异常

来源`凰家母婴在住表最新4.13.xlsx`的表内更新时间为2026-07-02：

- 33条完整明细。
- 人工汇总30人。
- 5条缺少实际日期。

新处理：

- 该批整体作为`ACTUAL_STAY_HISTORICAL_SNAPSHOT`。
- `33 vs 30`标记历史一致性Warning。
- 5条标记Historical Warning/Quarantine。
- 不再要求修复该历史快照后才能上线。
- 该快照不得作为Cutover日Actual Stay Current。

重新评估：历史异常`NON_BLOCKING_WARNING`；Actual Stay Current缺失仍是`BLOCKING`。

## 三、迁移Snapshot门

按照新原则，V2迁移内容可以包含：

| Domain | V2迁移内容 | 状态 |
| --- | --- | --- |
| Sales | Historical 186条，其中重复编号2条Warning | 可迁移 |
| Finance | Historical 470条 | 可迁移 |
| Contract Stay Plan | Plan 1326条，其中7条Warning | 可迁移 |
| Actual Stay | 2026-07-02 Historical Snapshot，33条完整、5条不完整Warning | 可迁移 |
| Room | 42间Room Master Data及可确认Historical | 可迁移 |

注：Sales的184条无冲突记录和2条重复编号记录都作为Historical保留；不再把两条冲突从历史迁移中删除。Contract Plan的7条异常记录作为Warning保留，但不进入可执行Plan集合。

```text
historical_migration_gate = PASS_WITH_WARNINGS
v2_preparation = READY_FOR_GENERATION
```

V2必须明确区分：

- 可查询Historical/Plan记录数。
- 可执行或可准入记录数。
- Warning/Quarantine记录数。
- Current为`NOT_INITIALIZED`的Domain。

## 四、真正的Cutover阻塞项

### BLOCK-001 Finance Current

需要：

- EMP004刘晶在OMS录入Cutover期初资金状态。
- EMP003张敬东复核。
- 生成`finance.current.published`、Audit和版本。

### BLOCK-002 Room Current

需要：

- EMP008刘芳羽在OMS逐房确认42间房状态。
- 生成`room.current.published`、Audit和版本。

### BLOCK-003 Actual Stay Current

需要：

- EMP008刘芳羽在OMS确认Cutover时点真实入住。
- EMP009尚丽娜核对现场资料。
- 生成`stay.actual.published`、Audit和版本。

Sales Current不再作为Cutover前强制初始化条件。上线后由OMS销售动作逐步产生。

## 五、Semantic Memory重新分类

| Domain | 旧状态 | 新语义 |
| --- | --- | --- |
| Sales两个Sheet | TEMPORARY / Current Candidate | 应改为`Sales Historical Import`；历史编号Warning不阻塞 |
| Finance月度Sheet | CONFIRMED | `Finance Historical`，保持 |
| Contract Stay Plan | CONFIRMED | 保持；7条记录级Warning不改变Sheet语义 |
| 在住表房态表 | TEMPORARY | 可确认`Actual Stay Historical Snapshot`，不得标为Current |

语义确认不等于记录质量全部无异常，也不等于可自动生成Current。

已执行生命周期调整：

- 原2条Sales Current Candidate记忆转为`DEPRECATED`。
- 新增2条Sales Historical Import `CONFIRMED`记忆。
- Actual Stay Historical Snapshot升级为`CONFIRMED`。
- Finance与Contract Stay Plan的46条`CONFIRMED`记忆保持不变。
- 当前共51个记忆版本：49条`CONFIRMED`、2条`DEPRECATED`、0条`TEMPORARY`。
- Audit累计51条；未创建任何Current语义。

## 六、Readiness修正

| 检查项 | 原结果 | 新结果 |
| --- | --- | --- |
| Historical迁移 | BLOCKED | PASS_WITH_WARNINGS |
| Sales历史编号冲突 | BLOCKED | NON_BLOCKING_WARNING |
| Contract Plan字段缺失 | BLOCKED | NON_BLOCKING_WARNING |
| Actual Stay历史差异 | BLOCKED | NON_BLOCKING_WARNING |
| Finance Current | BLOCKED | BLOCKED |
| Room Current | BLOCKED | BLOCKED |
| Actual Stay Current | BLOCKED | BLOCKED |

## 七、当前结论

```text
TS-20260711-V1 = ACTIVE
TS-20260711-V2 = READY_FOR_GENERATION / NOT GENERATED
historical_migration = PASS_WITH_WARNINGS
current_business_facts = BLOCKED
cutover_readiness = FAIL
cutover = BLOCKED
```

本次重新评估不修改V1、不修改原始Excel、不手工修正历史数字。
