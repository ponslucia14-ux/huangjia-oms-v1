# OMS V1.0 RC 验收清单

阶段：OMS V1.0 Release Candidate  
目标：确认 P0-P30 能力是否达到候选版本验收标准  
方式：只做验收准备，不开发、不修改业务逻辑

## 一、系统基础验收

| 验收项 | 验收内容 | 通过标准 | 状态 |
|---|---|---|---|
| Bootstrap | 系统启动链、基础模块加载 | 启动链完整，无阻断错误 | 待验收 |
| Health Check | 启动自检、关键阻断项 | Health Check 通过，阻断项为 0 | 待验收 |
| Master Data | 员工、角色、权限、身份映射 | 11 个员工主数据可读取，角色完整 | 待验收 |
| Persistence | 保存、读取、版本、Audit/Event 关联 | 本地持久化可读写，版本记录完整 | 待验收 |
| Event Bus | 事件发布、记录、分发 | 事件可发布，事件结构完整 | 待验收 |
| Audit | 审计写入、读取、追踪 | 关键动作均有 Audit，append-only 生效 | 待验收 |

基础验收必须先通过，才进入业务、经营、AI、真实数据验收。

## 二、业务验收

| 验收项 | 验收内容 | 通过标准 | 状态 |
|---|---|---|---|
| Contract | 合同领域模型、签约数据映射 | 合同数据可进入 Contract Domain | 待验收 |
| Payment | 收款、待收、待付、对账基础模型 | 财务数据可进入 Payment / Expense Domain | 待验收 |
| Stay | 入住周期、在住状态、出馆状态 | Stay Engine 状态边界正确 | 待验收 |
| Room | 房间生命周期、状态动作、Audit/Event | Room Engine 动作合法，状态流转正确 | 待验收 |
| Caregiver | 照护师状态、可用性、资源能力 | Caregiver Engine 只管理资源状态，不越界 | 待验收 |
| Scheduling | 调度请求、上下文、决策、审批、执行框架 | Scheduler 只分析，Decision/Approval/Execution 链路完整 | 待验收 |

业务验收边界：

- 不要求自动排房。
- 不要求自动分配照护师。
- 不要求自动修改真实业务状态。
- 不要求接 UI。

## 三、经营验收

| 验收项 | 验收内容 | 通过标准 | 状态 |
|---|---|---|---|
| Metrics | 销售、资金、经营指标定义与快照 | 指标有定义、来源、计算方式和 Snapshot | 待验收 |
| Dashboard Query | 按时间、分类查询驾驶舱数据 | 查询只读，返回指标、来源、时间、状态 | 待验收 |
| Alert | 异常定义、异常判断、状态流转 | 可发现异常，生成 AlertResult，Audit/Event 完整 | 待验收 |

经营验收重点：

- 指标必须可追溯到 Domain。
- 查询不得修改业务数据。
- 异常不得自动执行业务动作。

## 四、AI 验收

| 验收项 | 验收内容 | 通过标准 | 状态 |
|---|---|---|---|
| Assistant | AIQuery、AIContext、AIResponse | 可按权限构建 Context，生成只读回答 | 待验收 |
| Knowledge | 知识文档、分类、版本、AI Context 关联 | 知识可创建、更新、读取、关联 AI | 待验收 |
| Retrieval | 关键词/规则检索、匹配结果、来源版本 | 检索结果有来源、版本、相关领域 | 待验收 |
| Reasoning | 推理链、结论、证据、置信度、不确定性 | 每个结论有步骤和来源 | 待验收 |
| Recommendation | 建议、优先级、预期影响、风险 | 每条建议有依据、置信度、风险提示 | 待验收 |
| Governance | 建议记录、人工审核、状态流转、责任链 | AI 建议可进入审核，不自动执行 | 待验收 |
| Memory | 经验记录、反馈、结果沉淀、AI Context 读取 | 成功/失败经验可沉淀并进入 Context | 待验收 |

AI 验收边界：

- 不接真实外部 AI API。
- 不自动审批。
- 不自动执行。
- 不修改业务数据。
- 必须保留 Audit/Event。

## 五、真实数据验收

| 验收项 | 验收内容 | 通过标准 | 状态 |
|---|---|---|---|
| 销售导入 | 真实销售文件只读解析、Adapter、Validation、Mapping、Metrics | 导入成功，校验通过，生成 Contract Domain 与销售指标 | 待验收 |
| 财务导入 | 真实财务数据只读解析、Adapter、Validation、Mapping、Metrics | 导入成功，校验通过，生成 Payment Domain 与资金指标 | 待验收 |

真实数据验收边界：

- 不修改原始数据。
- 不自动执行业务。
- 不发送通知。
- 不写生产业务状态。
- 只验证真实数据进入 OMS 的最小闭环。

## 六、权限验收

| 验收项 | 验收内容 | 通过标准 | 状态 |
|---|---|---|---|
| 石磊全局权限 | 全局经营、指标、异常、AI Context 查询 | 可读取全局经营数据，所有查询有 Audit | 待验收 |
| 普通角色权限隔离 | 普通员工按角色范围访问数据 | 只能读取授权范围，越权查询被拒绝或裁剪 | 待验收 |

权限验收重点：

- AI Context 必须按 actor_emp_id 裁剪。
- Dashboard Query 必须受权限控制。
- 任何越权访问不得返回完整全局数据。
- 权限相关拒绝或裁剪必须可审计。

## 七、追溯验收

任意结果必须可追溯：

```text
数据来源
↓
处理过程
↓
Audit
↓
AI依据
```

详细追溯链：

```text
source_file / row_id
↓
adapter_id / source_version / mapping_version
↓
domain_object_id
↓
metric_snapshot / dashboard_query / alert_result
↓
ai_query / reasoning_chain / recommendation
↓
audit_id / event_id / correlation_id
```

| 验收项 | 验收内容 | 通过标准 | 状态 |
|---|---|---|---|
| 数据来源 | source_file、row_id、source_version | 来源字段完整，可反查 | 待验收 |
| 处理过程 | Adapter、Validation、Mapping、Domain、Metrics | 每步有明确输出 | 待验收 |
| Audit | action、actor、reason、result、correlation_id | 关键动作均可审计 | 待验收 |
| AI 依据 | source_domains、related_metrics、related_alerts、evidence_sources | AI 输出可解释、可追溯 | 待验收 |

## 八、RC 验收通过条件

OMS V1.0 RC 通过条件：

```text
系统基础验收 = PASS
业务验收 = PASS
经营验收 = PASS
AI验收 = PASS
真实数据验收 = PASS
权限验收 = PASS
追溯验收 = PASS
```

若任一大类失败：

```text
OMS V1.0 RC = NOT READY
```

## 九、RC 验收输出物

验收完成后应输出：

- `OMS_V1.0_RC验收报告.md`
- 全量测试结果
- Health Check 结果
- 真实数据导入核对结果
- Metrics / Dashboard Query 样例
- Alert 样例
- AI 查询、推理、建议样例
- Audit/Event 追溯样例
- 权限裁剪样例

## 十、当前状态

```text
P0-P30 = completed
OMS V1.0 RC checklist = ready
Next Step = execute RC validation after approval
```
