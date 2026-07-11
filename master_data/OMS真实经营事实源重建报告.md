# OMS真实经营事实源重建报告

## 一、执行结论

| 项目 | 状态 | 结论 |
| --- | --- | --- |
| P0.17.1 事实源重建定义 | COMPLETE | Finance、Stay、Room 生产口径已重新定义 |
| 原始文件补齐 | BLOCKED | 最新财务日报 Excel、2026-07-10 店总办在住原始 Excel 尚未取得 |
| TS-20260711-V2 | NOT CREATED | 对账前禁止生成正式快照 |
| 当前生产快照 | UNCHANGED | `TS-20260711-V1` 未覆盖 |
| 正式上线 | BLOCKED | V2 未 PASS 前禁止上线 |

本轮不修改页面，不人工调整数字，不使用截图转录值生成生产 Truth Source。

## 二、重建后的事实源结构

```text
Finance
├─ Finance Current
│  └─ 最新财务日报 Excel
└─ Finance Historical
   └─ 历史财务流水

Stay
├─ Contract Stay Plan
│  └─ 签约客户表
└─ Actual Stay
   └─ 店总办每日在住表

Room
└─ Room Current
   └─ 店总办每日房态表
```

老板首页和经营驾驶舱只允许读取：

- `Finance Current`
- `Actual Stay`
- `Room Current`

历史流水、签约入住计划、历史入住记录不得进入 Current 指标。

## 三、Finance 重建

### 3.1 Finance Current

唯一来源：财务负责人维护并确认的最新版财务日报 Excel。

必须包含：

- 经营日期
- 当日收入
- 当日支出
- 当前余额
- 现金
- 银行账户余额
- 当前待收
- 当前待付
- 资金主体
- 来源文件、Sheet、单元格、文件版本

每次导入必须整表对账：

```text
期初余额 + 当日收入 - 当日支出 = 当前余额
待收明细合计 = 待收总额
待付明细合计 = 待付总额
```

### 3.2 Finance Historical

来源：历史月份流水、历史财务事件和历史日报。

用途：历史查询、趋势分析、审计追溯。

禁止：直接汇总为首页当前资金状态。

### 3.3 当前文件状态

本机最新财务文件：

- 文件：`2026年财务报表（7月）.xlsx`
- 更新时间：`2026-07-10 19:00:01`
- Excel 待付：`275,575.08`
- 2026-07-11 经营截图待付：`286,657.08`
- 差额：`11,082.00`

结论：文件版本落后于最新经营日报，不能生成 Finance Current PASS。

## 四、Stay 重建

### 4.1 Contract Stay Plan

唯一来源：签约客户表。

表达：

- 已签约客户
- 预计生产日期
- 预计入住日期
- 计划房型
- 计划天数
- 合同关联

该实体只用于计划，不代表实际入住。

### 4.2 Actual Stay

唯一来源：店总办每日在住原始 Excel。

表达：

- 实际入住客户
- 实际房号
- 实际入住日期
- 预计/实际出馆日期
- 当前入住状态
- 管家
- 照护师
- 数据有效日期

`Resident Current` 必须由 `Actual Stay` 直接计数，禁止由 Contract Stay Plan 推算。

### 4.3 当前文件状态

本机可见原始 Excel：

- `凰家母婴在住表最新4.13.xlsx`
- 文件内容不能对应 2026-07-10 店总办当日在住表。

2026-07-10 店总办截图显示：

- Actual Stay / 产妇：`26`
- 待入住：`2`
- 照护师：`26`
- 陪护人员：`26`

截图只作为差异证据，不作为生产导入源。对应原始 Excel 未取得前，Actual Stay 不得 PASS。

## 五、Room 重建

### 5.1 Room Current

唯一状态来源：店总办每日房态原始 Excel。

房间主数据可继续保存 42 个房间资源，但以下状态必须每日从店总办表确认：

- `AVAILABLE`
- `RESERVED`
- `OCCUPIED`
- `CLEANING`
- `MAINTENANCE`
- `DISABLED`

每个 `OCCUPIED` 房间必须关联一条 Actual Stay；每条 Actual Stay 必须关联有效房号。签约计划不得覆盖 Room Current。

### 5.2 对账规则

```text
Room Master 总数 = 42
OCCUPIED 房间 ↔ Actual Stay 逐条对应
空房 + 预留 + 占用 + 清洁 + 维修 + 停用 = 42
重复房号 = 0
无效房号 = 0
```

当前仅确认房间主数据为 42，未取得 2026-07-10 原始房态 Excel，逐房状态对账 BLOCKED。

## 六、Truth Source 目标文件

| 文件 | Current 内容 | Historical/Plan 内容 |
| --- | --- | --- |
| `finance.json` | `finance_current` | `finance_historical` |
| `stay.json` | `actual_stays` | 不再混入计划 |
| `contract_stay_plan.json` | 不参与首页 | `contract_stay_plans` |
| `room.json` | `room_current` | 房态历史另存历史集合 |

每条 Current 记录必须具备：

- `record_id`
- `source_file`
- `source_sheet`
- `source_row`
- `source_columns`
- `source_version`
- `effective_time`
- `is_current=true`
- `quality_status=PASS`

## 七、TS-20260711-V2 验收条件

### 7.1 Finance Current

- 最新财务日报 Excel 文件哈希已锁定。
- 当日收入、支出、余额、待收、待付逐项一致。
- 明细合计与日报总额一致。
- 历史流水不参与 Current 汇总。

### 7.2 Actual Stay

- 2026-07-10 店总办原始 Excel 文件哈希已锁定。
- 实际在住逐人、逐房核对一致。
- Actual Stay 数量与日报产妇数量一致。
- Contract Stay Plan 不进入 Resident Current。

### 7.3 Room Current

- 42 房逐房核对。
- OCCUPIED 与 Actual Stay 一一对应。
- 无重复、无孤立入住、无非法房号。

### 7.4 快照门

```text
snapshot_id = TS-20260711-V2
finance_reconciliation = PASS
actual_stay_reconciliation = PASS
room_reconciliation = PASS
quarantine = 0
unresolved_anomalies = 0
acceptance_result = PASS
activated_for_production = true
```

任意一项不满足时：

```text
acceptance_result = FAIL
activated_for_production = false
ACTIVE_SNAPSHOT remains TS-20260711-V1
```

## 八、当前阻断项

1. 缺少与 2026-07-11 最新财务日报一致的原始 Excel。
2. 缺少与 2026-07-10 店总办在住/房态一致的原始 Excel。
3. Finance Current 无法完成最终金额对账。
4. Actual Stay 无法完成逐人逐房对账。
5. Room Current 无法完成 42 房逐房状态对账。

## 九、当前保护状态

- 未修改 `finance.json`。
- 未修改 `stay.json`。
- 未修改 `room.json`。
- 未修改 `ACTIVE_SNAPSHOT.json`。
- 未生成伪造的 `TS-20260711-V2.json`。
- 未恢复正式上线。

只有与最新经营日报一致、具备可验证 Current 结构的原始 Excel 通过 Data Quality Layer 后，才执行正式 Truth Source 重建和 V2 冻结。

## 十、四份原始 Excel 实际分析结果

分析时间：`2026-07-11`

执行链：

```text
原始 Excel（只读）
→ 文件 SHA-256
→ Data Quality Layer
→ 全 Sheet 分析
→ Current / Historical / Quarantine 分类
```

本轮分析只生成候选与数据质量报告，未写入生产 Truth Source。

### 10.1 销售 Excel

- 文件：`2026年销售明细表（经验为王7.10）(1).xlsx`
- SHA-256：`b101f55246145e5f738b4bb10ea1e087bf67fa8ddd8760bb28cb3e628d61c30e`
- Sheet 数：`8`
- 质量状态：`PARTIALLY_ADMISSIBLE`
- Current 候选：`185`
- Historical：`0`
- Quarantine：`35`
- 排除 Sheet：`6`

Sheet 分类：

| Sheet | 分类 | 状态 |
| --- | --- | --- |
| 2026年内店销售列表 | CURRENT_PRODUCTION | 部分记录可准入 |
| 2026外店上户列表 | CURRENT_PRODUCTION | 部分记录可准入 |
| 2026外店凤稚列表 | UNCONFIRMED | REVIEW_REQUIRED |
| 未入住及尾款 | UNCONFIRMED | REVIEW_REQUIRED |
| 销售部7月排名 | AUXILIARY_CALCULATION | 排除 |
| 7-8月PV | AUXILIARY_CALCULATION | 排除 |
| 销售数据 | AUXILIARY_CALCULATION | 排除 |
| Sheet1 | NOTES | 排除 |

结论：销售文件尚未通过完整对账，不能以 185 条候选替换现有 224 条销售事实。

### 10.2 财务 Excel

- 文件：`2026年财务报表（7月）.xlsx`
- SHA-256：`5d82c4735a81b8b725fb30301277ad88eec702d07327769e050261ef87f80990`
- Sheet 数：`8`
- 质量状态：`REVIEW_REQUIRED`
- Current：`0`
- Historical：`0`
- Quarantine：`0`
- 未确认 Sheet：`8`

Sheet：`日结、2026.1月、2月、3月、4月、5月、6月、7月`。

原因：同一 Sheet 混合双主体日报、余额、待收、待付、汇总和历史流水，缺少稳定交易编号及明确 Current 边界；Data Quality Layer 不允许按文件名或位置猜测生产口径。

结论：不能生成 Finance Current，财务对账 FAIL。

### 10.3 房态 Excel

- 文件：`①凰家母婴 2021房态表June(1).xlsx`
- SHA-256：`946fc4ddd9c3a12ada1644e5876a9a1a623dac198512d722fe076f653b96c37e`
- Sheet 数：`3`
- 质量状态：`REVIEW_REQUIRED`
- Current：`0`
- Historical：`0`
- Quarantine：`0`
- 未确认 Sheet：`3`

问题：

- Sheet1 与 Sheet3 为横向日期矩阵，列数分别达到 `3147`、`1231`。
- Sheet2 为陪护人员登记结构，不是 Room Current。
- 文件中没有可直接验证的统一房态状态字段。
- 无法证明该文件对应 2026-07-10 店总办当日 42 房状态。

结论：Room Current 对账 FAIL。

### 10.4 签约客户及入住相关 Excel

- 文件：`A  凰家母婴签约客户一览表（挤牙膏）(1).xlsx`
- SHA-256：`f83f07e17aeec26e669989278356d649ebfda70f6bf07d1a237263399474a3fb`
- Sheet 数：`38`
- 质量状态：`REVIEW_REQUIRED`
- Current：`0`
- Historical：`0`
- Quarantine：`0`
- 未确认 Sheet：`38`

该文件按月份记录签约、预产期、套餐、顾问和计划晚数，可作为 `Contract Stay Plan` 的候选来源；但不具备证明实际入住所需的完整实际房号、实际入住状态和每日有效日期。

结论：

- Contract Stay Plan：需要专用计划映射后重新验收。
- Actual Stay：无法从该文件生成。
- 入住对账：FAIL。

## 十一、V2 决策

| 对账门 | 结果 |
| --- | --- |
| 销售对账 | FAIL |
| 财务对账 | FAIL |
| 房态对账 | FAIL |
| 入住对账 | FAIL |

```text
TS-20260711-V2 = NOT GENERATED
acceptance_result = FAIL
activated_for_production = false
ACTIVE_SNAPSHOT = TS-20260711-V1
production_release_gate = BLOCKED
```

未通过原因不是 OMS 页面或计算错误，而是四份原始文件中仍缺少可确认的 Finance Current、Actual Stay 和 Room Current 生产结构。禁止用人工修数、截图转录或文件名推断绕过验收。

## 十二、Data Quality 输出

本轮自动报告目录：

`live_runtime/data_quality_reports/p0171/`

已生成四份逐 Sheet 数据质量报告，并保留 Audit/Event 记录。原始 Excel 未被修改。

## 十三、P0.17.2 文件信任与自动准入复核

### 13.1 文件信任

四份原始 Excel 均由凰家实际业务负责人日常使用，文件级状态统一调整为：

```text
source_trust = SOURCE_TRUSTED
```

文件可信只证明来源真实，不代表每个 Sheet 都属于 Current，也不豁免字段和数据质量检查。

### 13.2 自动准入结果

| 数据域 | Current候选 | 质量结果 | 自动准入 |
| --- | ---: | --- | --- |
| Sales | 2 个 | PARTIALLY_ADMISSIBLE，35 条 Quarantine | NO：多个候选且存在异常 |
| Finance | 0 个 PASS 候选 | REVIEW_REQUIRED | NO：Sheet 用途和字段结构冲突 |
| Room | 0 个 PASS 候选 | REVIEW_REQUIRED | NO：横向日期矩阵无法形成唯一 Room Current |
| Actual Stay | 0 个 PASS 候选 | REVIEW_REQUIRED | NO：未识别唯一实际入住 Sheet |

本轮没有任何数据域同时满足“唯一 Current 候选 + 质量 PASS”，因此没有可自动准入项。人工确认范围已收敛为四个明确例外，不再要求重复确认文件来源。

### 13.3 V2 状态

```text
source_file_trust = PASS
sheet_quality_gate = FAIL
TS-20260711-V2 = NOT CREATED
TS-20260711-V1 = ACTIVE
production_release_gate = BLOCKED
```

`TS-20260711-V2` 必须保留 `source_file`、`source_sheet`、`owner`、`quality_result`、`snapshot_version`。当前 Sheet 质量门未通过，禁止生成形式上的 V2。
