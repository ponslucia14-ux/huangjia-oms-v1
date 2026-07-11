# OMS 现有经营数据冻结报告

## 一、冻结结论

| 项目 | 状态 |
|---|---|
| 冻结结果 | PASS |
| 冻结时间 | 2026-07-11T22:57:20+08:00 |
| 原 Snapshot | TS-20260711-V1 |
| 冻结后状态 | ARCHIVED_LEGACY |
| 旧 Current 标签 | ARCHIVED |
| 是否可作为未来经营 Current | 否 |
| 新系统阶段 | WORKSPACE_DESIGN_PHASE |
| Cutover | 禁止 |

`TS-20260711-V1` 原文件和原指针均未修改。归档通过独立 Manifest 和运行状态文件声明其为 `ARCHIVED_LEGACY`，确保历史可追溯，同时不破坏不可变快照。

## 二、冻结数量

| Domain | 冻结数量 | 说明 |
|---|---:|---|
| Customer | 224 条客户关联记录；219 个唯一姓名 | 来自旧 Sales 初始化实体 |
| Contract | 224 条记录；223 个唯一合同号 | 包含已知历史合同号重复问题 |
| Finance | 1278 条财务事件；11 条结算记录 | 历史流水口径，不代表当前资金状态 |
| Room | 42 条 | 房间基础与旧房态候选 |
| Stay | 172 条 | 混合历史、计划和旧 Current 候选 |
| Employee | 11 条 | 保留 EMP、飞书 user_id、role、workspace 与权限关系 |
| Audit | 362 条 | 原样归档 |
| Event | 6167 条 | 原样归档 |
| Task | 6167 条 | 原样归档 |

Expense、Approval、Notification 未发现独立生产数据文件；其已有操作痕迹随 Audit/Event 归档保留，不制造空数据集或推算数量。

## 三、历史归档结构

归档位置：

`live_runtime/historical_archive/TS-20260711-V1/`

包含：

- `Customer Archive`
- `Contract Archive`
- `Finance Archive`
- `Room Archive`
- `Stay Archive`
- `Employee Archive`
- `Other Archive/Audit`
- `Other Archive/Event`
- `Other Archive/Task`
- `Raw Sources`
- `Snapshot`
- `archive_manifest.json`

共冻结 18 个对象，18 个状态均为 `FROZEN`，总大小 54,070,418 bytes。Manifest 记录每个对象的原始路径、归档路径、文件大小和 SHA-256。

## 四、原始文件

以下原始 Excel 已按原样复制并锁定哈希：

1. `2026年销售明细表（经验为王7.10）(1).xlsx`
2. `2026年财务报表（7月）.xlsx`
3. `①凰家母婴 2021房态表June(1).xlsx`
4. `A  凰家母婴签约客户一览表（挤牙膏）(1).xlsx`

原文件未修改、未清洗、未人工调整数字。

## 五、已知问题

1. 旧 Current 口径不代表现实经营 Current。
2. Stay 中历史、计划和推断记录混合。
3. 旧 Room 占用状态由日历标记推断，未绑定经确认的 Actual Stay Current。
4. Finance 主要是历史流水，不代表当前资金状态。
5. Contract 存在 224 条记录但只有 223 个唯一合同号。
6. Customer 以销售记录关联形成，224 条记录对应 219 个唯一姓名，不等同于正式 Customer Current。

以上问题作为历史技术版本事实保留，不再继续修复旧 Current。

## 六、冻结保护

- 禁止修改生产 Truth Source 旧数据。
- 禁止修改历史记录。
- 禁止覆盖 `TS-20260711-V1`。
- 禁止把任何 `ARCHIVED` 记录重新作为经营 Current。
- 禁止继续修旧 Current。
- 任何历史查询必须明确显示 `ARCHIVED_LEGACY`。

运行阶段文件：

`live_runtime/operating_mode.json`

当前值：

```text
phase = WORKSPACE_DESIGN_PHASE
current_operating_snapshot = null
legacy_snapshot = TS-20260711-V1
legacy_snapshot_status = ARCHIVED_LEGACY
cutover_allowed = false
old_current_repair_allowed = false
```

## 七、后续处理

OMS 停止旧 Current 修补，进入十一人工作台设计阶段。未来经营 Current 必须由新工作台中的授权业务动作生成，并保留 EMP、权限、Audit 和 Event 链路。
