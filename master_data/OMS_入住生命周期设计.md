# OMS 入住生命周期设计

Version: 1.0
Status: P8 Draft
Owner: 石磊

---

# 一、目标

Stay Engine 是 OMS 第一个运营核心，用于管理客户从已签约到待入住、在住、续住、出馆或取消的全过程。

Stay 不是房间。

Stay 不是客户。

Stay 是客户入住全过程。

本阶段只建立 Stay 生命周期内核，不接入房间、照护师、页面或数据库。

---

# 二、生命周期

| 状态 | 含义 |
|------|------|
| CONTRACTED | 已签约 |
| WAITING_CHECKIN | 待入住 |
| CHECKED_IN | 已办理入住 |
| IN_STAY | 在住 |
| CHECKED_OUT | 已出馆 |
| EXTENDED | 续住 |
| CANCELLED | 取消 |

说明：

create_stay 从 CONTRACTED 建立 WAITING_CHECKIN 入住计划。

check_in 发布 stay.checked_in，并将 Stay 进入 IN_STAY。

CHECKED_IN 作为办理入住事件节点记录在 transitions 中，最终业务状态进入 IN_STAY。

---

# 三、支持动作

| 动作 | 入口状态 | 结果状态 | 说明 |
|------|----------|----------|------|
| create_stay | CONTRACTED | WAITING_CHECKIN | 建立入住计划 |
| check_in | WAITING_CHECKIN | IN_STAY | 办理入住 |
| extend_stay | IN_STAY / EXTENDED | EXTENDED | 续住并更新计划出馆日期 |
| check_out | IN_STAY / EXTENDED | CHECKED_OUT | 办理出馆 |
| cancel_stay | WAITING_CHECKIN | CANCELLED | 取消入住计划 |

---

# 四、事件

| 动作 | Event |
|------|-------|
| create_stay | stay.created |
| check_in | stay.checked_in |
| extend_stay | stay.extended |
| check_out | stay.checked_out |
| cancel_stay | stay.cancelled |

所有事件通过 Event Bus 发布，source_module 固定为 stay。

---

# 五、审计

| 动作 | Audit module | Audit action_type |
|------|--------------|-------------------|
| create_stay | stay | stay.create |
| check_in | stay | stay.check_in |
| extend_stay | stay | stay.extend |
| check_out | stay | stay.check_out |
| cancel_stay | stay | stay.cancel |

每个关键动作必须写入 Audit Log。

reason 必填。

actor 必须使用 EMP 编号，并由 Master Data 校验真实员工与角色权限。

---

# 六、权限边界

Stay 修改权限继承 Domain 中 Stay 的 mutable_by_roles：

- ROLE_OWNER
- ROLE_STORE_MANAGER
- ROLE_BUTLER
- ROLE_NURSING_DIRECTOR

销售、财务、行政等角色不得直接修改 Stay 生命周期。

---

# 七、当前边界

本阶段不接入：

- 房间
- 照护师
- 页面
- 数据库
- 飞书审批
- 销售流程
- 财务流程

后续模块必须引用 StayService，不得自行维护入住生命周期状态。
