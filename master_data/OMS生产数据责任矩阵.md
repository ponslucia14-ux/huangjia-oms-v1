# OMS 生产数据责任矩阵

阶段：P0.13 OMS Production Data Responsibility Matrix

状态：设计冻结候选

## 一、目标与原则

本矩阵明确每一类进入 OMS 的生产数据：

- 谁负责维护原始数据。
- 谁负责审核业务事实。
- 谁负责执行数据质量检查。
- 谁对最终经营口径承担责任。

本矩阵与《OMS数据质量层设计》共同构成生产数据治理门槛：

```text
业务责任确认
  -> Excel / External Source
  -> Data Quality Layer
  -> Truth Source
  -> Adapter
  -> Domain
  -> API
  -> Page / AI Context
```

核心原则：

1. 每个 Truth Source 必须有唯一主责岗位和有效 EMP 身份。
2. 维护、复核、质量检查和最终责任不得隐式混用。
3. 页面展示责任不能转嫁给前端或系统。
4. OMS 不替业务人员确认业务事实，只记录确认过程与责任链。
5. 姓名不能作为永久权限规则；岗位通过 Human Identity Layer 绑定当前有效 `emp_id`。
6. 任何岗位人员变更必须更新责任绑定，但不得改写历史责任记录。

## 二、数据责任模型

### 2.1 TruthSourceResponsibility

每个 Truth Source 必须登记以下字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `responsibility_id` | string | 是 | 责任登记唯一 ID |
| `data_domain` | string | 是 | Customer / Contract / Payment / Finance / Expense / Room / Stay / Stay Plan |
| `truth_source_key` | string | 是 | 目标 Truth Source 标识 |
| `source_file` | string | 是 | 经批准的来源文件或文件模式 |
| `source_sheet` | string | 是 | 经 Data Quality Layer 确认用途的 Sheet；禁止默认首 Sheet |
| `owner` | role + emp_id | 是 | 日常维护主责人 |
| `backup_owner` | role + emp_id | 是 | 主责人缺席时的授权备份人 |
| `reviewer` | role + emp_id | 是 | 业务事实复核人 |
| `accountable_owner` | role + emp_id | 是 | 最终业务责任人 |
| `update_frequency` | enum | 是 | realtime / daily / weekly / monthly / on_event |
| `update_method` | enum | 是 | Excel maintenance / controlled import / API / Feishu sync |
| `quality_check_owner` | role + emp_id | 是 | 数据质量报告处理与准入检查人 |
| `allowed_edit_roles` | array | 是 | 获准修改原始数据的岗位 |
| `confirmation_rules` | array | 是 | 金额、状态、时效等确认规则 |
| `effective_from` | datetime | 是 | 责任绑定生效时间 |
| `effective_to` | datetime/null | 是 | 责任绑定失效时间 |
| `responsibility_version` | string | 是 | 责任矩阵版本 |

`owner`、`backup_owner`、`reviewer`、`quality_check_owner` 必须解析到真实、有效、在职的 `emp_id`。身份未绑定时，对应数据不得自动进入生产 Truth Source。

### 2.2 责任角色定义

| 责任 | 定义 | 可以做什么 | 不能做什么 |
|---|---|---|---|
| Owner | 原始业务数据日常维护主责 | 新增、修正、提交导入 | 不能绕过复核处理关键冲突 |
| Backup Owner | Owner 缺席时的授权代理 | 在授权期内代办维护 | 不能长期与 Owner 并行产生双主责 |
| Reviewer | 确认业务事实和关键字段 | 批准、驳回、要求补充 | 不能直接篡改原始责任记录 |
| Quality Check Owner | 处理质量报告和准入问题 | 核查 Sheet、字段、时效、变更与冲突 | 不能代替业务 Reviewer 判断业务事实 |
| Accountable Owner | 对最终经营口径负责 | 处理跨域争议、批准重大例外 | 不代替岗位进行日常录入 |

### 2.3 当前岗位绑定

| 岗位责任 | 当前组织身份 | 说明 |
|---|---|---|
| 主理人 | 石磊 / EMP001 | 最终经营责任与跨域争议裁决 |
| 销售负责人 | 杨欢欢 / EMP006 / ROLE_SALES | 销售与签约客户数据主责 |
| 店总 | 刘芳羽 / EMP008 / ROLE_STORE_MANAGER | 房态、入住运营事实主责 |
| 财务经办 | 刘晶 / EMP004 / ROLE_CASHIER | 收入、支出、待收、待付日常维护 |
| 财务复核 | 张敬东 / EMP003 / ROLE_ACCOUNTANT | 合同金额、到账、支出与结算复核 |
| 管家 | 尚丽娜 / EMP009 / ROLE_BUTLER | 入住计划、实际入住资料与房态备份维护 |

最终生效时以 Human Identity Layer 中的有效 `emp_id` 为准。岗位或人员发生变化时，新绑定只影响后续责任记录。

## 三、第一批生产数据责任总表

| 数据集 | data_domain | source_file | source_sheet | owner | backup_owner | reviewer | accountable_owner | update_frequency | update_method | quality_check_owner |
|---|---|---|---|---|---|---|---|---|---|---|
| 销售明细 | Customer / Contract | 经批准的销售 Excel | 经质量层确认为当前销售明细的 Sheet | 销售负责人 | 店总 | 财务复核（金额）+ 主理人（规则例外） | 主理人 | daily + on_event | 员工维护 Excel，受控导入 | 销售负责人；金额异常由财务复核 |
| 销售到账关联 | Payment | 销售 Excel + 财务到账事实 | 经确认的签约/收款 Sheet | 财务经办 | 财务复核 | 财务复核 | 主理人 | daily | 受控导入与跨域关联 | 财务复核 |
| 财务流水 | Finance / Payment / Expense | 经批准的财务 Excel | 经质量层确认的收入、支出、待收、待付 Sheet | 财务经办 | 财务复核 | 财务复核 | 主理人 | daily | 员工维护 Excel，受控导入 | 财务复核 |
| 当前房态 | Room | 经批准的房态 Excel | 经质量层确认为当前房态的 Sheet | 店总 | 管家 | 店总；冲突由主理人裁决 | 主理人 | on_event + daily | 员工维护 Excel，受控导入 | 店总 |
| 入住事实 | Stay | 在住/入住登记 Excel | 经质量层确认为当前入住的 Sheet | 店总 | 管家 | 店总 | 主理人 | on_event + daily | 员工维护 Excel，受控导入 | 店总 |
| 签约客户 | Customer / Contract / Stay Plan | 经批准的签约客户 Excel | 经质量层确认的客户、合同、入住计划 Sheet | 销售负责人 | 店总 | 财务复核（金额/到账）+ 店总（入住计划） | 主理人 | daily + on_event | 员工维护 Excel，受控导入 | 销售负责人；跨域字段由对应 Reviewer 检查 |

表中的 `source_sheet` 必须在每次导入时解析为实际 Sheet 名，并写入数据质量报告与责任记录。文件名或 Sheet 名变化不能自动改变责任归属。

## 四、销售数据责任

### 4.1 责任范围

来源：销售 Excel。

目标 Domain：

- Customer。
- Contract。
- Payment（仅销售侧收款主张，最终到账由财务确认）。

### 4.2 权责划分

| 业务字段或动作 | 维护人 | 确认人 | 最终责任 |
|---|---|---|---|
| 客户基本资料 | 销售负责人及获授权销售 | 销售负责人 | 销售负责人 |
| 跟进状态 | 对应销售人员 | 销售负责人 | 销售负责人 |
| 签约日期与合同号 | 对应销售人员 | 销售负责人 | 销售负责人 |
| 合同套餐与合同金额 | 销售负责人 | 财务复核 | 主理人 |
| 优惠、赠送、特殊条款 | 销售负责人 | 主理人或已授权审批人 | 主理人 |
| 销售主张的已收金额 | 销售负责人 | 财务复核到账 | 财务复核 |
| 未收金额 | 系统由已确认合同金额与到账事实形成 | 财务复核 | 财务复核 |
| 退款或合同结束 | 销售负责人提出 | 财务复核金额，主理人确认例外 | 主理人 |

### 4.3 修改权限

可以修改销售原始数据：

- 对应销售人员：仅限本人客户的非关键跟进字段。
- 销售负责人：客户、合同和销售状态字段。
- 财务人员：不能修改销售业务字段，只能确认财务事实。
- 主理人：只处理授权例外，不作为日常录入人。

合同金额、已收、未收不得由同一销售动作同时完成最终确认。

### 4.4 进入 OMS 的时间

签约记录在以下条件全部满足后进入当前生产 Truth Source：

1. 合同号或稳定合同标识已建立。
2. 客户、签约日期、套餐、合同金额完整。
3. 销售负责人已提交。
4. 合同金额已由财务复核，或按规则进入“待财务确认”隔离状态。
5. Data Quality Layer 判定为当前有效合同。

未满足条件的记录只能进入 `REVIEW_REQUIRED` 或 Quarantine，不能进入销售中心当前成交口径。

## 五、财务数据责任

### 5.1 责任范围

来源：财务 Excel。

目标 Domain：

- Finance。
- Payment。
- Expense。

### 5.2 权责划分

| 财务事实 | 维护人 | 确认人 | 最终责任 |
|---|---|---|---|
| 收入记录 | 财务经办 | 财务复核 | 财务复核 |
| 支出记录 | 财务经办 | 财务复核 | 财务复核 |
| 实际到账 | 财务经办依据银行/现金凭证登记 | 财务复核 | 财务复核 |
| 待收 | 财务经办维护 | 财务复核合同与到账差额 | 财务复核 |
| 待付 | 财务经办维护 | 财务复核付款依据与到期日 | 财务复核 |
| 退款 | 财务经办维护 | 财务复核；重大例外由主理人确认 | 主理人 |
| 对账状态 | 财务经办 | 财务复核 | 财务复核 |
| 经营口径例外 | 财务复核提出 | 主理人 | 主理人 |

### 5.3 确认规则

- 收入必须关联实际到账凭证、客户或明确的其他收入类型。
- 支出必须关联支付对象、用途和凭证。
- 待收必须关联有效合同或明确应收依据。
- 待付必须关联已确认义务、预计付款时间和责任人。
- 汇总金额不能替代基础流水。
- 同一流水不得同时作为收入和支出，也不得重复导入。

未经财务复核的金额不得标记为“已确认”，不得进入老板经营摘要的确认口径。

## 六、房态与入住数据责任

### 6.1 责任范围

来源：房态 Excel、在住/入住登记 Excel。

目标 Domain：

- Room。
- Stay。

### 6.2 权责划分

| 业务事实 | 维护人 | 确认人 | 最终责任 |
|---|---|---|---|
| 房间基础状态 | 店总 | 店总 | 店总 |
| 房态修改 | 店总；授权时由管家代办 | 店总 | 店总 |
| 入住计划 | 管家维护，销售提供签约信息 | 店总 | 店总 |
| 实际入住 | 管家登记 | 店总确认 | 店总 |
| 调房记录 | 店总维护 | 店总 | 店总 |
| 实际出馆 | 管家登记 | 店总确认；财务结算状态独立确认 | 店总 |
| 维修/停用 | 店总维护 | 主理人仅确认重大资源影响 | 店总 |
| 房态冲突 | 店总处理 | 主理人裁决未解决冲突 | 主理人 |

### 6.3 房态修改规则

- 店总是当前房态唯一主责。
- 管家只能在授权范围内提交入住、出馆和现场变化，不得绕过店总确认关键状态。
- 销售不能直接修改 Room 状态。
- 财务结算未完成不自动阻止事实上的出馆记录，但必须形成独立风险。
- 每次状态变化必须保留前态、后态、生效时间、操作人和确认人。

### 6.4 入住与出馆确认

入住确认至少需要：客户、房号、实际入住时间、有效签约或批准例外。

出馆确认至少需要：客户、房号、实际出馆时间、店总确认。财务结算由 Finance Domain 独立负责，不得由 Room/Stay 数据替代。

## 七、签约客户数据责任

### 7.1 责任范围

来源：客户签约 Excel。

目标 Domain：

- Customer。
- Contract。
- Stay Plan。

### 7.2 字段责任拆分

| 字段组 | 维护责任 | 复核责任 |
|---|---|---|
| 客户身份与联系方式 | 销售 | 销售负责人 |
| 合同号、签约日期、套餐 | 销售 | 销售负责人 |
| 合同金额、已收、未收 | 销售提供合同信息；财务登记到账 | 财务复核 |
| 预产期、预计入住日期 | 销售首次录入 | 店总/管家确认运营计划 |
| 房型与房间需求 | 销售记录客户需求 | 店总确认资源含义，不等于实际分房 |
| 实际入住日期、房号 | 管家登记 | 店总确认 |
| 实际出馆日期 | 管家登记 | 店总确认 |
| 客户结束、退款 | 销售提出 | 财务复核金额，店总确认入住状态 |

签约后的销售事实在当日或下一个受控导入批次进入 OMS。入住计划只有经过店总或管家确认后，才能进入 Stay Plan 当前口径；签约不等于入住。

## 八、数据修改责任

### 8.1 变化责任矩阵

所有业务变化必须进入以下状态之一：

| change_type | 发起责任 | 确认责任 | OMS 处理 |
|---|---|---|---|
| `NEW` | 对应 Domain Owner | Reviewer | 通过质量门槛后新增当前或历史记录 |
| `CHANGED` | 对应 Domain Owner | 关键字段由 Reviewer 确认 | 保留旧版本，生成新版本，不覆盖历史 |
| `MISSING` | Data Quality Layer 识别 | Owner 说明原因，Reviewer 确认处置 | 不自动删除，进入待确认或结束流程 |
| `CONFLICT` | Data Quality Layer 识别 | Owner 与 Reviewer 联合处理；跨域争议由主理人裁决 | 进入 Quarantine，解决前不进入当前事实源 |

### 8.2 新增

- 新增记录由对应 `owner` 负责内容完整与提交时效。
- `reviewer` 负责关键业务事实确认。
- `quality_check_owner` 负责质量报告、来源和准入条件。
- 系统记录发起人、确认人、时间、原因和来源版本。

### 8.3 修改

- 普通字段修改由 Owner 发起。
- 金额、到账、退款、入住、出馆、房态等关键字段必须复核。
- 修改生成 `CHANGED`，保留前后版本与差异。
- 禁止直接覆盖已生效记录。

### 8.4 删除

禁止物理删除生产记录。

Excel 行消失只能生成 `MISSING`。确认业务结束后，通过 `expire_time`、`is_current=false` 和终态状态结束记录；原始版本、Audit 与来源证据永久保留。

## 九、数据异常处理流程

### 9.1 标准流程

```text
异常或冲突被识别
  -> 写入 Quarantine
  -> 生成 Data Quality Issue
  -> 通知 Owner 与 Quality Check Owner
  -> Owner 提供业务说明或修正来源
  -> Reviewer 确认业务事实
  -> Data Quality Layer 重新校验
  -> 通过后进入 Current/Historical Truth Source
  -> 保留完整 Audit、版本与处置结果
```

异常处理不得直接修改已生效 Truth Source。

### 9.2 财务金额冲突

```text
销售合同金额 / 财务到账金额冲突
  -> Quarantine
  -> 通知销售负责人、财务经办、财务复核
  -> 销售确认合同依据
  -> 财务确认到账凭证
  -> 财务复核给出确认结果
  -> Data Quality Layer 重跑
  -> 合格版本进入 Truth Source
```

在冲突解决前：

- 不进入确认收入。
- 不进入确认已收。
- 不进入老板首页确认金额。
- 可显示为数据质量风险数量，但不得显示冲突金额为经营事实。

### 9.3 房态冲突

同一房间出现两个当前入住或当前状态互斥时：

- 进入 Quarantine。
- 店总核对现场事实。
- 管家提供入住执行记录。
- 未解决时保留上一已确认房态，不采用冲突新值。

### 9.4 处理时限

| 风险 | 处理时限 | 升级规则 |
|---|---|---|
| 影响首页金额或当前房态 | 当日、进入下次发布前 | 超时升级主理人 |
| 普通字段缺失 | 1 个工作日 | 超时通知 Reviewer |
| 历史记录问题 | 3 个工作日 | 超时进入治理待办 |
| 结构变化或 Adapter 不兼容 | 立即停止该批准入 | 必须完成映射复核 |

## 十、页面展示责任

页面只展示经过 Data Quality Layer 和 Truth Source 准入的数据，但准确性的业务责任仍属于对应岗位。

| 页面 | 展示内容 | 数据准确责任人 | 复核责任人 | 最终责任人 |
|---|---|---|---|---|
| 首页工作台 | 销售、财务、在住、房态、风险摘要 | 各 Domain Owner 分别负责 | 各 Domain Reviewer | 主理人负责经营口径裁决 |
| 销售中心 | 客户、合同、销售状态、合同金额 | 销售负责人 | 财务复核金额与到账 | 主理人 |
| 财务中心 | 收入、支出、已收、待收、待付、对账 | 财务经办 | 财务复核 | 主理人 |
| 运营中心 | 当前入住、当前房态、入住/出馆状态 | 店总 | 店总；管家提供现场记录 | 主理人处理重大争议 |
| 数据追溯 | 来源文件、Sheet、行、版本、责任链 | Quality Check Owner | 对应 Reviewer | 对应 Domain Accountable Owner |
| AI Context | 已准入且授权的数据 | 对应 Domain Owner | 对应 Reviewer | 主理人负责使用边界，不改变原数据责任 |

### 10.1 首页责任拆分

- 销售数量与合同金额：销售负责人负责，财务复核金额口径。
- 收款、待收、待付、支出与利润：财务经办维护，财务复核负责准确。
- 在住数量与 Stay 状态：店总负责，管家提供现场记录。
- 房态数量与当前状态：店总负责。
- 风险事项：产生风险的 Domain Owner 负责处理；主理人负责跨域升级。

系统、API 和页面负责忠实传递已准入事实，不承担原始业务事实的确认责任。

## 十一、权限与替岗规则

1. 所有写入和确认权限必须来自 EMP + Role + Execution Scope。
2. Backup Owner 只有在明确授权期内才能代办，并记录代理原因。
3. Owner 与 Reviewer 原则上应分离；人员不足无法分离时，必须由主理人进行第二确认。
4. 离职、调岗、停权后，责任绑定立即失效，不影响历史责任链。
5. 不允许使用共享账号、岗位群或未解析身份进行确认。
6. 系统不得生成虚拟责任人或 fallback owner。

## 十二、Audit 与通知

责任链至少记录：

- `data.responsibility.assigned`
- `data.change.submitted`
- `data.change.reviewed`
- `data.quality.issue.assigned`
- `data.quality.issue.resolved`
- `data.truth_source.admission.confirmed`

每条 Audit 必须包含：

- `responsibility_id`
- `data_domain`
- `record_id` 或 `import_id`
- `owner_emp_id`
- `reviewer_emp_id`
- `quality_check_owner_emp_id`
- `change_type`
- `decision`
- `reason`
- `timestamp`
- `correlation_id`

通知只用于提醒责任人，不代表自动确认，不得绕过 Data Quality Layer 或 Reviewer。

## 十三、责任矩阵维护

- 责任矩阵由主理人批准生效。
- 各 Domain Owner 每月确认一次责任绑定和来源清单。
- 组织人员变化、来源文件变化、Sheet 结构变化或 Adapter 版本变化时必须重新确认。
- 责任矩阵每次更新生成新版本，旧版本只读保留。
- 未登记 Owner、Reviewer 或 Quality Check Owner 的数据源不得进入生产。

## 十四、验收标准

P0.13 责任矩阵必须满足：

1. 第一批销售、财务、房态、入住和签约客户均有明确 Owner。
2. 每个数据源均有 Backup Owner、Reviewer、Quality Check Owner 和 Accountable Owner。
3. 每个责任岗位均可解析为有效 EMP。
4. 合同金额与到账确认责任分离。
5. 房态修改、入住确认和出馆确认责任明确。
6. 签约客户字段按销售、财务、店总/管家拆分责任。
7. NEW、CHANGED、MISSING、CONFLICT 均有处理责任人。
8. 生产记录禁止物理删除。
9. Quarantine 异常具有通知、确认、重检和准入闭环。
10. 首页、销售中心、财务中心、运营中心的数据准确责任明确。

## 十五、设计结论

OMS 生产数据责任链冻结为：

```text
Owner 维护
  -> Quality Check Owner 检查
  -> Reviewer 确认
  -> Data Quality Layer 准入
  -> Truth Source 生效
  -> 页面忠实展示
  -> Accountable Owner 承担最终业务责任
```

责任原则：

```text
数据有人维护；
关键事实有人复核；
异常有人处理；
页面数字有人负责；
历史责任不可改写。
```
