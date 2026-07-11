# OMS事实源迁移与运行切换设计

## 一、架构结论

Excel事实源治理属于OMS初始化迁移阶段，不是长期生产运行模式。

OMS上线后的第一事实源是经过权限、Audit和Event约束的OMS Domain Current。Excel仅保留历史导入、批量导入和外部数据交换职责。

## 二、迁移阶段

```text
Excel
-> Data Quality Layer
-> Migration Truth Source Snapshot
-> Domain初始化
-> 初始Current
```

迁移目标：

- 导入历史经营数据。
- 建立上线时点的初始Current。
- 完成Current、Historical和Quarantine分类。
- 形成可追溯的初始化快照。

P0.17属于该阶段。四大事实源首次语义确认和`TS-20260711-V2`仍必须完成，不能因未来切换到OMS录入而跳过初始数据校准。

## 三、正式运行阶段

```text
员工在OMS录入或执行
-> 权限校验
-> Domain Command
-> Domain Current
-> Audit + Event
-> API + 页面 + Metrics + AI Context
```

正式运行阶段规则：

1. OMS Domain Current是当前经营事实的第一来源。
2. 员工通过OMS完成新增、修改、审核和发布。
3. 所有状态变化保留EMP身份、Audit、Event和版本。
4. Excel不得直接覆盖已激活的Domain Current。
5. 外部导入必须经过Data Quality、差异检测和人工治理门。

## 四、Excel长期定位

Excel仅用于历史数据迁移、经批准的批量导入、外部系统数据交换以及灾备导出或人工核对。

Excel不得用于长期维护日常Current、绕过OMS权限修改状态、直接驱动首页或AI Context、覆盖OMS内已经确认的业务事实。

## 五、事实源优先级

初始化迁移期：

```text
已激活Migration Snapshot > 未激活候选 > 原始Excel
```

正式运行期：

```text
OMS Domain Current > 已激活初始化快照 > 外部导入候选
```

初始化快照保留为基线证据，不持续覆盖运行中的Domain Current。

## 六、切换门

从迁移阶段切换到正式运行阶段必须同时满足：

1. 四大初始事实源完成语义确认。
2. 初始化快照为PASS并激活。
3. Domain初始化数量与快照一致。
4. OMS录入权限、Audit和Event有效。
5. 各数据责任人开始使用OMS维护日常业务。
6. Excel日常Current写入进入只读或停止维护计划。

切换记录必须包含`cutover_id`、`snapshot_version`、`cutover_time`、`approved_by`和各Domain基线版本。

## 七、上线后外部导入

```text
External File
-> Data Quality
-> Semantic Memory
-> Diff: NEW / CHANGED / MISSING / CONFLICT
-> Review
-> Domain Command
```

外部导入不能直接写Domain存储。`CHANGED`、`MISSING`、`CONFLICT`必须按权限和责任矩阵处理。

## 八、当前状态

```text
phase = INITIAL_MIGRATION
active_snapshot = TS-20260711-V1
candidate_snapshot = TS-20260711-V2 / NOT GENERATED
production_cutover = BLOCKED
future_primary_truth = OMS Domain Current
```
