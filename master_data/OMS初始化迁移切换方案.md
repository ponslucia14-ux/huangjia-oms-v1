# OMS初始化迁移切换方案

## 一、目的

本方案定义凰家经营数据从Excel主导的初始化迁移阶段，切换到OMS Domain Current主导的正式运行阶段。

切换不是删除Excel，也不是让初始化快照持续覆盖业务状态。切换完成后，OMS Current是唯一日常经营事实源。

## 二、Cutover时间点

每次正式切换必须冻结以下信息：

| 字段 | 定义 |
| --- | --- |
| `cutover_id` | 唯一切换编号，格式`CUTOVER-YYYYMMDD-Vn` |
| `cutover_date` | 业务切换日期 |
| `cutover_time` | 精确到时区的实际切换时间 |
| `cutover_snapshot` | 通过验收且用于初始化的Truth Source Snapshot版本 |
| `approved_by` | 批准切换的真实EMP |
| `domain_baselines` | Sales、Finance、Room、Stay等Domain初始化版本 |
| `status` | `PLANNED / VALIDATING / ACTIVE / ABORTED` |

当前候选：

```text
cutover_date = PENDING
cutover_snapshot = TS-20260711-V2 / NOT GENERATED
active_snapshot = TS-20260711-V1
cutover_status = BLOCKED
```

只有`PASS + ACTIVE`的Cutover Snapshot可用于正式切换。

## 三、切换前状态

切换前系统处于`INITIAL_MIGRATION`：

- Excel是历史与初始Current的业务证据源。
- 所有文件必须经过全Sheet分析和Data Quality。
- Current、Historical、Quarantine必须明确分离。
- Sheet语义记忆必须完成首次业务确认。
- Snapshot用于冻结OMS初始化数据。
- OMS Domain尚未成为员工日常录入的唯一入口。

切换前禁止把未确认Sheet、Quarantine或临时数据初始化为Domain Current。

## 四、切换前置门禁

以下条件必须全部满足：

1. Sales Current、Finance Current、Room Current、Actual Stay首次语义记忆为`CONFIRMED`。
2. Data Quality结果满足上线要求。
3. Quarantine为零，或每条记录有明确的不准入结论和责任人。
4. 初始化Snapshot为`PASS`。
5. Snapshot数据量、金额及关键状态完成业务对账。
6. Domain初始化演练结果与Snapshot一致。
7. EMP、角色、workspace和数据变更权限有效。
8. Audit与Event可记录所有正式写入。
9. 员工录入入口与操作说明准备完成。
10. EMP001石磊批准Cutover。

任一门禁失败，状态保持`BLOCKED`，不得部分切换。

## 五、切换动作

切换必须按顺序执行：

### 5.1 最终数据快照

1. 停止初始化Excel的继续编辑或记录最终文件版本。
2. 运行Data Quality全量检查。
3. 生成最终候选Snapshot。
4. 完成销售、财务、房态、入住对账。
5. 仅在结果为PASS时激活Snapshot。

### 5.2 Domain初始化

1. 从激活Snapshot读取准入记录。
2. 生成各Domain基线版本。
3. 校验记录数、业务主键、金额和状态。
4. 写入初始化Audit和Event。
5. 保存Snapshot记录到Domain记录的追溯关系。

### 5.3 权限开启

1. 启用EMP到角色、workspace和责任范围的绑定。
2. 开启创建、修改、审核和发布权限。
3. 禁止匿名、fallback或虚拟用户写入。
4. 验证重大字段变更审批规则。

### 5.4 员工切换

1. 宣布Cutover生效时间。
2. 员工从生效时间起只在OMS录入Current业务。
3. Excel日常Current维护停止或转为只读。
4. EMP001石磊工作台开始读取OMS Domain Current。
5. Cutover状态变更为`ACTIVE`并写入Audit/Event。

## 六、切换后规则

切换后系统处于`OMS_OPERATION`：

```text
OMS录入
-> 权限校验
-> Domain Command
-> Domain Current
-> Audit/Event
-> API/页面/Metrics/AI Context
```

规则：

- OMS Domain Current是唯一日常Current来源。
- 初始化Snapshot保持不可变，作为基线与追溯证据。
- Excel仅用于历史查询、受控批量导入和外部数据交换。
- Excel导入必须进入Data Quality和差异审查，不能直接修改Current。
- 页面、Metrics和AI Context不得直接读取原始Excel。
- 所有业务变更必须绑定真实EMP、权限、原因、Audit和Event。

## 七、异常处理

### 7.1 Cutover前异常

数据质量、对账或权限异常时：

1. Cutover标记为`ABORTED`或继续`BLOCKED`。
2. 保留当前生产快照和全部候选证据。
3. 修正来源或映射后生成新Snapshot版本。
4. 禁止修改已冻结Snapshot。

### 7.2 Cutover执行中异常

Domain初始化不完整或校验失败时：

1. 不开放员工写权限。
2. 不宣告OMS Current生效。
3. 删除或隔离未激活的初始化批次，不影响既有生产状态。
4. 根据同一Snapshot重新执行完整初始化。

### 7.3 Cutover后发现数据错误

禁止使用Excel覆盖Current。必须：

```text
发现问题
-> 创建Data Issue
-> 定位Snapshot/Domain/Audit证据
-> 权限校验
-> 业务负责人确认
-> OMS Correction Command
-> 新Domain版本
-> Audit/Event
```

重大字段修正按数据变更权限设计进入审批。原错误版本不得物理删除。

### 7.4 外部批量导入异常

外部文件产生`CHANGED / MISSING / CONFLICT`时进入Quarantine或Review。确认后通过Domain Command逐批发布，不得绕过权限直接写存储。

## 八、回退边界

Cutover前可以取消候选切换，继续保留原有运行状态。

Cutover后不允许“回退为Excel主导”。如OMS入口临时不可用，应启动受控应急记录，恢复后经过Data Quality与补录审批进入OMS；应急Excel不能自动覆盖Current。

## 九、Audit与Event

建议Audit：

- `cutover.plan`
- `cutover.validate`
- `cutover.activate`
- `cutover.abort`
- `cutover.correction`

建议Event：

- `migration.cutover.planned`
- `migration.cutover.validated`
- `migration.cutover.activated`
- `migration.cutover.aborted`

每条记录必须关联`cutover_id`、Snapshot、操作者EMP、原因和结果。

## 十、当前决策

```text
phase = INITIAL_MIGRATION
TS-20260711-V1 = ACTIVE
TS-20260711-V2 = NOT GENERATED
four_semantic_memories = NOT CONFIRMED
cutover = BLOCKED
```

下一步仍为P0.17四大初始事实源业务确认与数据校准。本方案不生成V2，也不改变当前ACTIVE快照。
