# OMS真实经营数据口径校准报告

## 一、校准结论

| 项目 | 状态 | 结论 |
| --- | --- | --- |
| P0.17 数据事实源重新校准 | FAIL | 真实经营口径与当前生产 Truth Source 不一致 |
| TS-20260711-V2 | NOT ACTIVATED | 财务日报和店总在住表尚未同时通过对账，禁止生成 PASS/ACTIVE 快照 |
| 正式上线 | BLOCKED | 不允许继续生产发布 |

本报告只做事实源校准，不修改页面，不人工调整经营数字，不以截图或旧快照冒充生产事实源。

## 二、当前差异

| 数据域 | 当前 OMS 口径 | 真实经营口径 | 校准结果 |
| --- | --- | --- | --- |
| Finance | `1278` 条跨月历史财务事件参与经营汇总 | 财务日报中的当日资金状态、当日收支、待收、待付 | FAIL |
| Stay | `172` 条签约/入住计划记录统一作为 Stay | `Contract Stay Plan` 与 `Actual Stay` 必须分离 | FAIL |
| Resident | 从 172 条计划记录按日期推导出 `8` | 店总办在住表 2026-07-10 明示产妇 `26` 人 | FAIL |
| Room | 房间资源总数 `42` | 当前占用、空房、预留必须以店总办当日房态为准 | WARNING |

## 三、Finance Truth Source

### 3.1 正式定义

```text
财务日报（当前有效版本）
→ Data Quality Layer
→ Finance Current
→ Finance Domain
```

`Finance Current` 只表达当前经营资金状态。跨月历史流水保留在 `Finance Historical`，不得直接作为老板首页的当前财务口径。

### 3.2 原始文件核查

- 文件：`2026年财务报表（7月）.xlsx`
- 本机文件更新时间：`2026-07-10 19:00:01`
- 当前页：`日结`
- Excel 当前记录：
  - 凰家 7月10日收入：`37,580.00`
  - 凰家 7月10日支出：`0.00`
  - 凰家余额：`142,585.15`
  - 现金：`142,393.87`
  - 基本户：`191.28`
  - 7月11日待收：`2,000.00`
  - 待付：`275,575.08`
  - 凤稚余额：`5,070.05`
  - 凤稚待收：`2,000.00`
  - 凤稚待付：`1,418.00`

### 3.3 最新经营截图核查

- 截图时间：`2026-07-11 15:10:02`
- 截图显示凰家待收：`7,000.00`
- 截图显示凰家待付：`286,657.08`
- 截图显示凤稚待收：`2,000.00`
- 截图显示凤稚待付：`1,908.90`
- 截图与本机 Excel 的凰家待付差额：`11,082.00`
- 差额项目：`6月出馆客户销售提成`

结论：本机 Excel 不是截图对应的最新财务日报版本。最新 Excel 未取得前，Finance 对账不得 PASS。

## 四、Stay Truth Source

### 4.1 Contract Stay Plan

定义：签约客户、预计生产、预计入住、计划房型和计划天数。

```text
签约客户 Excel
→ Contract Stay Plan
```

该数据用于计划和预测，不得计入当前在住人数，不得直接生成 `Resident Current`。

### 4.2 Actual Stay

定义：已经真实入住且尚未实际出馆的客户。

```text
店总办在住表（当前有效版本）
→ Actual Stay
→ Resident Current
```

2026-07-10 店总办在住表截图显示：

- 产妇数量：`26`
- 待入住：`2`
- 孩子住院：`2`
- 照护师：`26`
- 陪护人员：`26`

结论：当前 OMS 的 `Resident=8` 与店总办实际在住 `26` 不一致；`Stay=172` 是计划/历史集合，不能作为 Actual Stay Current。

## 五、Room Truth Source

### 5.1 正式定义

```text
店总办当日房态
→ Data Quality Layer
→ Room Current
→ Room Domain
```

- 房间资源主数据总数：`42`
- 当前占用、预留、空房和异常状态：必须由店总办当日房态逐房确认。
- 签约客户计划和历史入住记录不得反向覆盖当前房态。

当前 42 个房间编号可继续作为资源主数据，但房态状态尚未与 2026-07-10 店总办表逐房结构化对账，因此 Room Current 暂为 WARNING。

## 六、TS-20260711-V2 验收门

| 验收项 | 目标 | 当前结果 |
| --- | --- | --- |
| 财务日报版本一致 | Excel 与 7月11日经营日报一致 | FAIL |
| Finance Current 对账 | 当日收支、余额、待收、待付逐项一致 | FAIL |
| Actual Stay 对账 | 当前在住逐人、逐房一致 | FAIL |
| Resident Current 数量 | `26`，且每条可追溯到店总办在住表 | FAIL |
| Room Current 对账 | 42 房逐房状态一致 | WARNING |
| Contract Stay Plan 隔离 | 不进入 Resident Current | 待重建 Truth Source 后验证 |
| Quarantine | `0` | 暂未执行新一轮导入 |
| 未解决异常 | `0` | 当前至少 3 项未解决 |

### 未解决异常

1. `FINANCE_SOURCE_VERSION_MISMATCH`：本机财务 Excel 落后于 7月11日经营截图。
2. `STAY_PLAN_ACTUAL_MIXED`：172 条计划/历史 Stay 与 Actual Stay 未分层。
3. `RESIDENT_COUNT_MISMATCH`：OMS 为 8，店总办实际为 26。
4. `ROOM_CURRENT_NOT_RECONCILED`：42 房资源存在，但当前房态未逐房完成结构化验收。

## 七、快照状态

```text
requested_snapshot_id = TS-20260711-V2
acceptance_result = FAIL
activated_for_production = false
active_snapshot_unchanged = TS-20260711-V1
production_release_gate = BLOCKED
```

为遵守快照不可伪造、不可覆盖规则，本轮未写入正式 `TS-20260711-V2.json`，也未修改 `ACTIVE_SNAPSHOT.json`。只有取得最新版财务日报 Excel 和店总办当前在住/房态原始表，并完成逐项对账后，才允许生成正式 `TS-20260711-V2 = PASS / ACTIVE`。

## 八、待补齐原始证据

1. 与 2026-07-11 财务截图完全一致的最新版财务日报 Excel。
2. 与 2026-07-10 店总办在住截图完全一致的原始在住/房态 Excel，而非截图副本。
3. 店总确认的 42 房当前状态清单。

以上三项未齐前，OMS 不允许恢复正式上线。
