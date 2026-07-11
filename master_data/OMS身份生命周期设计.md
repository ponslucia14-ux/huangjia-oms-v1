# OMS 身份生命周期设计

阶段：P0.13.5  
版本：1.0  
状态：Design  
日期：2026-07-10  
唯一身份源：飞书生产身份 + OMS 组织主数据

## 一、目标

本设计用于处理员工从加入组织到离开组织期间的身份连续性，覆盖：

- 新员工入职。
- 员工离职。
- 员工转岗或调部门。
- 员工正式改名。

OMS 身份主链固定为：

```text
Feishu user_id
-> Feishu 生产真实姓名
-> EMP
-> role_code
-> workspace
-> responsibility_scope
-> identity_status
```

生命周期变化不得破坏历史 Audit、合同、业务记录、任务归属和数据责任记录。

## 二、核心标识

| 标识 | 是否可变 | 规则 |
|---|---|---|
| `emp_id` | 否 | 员工在 OMS 中的永久编号；离职后不得复用 |
| `feishu_user_id` | 原则上否 | 同一飞书生产账号保持不变；账号迁移必须进入人工核验 |
| `open_id` | 受应用范围影响 | 变化时保留历史值并记录新旧关系 |
| `union_id` | 受平台身份影响 | 变化时必须验证是否仍为同一自然人 |
| `official_name` | 是 | 只允许由飞书生产正式姓名触发变更 |
| `role_code` | 是 | 转岗后生成新版本，不覆盖历史版本 |
| `workspace_key` | 是 | 与当前岗位版本绑定 |
| `responsibility_scope` | 是 | 与当前角色、岗位和数据责任版本绑定 |

禁止通过姓名、昵称、岗位代称或备注名创建身份主键。

## 三、身份状态

### ACTIVE

定义：身份已通过飞书生产校验，员工在职，当前角色、workspace 和权限有效。

要求：

- `emp_id`、`feishu_user_id`、正式姓名均已确认。
- 当前 `role_code` 和 `workspace_key` 唯一。
- 权限只按当前有效角色生效。
- 可接收任务、审批、通知和数据责任。

### INACTIVE

定义：员工已离职、停用或不再具有 OMS 执行资格。

要求：

- 禁止登录工作台。
- 禁止新增任务、审批、通知和数据责任分配。
- 撤销活动权限，不删除权限历史。
- 保留历史 Audit、合同、任务、审批、数据责任和 workspace 快照。
- `emp_id` 和历史 `feishu_user_id` 永久保留且不得复用。

### TRANSFERRED

定义：旧岗位版本已结束，员工已转入新部门、角色或 workspace。

要求：

- `emp_id` 和 `feishu_user_id` 不变。
- 旧角色和旧 workspace 版本标记为 `TRANSFERRED`。
- 创建新的 ACTIVE 角色版本和 workspace 绑定。
- 旧权限立即失效，新权限在审核通过后生效。
- 历史业务仍引用旧角色快照，不回写为新岗位。

`TRANSFERRED` 是岗位版本状态，不代表员工身份失效。

### PENDING_VERIFY

定义：身份新增或变更已被发现，但证据不完整、存在冲突或尚未审核。

适用情况：

- 新员工尚未完成飞书 user_id 核验。
- 飞书账号、姓名或组织关系发生无法自动确认的变化。
- 同一 user_id 对应多个 EMP。
- 同一 EMP 出现多个活动 user_id。
- 转岗信息尚未获得组织负责人确认。

限制：

- 不得授予生产写权限。
- 不得进入员工工作台。
- 不得成为任务执行人、审批人或数据 Owner。
- 可以保留待核验记录和核验 Audit。

## 四、状态迁移

```text
新身份发现
  -> PENDING_VERIFY
  -> ACTIVE

ACTIVE
  -> PENDING_VERIFY      身份证据发生冲突
  -> TRANSFERRED         岗位版本结束
  -> INACTIVE            离职或停用

TRANSFERRED
  -> ACTIVE              新岗位审核通过
  -> PENDING_VERIFY      新岗位证据不完整
  -> INACTIVE            转岗期间离职

PENDING_VERIFY
  -> ACTIVE              核验通过
  -> INACTIVE            核验确认不再启用

INACTIVE
  -> PENDING_VERIFY      重新入职申请
  -> ACTIVE              禁止直接迁移
```

任何状态迁移必须是事务化操作：

```text
验证证据
-> 写入身份版本
-> 更新权限状态
-> 更新 workspace 状态
-> 更新数据责任状态
-> 写 Audit
-> 发布 Event
-> 提交
```

任一步失败，活动身份不得部分更新。

## 五、新员工规则

1. 从飞书生产组织发现新成员。
2. 创建新的永久 `emp_id`，不得复用历史 EMP。
3. 初始状态必须为 `PENDING_VERIFY`。
4. 核对 user_id、正式姓名、部门、岗位和直属责任关系。
5. 指定 `role_code`、workspace 和 responsibility scope。
6. 完成权限审核后切换为 `ACTIVE`。
7. ACTIVE 后方可登录、接收任务或承担数据责任。

禁止因群成员、昵称、Excel 姓名或历史聊天记录自动激活新员工。

## 六、离职规则

离职生效时执行：

1. 身份状态改为 `INACTIVE`。
2. 关闭登录和工作台访问。
3. 撤销活动权限、审批资格和通知目标资格。
4. 停止新增任务分配。
5. 将未完成任务转入责任移交队列，不自动转给其他人。
6. 将数据 Owner 责任转入待确认状态，等待新 Owner 审批生效。
7. 保留全部历史业务和身份版本。

禁止：

- 物理删除员工。
- 删除或改写历史 Audit。
- 将离职员工 EMP 或 user_id 分配给其他人。
- 将历史合同、任务或数据责任中的姓名改成接任人。

## 七、转岗规则

转岗必须生成新的岗位版本：

```text
原 role/workspace version
-> TRANSFERRED

新 role/workspace version
-> PENDING_VERIFY
-> ACTIVE
```

转岗记录至少包含：

- `transfer_id`。
- `emp_id`。
- `effective_time`。
- 原部门、原 `role_code`、原 workspace。
- 新部门、新 `role_code`、新 workspace。
- 原权限、新权限。
- 原 responsibility scope、新 responsibility scope。
- 发起人、审核人、原因和证据。

生效原则：

- 旧权限在生效时间关闭。
- 新权限不得提前生效。
- 生效中的任务按任务创建时的责任快照保留。
- 新任务只分配到新 workspace。
- 数据 Owner 变化必须单独完成责任矩阵审批。

## 八、改名规则

正式改名只允许由飞书生产身份触发。

规则：

1. `emp_id` 不变。
2. `feishu_user_id` 不变。
3. `role_code`、workspace 和权限不因改名自动改变。
4. 新姓名成为 `official_name`。
5. 原姓名进入 alias 历史，仅用于查询和追溯。
6. 当前工作台、权限主体显示和新 Audit 使用新姓名。
7. 历史 Audit、合同和已完成记录保留当时姓名快照，不覆盖。

如果 user_id 同时变化，则不得按普通改名处理，必须进入 `PENDING_VERIFY`。

## 九、权限联动

| 状态 | 登录 | 读取 | 写入 | 审批 | 接收任务 | 数据 Owner |
|---|---|---|---|---|---|---|
| ACTIVE | 允许 | 按角色 | 按角色 | 按角色 | 允许 | 可分配 |
| PENDING_VERIFY | 禁止 | 仅核验人员可查 | 禁止 | 禁止 | 禁止 | 禁止 |
| TRANSFERRED | 旧 workspace 禁止 | 历史只读 | 禁止 | 禁止 | 禁止新分配 | 旧责任待移交 |
| INACTIVE | 禁止 | 历史按审计权限 | 禁止 | 禁止 | 禁止 | 禁止新增 |

权限判断必须使用：

```text
emp_id
+ feishu_user_id
+ identity_status
+ active role version
+ role_code
+ responsibility_scope
```

姓名和 alias 不参与权限判断。

## 十、历史保留

以下内容必须永久保留：

- 身份状态历史。
- 姓名和 alias 历史。
- role/workspace 版本历史。
- 权限授予与撤销历史。
- 数据责任分配历史。
- 历史 Audit、合同、任务、审批和执行记录。

业务记录必须保存“发生时身份快照”，至少包含：

- `emp_id`。
- 当时正式姓名。
- 当时 `role_code`。
- 当时 workspace。
- 身份版本。

## 十一、Audit 与 Event

### Audit

- `identity.lifecycle.created`
- `identity.lifecycle.activated`
- `identity.lifecycle.deactivated`
- `identity.lifecycle.transferred`
- `identity.lifecycle.renamed`
- `identity.lifecycle.verify.requested`
- `identity.lifecycle.verify.completed`
- `identity.permission.revoked`
- `identity.responsibility.transfer.requested`

Audit 必须记录：

- actor EMP 与正式姓名。
- target EMP。
- 变更原因。
- 变更前后状态。
- 生效时间。
- 证据来源。
- correlation_id。

### Event

- `identity.pending_verify`
- `identity.activated`
- `identity.inactivated`
- `identity.transferred`
- `identity.renamed`
- `identity.permission.changed`
- `identity.responsibility.pending_transfer`

Event 只通知下游重新计算权限、workspace 和责任状态，不得直接修改业务历史。

## 十二、冲突与恢复

发现下列情况必须生成 `IDENTITY_CONFLICT` 并进入 `PENDING_VERIFY`：

- user_id 与正式姓名不一致。
- user_id 被多个 EMP 使用。
- EMP 同时绑定多个活动 user_id。
- 活动 workspace 与当前 role_code 不一致。
- INACTIVE 身份仍持有权限或任务。
- TRANSFERRED 旧角色仍可写入。
- 数据 Owner 指向非 ACTIVE 身份。

冲突解决顺序：

1. 飞书生产 user_id 和正式姓名。
2. OMS 永久 EMP。
3. 已审批的岗位变更记录。
4. 已审批的数据责任记录。

禁止通过人工自由选择、昵称匹配或 runtime fallback 解决冲突。

## 十三、验收标准

- 新员工未经核验不能进入生产：PASS。
- 离职身份不删除且权限归零：PASS。
- 转岗保留旧版本并生成新 role/workspace：PASS。
- 改名保持 user_id 与 EMP 不变：PASS。
- 历史 Audit、合同、任务和数据责任可追溯：PASS。
- 非 ACTIVE 身份不能成为执行人或 Owner：PASS。
- 所有状态迁移均有 Audit 与 Event：PASS。

## 十四、实施边界

本阶段仅完成设计，不修改现有身份代码、权限代码、业务 Engine、UI 或数据库。

下一阶段进入数据质量运营闭环实现时，身份状态必须作为数据 Owner、Reviewer、Publisher 和异常责任人的前置校验条件。
