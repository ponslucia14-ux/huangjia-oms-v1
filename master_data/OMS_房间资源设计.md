# OMS 房间资源设计

Version: 1.0
Status: P9 Draft
Owner: 石磊

---

# 一、目标

Room Engine 是 OMS 的房间资源核心，用于统一管理房间资源的基础状态。

本阶段不是排房算法。

本阶段不是自动排房。

本阶段不是 UI。

本阶段只建立 Room Engine。

---

# 二、生命周期

| 状态 | 含义 |
|------|------|
| AVAILABLE | 可用 |
| RESERVED | 已预留 |
| OCCUPIED | 已占用 |
| CLEANING | 清洁中 |
| MAINTENANCE | 维修维护 |
| DISABLED | 停用 |

---

# 三、支持动作

| 动作 | 入口状态 | 结果状态 | 说明 |
|------|----------|----------|------|
| create_room | 无 | AVAILABLE | 建立房间资源 |
| reserve_room | AVAILABLE | RESERVED | 预留房间 |
| check_in_room | RESERVED | OCCUPIED | 房间进入占用 |
| release_room | RESERVED | AVAILABLE | 释放预留房间 |
| release_room | OCCUPIED | CLEANING | 出馆后释放房间并进入清洁 |
| maintenance_room | AVAILABLE / RESERVED / CLEANING / MAINTENANCE / DISABLED | MAINTENANCE / DISABLED | 标记维修或停用 |
| enable_room | CLEANING / MAINTENANCE / DISABLED | AVAILABLE | 清洁、维修或停用结束后重新启用 |

---

# 四、事件

| 动作 | Event |
|------|-------|
| create_room | room.created |
| reserve_room | room.reserved |
| check_in_room | room.checked_in |
| release_room | room.released |
| maintenance_room | room.maintenance |
| enable_room | room.enabled |

所有事件通过 Event Bus 发布，source_module 固定为 room。

---

# 五、审计

| 动作 | Audit module | Audit action_type |
|------|--------------|-------------------|
| create_room | room | room.create |
| reserve_room | room | room.reserve |
| check_in_room | room | room.check_in |
| release_room | room | room.release |
| maintenance_room | room | room.maintenance |
| enable_room | room | room.enable |

每个关键动作必须写入 Audit Log。

reason 必填。

actor 必须使用 EMP 编号，并由 Master Data 校验真实员工与角色权限。

---

# 六、权限边界

Room 修改权限继承 Domain 中 Room 的 mutable_by_roles：

- ROLE_OWNER
- ROLE_STORE_MANAGER
- ROLE_ADMIN

销售、财务、管家、产护、料理等角色不得直接修改 Room 资源状态。

---

# 七、当前边界

本阶段不接入：

- Stay
- Caregiver
- 排房算法
- 数据库
- 页面
- 飞书审批
- 自动通知

后续模块必须引用 RoomService，不得自行维护房间资源状态。
