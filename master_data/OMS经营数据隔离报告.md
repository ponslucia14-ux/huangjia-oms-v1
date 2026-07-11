# OMS 经营数据隔离报告

## 隔离结论

| 项目 | 状态 |
|---|---|
| 旧经营数据 | ARCHIVED |
| 旧 Snapshot | TS-20260711-V1 / ARCHIVED_LEGACY |
| 新 Current | NOT_INITIALIZED |
| 当前经营 Snapshot | 无 |
| 工作台读取旧数据 | 禁止 |
| 当前阶段 | WORKSPACE_DESIGN_PHASE |

## 工作台隔离范围

以下旧数据全部禁止进入首页、销售中心、财务中心和运营中心：

- Customer
- Contract
- Finance
- Room
- Stay
- Caregiver
- 旧 Task、Approval、Expense、Notification 经营记录
- 旧业务 Event 聚合结果

历史数据只允许通过 Historical Archive 和历史追溯工具按需读取。

## API Current 状态

生产 Adapter 在 `current_operating_snapshot = null` 时统一返回：

```text
current_status = NOT_INITIALIZED
sales = 0 records exposed
finance = 0 records exposed
room = 0 records exposed
stay = 0 records exposed
resident = 0 records exposed
```

这些零值只代表“未向 Current 暴露任何记录”，不是现实经营数字。页面禁止把零值渲染成经营指标。

## 页面状态

首页显示：

```text
当前经营：等待初始化
Status：NOT_INITIALIZED
先完成十一人工作台设计，再由真实业务动作产生经营数据
```

页面不显示：

- 当前在住数量
- 当前房态数量
- 销售金额
- 财务金额
- 旧 Snapshot Health Score

## 下一阶段

进入十一人工作台设计，依次明确：

1. 谁可以查看什么。
2. 谁负责录入什么。
3. 哪个真实业务动作产生哪个 Domain Current。
4. 每项写入需要的权限、Audit 和 Event。

工作台设计完成前，不初始化新 Current，不恢复任何旧 Excel Current。
