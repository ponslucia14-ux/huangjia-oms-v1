# OMS Cutover执行设计

## 一、目标

本设计用于完成凰家从Excel管理模式到OMS经营模式的上线切换。

```text
Excel初始化迁移
-> Cutover验证
-> OMS Domain初始化
-> 员工首次操作
-> OMS Domain Current成为唯一事实源
```

本文件只定义执行方案，不实施Cutover、不生成V2、不改变当前生产状态。

## 二、Cutover Date

### 2.1 必填信息

| 字段 | 要求 |
| --- | --- |
| `cutover_id` | `CUTOVER-YYYYMMDD-Vn` |
| `cutover_date` | EMP001石磊批准的业务日期 |
| `cutover_start_time` | 切换开始时间，含`Asia/Shanghai`时区 |
| `cutover_effective_time` | OMS Current正式生效时间 |
| `cutover_snapshot` | 用于初始化的PASS Snapshot |
| `approved_by` | EMP001 石磊 |
| `execution_owner` | 每个Domain的真实责任EMP |
| `status` | `PLANNED / VALIDATING / READY / ACTIVE / ABORTED` |

### 2.2 时间安排

建议选择业务变更较少的时段执行：

1. `T-1日`：通知员工、冻结迁移Excel版本、完成权限检查。
2. `T日切换前`：生成最终Snapshot并完成对账。
3. `T日切换窗口`：初始化Domain、核对数量、开启写权限。
4. `T日生效时间`：员工开始在OMS录入，Excel Current维护停止。
5. `T+1日`：完成首日Current与Audit复核。

当前`cutover_date`保持`PENDING`，不得在V2通过前填写为已执行。

## 三、切换日四大Domain初始状态

### 3.1 Sales

```text
initialization_status = CONDITIONAL
```

- 若Cutover前Sales候选Sheet完成业务签认、对账和质量验收，则从Snapshot初始化已确认Sales Current。
- 若未通过，则仅迁移Sales Historical；Sales Current为空且标记`NOT_INITIALIZED`。
- 生效后首条Sales Current由有权限的销售人员在OMS创建，禁止从历史候选自动升级。

### 3.2 Finance

```text
initialization_status = HISTORICAL_ONLY
current_status = NOT_INITIALIZED
```

- 迁移可追溯的Finance Historical。
- 不从历史流水倒推余额、待收或待付。
- Cutover期初资金状态由EMP004刘晶在OMS录入，EMP003张敬东复核后发布为Finance Current。

### 3.3 Room

```text
initialization_status = MASTER_DATA_AND_HISTORICAL
current_status = NOT_INITIALIZED
```

- 初始化42间房的Room Master Data及可确认历史记录。
- 42间房存在不等于42间房当前状态已经确认。
- EMP008刘芳羽在OMS逐房确认Cutover时点状态，发布后形成Room Current。

### 3.4 Actual Stay

```text
initialization_status = CONTRACT_PLAN_AND_HISTORICAL
current_status = NOT_INITIALIZED
```

- 迁移经确认的Contract Stay Plan及历史记录。
- 不从合同、预产期、计划晚数或房态历史推算实际入住。
- EMP008刘芳羽通过OMS逐条办理或确认真实入住，形成Actual Stay Current。

## 四、11名EMP首次操作

所有首次操作必须先完成飞书身份、EMP、姓名、role_code、workspace一致性校验。

| EMP | 飞书正式姓名 | 首次操作 | 结果与边界 |
| --- | --- | --- | --- |
| EMP001 | 石磊 | 审批Cutover并查看四域初始化摘要 | 只批准切换和查看全局，不代替责任人录入业务事实 |
| EMP002 | 宗惠 | 核对11人ACTIVE状态、角色和工作台权限 | 输出身份与权限核验结果，不修改四大Domain |
| EMP003 | 张敬东 | 复核财务期初状态及首笔财务记录 | 复核通过后允许Finance Current发布 |
| EMP004 | 刘晶 | 在OMS录入期初资金状态或首笔真实财务业务 | 生成Finance候选Current，等待规定复核 |
| EMP005 | 石昊盺 | 验证行政采购工作台及本人权限 | 不具备四大Domain发布权限，不代录经营Current |
| EMP006 | 杨欢欢 | 确认或创建首条真实销售合同/收款状态 | 生成Sales Current，重大金额按规则复核 |
| EMP007 | 薛子渝 | 验证本人销售责任范围并录入授权范围内首条销售业务 | 只能操作本人责任范围，不获得销售全局发布权 |
| EMP008 | 刘芳羽 | 逐房确认42间房状态并办理/确认真实入住 | 生成Room Current与Actual Stay Current |
| EMP009 | 尚丽娜 | 复核入住资料、房号及房态一致性 | 记录差异，不得覆盖EMP008已发布事实 |
| EMP010 | 陈晶辉 | 验证产护工作台并确认首个已授权服务事项 | 不推算或修改Actual Stay事实 |
| EMP011 | 周志朋 | 验证料理工作台并确认首个已授权服务事项 | 不推算或修改Actual Stay事实 |

首次操作不得使用共享账号、虚拟用户、fallback身份或岗位代称。

## 五、Current生成事件

### 5.1 通用事件链

```text
domain.current.creation.requested
-> permission.checked
-> domain.current.created
-> domain.current.validated
-> domain.current.published
```

任何校验失败发布：

```text
domain.current.creation.failed
```

### 5.2 Domain事件

| Domain | 首次Current事件 | 责任人 |
| --- | --- | --- |
| Sales | `sales.current.created`、`sales.current.published` | EMP006；授权范围内可由EMP007创建 |
| Finance | `finance.current.created`、`finance.current.reviewed`、`finance.current.published` | EMP004创建，EMP003复核 |
| Room | `room.current.initialized`、`room.current.published` | EMP008 |
| Actual Stay | `stay.actual.created`、`stay.actual.published` | EMP008 |

每个事件必须包含：

- `event_id`
- `cutover_id`
- `actor_emp_id`
- `domain`
- `entity_id`
- `previous_version`
- `current_version`
- `reason`
- `occurred_at`
- `correlation_id`

事件发布本身不得绕过Domain校验或审批。

## 六、首次Snapshot

### 6.1 Cutover Snapshot

Cutover使用的首次Snapshot记录初始化迁移结果，而不是伪造四域Current。

Snapshot必须分别记录：

- `current_count`
- `historical_count`
- `plan_count`
- `master_data_count`
- `quarantine_count`
- `initialization_status`
- `not_initialized_reason`
- `responsible_emp_id`
- `post_cutover_entry_plan`

### 6.2 Snapshot规则

1. Snapshot必须为PASS才能进入`READY`。
2. Current缺失可接受，但必须明确标记`NOT_INITIALIZED`和责任人。
3. Historical、Plan和Master Data不能计入Current数量。
4. Snapshot激活后不可修改。
5. Cutover后产生的Current进入Domain版本链，不回写初始化Snapshot。

### 6.3 首日运行快照

Cutover生效后生成独立的`Operational Baseline Snapshot`，用于记录员工首次操作后的真实Domain Current状态。它引用Cutover Snapshot，但不替换或覆盖Cutover Snapshot。

## 七、执行步骤

### 7.1 切换前

1. 确认最终迁移文件版本和Sheet语义。
2. 运行Data Quality并生成候选Snapshot。
3. 验证Historical、Plan、Master Data和Current分类。
4. 验证11人身份与权限。
5. EMP001批准Cutover。

### 7.2 切换窗口

1. 将Cutover状态设为`VALIDATING`。
2. 从PASS Snapshot初始化Domain基线。
3. 核对数量、金额、主键和追溯关系。
4. 将Cutover状态设为`READY`。
5. 开启员工OMS写权限。
6. 在生效时间停止Excel Current维护。

### 7.3 生效后

1. 11名员工完成首次登录和职责内操作。
2. 各责任人生成四大Domain实际需要的Current。
3. EMP001查看经营摘要和数据健康状态。
4. 生成Operational Baseline Snapshot。
5. Cutover状态设为`ACTIVE`。

## 八、异常处理

### 8.1 Snapshot或初始化失败

- 不开启员工写权限。
- Cutover保持`BLOCKED`或标记`ABORTED`。
- 保留V1和失败候选全部证据。
- 修正后生成新Snapshot版本，禁止原地修改。

### 8.2 EMP首次操作失败

- 记录失败EMP、权限、动作、时间和错误。
- 不允许其他无责任人员代替写入。
- 身份或权限修复后由原责任人重试。

### 8.3 Current录入错误

```text
Data Issue
-> Responsibility Assignment
-> Approval if required
-> OMS Correction Command
-> New Domain Version
-> Audit/Event
```

禁止通过Excel覆盖Current，禁止物理删除错误历史。

### 8.4 OMS临时不可用

- 启动受控应急记录，记录操作者、时间、业务事实和原因。
- OMS恢复后，应急记录经过Data Quality、权限和复核后补录。
- 应急Excel或纸质记录不能自动写入Current。

### 8.5 跨Domain不一致

Room与Actual Stay、Sales与Finance发生冲突时进入`CONFLICT`，阻止相关发布并通知责任人。禁止用任一历史或计划数据自动覆盖另一Domain Current。

## 九、Cutover验收

| 验收项 | 通过标准 |
| --- | --- |
| Cutover Date | 已由EMP001批准并记录时区 |
| Cutover Snapshot | PASS、不可变、追溯完整 |
| Domain初始化 | 分类与Snapshot完全一致 |
| 身份权限 | 11/11真实EMP通过 |
| 首次操作 | 11/11完成职责内动作 |
| Current生成 | 由对应责任人通过OMS产生 |
| Audit/Event | 每个关键步骤可追溯 |
| Excel冻结 | 生效后不再维护日常Current |
| 老板验收 | EMP001能够看到真实经营状态及数据健康 |

## 十、当前状态

```text
TS-20260711-V1 = ACTIVE
TS-20260711-V2 = NOT GENERATED
cutover_date = PENDING
cutover_status = BLOCKED
production_release = NOT STARTED
```

本设计不执行任何切换动作。只有P0.17初始数据校准与V2验收完成后，才进入Cutover准备。
