# OMS 领域模型设计

## 目标

OMS Domain 是全系统统一领域模型。

以后所有业务模块必须引用 Domain，不得自行定义对象。

本阶段只定义 OMS 管理哪些对象，不写业务、不写页面、不接数据库。

## 领域对象

| Domain | 唯一标识 | 职责 |
|--------|----------|------|
| Customer | customer_id | 管理客户与妈妈档案的统一身份 |
| Contract | contract_id | 管理客户签约、套餐、合同金额和合同状态 |
| Payment | payment_id | 管理收款、退款、付款与到账确认 |
| Room | room_id | 管理房间、房态、排房资源与房态冲突 |
| Stay | stay_id | 管理客户入住、在住、出馆和服务周期 |
| Employee | emp_id | 管理 OMS 内部正式员工主数据引用 |
| Caregiver | caregiver_id | 管理照护师、产护资源、排班和服务能力 |
| Expense | expense_id | 管理采购、报销、成本和费用归集 |
| Approval | approval_id | 管理审批请求、审批流状态和审批结果 |
| Task | task_id | 管理 OMS 内部待办、派单、跟进与完成状态 |
| Notification | notification_id | 管理系统通知、飞书消息、提醒和送达状态 |

## Domain 契约

每个 Domain 必须定义：

- 唯一标识
- 生命周期
- 状态
- 允许动作
- 产生 Event
- 记录 Audit
- 可修改角色

## Customer

- 生命周期：lead, consulting, contracted, in_service, completed, archived
- 状态：active, inactive, blocked, archived
- 允许动作：create_customer, update_customer, archive_customer, link_contract
- Event：customer.created, customer.updated, customer.archived, customer.contract_linked
- Audit：customer.create, customer.update, customer.archive, customer.link_contract
- 可修改角色：ROLE_OWNER, ROLE_STORE_MANAGER, ROLE_SALES, ROLE_BUTLER

## Contract

- 生命周期：draft, submitted, confirmed, active, completed, cancelled
- 状态：draft, pending_review, active, completed, cancelled
- 允许动作：create_contract, submit_contract, confirm_contract, cancel_contract, complete_contract
- Event：contract.created, contract.submitted, contract.confirmed, contract.cancelled, contract.completed
- Audit：contract.create, contract.submit, contract.confirm, contract.cancel, contract.complete
- 可修改角色：ROLE_OWNER, ROLE_STORE_MANAGER, ROLE_SALES, ROLE_ACCOUNTANT

## Payment

- 生命周期：created, pending_confirm, confirmed, reconciled, voided
- 状态：pending, confirmed, reconciled, failed, voided
- 允许动作：create_payment, confirm_payment, reconcile_payment, void_payment
- Event：payment.created, payment.confirmed, payment.reconciled, payment.voided
- Audit：payment.create, payment.confirm, payment.reconcile, payment.void
- 可修改角色：ROLE_OWNER, ROLE_ACCOUNTANT, ROLE_CASHIER

## Room

- 生命周期：available, reserved, occupied, cleaning, maintenance, closed
- 状态：available, reserved, occupied, cleaning, maintenance, closed
- 允许动作：create_room, reserve_room, assign_room, release_room, mark_cleaning, mark_maintenance
- Event：room.created, room.reserved, room.assigned, room.released, room.status_changed
- Audit：room.create, room.reserve, room.assign, room.release, room.status_change
- 可修改角色：ROLE_OWNER, ROLE_STORE_MANAGER, ROLE_ADMIN

## Stay

- 生命周期：planned, checkin_ready, in_house, checkout_pending, completed, cancelled
- 状态：planned, ready, in_house, pending_checkout, completed, cancelled
- 允许动作：create_stay, prepare_checkin, check_in, update_stay, check_out, cancel_stay
- Event：stay.created, stay.prepared, stay.checked_in, stay.updated, stay.checked_out, stay.cancelled
- Audit：stay.create, stay.prepare, stay.check_in, stay.update, stay.check_out, stay.cancel
- 可修改角色：ROLE_OWNER, ROLE_STORE_MANAGER, ROLE_BUTLER, ROLE_NURSING_DIRECTOR

## Employee

- 生命周期：candidate, active, transferred, inactive, archived
- 状态：active, inactive, transferred, archived
- 允许动作：create_employee, update_employee, transfer_employee, deactivate_employee
- Event：employee.created, employee.updated, employee.transferred, employee.deactivated
- Audit：employee.create, employee.update, employee.transfer, employee.deactivate
- 可修改角色：ROLE_OWNER, ROLE_HR

## Caregiver

- 生命周期：candidate, active, scheduled, serving, resting, inactive
- 状态：active, scheduled, serving, resting, inactive
- 允许动作：create_caregiver, update_caregiver, schedule_caregiver, release_caregiver, deactivate_caregiver
- Event：caregiver.created, caregiver.updated, caregiver.scheduled, caregiver.released, caregiver.deactivated
- Audit：caregiver.create, caregiver.update, caregiver.schedule, caregiver.release, caregiver.deactivate
- 可修改角色：ROLE_OWNER, ROLE_HR, ROLE_NURSING_DIRECTOR

## Expense

- 生命周期：draft, submitted, reviewing, approved, paid, rejected, voided
- 状态：draft, pending_review, approved, paid, rejected, voided
- 允许动作：create_expense, submit_expense, approve_expense, reject_expense, mark_paid, void_expense
- Event：expense.created, expense.submitted, expense.approved, expense.rejected, expense.paid, expense.voided
- Audit：expense.create, expense.submit, expense.approve, expense.reject, expense.pay, expense.void
- 可修改角色：ROLE_OWNER, ROLE_ACCOUNTANT, ROLE_CASHIER, ROLE_ADMIN, ROLE_KITCHEN_DIRECTOR

## Approval

- 生命周期：created, pending, approved, rejected, cancelled, expired
- 状态：pending, approved, rejected, cancelled, expired
- 允许动作：create_approval, approve, reject, cancel, expire
- Event：approval.created, approval.approved, approval.rejected, approval.cancelled, approval.expired
- Audit：approval.create, approval.approve, approval.reject, approval.cancel, approval.expire
- 可修改角色：ROLE_OWNER, ROLE_ACCOUNTANT, ROLE_CASHIER, ROLE_STORE_MANAGER, ROLE_BUTLER

## Task

- 生命周期：created, assigned, in_progress, blocked, completed, cancelled
- 状态：open, assigned, in_progress, blocked, completed, cancelled
- 允许动作：create_task, assign_task, start_task, block_task, complete_task, cancel_task
- Event：task.created, task.assigned, task.started, task.blocked, task.completed, task.cancelled
- Audit：task.create, task.assign, task.start, task.block, task.complete, task.cancel
- 可修改角色：ROLE_OWNER, ROLE_STORE_MANAGER, ROLE_BUTLER, ROLE_ADMIN, ROLE_HR

## Notification

- 生命周期：created, queued, sent, delivered, failed, cancelled
- 状态：queued, sent, delivered, failed, cancelled
- 允许动作：create_notification, queue_notification, send_notification, mark_delivered, mark_failed, cancel_notification
- Event：notification.created, notification.queued, notification.sent, notification.delivered, notification.failed, notification.cancelled
- Audit：notification.create, notification.queue, notification.send, notification.deliver, notification.fail, notification.cancel
- 可修改角色：ROLE_OWNER, ROLE_ADMIN, ROLE_HR, ROLE_STORE_MANAGER, ROLE_BUTLER

## 使用规则

- 业务模块必须通过 `DomainRegistry` 读取 Domain。
- 不允许业务模块自行维护对象定义。
- 不允许出现多个 Customer、Contract、Payment 等本地定义。
- 本阶段不绑定数据库。
- 本阶段不实现业务流程。
