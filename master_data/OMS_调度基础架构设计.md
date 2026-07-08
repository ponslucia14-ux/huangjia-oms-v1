# OMS 调度基础架构设计

Version: 1.0

Status: P12 Design Draft

Owner: 石磊

Stage: Scheduling Foundation

---

# 一、阶段目标

P12 Scheduling Foundation 的目标是建立 OMS 调度基础架构。

本阶段只回答一个问题：

> 在不修改业务状态的前提下，OMS 如何接收调度请求、汇总调度上下文、分析候选资源，并返回可追踪的调度建议。

本阶段不是排房算法。

本阶段不是自动排房。

本阶段不是自动分配照护师。

本阶段不是 UI。

本阶段不修改任何业务实体状态。

---

# 二、核心边界

Scheduler Engine 只能读取和分析：

- Stay
- Room
- Caregiver
- Business Rules

Scheduler Engine 禁止直接修改：

- Room 状态
- Stay 状态
- Caregiver 状态

Scheduler Engine 输出的是建议，不是执行结果。

任何真实状态变更必须由后续明确的执行层完成，不属于 P12。

---

# 三、Scheduling Request

Scheduling Request 是一次调度分析请求。

## 3.1 谁可以发起调度请求

调度请求必须由明确的 EMP 发起。

允许发起者：

- EMP001 / ROLE_OWNER
- EMP008 / ROLE_STORE_MANAGER
- EMP009 / ROLE_BUTLER
- 后续经权限系统授权的正式 EMP

系统自动触发的调度请求也必须携带 triggering_emp_id。

禁止：

- 匿名请求
- 未绑定 user_id 的请求
- 只有岗位、群、昵称但没有 EMP 的请求

## 3.2 Request 字段

Scheduling Request 必须包含：

| 字段 | 必填 | 说明 |
|------|------|------|
| request_id | 是 | 调度请求唯一 ID |
| request_type | 是 | room / caregiver / combined |
| actor_emp_id | 是 | 发起调度请求的 EMP |
| reason | 是 | 发起调度分析的业务原因 |
| stay_id | 是 | 关联 Stay |
| source_module | 是 | 来源模块，例如 stay / room / caregiver / boss |
| requested_room_id | 否 | 指定房间，仅作为偏好输入 |
| requested_caregiver_id | 否 | 指定照护师，仅作为偏好输入 |
| requirements | 否 | 调度要求，例如房型、护理需求、时间窗口 |
| priority | 否 | normal / urgent / critical |
| correlation_id | 否 | 关联上游业务事件 |
| created_at | 是 | 请求创建时间 |

## 3.3 Request 原则

- request 不代表执行。
- requested_room_id 不代表房间已被占用。
- requested_caregiver_id 不代表照护师已被分配。
- reason 不能为空。
- actor_emp_id 必须来自 OMS Master Data。

---

# 四、Scheduling Context

Scheduling Context 是 Scheduler Engine 的只读分析上下文。

## 4.1 Context 必须包含

| 上下文 | 说明 |
|--------|------|
| stay | 当前 Stay 信息 |
| room_candidates | 可读的 Room 候选资源 |
| caregiver_candidates | 可读的 Caregiver 候选资源 |
| business_rule_results | Business Rules Engine 的只读判断结果 |
| current_time | 调度分析时间 |
| source_snapshot | 输入数据快照引用 |

## 4.2 Stay 信息

Stay Context 至少包含：

- stay_id
- guest_id
- expected_check_in
- expected_check_out
- care_level
- special_requirements
- current_status

## 4.3 Room 可用资源

Room Context 至少包含：

- room_id
- room_number
- room_type
- room_status
- floor
- available_from
- constraints

Room Context 只能读取 Room Engine 当前状态。

禁止在 Context 构建阶段修改 Room。

## 4.4 Caregiver 可用资源

Caregiver Context 至少包含：

- caregiver_id
- caregiver_emp_id
- availability_status
- skill_tags
- current_load
- available_time_window
- constraints

Caregiver Context 只能读取 Caregiver Engine 当前状态。

禁止在 Context 构建阶段修改 Caregiver。

## 4.5 Business Rules 结果

Business Rules Context 至少包含：

- rule_id
- rule_name
- decision
- severity
- reason
- affected_resource_id

Business Rules 只负责判断，不负责执行调度。

---

# 五、Scheduling Result

Scheduling Result 是调度分析输出。

## 5.1 Result 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| result_id | 是 | 调度结果唯一 ID |
| request_id | 是 | 关联 Scheduling Request |
| status | 是 | completed / failed |
| decision_status | 是 | PENDING / RECOMMENDED / APPROVED / REJECTED / EXECUTED |
| recommendations | 是 | 建议方案列表 |
| room_candidates | 是 | 房间候选资源及评分 |
| caregiver_candidates | 是 | 照护师候选资源及评分 |
| failure_reasons | 是 | 失败原因列表，可为空 |
| warnings | 是 | 警告信息列表，可为空 |
| business_rule_trace | 是 | 规则判断追踪 |
| mutates_business_state | 是 | 固定为 false |
| generated_at | 是 | 结果生成时间 |

## 5.2 Decision Status

decision_status 用于保留调度决策链。

调度链路允许未来扩展为：

系统推荐

↓

人工确认

↓

执行

状态定义：

| decision_status | 含义 |
|-----------------|------|
| PENDING | 已收到请求，但尚未形成建议 |
| RECOMMENDED | Scheduler 已生成建议，等待人工确认 |
| APPROVED | 建议已被授权确认，但尚未执行 |
| REJECTED | 建议被拒绝或规则拒绝 |
| EXECUTED | 后续执行层已完成执行回写 |

P12 阶段 Scheduler Engine 只能生成 PENDING、RECOMMENDED 或 REJECTED。

APPROVED 与 EXECUTED 只为后续执行闭环保留，不在 P12 直接写入业务状态。

## 5.3 Recommendation 字段

建议方案至少包含：

- recommendation_id
- recommended_room_id
- recommended_caregiver_id
- confidence
- reasons
- warnings
- rejected_candidates

## 5.4 Failure Reason

失败原因必须结构化：

- code
- message
- severity
- affected_resource

示例：

- no_available_room
- no_available_caregiver
- business_rule_rejected
- missing_stay_context

## 5.5 Result 原则

- Result 只表示分析完成。
- Result 不代表资源已分配。
- Result 不修改 Room、Stay、Caregiver。
- mutates_business_state 必须始终为 false。
- decision_status 只表达决策阶段，不代表 P12 已执行资源分配。

---

# 六、Scheduler Engine

Scheduler Engine 是 P12 的核心。

## 6.1 职责

Scheduler Engine 负责：

1. 接收 Scheduling Request。
2. 校验 actor_emp_id 与 reason。
3. 构建 Scheduling Context。
4. 调用 Business Rules Engine 获取只读规则判断。
5. 生成候选资源列表。
6. 生成 Scheduling Result。
7. 写入 Audit。
8. 发布 Event。

## 6.2 禁止职责

Scheduler Engine 禁止：

- 修改 Room。
- 修改 Stay。
- 修改 Caregiver。
- 自动占用房间。
- 自动分配照护师。
- 执行超售算法。
- 执行倒房算法。
- 改变入住状态。
- 改变照护师状态。
- 写数据库。
- 渲染 UI。

## 6.3 Engine 输出原则

Scheduler Engine 的输出只能是：

- 建议方案
- 候选资源
- 失败原因
- 警告信息
- 审计记录
- 调度事件

---

# 七、Event

P12 至少定义以下事件。

| Event | 触发时机 | payload |
|-------|----------|---------|
| scheduling.requested | 调度请求被接收并通过基础校验 | request_id, actor_emp_id, stay_id, reason |
| scheduling.completed | 调度分析完成并生成建议 | request_id, result_id, recommendations, warnings |
| scheduling.failed | 调度分析失败 | request_id, failure_reasons, warnings |

## 7.1 Event 原则

- Event 必须包含 event_id。
- Event 必须包含 request_id。
- Event 必须包含 actor_emp_id。
- Event 必须包含 reason。
- Event 不代表执行状态变更。

---

# 八、Audit

调度过程必须可追踪。

## 8.1 Audit 必须记录

| Audit action | 说明 |
|--------------|------|
| scheduling.request | 记录调度请求 |
| scheduling.context_built | 记录上下文构建完成 |
| scheduling.complete | 记录调度分析完成 |
| scheduling.fail | 记录调度失败 |

## 8.2 Audit 字段

Audit 必须包含：

- audit_id
- actor_emp_id
- actor_name
- action
- reason
- request_id
- result_id
- target_type
- target_id
- timestamp
- metadata

## 8.3 Audit 原则

- reason 必填。
- actor_emp_id 必须来自 Master Data。
- Audit 记录调度分析，不记录业务状态修改。
- Audit metadata 必须包含 mutates_business_state=false。

---

# 九、P12 禁止事项

本阶段禁止：

- 自动排房
- 自动分配照护师
- 超售算法
- 倒房算法
- 修改入住状态
- 修改房间状态
- 修改照护师状态
- 接入 UI
- 接入数据库
- 写入真实 Room / Stay / Caregiver 状态

---

# 十、验收标准

P12 设计验收必须满足：

1. Scheduling Request 定义清晰。
2. Scheduling Context 明确包含 Stay、Room、Caregiver、Business Rules。
3. Scheduling Result 明确返回建议、候选资源、失败原因、警告信息。
4. Scheduler Engine 明确只分析、不修改业务状态。
5. Event 至少包含 scheduling.requested、scheduling.completed、scheduling.failed。
6. Audit 全链路可追踪。
7. 明确禁止自动排房、自动分配照护师、超售、倒房、状态修改、数据库和 UI。

---

# 十一、当前阶段结论

P12 Scheduling Foundation 是 OMS 调度中心的只读分析基础。

它负责建立调度请求、上下文、结果、事件和审计的统一架构。

它不负责真实分配。

它不负责状态落地。

它不改变 Room、Stay、Caregiver 的任何状态。
