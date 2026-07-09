# OMS V1.0 RC 验收报告

阶段：OMS V1.0 Release Candidate 第一轮验收  
执行日期：2026-07-09  
执行原则：只验证，不新增功能，不修复问题  
验收范围：系统基础、真实数据、经营指标、AI 能力、权限、审计追溯

## 一、验收结论

```text
RC validation result = PASS WITH RISKS
Blocking issue = 0
RC issue = 2
Full test result = 358 OK
```

结论：

- 现有系统基础能力可启动。
- P0-P30 全量测试通过。
- 销售与财务真实数据最小闭环通过。
- 经营指标、查询、异常、AI、权限、追溯能力通过现有测试。
- 第一轮未发现阻断型问题。
- 发现 2 个 RC Issue，需进入统一处理池。

## 二、执行命令与结果

| 验收命令 | 结果 |
|---|---|
| `git status --branch --short` | `main...origin/main`，执行前 clean |
| `python -m unittest discover -s tests` | 358 tests OK |
| `python -m oms_v1.health_check --json --report <temp>` | startup_allowed=true；pass=9；warning=1；fail=0 |
| 系统基础专项测试 | 21 tests OK |
| 业务专项测试 | 67 tests OK |
| 经营/真实数据相关专项测试 | 36 tests OK |
| AI 专项测试 | 60 tests OK |
| 权限专项测试 | 4 tests OK |
| 追溯专项测试 | 27 tests OK |

## 三、系统基础验收

### 1. Bootstrap

| 项目 | 内容 |
|---|---|
| 操作步骤 | 执行 `tests.test_bootstrap`，并纳入系统基础专项测试 |
| 验收结果 | PASS |
| 发现问题 | 无 |
| 风险等级 | 低 |

### 2. Health Check

| 项目 | 内容 |
|---|---|
| 操作步骤 | 执行 `python -m oms_v1.health_check --json --report <temp>` |
| 验收结果 | PASS WITH WARNING |
| 发现问题 | 飞书 API 探测存在非阻断 warning：approval endpoint 返回 invalid access token |
| 风险等级 | 中 |

Health Check 明细：

| 指标 | 结果 |
|---|---:|
| startup_allowed | true |
| pass | 9 |
| warning | 1 |
| fail | 0 |

### 3. Master Data

| 项目 | 内容 |
|---|---|
| 操作步骤 | 执行 `tests.test_master_data`，并由 Health Check 读取主数据 |
| 验收结果 | PASS |
| 发现问题 | 无 |
| 风险等级 | 低 |

验证结果：

- 员工主数据：11 条
- EMP 无重复
- user_id 无重复
- open_id / union_id 已填写
- 角色覆盖完整

### 4. Persistence

| 项目 | 内容 |
|---|---|
| 操作步骤 | 执行 `tests.test_persistence` |
| 验收结果 | PASS |
| 发现问题 | 无 |
| 风险等级 | 低 |

验证结果：

- 保存成功
- 读取成功
- 版本记录成功
- Audit 关联成功
- Event 关联成功

### 5. Event Bus

| 项目 | 内容 |
|---|---|
| 操作步骤 | 执行 `tests.test_event_bus` |
| 验收结果 | PASS |
| 发现问题 | 无 |
| 风险等级 | 低 |

### 6. Audit

| 项目 | 内容 |
|---|---|
| 操作步骤 | 执行 `tests.test_audit_log` |
| 验收结果 | PASS |
| 发现问题 | 无 |
| 风险等级 | 低 |

验证结果：

- Audit 可写入
- Audit 可读取
- append-only 边界生效

## 四、真实数据验收

### 1. 销售导入

| 项目 | 内容 |
|---|---|
| 操作步骤 | 只读读取 7.9 销售明细文件，核对 P29 Adapter 结果 |
| 验收结果 | PASS |
| 发现问题 | 无 |
| 风险等级 | 低 |

核对结果：

| 指标 | 结果 |
|---|---:|
| 文件存在 | true |
| 销售记录数 | 223 |
| 合同金额合计 | 4675582 |
| 已收字段合计 | 1712580 |
| 未收字段合计 | 723074 |

### 2. 财务导入

| 项目 | 内容 |
|---|---|
| 操作步骤 | 只读核对 7.9 财务截图可见行，核对 P29 Adapter 结果 |
| 验收结果 | PASS |
| 发现问题 | 财务源本轮仍为截图可见行，不是结构化财务源文件 |
| 风险等级 | 中 |

核对结果：

| 指标 | 结果 |
|---|---:|
| 财务记录数 | 15 |
| 收款金额 | 31490.00 |
| 待收金额 | 37580.00 |
| 待付款金额 | 276993.08 |

### 3. 真实数据范围说明

| 数据域 | 第一轮结果 |
|---|---|
| 销售 | PASS |
| 财务 | PASS |
| 入住 | 未进行真实样本导入，本轮仅验证系统模块 |
| 房态 | 未进行真实样本导入，本轮仅验证系统模块 |
| 照护师 | 未进行真实样本导入，本轮仅验证系统模块 |

## 五、经营指标验收

| 验收项目 | 操作步骤 | 验收结果 | 发现问题 | 风险等级 |
|---|---|---|---|---|
| Metrics | 执行 `tests.test_metrics`，并核对 P29 指标输出 | PASS | 无 | 低 |
| Dashboard Query | 执行 `tests.test_dashboard_query` | PASS | 无 | 低 |
| Alert | 执行 `tests.test_alert_engine` | PASS | 无 | 低 |

Metrics 真实数据核对：

| metric_id | value |
|---|---:|
| `sales.today_contracts` | 223 |
| `sales.deal_amount` | 4675582 |
| `funds.today_received` | 31490.00 |
| `funds.receivable_amount` | 37580.00 |
| `funds.payable_amount` | 276993.08 |

验收结论：

- 指标模型可生成 Snapshot。
- Dashboard Query 只读。
- Alert 可生成异常结果。
- 经营能力未修改业务数据。

## 六、AI 能力验收

| 验收项目 | 操作步骤 | 验收结果 | 发现问题 | 风险等级 |
|---|---|---|---|---|
| Assistant | 执行 `tests.test_ai_assistant` | PASS | 无 | 低 |
| Knowledge | 执行 `tests.test_knowledge` | PASS | 无 | 低 |
| Retrieval | 执行 `tests.test_knowledge_retrieval` | PASS | 无 | 低 |
| Reasoning | 执行 `tests.test_ai_reasoning` | PASS | 无 | 低 |
| Recommendation | 执行 `tests.test_ai_recommendation` | PASS | 无 | 低 |
| Governance | 执行 `tests.test_ai_governance` | PASS | 无 | 低 |
| Memory | 执行 `tests.test_ai_memory` | PASS | 无 | 低 |

AI 专项结果：

```text
AI tests = 60 OK
external_ai_called = false
mutates_business_state = false
```

验收结论：

- AI 可构建授权 Context。
- AI 查询、推理、建议均保留来源。
- AI 建议可进入治理与记忆层。
- 未调用真实外部 AI API。
- 未自动执行。
- 未修改业务数据。

## 七、权限验收

### 1. 石磊全局权限

| 项目 | 内容 |
|---|---|
| 操作步骤 | 执行 AI 全局 Context 权限测试、Dashboard 查询权限测试 |
| 验收结果 | PASS |
| 发现问题 | 无 |
| 风险等级 | 低 |

验证结果：

- 可读取全局 Metrics。
- 可读取销售、资金、经营 Dashboard 数据。
- 可读取 Alert、Audit、Event Context。
- 查询和响应均写入 Audit/Event。

### 2. 普通角色权限隔离

| 项目 | 内容 |
|---|---|
| 操作步骤 | 执行普通角色 AI Context 裁剪和 Dashboard 越权阻断测试 |
| 验收结果 | PASS |
| 发现问题 | 无 |
| 风险等级 | 低 |

验证结果：

- 财务角色仅读取资金相关 Context。
- 销售角色不能读取资金或经营 Context。
- Dashboard 越权查询会被阻断。
- AI Context 会按权限裁剪。

权限专项结果：

```text
permission tests = 4 OK
```

## 八、审计追溯验收

| 验收项目 | 操作步骤 | 验收结果 | 发现问题 | 风险等级 |
|---|---|---|---|---|
| 数据来源追溯 | 执行 Data Adapter source trace 测试 | PASS | 无 | 低 |
| 处理过程追溯 | 验证 Adapter、Validation、Mapping、Domain 输出 | PASS | 无 | 低 |
| Audit 追溯 | 执行 Audit Log 测试 | PASS | 无 | 低 |
| Event 追溯 | 执行 Event Bus 测试 | PASS | 无 | 低 |
| AI 依据追溯 | 执行 Reasoning / Recommendation 测试 | PASS | 无 | 低 |

追溯专项结果：

```text
traceability tests = 27 OK
```

已验证链路：

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

## 九、RC Issue 记录

### RC-001：飞书 API 探测 warning

| 字段 | 内容 |
|---|---|
| 来源 | Health Check |
| 现象 | approval endpoint 返回 invalid access token |
| 影响 | 不阻断 OMS 启动；会影响未来真实飞书审批/同步生产适配 |
| 风险等级 | 中 |
| 当前处理 | 记录，不修复 |

### RC-002：真实数据第一轮仅覆盖销售与财务

| 字段 | 内容 |
|---|---|
| 来源 | 真实数据验收 |
| 现象 | 入住、房态、照护师未进行真实样本导入 |
| 影响 | 不影响 P29/P30 已验收范围；影响 V1.0 全量真实经营数据覆盖度 |
| 风险等级 | 中 |
| 当前处理 | 记录，不修复 |

## 十、第一轮 RC 验收总表

| 验收大类 | 结果 | 风险等级 |
|---|---|---|
| 系统基础验收 | PASS WITH WARNING | 中 |
| 真实数据验收 | PASS WITH SCOPE LIMIT | 中 |
| 经营指标验收 | PASS | 低 |
| AI 能力验收 | PASS | 低 |
| 权限验收 | PASS | 低 |
| 审计追溯验收 | PASS | 低 |

## 十一、最终判断

```text
OMS V1.0 RC first validation = PASS WITH RISKS
Blocking issue = 0
Open RC issue = 2
Code change during validation = 0
```

建议：

```text
进入 RC Issue 统一处理评审。
暂不直接修改系统。
```
