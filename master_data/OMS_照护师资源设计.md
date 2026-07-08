# OMS 照护师资源设计

Version: 1.0
Status: P11 Draft
Owner: 石磊

---

# 一、目标

Caregiver Engine 是 OMS 的照护师资源核心，用于统一管理照护师资源的基础状态。

本阶段不是排班。

本阶段不是工资。

本阶段不是考勤。

本阶段不是绩效。

本阶段不是页面。

本阶段不是数据库。

本阶段只建立 Caregiver Engine。

---

# 二、生命周期

| 状态 | 含义 |
|------|------|
| AVAILABLE | 可分配 |
| RESERVED | 已预留 |
| ASSIGNED | 已分配 |
| ON_LEAVE | 请假 |
| OFF_DUTY | 休息 |
| DISABLED | 停用 |

---

# 三、支持动作

| 动作 | 入口状态 | 结果状态 | 说明 |
|------|----------|----------|------|
| create_caregiver | 无 | AVAILABLE | 建立照护师资源 |
| reserve_caregiver | AVAILABLE | RESERVED | 预留照护师 |
| assign_caregiver | RESERVED | ASSIGNED | 分配照护师 |
| release_caregiver | RESERVED | AVAILABLE | 释放预留照护师 |
| release_caregiver | ASSIGNED | OFF_DUTY | 服务结束后释放照护师并进入休息 |
| leave_caregiver | AVAILABLE / RESERVED / OFF_DUTY / ON_LEAVE / DISABLED | ON_LEAVE / DISABLED | 标记请假或停用 |
| enable_caregiver | ON_LEAVE / OFF_DUTY / DISABLED | AVAILABLE | 请假、休息或停用结束后重新启用 |

---

# 四、事件

| 动作 | Event |
|------|-------|
| create_caregiver | caregiver.created |
| reserve_caregiver | caregiver.reserved |
| assign_caregiver | caregiver.assigned |
| release_caregiver | caregiver.released |
| leave_caregiver | caregiver.leave |
| enable_caregiver | caregiver.enabled |

所有事件通过 Event Bus 发布，source_module 固定为 caregiver。

---

# 五、审计

| 动作 | Audit module | Audit action_type |
|------|--------------|-------------------|
| create_caregiver | caregiver | caregiver.create |
| reserve_caregiver | caregiver | caregiver.reserve |
| assign_caregiver | caregiver | caregiver.assign |
| release_caregiver | caregiver | caregiver.release |
| leave_caregiver | caregiver | caregiver.leave |
| enable_caregiver | caregiver | caregiver.enable |

每个关键动作必须写入 Audit Log。

reason 必填。

actor 必须使用 EMP 编号，并由 Master Data 校验真实员工与角色权限。

---

# 六、权限边界

Caregiver 修改权限继承 Domain 中 Caregiver 的 mutable_by_roles：

- ROLE_OWNER
- ROLE_HR
- ROLE_NURSING_DIRECTOR

销售、财务、行政、管家、料理等角色不得直接修改 Caregiver 资源状态。

---

# 七、当前边界

本阶段不接入：

- Stay 自动分配
- 排班算法
- 工资
- 考勤
- 绩效
- 数据库
- 页面
- 飞书审批
- 自动通知

后续模块必须引用 CaregiverService，不得自行维护照护师资源状态。
