# OMS 数据适配框架设计

## 阶段边界

P28 Data Adapter Framework 建立 OMS 外部数据接入框架。

本阶段只建立统一 Adapter 能力，不接真实凰家数据，不接真实 Excel，不接飞书，不接 API，不接生产系统。

本阶段禁止：

- 修改业务 Engine
- 直接写业务状态
- 接 UI
- 导入真实生产数据
- 绕过 Domain

## 一、总体流程

```text
External Data
-> Adapter
-> Validation
-> Mapping
-> Domain Object
```

说明：

- External Data 第一阶段只支持 Mock CSV / Mock JSON。
- Adapter 只解析输入，不写业务状态。
- Validation 负责结构校验、必填字段校验、版本校验。
- Mapping 负责把外部字段映射为 Domain Object。
- Domain Object 是适配后的标准对象，不代表已经写入业务引擎。

## 二、AdapterConfig

AdapterConfig 是一个数据源适配器的版本与映射配置。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `adapter_id` | 是 | Adapter 唯一 ID |
| `source_system` | 是 | 外部数据来源 |
| `source_version` | 是 | 外部数据格式版本 |
| `target_domain` | 是 | 目标 OMS Domain |
| `mapping_version` | 是 | 字段映射版本 |
| `input_format` | 是 | `mock_csv` 或 `mock_json` |
| `required_fields` | 否 | 外部数据必填字段 |
| `field_mapping` | 否 | 外部字段到 Domain 字段映射 |
| `last_sync_time` | 否 | 最近成功同步时间 |

配置要求：

- `target_domain` 必须存在于 Domain Registry。
- `input_format` 只能是 mock 类型。
- `mapping_version` 必须明确，禁止隐式映射。

## 三、DataAdapter

DataAdapter 是统一接入编排层。

职责：

- 接收 Mock CSV / Mock JSON。
- 调用 DataValidator。
- 调用 DataMapper。
- 输出 AdapterResult。
- 写 Audit。
- 发布 Event。

边界：

- 不修改 Domain Engine。
- 不写真实业务状态。
- 不执行后续工作流。
- 不接真实生产系统。

## 四、DataValidator

DataValidator 负责校验外部输入。

校验内容：

- 输入格式是否受支持。
- 数据是否为空。
- required_fields 是否存在。
- 每行 required_fields 是否有值。
- source_version 是否存在。
- mapping_version 是否存在。
- target_domain 是否存在。

输出：

```text
validation_result
```

字段：

- `is_valid`
- `record_count`
- `valid_count`
- `invalid_count`
- `issues`
- `source_version`
- `mapping_version`

## 五、DataMapper

DataMapper 负责把校验通过的记录映射为 Domain Object。

输出 Domain Object 字段：

| 字段 | 说明 |
| --- | --- |
| `domain_object_id` | 适配后的对象 ID |
| `domain` | 目标 Domain |
| `source` | Adapter 与来源信息 |
| `payload` | 映射后的业务字段 |
| `mapping_version` | 映射版本 |
| `import_time` | 导入时间 |
| `mutates_business_state` | 固定为 false |

说明：

- Domain Object 只是接入结果。
- 不等于业务状态已被修改。

## 六、AdapterResult

AdapterResult 是一次接入结果。

字段：

| 字段 | 说明 |
| --- | --- |
| `adapter_id` | Adapter ID |
| `source_system` | 来源系统 |
| `source_version` | 来源版本 |
| `target_domain` | 目标 Domain |
| `mapping_version` | 映射版本 |
| `import_time` | 导入时间 |
| `validation_result` | 校验结果 |
| `domain_objects` | 映射结果 |
| `status` | `COMPLETED` 或 `FAILED` |
| `failure_reasons` | 失败原因 |
| `audit_records` | Audit 记录 |
| `events` | Event 记录 |

## 七、Audit

导入请求必须写入：

```text
data.import.request
```

导入完成必须写入：

```text
data.import.completed
```

导入失败必须写入：

```text
data.import.failed
```

Audit metadata 必须包含：

- `adapter_id`
- `source_system`
- `source_version`
- `target_domain`
- `mapping_version`
- `import_time`
- `validation_result`
- `mutates_business_state = false`
- `production_system_connected = false`

## 八、Event

导入完成发布：

```text
data.adapter.completed
```

导入失败发布：

```text
data.adapter.failed
```

Event payload 必须包含：

- `adapter_id`
- `source_system`
- `source_version`
- `target_domain`
- `mapping_version`
- `import_time`
- `domain_object_count`
- `validation_result`
- `mutates_business_state = false`
- `production_system_connected = false`

## 九、第一阶段输入范围

第一阶段只支持：

- Mock CSV
- Mock JSON

不支持：

- 真实 Excel
- 飞书同步
- API
- 生产数据库
- 生产业务系统

## 十、设计结论

Data Adapter Framework 的目标，是建立统一外部数据进入 OMS 的标准通道。

当前阶段目标状态：

```text
Mock External Data
-> AdapterConfig
-> DataValidator
-> DataMapper
-> AdapterResult
```

系统边界：

```text
Adapter Output != Business State Mutation
```

Adapter 只负责接入、校验、映射、审计、事件，不负责执行和业务状态修改。
