# OMS 数据变更权限设计

阶段：P0.13.1 OMS Data Change Authorization

状态：设计冻结候选

## 一、目标与边界

本设计回答一个问题：谁可以改变 OMS 生产数据，以及改变到什么程度。

覆盖的 Truth Source：

- Sales
- Finance
- Room
- Stay
- Contract
- Customer

数据变更必须同时受身份、角色、责任范围、字段等级、变更类型和审批状态约束。任何一个条件不满足，都不能发布到生产 Truth Source。

统一权限链路：

```text
EMP
  -> user_id
  -> role_code
  -> responsibility_scope
  -> data_domain
  -> field_permission
  -> change_type
  -> approval_policy
  -> Truth Source publication
```

本阶段只定义权限，不实现代码，不修改页面，不改变业务 Engine。

## 二、身份与权限基础

### 2.1 唯一身份链

所有变更主体必须满足：

```text
有效 EMP
  -> 唯一启用 user_id
  -> 唯一有效 role_code
  -> 已登记的数据责任范围
```

权限判断不得直接使用姓名、昵称、工作台名称或前端传入的角色文字。

### 2.2 强制身份字段

每个变更请求必须包含：

| 字段 | 必填 | 说明 |
|---|---:|---|
| `actor_emp_id` | 是 | Master Data 中的正式 EMP |
| `actor_user_id` | 是 | 与 EMP 强绑定的启用 user_id |
| `actor_role_code` | 是 | Master Data 返回的有效 role_code |
| `data_domain` | 是 | 目标数据 Domain |
| `record_id` | 条件必填 | 修改、缺失、冲突必须提供 |
| `change_type` | 是 | NEW / CHANGED / MISSING / CONFLICT |
| `field_changes` | 是 | 字段级前值与后值 |
| `reason` | 是 | 业务原因，禁止空原因 |
| `source_file` | 是 | 来源文件 |
| `source_sheet` | 是 | 来源 Sheet |
| `source_version` | 是 | 来源版本 |
| `correlation_id` | 是 | Audit、审批、质量报告关联 ID |

### 2.3 权限判定公式

```text
allow_change =
  emp_is_active
  AND user_id_is_bound_and_active
  AND role_code_is_current
  AND domain_is_in_responsibility_scope
  AND operation_is_allowed
  AND fields_are_allowed
  AND approval_requirement_is_satisfied
  AND data_quality_gate_is_passed
```

禁止任何 fallback 身份、虚拟用户、共享账号、群身份、仅岗位无 EMP 的操作主体。

## 三、变更角色模型

每类生产数据必须定义四种操作责任：

| 角色 | 英文标识 | 职责 |
|---|---|---|
| 创建者 | Creator | 提交新业务事实，不直接使其生效 |
| 修改者 | Modifier | 对现有记录提出字段变更，不覆盖原版本 |
| 审核者 | Reviewer | 核实业务事实、重大字段和变更原因 |
| 发布者 | Publisher | 激活已通过审核和质量检查的版本 |

发布者只能发布候选版本，不得在发布动作中修改字段内容。发现问题必须退回创建者或修改者重新提交。

### 3.1 权限操作码

权限实现阶段应使用以下稳定操作码：

- `DATA_CREATE`
- `DATA_CHANGE`
- `DATA_REVIEW`
- `DATA_PUBLISH`
- `DATA_REJECT`
- `DATA_QUARANTINE`
- `DATA_RESOLVE_CONFLICT`
- `DATA_VIEW_HISTORY`

`role_code` 只定义最大能力边界；实际授权还必须经过《OMS生产数据责任矩阵》中的责任绑定。

### 3.2 四权分离

重大字段必须遵守：

```text
submitter_emp_id != reviewer_emp_id
```

原则上：

```text
reviewer_emp_id != publisher_emp_id
```

当前组织规模无法完全三人分离时，Reviewer 可以兼任 Publisher，但必须满足：

- 创建者或修改者与 Reviewer 不同。
- Data Quality Layer 已通过。
- 无未解决 Conflict。
- Audit 完整记录 Reviewer 兼任 Publisher。
- 重大例外增加 `ROLE_OWNER` 二次批准。

## 四、六类 Truth Source 权限矩阵

### 4.1 总矩阵

| Truth Source | 创建者 | 修改者 | 审核者 | 发布者 |
|---|---|---|---|---|
| Sales | `ROLE_SALES`，且在销售责任范围 | `ROLE_SALES`，仅本人或获授权客户范围 | 指定销售负责人；金额相关由 `ROLE_ACCOUNTANT` | 指定销售负责人；重大例外由 `ROLE_OWNER` |
| Finance | `ROLE_CASHIER` | `ROLE_CASHIER`，仅未发布候选或更正申请 | `ROLE_ACCOUNTANT` | `ROLE_ACCOUNTANT`；重大例外由 `ROLE_OWNER` 二次批准 |
| Room | `ROLE_STORE_MANAGER`；现场人员只能提交变化请求 | `ROLE_STORE_MANAGER` | 非本人提交时由指定店总复核；本人提交重大变更由 `ROLE_OWNER` 复核 | `ROLE_STORE_MANAGER`；冲突与重大例外由 `ROLE_OWNER` |
| Stay | `ROLE_BUTLER` / `ROLE_STORE_MANAGER` | `ROLE_BUTLER` / `ROLE_STORE_MANAGER`，按负责客户范围 | `ROLE_STORE_MANAGER` | `ROLE_STORE_MANAGER`；重大例外由 `ROLE_OWNER` |
| Contract | `ROLE_SALES` | `ROLE_SALES`，按负责客户范围 | 业务字段由指定销售负责人；金额由 `ROLE_ACCOUNTANT` | 指定销售负责人；金额重大变更需 `ROLE_ACCOUNTANT` 审核后发布 |
| Customer | `ROLE_SALES`；入住现场字段由 `ROLE_BUTLER` 提交变更请求 | `ROLE_SALES` 按客户范围；运营字段由 `ROLE_BUTLER` 按 Stay 范围 | 销售字段由指定销售负责人；入住相关由 `ROLE_STORE_MANAGER` | 对应 Domain 负责人；重大状态变更按本设计审批 |

“指定销售负责人”“指定店总”必须解析为责任矩阵中的具体 EMP，不能仅凭相同 `role_code` 自动获得审核权。

### 4.2 Sales 权限

| 操作 | 允许主体 | 限制 |
|---|---|---|
| 创建销售线索 | `ROLE_SALES` | 仅创建本人负责记录 |
| 修改跟进信息 | `ROLE_SALES` | 仅本人客户或书面转交范围 |
| 修改销售阶段 | `ROLE_SALES` | 终态变化需要销售负责人审核 |
| 确认成交 | 指定销售负责人 | 必须关联有效 Contract |
| 修改成交金额 | 创建者提交；`ROLE_ACCOUNTANT` 审核 | 属于重大字段 |
| 发布 Sales 当前记录 | 指定销售负责人 | Data Quality PASS 后发布 |

`ROLE_OWNER` 有查看与例外审批权，不作为日常销售录入人。

### 4.3 Finance 权限

| 操作 | 允许主体 | 限制 |
|---|---|---|
| 创建收入/支出候选 | `ROLE_CASHIER` | 必须有凭证与来源 |
| 修改未发布候选 | 原创建人或被授权 `ROLE_CASHIER` | 已发布记录不得原地修改 |
| 提交更正 | `ROLE_CASHIER` | 生成 CHANGED，不覆盖原流水 |
| 审核金额与方向 | `ROLE_ACCOUNTANT` | 审核人与提交人必须不同 |
| 发布 Finance 记录 | `ROLE_ACCOUNTANT` | 必须通过质量检查 |
| 重大例外发布 | `ROLE_ACCOUNTANT` + `ROLE_OWNER` | 冲突、无凭证、跨期重大调整 |

任何角色都不得物理删除财务流水。

### 4.4 Room 权限

| 操作 | 允许主体 | 限制 |
|---|---|---|
| 创建房间主数据 | `ROLE_OWNER` 或受控主数据管理员 | 不属于日常房态维护 |
| 提交现场房态变化 | 已授权现场 EMP | 只生成变更请求，不直接发布 |
| 修改当前房态 | `ROLE_STORE_MANAGER` | 必须符合 Room 生命周期 |
| 修改房号 | 仅主数据更正申请 | 重大字段，不能作为普通房态修改 |
| 审核入住占用/调房 | `ROLE_STORE_MANAGER` | 本人提交时重大变更需第二审核人 |
| 发布 Room 当前状态 | `ROLE_STORE_MANAGER` | Conflict 未解决不得发布 |
| 发布冲突例外 | `ROLE_OWNER` | 必须记录现场证据和原因 |

`ROLE_BUTLER` 可以提交入住现场变化，但不能直接改写 Room Truth Source。

### 4.5 Stay 权限

| 操作 | 允许主体 | 限制 |
|---|---|---|
| 创建入住计划 | `ROLE_BUTLER` / `ROLE_STORE_MANAGER` | 必须关联 Customer/Contract 或批准例外 |
| 修改普通服务字段 | `ROLE_BUTLER` | 仅负责客户范围 |
| 修改入住日期 | 提交者可为 `ROLE_BUTLER` / `ROLE_STORE_MANAGER` | 重大字段，需店总审核 |
| 修改房间关联 | 提交者可为 `ROLE_BUTLER` / `ROLE_STORE_MANAGER` | 重大字段，需同时校验 Room 冲突 |
| 确认实际入住/出馆 | `ROLE_STORE_MANAGER` | 现场记录完整，保留前后状态 |
| 发布 Stay 当前记录 | `ROLE_STORE_MANAGER` | Data Quality PASS 后发布 |

### 4.6 Contract 权限

| 操作 | 允许主体 | 限制 |
|---|---|---|
| 创建合同候选 | `ROLE_SALES` | 必须绑定客户和来源 |
| 修改非金额字段 | 原销售或销售负责人 | 已签约关键条款变更需审核 |
| 修改合同金额 | `ROLE_SALES` 提交 | `ROLE_ACCOUNTANT` 审核；重大例外需 `ROLE_OWNER` |
| 修改合同状态 | 指定销售负责人 | 退款、终止属于重大状态 |
| 确认到账 | 禁止 Sales 直接确认 | 只能由 Finance 流程确认 |
| 发布 Contract | 指定销售负责人 | 金额审核完成且质量检查通过 |

### 4.7 Customer 权限

| 操作 | 允许主体 | 限制 |
|---|---|---|
| 创建客户 | `ROLE_SALES` | 必须在本人责任范围 |
| 修改联系与跟进字段 | 对应 `ROLE_SALES` | 保留变更历史 |
| 修改入住相关字段 | `ROLE_BUTLER` 提交，`ROLE_STORE_MANAGER` 审核 | 不得反向篡改销售合同 |
| 合并重复客户 | 指定销售负责人提交 | 需审核，保留被合并 ID |
| 修改客户状态 | 指定销售负责人 | 结束、退款、失效需跨域确认 |
| 发布 Customer 当前记录 | 指定销售负责人 | 冲突客户不得发布 |

## 五、变更类型权限

### 5.1 NEW

```text
Creator 创建候选
  -> Data Quality 检查
  -> Reviewer 审核关键事实
  -> Publisher 发布
  -> 新版本进入 current_records 或 historical_records
```

权限要求：

- Creator 对目标 Domain 有 `DATA_CREATE`。
- Reviewer 有 `DATA_REVIEW` 且在对应责任范围。
- Publisher 有 `DATA_PUBLISH`。
- 新记录未发布前不能进入页面、Metrics 或 AI Context。

### 5.2 CHANGED

```text
Modifier 提交前值/后值和原因
  -> 字段级权限校验
  -> 重大字段审批（如需要）
  -> Data Quality 重检
  -> Publisher 激活新版本
  -> 旧版本转历史
```

权限要求：

- Modifier 只能修改获授权字段。
- 已发布记录不得原地覆盖。
- 每次修改必须包含字段 diff、原因和来源证据。
- Reviewer 不能在审核时直接改内容。

### 5.3 MISSING

`MISSING` 只能由 Data Quality Layer 根据版本差异生成，人工用户不能直接把记录标记为已删除。

```text
Data Quality 识别缺失
  -> Owner 说明原因
  -> Reviewer 判断漏录/结束/迁移/错误删除
  -> Publisher 发布终止版本或恢复记录
```

权限要求：

- Owner 有 `DATA_CHANGE`，只能提交处置说明。
- Reviewer 决定处置类型。
- Publisher 只能发布已确认的终止或恢复结果。
- 禁止物理删除。

### 5.4 CONFLICT

`CONFLICT` 由 Data Quality Layer 或跨 Domain 校验产生。

```text
Conflict -> Quarantine
  -> 各 Domain Owner 提交证据
  -> 指定 Reviewer 审核
  -> 跨域冲突由 ROLE_OWNER 裁决
  -> Data Quality 重检
  -> Publisher 发布解决后的唯一版本
```

权限要求：

- 冲突当事记录的 Creator/Modifier 不能单独解除 Quarantine。
- `DATA_RESOLVE_CONFLICT` 必须绑定指定 Reviewer 或 `ROLE_OWNER`。
- 未解决冲突不得进入当前 Truth Source。

## 六、字段风险等级

### 6.1 字段分级

| 等级 | 定义 | 示例 | 控制要求 |
|---|---|---|---|
| L1 普通字段 | 不改变金额、生命周期或资源占用 | 备注、非关键联系信息 | 授权 Modifier 可改，保留 Audit |
| L2 业务字段 | 改变业务进度但不直接改变资金或资源占用 | 销售阶段、预计入住日期 | 负责人审核或规则审核 |
| L3 重大字段 | 改变合同、资金、入住、房间或客户终态 | 合同金额、到账金额、实际入住日期、房号、客户结束状态 | 强制人工审批与双人控制 |
| L4 受限字段 | 主数据身份、已发布不可变事实、审计字段 | record_id、EMP、source hash、Audit | 禁止普通变更，只能受控更正或永不修改 |

### 6.2 重大字段审批矩阵

| 重大字段 | 提交者 | 必须审核 | 发布者 | 是否需要审批 |
|---|---|---|---|---|
| 合同金额 | `ROLE_SALES` | `ROLE_ACCOUNTANT` | 指定销售负责人或受控发布者 | 是 |
| 到账金额 | `ROLE_CASHIER` | `ROLE_ACCOUNTANT` | `ROLE_ACCOUNTANT` | 是 |
| 实际入住日期 | `ROLE_BUTLER` / `ROLE_STORE_MANAGER` | `ROLE_STORE_MANAGER`；提交审核同人时增加第二授权人 | `ROLE_STORE_MANAGER` | 是 |
| 房号/房间关联 | `ROLE_BUTLER` 提交或 `ROLE_STORE_MANAGER` 修改 | `ROLE_STORE_MANAGER` + Room 冲突校验 | `ROLE_STORE_MANAGER` | 是 |
| 房间主数据房号 | 受控主数据管理员 | `ROLE_OWNER` | `ROLE_OWNER` | 是，且只允许更正 |
| 客户状态转成交 | `ROLE_SALES` | 指定销售负责人，且存在有效 Contract | 指定销售负责人 | 是 |
| 客户状态转退款/结束 | 销售负责人 | `ROLE_ACCOUNTANT` 确认资金，运营终态由 `ROLE_STORE_MANAGER` 确认 | 对应 Domain Publisher | 是 |

### 6.3 审批结果

重大字段变更状态：

- `PENDING_REVIEW`
- `APPROVED`
- `REJECTED`
- `EXPIRED`

只有 `APPROVED` 且 Data Quality PASS 的候选版本可以发布。审批通过不等于已经发布，发布也不等于自动执行业务动作。

## 七、审批链设计

### 7.1 ChangeApprovalRequest

每个重大字段变更审批必须包含：

- `change_request_id`
- `data_domain`
- `record_id`
- `change_type`
- `field_changes`
- `requester_emp_id`
- `requester_user_id`
- `requester_role_code`
- `reviewer_emp_id`
- `reason`
- `source_file`
- `source_sheet`
- `source_version`
- `quality_report_id`
- `correlation_id`
- `requested_at`

### 7.2 ChangeApprovalDecision

审批决定必须包含：

- `approval_id`
- `change_request_id`
- `reviewer_emp_id`
- `reviewer_user_id`
- `reviewer_role_code`
- `decision_status`
- `decision_reason`
- `decided_at`
- `execution_authorized=false`
- `publication_authorized`

`publication_authorized=true` 只允许进入发布校验，不允许绕过 Data Quality Layer，也不触发 Room、Stay、Payment 等业务 Engine。

### 7.3 审批失效

以下情况使审批失效：

- 候选记录在审批后再次变化。
- 来源文件版本或 Sheet 结构变化。
- Reviewer 的 EMP、user_id 或 role_code 失效。
- 审批超过规定有效期。
- Data Quality 重检产生新 Conflict。

失效后必须重新提交，不得复用旧审批。

## 八、发布权限

### 8.1 发布前置条件

Publisher 必须验证：

1. EMP、user_id、role_code 当前有效。
2. Publisher 在对应责任范围内。
3. 变更请求状态有效。
4. 重大字段审批为 `APPROVED`。
5. Data Quality Layer 结论允许准入。
6. 无未解决 Conflict。
7. Truth Source 目标版本未被其他批次抢先更新。
8. Audit 与 correlation_id 完整。

### 8.2 发布行为

发布只能：

- 将候选版本写入 versioned Truth Source。
- 激活新的 current 版本或 historical 版本。
- 将旧 current 版本转入历史。
- 写 Audit 和 Event。

发布不能：

- 修改候选字段。
- 补造缺失字段。
- 跳过审批。
- 删除旧版本。
- 直接修改页面缓存。

### 8.3 并发保护

发布必须使用目标 Truth Source 的版本号进行乐观锁检查。若基准版本已变化：

```text
publication = REJECTED_VERSION_CONFLICT
```

候选记录回到 Conflict 或重新评估流程，禁止后写覆盖先写。

## 九、权限拒绝规则

以下情况必须拒绝：

- EMP 不存在、停用或离职。
- user_id 缺失、未绑定或与 EMP 不一致。
- role_code 缺失、过期或不在 Domain 允许范围。
- 只有姓名、昵称、群或 workspace 标识。
- 不在责任范围内修改其他人的客户或记录。
- Creator 审核自己的重大字段变更。
- 未审批即发布重大字段。
- Publisher 尝试在发布时修改数据。
- MISSING 被当作物理删除。
- Conflict 未解决即发布。
- 未经过 Data Quality Layer。
- 前端声称有权限但后端 Master Data 不认可。

所有拒绝必须写 Audit，并向调用方返回稳定拒绝码和业务原因。

## 十、Audit 与 Event

### 10.1 Audit

必须记录：

- `data.change.requested`
- `data.change.permission.granted`
- `data.change.permission.denied`
- `data.change.review.requested`
- `data.change.review.approved`
- `data.change.review.rejected`
- `data.change.published`
- `data.change.publication.failed`

Audit 必须包含：

- `actor_emp_id`
- `actor_user_id`
- `actor_role_code`
- `data_domain`
- `record_id`
- `change_type`
- `field_changes`
- `field_risk_level`
- `reviewer_emp_id`
- `publisher_emp_id`
- `decision`
- `reason`
- `source_version`
- `quality_report_id`
- `correlation_id`
- `timestamp`

### 10.2 Event

建议发布：

- `data.change.requested`
- `data.change.review.completed`
- `data.change.publication.completed`
- `data.change.publication.failed`
- `data.change.conflict.detected`

Event 不自动修改业务状态，不自动审批，不自动解除 Quarantine。

## 十一、Truth Source 权限声明

每个 Truth Source manifest 必须登记：

```json
{
  "data_domain": "Sales",
  "creator_role_codes": ["ROLE_SALES"],
  "modifier_role_codes": ["ROLE_SALES"],
  "reviewer_role_codes": ["ROLE_SALES", "ROLE_ACCOUNTANT"],
  "publisher_role_codes": ["ROLE_SALES", "ROLE_OWNER"],
  "major_fields": ["contract_amount", "customer_status"],
  "responsibility_version": "p0.13.1",
  "physical_delete_allowed": false
}
```

该声明只定义角色上限。最终权限仍需结合具体 EMP、user_id 和责任范围解析，不能因为同角色就获得全部记录权限。

## 十二、前端与 API 边界

- 前端只能显示后端返回的允许动作，不能自行计算权限。
- 隐藏按钮不等于权限控制；所有写操作必须由服务端重新校验。
- API 必须接收 `actor_emp_id` 对应的认证上下文，不能信任请求体自报 role_code。
- API 返回 `allowed_actions` 时，只能作为界面提示。
- 所有提交必须具有幂等键，防止重复点击产生重复变更。
- 查询权限与变更权限分离；可以查看不代表可以修改。

## 十三、验收标准

P0.13.1 后续实现必须满足：

1. Sales、Finance、Room、Stay、Contract、Customer 均定义 Creator、Modifier、Reviewer、Publisher。
2. 每次变更均通过 `EMP -> user_id -> role_code` 验证。
3. 相同 role_code 不能绕过记录责任范围。
4. NEW、CHANGED、MISSING、CONFLICT 均有明确权限流。
5. 合同金额、到账金额、入住日期、房号和客户状态均强制审批。
6. 重大字段提交人与审核人不能相同。
7. 未审批或审批失效的变更不能发布。
8. Publisher 不能在发布时修改内容。
9. MISSING 不触发物理删除。
10. Conflict 未解决不能进入生产 Truth Source。
11. 虚拟用户、fallback 用户、共享账号操作数量为 0。
12. 所有授权、拒绝、审核和发布均可通过 Audit 追溯。

## 十四、设计结论

OMS 数据变更权限链冻结为：

```text
真实 EMP 身份
  -> user_id 强绑定
  -> role_code 最大权限
  -> responsibility_scope 记录范围
  -> field_permission 字段范围
  -> approval_policy 重大字段审批
  -> Data Quality Gate
  -> Publisher 原子发布
  -> versioned Truth Source
```

最终原则：

```text
能看不等于能改；
能改不等于能审；
能审不等于已发布；
发布不能改变内容；
没有真实身份，不允许发生生产变更。
```
