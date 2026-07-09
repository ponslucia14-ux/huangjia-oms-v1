# OMS V1.0 生产验证方案

阶段：P30 OMS V1.0 Production Validation  
目标：验证 OMS 是否具备真实经营使用能力  
执行方式：先设计验证方案，不接真实生产执行，不写代码

## 一、验证目标

P30 生产验证的目标不是继续扩展架构，而是确认 OMS V1.0 在真实经营数据和真实角色权限下是否能够形成可信闭环。

核心验证目标：

1. 数据正确  
   真实数据进入 OMS 后，字段、金额、状态、来源、版本、时间均可核对。

2. 流程闭环  
   外部数据进入 OMS 后，能够完成：

   ```text
   Data Adapter
   → Domain
   → Metrics
   → Dashboard Query
   → Alert
   → AI Context
   → Audit/Event
   ```

3. 权限正确  
   不同员工只能看到和查询自己权限范围内的数据；经营管理角色可查看全局经营数据。

4. Audit 完整  
   数据导入、查询、AI 分析、异常发现、建议生成均必须留下 Audit 和 Event。

5. AI 输出可追溯  
   AI 查询、推理、建议必须能追溯到：

   ```text
   source_domain
   → metric
   → alert
   → knowledge
   → audit/event
   ```

## 二、验证环境

### 1. 本地验证环境

| 项目 | 要求 |
|---|---|
| 代码分支 | `main` |
| 稳定节点 | P0-P29 |
| 测试基线 | 全量测试通过 |
| 数据模式 | 只读导入 |
| 执行模式 | 不自动执行业务 |
| 通知模式 | 不发送真实通知 |

### 2. 数据输入环境

| 输入方式 | 本阶段用途 | 状态 |
|---|---|---|
| 文件导入 | 真实经营数据试运行 | 允许 |
| Mock CSV / JSON Adapter | Adapter 框架验证 | 允许 |
| Excel 只读解析 | 真实文件预处理 | 允许 |
| 飞书同步 | 生产适配验证项 | 暂不开放 |
| API 接入 | 生产适配验证项 | 暂不开放 |
| 管理端录入 | 后续上线验证项 | 暂不开放 |

### 3. 输出验证环境

| 输出层 | 验证内容 |
|---|---|
| Domain | 真实数据是否映射为标准业务对象 |
| Metrics | 指标是否正确生成 |
| Dashboard Query | 是否能按分类和时间查询 |
| Alert | 是否能发现异常 |
| AI Assistant | 是否能基于授权 Context 回答 |
| AI Reasoning | 是否能生成可追溯推理链 |
| AI Recommendation | 是否能生成有依据的建议 |
| Audit/Event | 是否完整留痕 |

## 三、真实数据范围

### 1. 销售数据

验证内容：

- 销售签约记录
- 合同金额
- 已收金额
- 未收金额
- 销售人员
- 签约日期
- 来源文件和行号

进入链路：

```text
销售文件
→ Data Adapter
→ Contract Domain
→ Sales Metrics
→ Dashboard Query
→ AI Context
```

关键校验：

- 合同记录数正确
- 合同金额合计正确
- 来源行号可追溯
- 缺失字段可识别

### 2. 财务数据

验证内容：

- 收款
- 待收
- 待付款
- 余额
- 日期
- 来源文件

进入链路：

```text
财务文件
→ Data Adapter
→ Payment / Expense Domain
→ Funds Metrics
→ Alert
→ AI Context
```

关键校验：

- 收款金额正确
- 待收金额正确
- 待付款金额正确
- 财务异常可识别

### 3. 入住数据

验证内容：

- 入住人
- 入住日期
- 出馆日期
- 入住状态
- 服务周期
- 关联房间

进入链路：

```text
入住文件
→ Data Adapter
→ Stay Domain
→ Operations Metrics
→ Alert
→ AI Context
```

关键校验：

- 当前在住人数正确
- 入住/出馆状态正确
- 入住冲突可识别

### 4. 房态数据

验证内容：

- 房间号
- 房间类型
- 房间状态
- 当前入住关联
- 清洁/维修/停用状态

进入链路：

```text
房态文件
→ Data Adapter
→ Room Domain
→ Operations Metrics
→ Alert
→ Scheduling Context
```

关键校验：

- 房间资源数量正确
- 可用房间数量正确
- 房间状态限制可识别

### 5. 照护师数据

验证内容：

- 员工身份
- 状态
- 排班
- 可用性
- 服务负载

进入链路：

```text
照护师文件
→ Data Adapter
→ Caregiver Domain
→ Operations Metrics
→ Scheduling Context
```

关键校验：

- 可用照护师数量正确
- 状态分类正确
- 不可用资源不会进入候选结果

## 四、验证场景

### 场景 0：OMS 运行健康验证

目标：验证 OMS 基础能力正常后，再进入经营查看、AI 查询分析、异常发现、建议生成、审计追踪。

验证内容：

| 基础能力 | 验证重点 |
|---|---|
| Bootstrap | 系统启动链是否完整，基础模块是否可加载 |
| Health Check | 启动自检是否通过，阻断项是否为 0 |
| Master Data | 员工、角色、权限、身份映射是否可读取 |
| Persistence | 基础持久化保存、读取、版本记录是否正常 |
| Event Bus | 事件发布、事件记录、事件类型是否正常 |
| Audit | 审计写入、读取、关联 correlation_id 是否正常 |

验证步骤：

1. 执行 Bootstrap 验证。
2. 执行 Health Check。
3. 读取 Master Data。
4. 验证 Persistence 基础保存与读取。
5. 发布一条基础 Event。
6. 写入一条基础 Audit。
7. 确认无基础能力阻断项。

通过标准：

- Bootstrap 正常。
- Health Check 无阻断项。
- Master Data 可读取。
- Persistence 可保存、读取、保留版本。
- Event Bus 可发布事件。
- Audit 可写入和查询。
- 基础能力正常后，才允许进入场景 1-5。

### 场景 1：经营管理查看

目标：验证经营管理角色是否可以看到真实经营状态。

验证步骤：

1. 导入销售、财务、入住、房态、照护师真实样本。
2. 生成 Metrics Snapshot。
3. 使用 Dashboard Query 查询：
   - 销售驾驶舱
   - 资金驾驶舱
   - 经营驾驶舱
4. 核对指标来源 Domain。

通过标准：

- 指标值与源文件一致。
- 查询结果包含生成时间、来源 Domain、数据状态。
- 查询动作写入 `dashboard.query` Audit。
- 查询动作发布 `dashboard.query.executed` Event。

### 场景 2：AI 查询分析

目标：验证 AI 可以基于授权 Context 进行只读分析。

验证步骤：

1. 构建 AIQuery。
2. 按 actor_emp_id 进行权限裁剪。
3. 读取授权范围内的：
   - Domain
   - Metrics
   - Dashboard Query
   - Alert
   - Audit
   - Event
   - Knowledge
4. 生成 AIResponse。

通过标准：

- AI 不读取未授权数据。
- AI 查询写入 `ai.query` Audit。
- AI 响应写入 `ai.response` Audit。
- 发布 `ai.query.requested` 和 `ai.response.generated` Event。
- AI 不修改任何业务数据。

### 场景 3：异常发现

目标：验证 OMS 能主动发现经营异常。

验证规则：

- 房间资源不足
- 入住冲突
- 待收异常
- 待付款异常
- 审批超时
- Health Check Warning

验证步骤：

1. 输入真实样本数据。
2. 构建 AlertContext。
3. 执行 ExceptionEngine。
4. 生成 AlertResult。

通过标准：

- 异常规则命中正确。
- 严重级别正确。
- 状态初始为 `OPEN`。
- 写入 Audit。
- 发布 `alert.created` Event。
- 可被 Notification Layer 消费，但本阶段不发送真实通知。

### 场景 4：建议生成

目标：验证 AI 可以基于推理结果生成可解释建议。

验证步骤：

1. 使用 AIContext、Knowledge Retrieval Result、Metrics、Alerts 构建 ReasoningContext。
2. 生成 ReasoningChain。
3. 基于 ReasoningResult 生成 RecommendationResult。
4. 检查建议的依据、风险和置信度。

通过标准：

- 每条建议包含 evidence_sources。
- 每条建议包含 confidence。
- 每条建议包含 risks。
- 写入 `ai.recommendation.request` Audit。
- 写入 `ai.recommendation.generated` Audit。
- 发布 `ai.recommendation.generated` Event。
- 不进入自动执行。

### 场景 5：审计追踪

目标：验证一条真实数据从导入到查询、异常、AI 分析的完整追踪链。

验证链路：

```text
source_file
→ adapter_id
→ source_version
→ mapping_version
→ domain_object_id
→ metric_snapshot
→ dashboard_query
→ alert_result
→ ai_query
→ ai_response
→ audit/event
```

通过标准：

- 每个关键节点都有唯一 ID。
- 每个关键节点都有 timestamp。
- 每个关键节点有关联 correlation_id。
- 可以从最终结果反查数据来源。

## 五、验收标准

### 1. 数据正确

| 验收项 | 标准 |
|---|---|
| 记录数 | 与源文件可核对 |
| 金额 | 与源文件合计一致 |
| 状态 | 与源文件业务状态一致 |
| 来源 | source_file / row_id / adapter_id 完整 |
| 版本 | source_version / mapping_version 完整 |

### 2. 流程闭环

| 验收项 | 标准 |
|---|---|
| Data Adapter | Completed 或明确 Failed |
| Domain | 生成标准 Domain Object |
| Metrics | 能生成 Snapshot |
| Dashboard Query | 只读查询成功 |
| Alert | 能生成异常结果 |
| AI | 能生成可追溯回答和建议 |

### 3. 权限正确

| 验收项 | 标准 |
|---|---|
| 全局经营角色 | 可查询全局经营数据 |
| 普通角色 | 仅查询授权范围 |
| AI Context | 按权限裁剪 |
| 越权查询 | 被拒绝或裁剪 |

### 4. Audit 完整

必须覆盖：

- `data.import.request`
- `data.import.completed`
- `dashboard.query`
- `alert.created`
- `ai.query`
- `ai.response`
- `ai.reasoning.request`
- `ai.reasoning.completed`
- `ai.recommendation.request`
- `ai.recommendation.generated`

### 5. AI 输出可追溯

| 验收项 | 标准 |
|---|---|
| answer | 有来源 |
| reasoning_chain | 有步骤 |
| recommendation | 有依据 |
| confidence | 有数值或等级 |
| uncertainty | 有说明 |
| evidence_sources | 可反查 |

## 六、当前限制

| 限制项 | 当前状态 | 影响 |
|---|---|---|
| UI | 未完成生产级入口 | 本阶段只能验证后端能力和数据链路 |
| 飞书生产适配 | 未完成真实生产接入 | 暂不能作为飞书生产应用验收 |
| 真实通知发送 | 未开放 | Notification Layer 只验证可消费事件 |
| 自动化执行 | 未完全开放 | AI 建议和异常不自动执行 |
| 生产数据库 | 未接入 | 当前仍以基础持久化和只读样本验证为主 |
| 数据接入范围 | P29 仅完成销售与财务试运行 | 入住、房态、照护师仍需后续试运行 |
| 真实审批流 | 未接生产审批系统 | Approval 只验证内部模型 |
| 真实 AI API | 未接入 | AI 输出为框架级模拟或规则生成 |

## 七、P30 最小验证范围建议

P30 第一轮建议只验证最小闭环：

1. 销售签约数据  
   验证 Contract Domain、Sales Metrics、Dashboard Query、AI Context。

2. 财务收款数据  
   验证 Payment Domain、Funds Metrics、Alert、AI Context。

3. 房态与入住样本  
   验证 Room / Stay Domain、Operations Metrics、入住冲突 Alert。

4. 照护师样本  
   验证 Caregiver Domain、资源状态统计、Scheduling Context。

5. 一条完整追踪链  
   从真实 source_file 追踪到 AI 建议。

## 八、P30 通过判定

P30 可判定通过的最低条件：

```text
真实数据进入 = PASS
Domain 映射 = PASS
Metrics 输出 = PASS
Dashboard Query = PASS
Alert 发现 = PASS
AI 查询/推理/建议 = PASS
Audit/Event = PASS
权限裁剪 = PASS
业务状态未被自动修改 = PASS
```

若任一项失败：

```text
P30 = NOT READY
```

## 九、P30 输出物

P30 验证执行完成后，应输出：

- `OMS_V1.0生产验证报告.md`
- 验证数据清单
- 指标核对表
- 异常发现清单
- AI 输出追溯样例
- Audit/Event 追踪样例
- 风险与限制清单

## 十、结论

P30 的核心不是新增能力，而是验证 OMS V1.0 是否已经具备真实经营使用基础。

本方案定义的验证重点为：

```text
真实数据
→ 正确映射
→ 指标可查
→ 异常可发现
→ AI 可解释
→ Audit 可追踪
→ 权限可控制
```

当前建议：

```text
P30 Design = READY
Next Step = 等待验收后进入生产验证执行阶段
```
