# OMS P0.19 现实经营基线重建报告

## 结论

- 验收状态：`FAIL / BLOCKED`
- 旧快照：`TS-20260711-V1` 保留，但不得作为经营 Current 依据
- 新候选：`OB-20260711-V1-CANDIDATE`
- 新候选状态：`FAIL / INACTIVE`
- Cutover：继续停止
- 正式上线：继续停止

## 原始事实检查

| 项目 | 结果 |
|---|---:|
| 房间基础记录 | 42 |
| 原 Stay 记录 | 172 |
| 可证明仍在馆的 Stay | 0 |
| 可证明真实占用的 Room | 0 |
| 排除记录 | 172 |

原始房态工作簿是跨年度排期日历。2026 年 7 月区块记录了日期上的姓名与备注，但没有持续在馆状态、实际出馆闭环和责任人实时确认。原 8 条 `IN_STAY` 来自 2026-07-10 日期格中的姓名标记，不能证明截至当前仍在馆。

## Current 准入规则

Actual Stay Current 必须同时满足：

1. `active = true`
2. `stay_status = IN_STAY`
3. `checkout_date` 为空
4. `reality_verified = true`
5. 存在 `verified_by_emp_id`
6. 存在 `verified_at`
7. 一个房间只能对应一个 Current Stay

已出馆、计划入住、历史标记和未确认记录全部不得进入 Current。

## Room Current 规则

- 42 间房只作为 Room Master。
- `OCCUPIED` 必须由已确认 Actual Stay Current 反向生成。
- 每个 `OCCUPIED` 房间必须具有 `current_stay_id` 和当前客户。
- 不允许历史姓名或日期标记直接把房间设为 `OCCUPIED`。
- 当前未获得真实在住确认，因此 Room Current 未激活。

## Action Today 修正

Action 区只允许：

- 待审批
- 待确认
- 风险
- 异常
- 今日任务

在住、房态、销售和财务数字属于 Status，不再被转换成虚假“今日任务”。没有真实待办时显示“今天暂无待处理事项”。

## 生成物

- `live_runtime/operational_baseline/OB-20260711-V1-CANDIDATE.json`
- `live_runtime/operational_baseline/operational_baseline_state.json`
- 状态门禁：`REALITY_BASELINE_NOT_CONFIRMED`

## 剩余验收

需要由运营责任人逐条确认当前在住，并记录操作 EMP 和时间。确认后才能生成 PASS 基线。EMP001 手机端随后随机核验 5 个在住客户和 5 个占用房间；两组全部真实一致后，方可激活 Operational Baseline Snapshot。
