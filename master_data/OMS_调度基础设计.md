# OMS 调度基础设计

Version: 1.0
Status: P12 Draft
Owner: 石磊

---

# 一、目标

Scheduling Foundation 是 OMS 调度中心的基础框架。

本阶段不是排房算法。

本阶段不是自动推荐。

本阶段不是业务规则。

本阶段只建立调度框架。

Scheduler 不直接修改：

- Room
- Stay
- Caregiver

Scheduler 只负责：

- 分析
- 协调
- 返回建议

---

# 二、核心对象

## Scheduling Request

调度请求。

当前必须输入 Stay。

字段包括：

- stay
- actor_emp_id
- requested_room_id
- requested_caregiver_id
- requirements
- request_id

## Scheduling Context

调度上下文。

能够关联：

- Room
- Caregiver
- Business Rules

## Scheduling Result

调度输出。

包含：

- status
- reason
- room_candidates
- caregiver_candidates
- recommendations
- warnings
- rejects
- mutates_business_state=False

## Scheduler Engine

统一调度分析引擎。

只读取输入，不写业务状态。

## Scheduler

轻量 facade，用于未来业务模块调用。

---

# 三、输入输出

输入：

- Stay
- Room 候选资源
- Caregiver 候选资源
- Business Rules Engine

输出：

- PASS
- WARNING
- REJECT
- 推荐候选
- 阻塞原因
- 非阻塞提醒

---

# 四、当前支持对象

| 对象 | 作用 |
|------|------|
| Stay | 调度主体 |
| Room | 房间候选资源 |
| Caregiver | 照护师候选资源 |
| Business Rules | 判断房间是否可入住等规则 |

---

# 五、当前边界

本阶段不做：

- 自动分配
- 最优算法
- 超卖
- 倒房
- 排班算法
- 页面
- 数据库
- Audit 写入
- Event 发布

recommendations 只是建议，不代表已分配。

---

# 六、当前策略

当前 Scheduler 只做最小可用分析：

1. 输入 Stay。
2. 分析 Room 候选。
3. 分析 Caregiver 候选。
4. 调用 Business Rules 做只读判断。
5. 返回第一组可用资源建议。
6. 明确标记 auto_assigned=False。

P12 不做最优排序。

P12 不做自动占用。

P12 不改变 Room、Stay、Caregiver 状态。
