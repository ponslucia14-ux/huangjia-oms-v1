# OMS P0.18.3事实源候选与V2准备报告

执行时间：2026-07-11  
执行原则：有证据继续，无证据不猜  
生产影响：无；V1未修改

## 一、业务证据链

| 数据来源 | 来源责任人 | 业务用途 | Current运行责任 |
| --- | --- | --- | --- |
| 销售Excel | EMP004 刘晶 | 销售合同与收款业务来源 | EMP006杨欢欢创建/确认；重大金额由EMP003张敬东复核 |
| 财务Excel | EMP004 刘晶 | Finance Historical迁移 | EMP004刘晶在OMS生成Current；EMP003张敬东复核 |
| 挤牙膏Excel | EMP008 刘芳羽 | Contract Stay Plan | 不生成Actual Stay |
| 在住表 | EMP009 尚丽娜 | Actual Stay业务来源 | EMP008刘芳羽在OMS办理Current；EMP009核对资料 |

来源Owner与Current操作责任人分别记录，不相互替代。

## 二、Sales候选

来源：`2026年销售明细表（经验为王7.10）(1).xlsx`  
SHA-256：`b101f55246145e5f738b4bb10ea1e087bf67fa8ddd8760bb28cb3e628d61c30e`

纳入分析：

- `2026年内店销售列表`：181条原始合同级记录
- `2026外店上户列表`：5条原始合同级记录

Data Quality发现合同号`NSEKI94131081`对应两位不同客户、不同日期及金额。两条记录均进入`CONFLICT`，不得进入Current候选。

```text
admissible_candidate = 184
quarantine = 2
quality = WARNING
classification = CONDITIONAL_CURRENT
```

销售候选具备合同级字段，但合同生命周期状态未显式记录，因此在冲突关闭和Current口径确认前不标记为正式Current。

## 三、Finance候选

来源：`2026年财务报表（7月）.xlsx`  
SHA-256：`5d82c4735a81b8b725fb30301277ad88eec702d07327769e050261ef87f80990`

迁移范围：2026年1月至7月的可解析收入和支出流水。`日结`不作为Current导入，也不与月表重复迁移。

| Sheet | Historical记录 |
| --- | ---: |
| 2026.1月 | 73 |
| 2月 | 67 |
| 3月 | 76 |
| 4月 | 78 |
| 5月 | 74 |
| 6月 | 76 |
| 7月 | 26 |
| 合计 | 470 |

```text
historical = 470
quarantine = 0
quality = PASS
current = NOT_INITIALIZED
```

Finance Current由Cutover后EMP004在OMS录入产生，不从历史流水倒推。

## 四、Contract Stay Plan候选

来源：`A  凰家母婴签约客户一览表（挤牙膏）(2).xlsx`  
SHA-256：`591dc1b119d48cc3bc7ee8626a934b28ffe07bbe8310ea81c43cd3262a99d3ac`

- 全部39个Sheet已扫描。
- 合格Plan候选：1319条。
- 字段不完整：7条，进入Quarantine。
- 文件只用于Contract Stay Plan，禁止生成Actual Stay。

```text
plan = 1319
quarantine = 7
quality = WARNING
actual_stay_prohibited = true
```

## 五、Actual Stay候选

来源：`凰家母婴在住表最新4.13.xlsx`  
SHA-256：`73e8b7629514950d517e0553aff7e19a6cae6039b5be1af0a8b2ac99f755b0b8`

业务Sheet：`房态表`。表内明确更新时间为`2026-07-02`。

- 具备完整房号、姓名、入住和出馆日期：33条。
- 缺少实际日期：5条，进入Quarantine。
- 以7月2日计算的有效记录：33条。
- 表尾人工汇总产妇数量：30人。
- 计算值与人工汇总相差3人，进入一致性异常。

```text
historical_snapshot_records = 33
quarantine = 5
reported_resident_count = 30
calculated_active_count = 33
quality = WARNING
current = NOT_INITIALIZED
```

由于来源有效日期早于7月11日，该批只能建立Actual Stay历史时点候选。Cutover Current必须由EMP008在OMS确认产生。

## 六、Semantic Memory候选

隔离候选库：

`live_runtime/p0183_v2_preparation_final/sheet_semantic_memory_candidates.json`

```text
candidate_count = 49
memory_version = V1 per candidate rule
memory_status = TEMPORARY
CONFIRMED = 0
```

Owner：

- Sales：EMP004
- Finance：EMP004
- Contract Stay Plan：EMP008
- Actual Stay：EMP009

TEMPORARY记忆不会自动准入。结构变化或质量下降仍进入REVIEW。

## 七、V2准备状态

准备清单：

`live_runtime/p0183_v2_preparation_final/TS-20260711-V2_PREPARATION.json`

```text
candidate_snapshot = TS-20260711-V2
status = PREPARED_NOT_GENERATED
requires_all_current = false
requires_quality_acceptance = true
requires_no_false_current = true
ready = false
```

当前尚不能生成PASS V2，待关闭：

1. Sales重复合同冲突及Current生命周期口径。
2. Contract Plan 7条字段异常的准入结论。
3. Actual Stay 5条缺失日期及33/30人数差异。
4. Cutover后Finance、Room、Actual Stay首次Current动作仍未执行。

## 八、V1保护

```text
TS-20260711-V1 = ACTIVE
TS-20260711-V2 = NOT GENERATED
production_truth_source_modified = false
cutover = BLOCKED
```

本轮只写入隔离准备目录和报告，不写生产Truth Source，不修改页面数字。
