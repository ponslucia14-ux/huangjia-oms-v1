# OMS四域初始化迁移范围定义

阶段：P0.18.2  
用途：TS-20260711-V2生成前的迁移边界定义

## 一、共同规则

初始化迁移只处理可证明的历史、计划、主数据及已确认Current。任何未确认数据不得为了生成V2而强制准入。

- 原始文件保持只读。
- 全Sheet经过Data Quality。
- `CURRENT / HISTORICAL / PLAN / MASTER_DATA / QUARANTINE`分别计数。
- 无Current时标记`NOT_INITIALIZED`，不得用零值伪装已确认。
- Cutover后Current由真实EMP通过OMS权限、Domain Command、Audit和Event产生。
- 禁止从计划或历史推算事实。

## 二、Sales

| 项目 | 定义 |
| --- | --- |
| 初始化策略 | `CONDITIONAL_CURRENT_OR_HISTORICAL` |
| Current候选 | `2026年内店销售列表`、`2026外店上户列表` |
| Current准入条件 | EMP006业务签认、金额复核、Data Quality通过、与迁移口径完成对账 |
| Historical | 未作为Current签认但具备追溯和质量条件的历史成交、合同、收款记录 |
| 排除 | 排名、PV、辅助计算、备注说明 |
| Quarantine | 字段冲突、金额冲突、重复、缺失业务主键的记录 |
| 首次Current | EMP006杨欢欢在OMS确认或创建；EMP003张敬东按重大金额规则复核 |

未完成Current签认时，V2中Sales Current必须标记`NOT_INITIALIZED`或仅保留已明确准入部分，不得用旧224条自动替换候选结果。

## 三、Finance

| 项目 | 定义 |
| --- | --- |
| 初始化策略 | `HISTORICAL_ONLY` |
| Current | 当前Excel不初始化Finance Current |
| Historical | 通过质量检查、可追溯且业务类型明确的收入、支出、收款、付款历史流水 |
| 排除 | 无法拆分的纯展示汇总、公式中间值和备注 |
| Quarantine | 主体冲突、金额冲突、日期或方向不明确、重复记录 |
| 期初状态 | 不从历史流水倒推；由EMP004刘晶在OMS录入 |
| 首次Current | EMP004创建，EMP003张敬东复核后发布 |

## 四、Room

| 项目 | 定义 |
| --- | --- |
| 初始化策略 | `MASTER_DATA_AND_HISTORICAL` |
| Master Data | 可验证的42间房编号及稳定资源属性 |
| Current | 当前Excel不初始化Room Current |
| Historical | 能明确关联业务日期和房号的历史状态记录 |
| 排除 | 陪护人员登记及不能表达房态事实的辅助区域 |
| Quarantine | 日期、房号或状态无法唯一识别的矩阵数据 |
| 首次Current | EMP008刘芳羽在OMS逐房确认并发布；EMP009尚丽娜复核资料差异 |

## 五、Actual Stay

| 项目 | 定义 |
| --- | --- |
| 初始化策略 | `CONTRACT_PLAN_AND_HISTORICAL` |
| Contract Plan | 经业务确认的签约、预产期、套餐和入住计划 |
| Actual Stay Current | 当前文件不初始化 |
| Historical | 能证明实际发生且具备客户、房号、日期、状态证据的历史入住记录 |
| 排除 | 仅有计划日期或套餐、不能证明实际入住的记录 |
| Quarantine | 实际房号、入住状态或有效日期冲突的记录 |
| 首次Current | EMP008刘芳羽在OMS办理真实入住；EMP009尚丽娜核对资料 |

## 六、V2输出要求

V2必须对四域分别输出：

- `initialization_strategy`
- `current_count`
- `historical_count`
- `plan_count`
- `master_data_count`
- `quarantine_count`
- `not_initialized_reason`
- `responsible_emp_id`
- `first_current_action`

V2不得把V1旧页面计数自动当作新口径初始化结果。

## 七、当前状态

```text
migration_scope = DEFINED
business_sheet_signoff = PARTIAL/PENDING
TS-20260711-V1 = ACTIVE
TS-20260711-V2 = NOT GENERATED
```
