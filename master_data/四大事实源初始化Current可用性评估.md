# 四大事实源初始化Current可用性评估

## 一、评估目的

本评估判断Sales、Finance、Room、Actual Stay四个域在OMS初始化迁移阶段是否具备可直接形成Current的业务证据。

初始化阶段不强制四个域全部存在Current。无法证明Current的数据可以迁移为Historical或Plan；正式Current由Cutover后具备权限的员工在OMS中录入和维护。

## 二、评估规则

| 结果 | 定义 |
| --- | --- |
| `AVAILABLE` | 存在唯一、质量PASS且业务含义明确的Current来源，可初始化Current |
| `CONDITIONAL` | 存在Current候选，但仍需业务签认或质量问题关闭，不得直接初始化 |
| `UNAVAILABLE` | 当前文件不能证明Current，只能迁移Historical/Plan或排除 |

共同规则：

- 文件可信不等于Sheet可以进入Current。
- 禁止根据Sheet名称、记录数量或位置推断Current。
- 禁止从计划数据推算事实数据。
- `UNAVAILABLE`不等于伪造空数据，也不等于允许旧数据充当Current。
- Cutover后Current只能通过OMS权限、Domain Command、Audit和Event产生。

## 三、Sales评估

### 3.1 证据

- 来源文件：`2026年销售明细表（经验为王7.10）(1).xlsx`
- 文件状态：`SOURCE_TRUSTED`
- Data Quality：`PARTIALLY_ADMISSIBLE`
- Current候选：`2026年内店销售列表`、`2026外店上户列表`
- 候选记录：185
- Quarantine：35
- 现有生产基线：224条，尚未与185条候选完成一致性对账

### 3.2 判断

```text
initial_current_availability = CONDITIONAL
```

原因：存在两个业务候选，且质量及数量对账未关闭，当前不能创建唯一`Sales Current CONFIRMED memory`。

### 3.3 初始化策略

- 已完成业务签认且通过质量检查的记录可初始化Sales Current。
- 未签认前，可迁移为Sales Historical候选或继续隔离，不得替换现有Current。
- 排名、PV、辅助统计和备注Sheet不得作为Sales Current。
- 若Cutover前仍未完成签认，Sales Current由OMS上线后通过签约、合同和收款业务录入产生。

## 四、Finance评估

### 4.1 证据

- 来源文件：`2026年财务报表（7月）.xlsx`
- 文件状态：`SOURCE_TRUSTED`
- Data Quality：`REVIEW_REQUIRED`
- Sheet包含日报、月份流水、余额、待收、待付和汇总等混合口径
- 无唯一稳定交易标识和明确Current边界

### 4.2 判断

```text
initial_current_availability = UNAVAILABLE
```

当前文件不能证明唯一Finance Current，不得用全部流水或汇总位置推算当前资金状态。

### 4.3 初始化策略

- 可识别且可追溯的流水迁移为Finance Historical。
- 余额、待收、待付等候选在未完成业务确认前保持Review或Quarantine。
- 不创建`Finance Current CONFIRMED memory`。
- Cutover后由财务人员通过OMS录入收款、支出、待收、待付和对账结果，生成Finance Current。
- 如需Cutover期初余额，必须由财务负责人在OMS内录入并经授权确认，不得从历史流水自动倒推。

## 五、Room评估

### 5.1 证据

- 来源文件：`①凰家母婴 2021房态表June(1).xlsx`
- 文件状态：`SOURCE_TRUSTED`
- Data Quality：`REVIEW_REQUIRED`
- `Sheet1`、`Sheet3`为横向日期矩阵
- `Sheet2`为陪护人员登记，不是Room Current
- 缺少可验证的统一房态状态字段和明确业务日期

### 5.2 判断

```text
initial_current_availability = UNAVAILABLE
```

当前文件不能证明Cutover时点逐房Current状态。42个房间资源主数据不等同于42间房的当前房态。

### 5.3 初始化策略

- 房间编号等稳定资源信息可进入Room Master Data。
- 可识别的历史日期矩阵仅作为Room Historical候选。
- 不创建`Room Current CONFIRMED memory`。
- Cutover后由运营负责人在OMS逐房确认并录入`AVAILABLE / RESERVED / OCCUPIED / CLEANING / MAINTENANCE / DISABLED`状态。
- 当前房态必须由OMS Room Domain产生，禁止从历史入住或签约计划推算。

## 六、Actual Stay评估

### 6.1 证据

- 来源文件：`A  凰家母婴签约客户一览表（挤牙膏）(1).xlsx`
- 文件状态：`SOURCE_TRUSTED`
- Data Quality：`REVIEW_REQUIRED`
- 38个Sheet按月份记录签约、预产期、套餐和计划晚数
- 缺少证明实际入住所需的完整实际房号、实际入住状态和每日有效日期

### 6.2 判断

```text
initial_current_availability = UNAVAILABLE
```

该文件可作为Contract Stay Plan候选，但不能作为Actual Stay。禁止从预产期、入住计划或合同状态推算真实入住。

### 6.3 初始化策略

- 经签认的计划记录可迁移为Contract Stay Plan。
- 历史签约与计划记录可进入Historical/Plan。
- 不创建`Actual Stay CONFIRMED memory`。
- Cutover后由运营负责人通过OMS办理实际入住，生成Actual Stay Current。
- Actual Stay必须记录真实客户、房号、入住时间、状态、操作EMP、Audit和Event。

## 七、汇总结论

| Domain | 初始化Current可用性 | 初始化迁移内容 | Cutover后Current来源 |
| --- | --- | --- | --- |
| Sales | `CONDITIONAL` | 已确认销售Current或Historical候选 | OMS签约、合同、收款录入 |
| Finance | `UNAVAILABLE` | Finance Historical | OMS财务录入与对账 |
| Room | `UNAVAILABLE` | Room Master Data与Room Historical | OMS逐房状态确认与变更 |
| Actual Stay | `UNAVAILABLE` | Contract Stay Plan与Historical | OMS实际入住办理 |

## 八、语义记忆决策

当前不应为了凑齐四条记忆而创建虚假`CONFIRMED Current memory`：

- Sales Current：等待两个候选Sheet的业务签认和对账。
- Finance Current：当前文件无可确认Current。
- Room Current：当前文件无可确认Current。
- Actual Stay：当前文件无Actual Stay Current。

可以为经业务签认的Historical、Plan或Master Data用途建立对应语义记忆，但不得把其`fact_type`标记为Current。

## 九、Snapshot与Cutover影响

`TS-20260711-V2`不再要求四个域全部含Current，但必须真实记录每个域的初始化类型和空缺原因：

- Current记录只来自已确认且质量合格的来源。
- Historical、Plan和Master Data分别计数。
- Current缺失必须标记为`NOT_INITIALIZED`，不得用零值伪装已确认。
- Snapshot必须附带Cutover后的Current创建责任人和录入计划。

V2只有在迁移内容、空缺原因、责任人及Cutover录入方案全部通过验收后才能PASS。

## 十、当前状态

```text
TS-20260711-V1 = ACTIVE
TS-20260711-V2 = NOT GENERATED
Sales Current = CONDITIONAL
Finance Current = NOT_INITIALIZED
Room Current = NOT_INITIALIZED
Actual Stay Current = NOT_INITIALIZED
production_cutover = BLOCKED
```
