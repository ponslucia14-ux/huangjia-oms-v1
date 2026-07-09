# OMS 生产接入设计

## 阶段目标

P28 Production Integration Layer 的目标，是让 OMS 从架构系统进入真实经营环境。

本阶段只完成生产接入方案设计，不写代码，不接真实系统，不修改现有 P0-P27 架构。

本阶段输出：

```text
真实数据来源
-> 接入方式
-> 数据映射
-> 风险控制
-> 最小上线范围
```

## 一、真实数据来源

生产接入层需要明确哪些真实经营数据可以进入 OMS，并为后续 Adapter 建设预留边界。

### 1. 销售数据

数据内容：

- 客户线索
- 客户跟进记录
- 签约状态
- 销售人员
- 成交金额
- 转化状态
- 流失原因

建议来源：

- 销售 Excel
- CRM 表格
- 飞书表格
- 人工录入入口
- 后续 API 对接

进入 OMS 后对应：

- Domain：Sales
- Metrics：今日接待数、今日签约数、成交金额、转化率
- AI Context：销售转化分析、流失原因分析、销售建议

### 2. 合同数据

数据内容：

- 合同编号
- 客户信息
- 套餐类型
- 合同金额
- 已收金额
- 待收金额
- 合同状态
- 签约时间

建议来源：

- 合同台账 Excel
- 合同审批记录
- 财务收款表
- 后续合同系统 API

进入 OMS 后对应：

- Domain：Contract / Payment
- Metrics：成交金额、待收金额、收款进度
- AI Context：合同风险、待收异常、客户履约状态

### 3. 财务数据

数据内容：

- 收入记录
- 支出记录
- 应收金额
- 应付金额
- 收款账户
- 付款对象
- 对账状态
- 结算状态

建议来源：

- 财务日报表
- 银行流水
- 现金日记账
- 实入账表
- 报销表
- 后续财务系统 API

进入 OMS 后对应：

- Domain：Finance
- Metrics：今日收款、待收金额、待付款金额
- AI Context：现金流分析、收款异常、待付款风险

### 4. 入住数据

数据内容：

- 客户姓名
- 入住时间
- 预产期
- 生产时间
- 出馆时间
- 套餐类型
- 管家
- 照护师
- 入住状态

建议来源：

- 在住表
- 入住登记表
- 飞书登记表
- 后续入住系统 API

进入 OMS 后对应：

- Domain：Stay
- Metrics：在住人数、今日入住、今日出馆
- AI Context：入住风险、服务进度、经营负载

### 5. 房态数据

数据内容：

- 房间号
- 房型
- 房间状态
- 当前入住客户
- 预订状态
- 清洁状态
- 维修状态
- 停用状态

建议来源：

- 房态表
- 在住表
- 房间巡检记录
- 飞书房态记录
- 后续房态系统 API

进入 OMS 后对应：

- Domain：Room
- Metrics：房间利用率、可用房间数、异常房间数
- AI Context：房态冲突、资源不足、调度建议

### 6. 照护师数据

数据内容：

- 照护师姓名
- 当前状态
- 负责客户
- 排班信息
- 负载情况
- 服务评价
- 异常记录

建议来源：

- 照护师排班表
- 服务登记表
- 在住表
- 人事台账
- 后续人效系统 API

进入 OMS 后对应：

- Domain：Caregiver
- Metrics：照护师状态数量、负载分布、服务资源利用
- AI Context：人效分析、服务风险、资源调度建议

### 7. 市场数据

数据内容：

- 渠道线索
- 活动记录
- 投放数据
- 客户来源
- 咨询转化
- 市场费用

建议来源：

- 市场 Excel
- 飞书活动记录
- 广告平台导出文件
- 后续市场系统 API

进入 OMS 后对应：

- Domain：Market / Sales
- Metrics：线索数、渠道转化、获客成本
- AI Context：渠道效果分析、市场投入建议

## 二、数据进入 OMS 的方式

生产接入层必须支持多种接入方式，但每种方式都需要统一进入 OMS Adapter，再进入 Domain。

### 1. 手工输入

适用场景：

- 少量关键数据补录
- 临时业务变更
- 异常数据更正
- 管理人员确认结果

要求：

- 必须有操作人。
- 必须有原因。
- 必须写 Audit。
- 必须生成 Event。
- 必须保留 source_type = manual_input。

边界：

- 不允许绕过 Domain。
- 不允许直接修改指标。
- 不允许无审计写入。

### 2. 文件导入

适用场景：

- Excel 台账
- 财务日报
- 在住表
- 房态表
- 销售明细

要求：

- 必须记录 source_file。
- 必须记录 row_id。
- 必须记录 import_batch_id。
- 必须保留原始字段快照。
- 必须生成 ingestion_event。

边界：

- 文件不是运行源。
- 文件只作为导入来源。
- 进入 OMS 后必须映射为 Domain 对象。

### 3. API

适用场景：

- 后续合同系统
- 后续财务系统
- 后续房态系统
- 后续 CRM

要求：

- 必须校验认证。
- 必须校验权限。
- 必须校验数据契约。
- 必须具备幂等键。
- 必须支持失败重试。

边界：

- 外部 API 不能直接写指标。
- 外部 API 不能直接触发执行。
- 必须通过 Adapter 和 Domain。

### 4. 飞书同步

适用场景：

- 飞书表格
- 飞书审批
- 飞书任务
- 飞书消息
- 飞书组织身份

要求：

- 必须记录 feishu_object_id。
- 必须记录 sync_cursor。
- 必须记录 sync_status。
- 必须处理权限不足。
- 必须处理同步失败。

边界：

- 飞书不是 OMS 的业务真相层。
- 飞书是数据来源与协作通道。
- OMS Domain 才是系统内运行标准。

### 5. 管理端同步

适用场景：

- 管理人员批量确认
- 数据修正
- 审核后同步
- 运营日报汇总

要求：

- 必须绑定 actor_emp_id。
- 必须填写 reason。
- 必须写 Audit。
- 必须保留 before / after。
- 必须走权限检查。

边界：

- 管理端不能绕过权限。
- 管理端不能直接写 AI 结果。
- 管理端不能跳过事件总线。

## 三、数据映射

所有外部数据进入 OMS 后，必须统一走以下链路：

```text
External Data
-> Ingestion Adapter
-> Data Contract Validation
-> Domain Object
-> Event
-> Metrics
-> Alert
-> AI Context
```

### 1. 外部数据到 Domain

| 外部数据 | Domain | 说明 |
| --- | --- | --- |
| 销售线索 | Sales | 进入销售生命周期 |
| 合同记录 | Contract | 进入合同与收款链路 |
| 收款记录 | Payment / Finance | 进入资金指标与财务风险 |
| 入住记录 | Stay | 进入入住生命周期 |
| 房间记录 | Room | 进入房间生命周期 |
| 照护师记录 | Caregiver | 进入资源状态管理 |
| 市场记录 | Market / Sales | 进入渠道与销售分析 |

要求：

- 每条外部数据必须映射到一个或多个 Domain。
- 无法映射的数据必须进入异常队列。
- 禁止外部数据直接驱动 Metrics 或 AI。

### 2. Domain 到 Metrics

| Domain | Metrics |
| --- | --- |
| Sales | 今日接待数、今日签约数、成交金额、转化率 |
| Contract / Payment | 今日收款、待收金额、收款完成率 |
| Finance | 待付款金额、支出金额、现金流状态 |
| Stay | 在住人数、今日入住、今日出馆 |
| Room | 房间利用率、可用房间数、异常房间数 |
| Caregiver | 照护师状态数量、服务负载 |
| Market | 渠道线索数、获客成本、渠道转化 |

要求：

- Metrics 只能从 Domain 或已验证的 Snapshot 生成。
- UI 或报表不能自行计算核心指标。
- 指标必须可追溯到来源 Domain。

### 3. Domain / Metrics / Alert 到 AI Context

AI Context 可读取：

- Domain Data
- Metrics Snapshot
- Dashboard Query Result
- Alert Result
- Audit Record
- Event Record
- Knowledge Context
- Memory Context

要求：

- 必须经过权限裁剪。
- 必须保留 source_domains。
- 必须保留 evidence_sources。
- AI 不能绕过 Domain 读取原始外部数据。

### 4. 数据追溯链

生产接入后，每条数据建议保留以下链路：

```text
source_type
source_id
source_file / external_object_id
row_id / object_version
import_batch_id / sync_cursor
domain_id
event_id
metric_snapshot_id
alert_id
ai_context_id
```

## 四、Data Adapter Version 管理

生产接入层必须管理每个外部数据 Adapter 的版本，避免外部数据格式变化后，OMS 仍按旧字段映射写入 Domain，造成业务数据错位。

### 1. Adapter Version 字段

每个 Adapter 必须保留：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `adapter_id` | 是 | Adapter 唯一 ID |
| `source_system` | 是 | 外部来源系统或文件类型 |
| `source_version` | 是 | 外部数据格式版本 |
| `target_domain` | 是 | 映射到的 OMS Domain |
| `mapping_version` | 是 | OMS 字段映射版本 |
| `last_sync_time` | 否 | 最近一次成功同步时间 |

### 2. Adapter Version 作用

Adapter Version 用于判断：

- 当前外部数据格式是否与 OMS 映射规则一致。
- 外部文件模板是否发生变化。
- API 返回字段是否发生变化。
- 飞书表格字段是否发生变化。
- 当前 Domain Mapping 是否需要升级。

### 3. Adapter Version 流程

```text
External Data
-> detect source_system / source_version
-> load adapter_id
-> verify mapping_version
-> map to target_domain
-> update last_sync_time
```

### 4. Version 风险处理

当发现版本不一致时：

- 禁止静默导入。
- 必须标记 `mapping_version_mismatch`。
- 必须进入异常队列。
- 必须写 Audit。
- 必须保留原始数据快照。
- 必须等待人工确认或 Adapter 升级。

### 5. Version 管理原则

```text
source_version changed
-> mapping_version must be reviewed
-> target_domain must not receive unverified data
```

Adapter Version 是生产接入层的基础治理能力，不参与业务执行，不修改业务状态。

## 五、生产风险

### 1. 数据质量风险

风险：

- 字段缺失
- 日期格式不一致
- 金额格式不一致
- 客户姓名重复
- 房间号不规范
- 状态值不统一

控制：

- Data Contract Validation
- 字段标准化
- 枚举映射
- 异常队列
- 人工复核

### 2. 权限风险

风险：

- 越权导入
- 越权查看
- 越权同步
- 外部系统权限过大

控制：

- actor_emp_id 必填
- role permission check
- operation scope check
- Audit mandatory
- sensitive data masking

### 3. 同步失败风险

风险：

- 飞书权限不足
- API 超时
- 文件格式变化
- 网络失败
- 外部系统不可用

控制：

- retry policy
- pending queue
- dead-letter queue
- sync_status
- failure_reason
- non-blocking main flow

### 4. 重复数据风险

风险：

- 重复导入 Excel
- API 重试重复写入
- 飞书同步重复事件
- 手工补录与自动同步冲突

控制：

- idempotency_key
- source fingerprint
- import_batch_id
- external_object_id
- duplicate detection
- conflict resolution

### 5. 数据时效风险

风险：

- Excel 不是最新版本
- 飞书同步延迟
- 财务流水延迟
- 手工确认滞后

控制：

- source_updated_at
- ingested_at
- freshness_status
- stale data warning
- dashboard data status

### 6. 业务语义漂移风险

风险：

- 外部字段含义变化
- 套餐名称变化
- 房态状态变化
- 销售阶段变化

控制：

- Semantic Contract
- Mapping Version
- Change Review
- Data Dictionary
- Regression Test

## 六、当前最小上线范围建议

P28 最小上线范围建议采用“小闭环、低风险、可追溯”的原则。

### 1. 建议优先接入的数据

第一批建议只接入：

| 数据 | 原因 |
| --- | --- |
| 在住数据 | 与经营状态直接相关 |
| 房态数据 | 与资源可用性直接相关 |
| 财务收款数据 | 与经营现金流直接相关 |
| 销售签约数据 | 与增长状态直接相关 |

暂缓：

- 市场投放数据
- 完整照护师人效数据
- 全量审批数据
- 复杂报销数据

### 2. 建议优先接入方式

第一阶段建议：

```text
Excel / 文件导入
-> Ingestion Adapter
-> Domain
-> Metrics
-> Dashboard Query
-> Alert
-> AI Context
```

原因：

- 风险低。
- 可人工核对。
- 不依赖外部 API 稳定性。
- 方便建立字段映射与数据契约。

### 3. 最小上线闭环

建议最小闭环：

```text
在住表 / 房态表 / 财务收款表 / 销售签约表
-> 文件导入
-> Domain Object
-> Metrics Snapshot
-> Alert Evaluation
-> Dashboard Query
-> AI Context
```

本阶段不建议直接上线：

- 自动执行
- 自动审批
- 自动排房
- 自动修改房态
- 自动发送真实通知

### 4. 最小生产验收标准

最小上线需要满足：

- 每条导入数据可追溯。
- 每条数据可映射到 Domain。
- Metrics 可从 Domain 生成。
- Alert 可识别异常。
- AI Context 可读取经过权限裁剪的数据。
- 同步失败不阻断系统。
- 重复导入不会重复生成业务对象。
- 全部导入动作写 Audit。
- 关键变化发布 Event。

### 5. P28 后续实施顺序建议

建议拆为以下子阶段：

```text
P28.1 Data Source Registry
P28.2 File Ingestion Adapter
P28.3 Data Contract Validation
P28.4 Domain Mapping
P28.5 Import Audit + Event
P28.6 Duplicate Detection
P28.7 Minimal Production Data Trial
```

## 七、P28 设计结论

P28 Production Integration Layer 的关键不是多接系统，而是建立统一接入标准。

核心原则：

```text
External Data
!= OMS Runtime Truth

External Data
-> Adapter
-> Contract Validation
-> Domain
-> Metrics
-> AI Context
```

当前建议：

- 第一阶段优先文件导入。
- 先接在住、房态、财务收款、销售签约四类核心数据。
- 不直接接自动执行。
- 不直接接真实通知。
- 不直接改业务状态。
- 先保证可追溯、可校验、可回滚。

P28 的目标状态：

```text
OMS = Architecture Complete
      + Production Data Entry Standard
      + Minimal Real Business Data Loop
```
