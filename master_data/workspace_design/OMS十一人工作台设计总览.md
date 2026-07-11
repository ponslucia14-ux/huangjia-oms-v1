# OMS 十一人工作台设计总览

## 状态

```text
旧数据 = ARCHIVED_LEGACY
Current = NOT_INITIALIZED
阶段 = WORKSPACE_DESIGN_PHASE
```

## 设计总原则

1. 先按真实岗位分工，再由操作产生 Current。
2. 查看、录入、复核、审批、发布相互分离。
3. 每个写入必须绑定真实 EMP、user_id、role_code、Audit 和 Event。
4. 合同计划不等于 Actual Stay，收款主张不等于到账，日历标记不等于 Room Current。
5. 老板处理经营判断与例外，不代替岗位日常录入。
6. 销售只管理签约后业务，不建设线索和签约前跟进 CRM。

## Current 产生责任

| 事实 | 发起/录入 | 复核/发布 |
|---|---|---|
| Customer / Contract | EMP006、EMP007 | EMP006；金额由 EMP003 复核 |
| Payment / Expense | EMP004 | EMP003 |
| Actual Stay / Room | EMP009 提交现场资料 | EMP008 确认发布 |
| Employee / Attendance | EMP002 | 按身份与权限规则生效 |
| Administration / Purchase | EMP005 | 财务仅确认费用与付款 |
| Care Service | EMP010 | EMP010 质量确认 |
| Meal Service | EMP011 | EMP011 完成确认 |
| 跨域例外 | 对应责任人提交 | EMP001 裁决 |

## 开发门禁

工作台实现不得读取 Historical Archive 作为 Current，不得恢复旧 Excel 页面逻辑，不得在前端自行计算事实，不得提供岗位无权执行的按钮。
