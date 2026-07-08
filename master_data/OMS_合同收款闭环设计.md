# OMS 合同收款闭环设计

## 目标

建立 OMS V1 第一个最小真实业务闭环：

```text
合同签约
↓
收款记录
↓
到账确认
↓
审计日志
↓
事件发布
```

本阶段只实现业务内核，不做页面、不接真实数据库、不做复杂销售流程。

## 新增服务

ContractService

负责创建合同。

PaymentService

负责记录收款和确认到账。

ContractPaymentStore

本阶段使用内存存储，仅用于最小闭环验证。

## 支持动作

create_contract

- 创建合同
- actor 必须是 EMP
- reason 必填
- 写入 Audit Log
- 发布 `contract.created`

record_payment

- 记录收款
- actor 必须是 EMP
- actor 必须具备 Payment Domain 修改权限
- reason 必填
- 写入 Audit Log
- 发布 `payment.recorded`

confirm_payment

- 确认到账
- actor 必须是 EMP
- actor 必须具备 Payment Domain 修改权限
- reason 必填
- 不允许重复确认
- 写入 Audit Log
- 发布 `payment.confirmed`

## 事件

| Event | 说明 |
|-------|------|
| contract.created | 合同已创建 |
| payment.recorded | 收款已记录 |
| payment.confirmed | 到账已确认 |

## 审计

| Audit Action | 说明 |
|--------------|------|
| create_contract | 合同创建 |
| record_payment | 收款录入 |
| confirm_payment | 到账确认 |

## 身份规则

- actor 只接受 EMP 编号。
- actor 正式姓名从 Master Data 读取。
- 不允许使用昵称作为 actor。
- 不允许使用姓名代替 EMP。

## 边界

本阶段不做：

- 页面
- 真实数据库
- 复杂销售流程
- 飞书审批
- 财务入账
- 发票
- 退款

本阶段只验证：

- Contract Domain
- Payment Domain
- Audit Log
- Event Bus
- EMP 身份约束
