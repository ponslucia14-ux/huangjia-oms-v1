# OMS 数据持久化设计

## 阶段边界

P17 Data Persistence Foundation 建立 OMS 统一数据存储基础层。

本阶段只建立 Persistence Layer。

本阶段不是：

- 接生产数据库
- 迁移业务数据
- 做报表
- 修改业务逻辑
- 接 UI
- 改业务 Engine

第一阶段只支持 Local Storage Adapter。

## 持久化链路

```text
Domain Object
-> EntitySerializer
-> DataRepository
-> StorageAdapter
-> Local Versioned Record
```

每条持久化记录必须关联：

- `audit_id`
- `event_id`
- `correlation_id`

## 存储模型

### EntitySerializer

职责：

- 接收 dict
- 接收 dataclass
- 接收带 `to_dict()` 的对象
- 输出 JSON-safe dict

### StorageAdapter

职责：

- 本地追加写入
- 本地读取版本记录
- 第一阶段使用 JSONL 文件

默认路径：

```text
live_runtime/persistence/
```

存储结构：

```text
entity_type/entity_id.jsonl
```

### DataRepository

职责：

- 保存 Domain 对象
- 读取 Domain 对象
- 读取指定版本
- 读取全部版本
- 计算 next_version

### PersistenceManager

职责：

- 提供统一持久化入口
- 写入 Audit
- 保存对象版本
- 返回持久化记录

## 数据结构

### PersistenceRecord

字段：

- `record_id`
- `entity_type`
- `entity_id`
- `version`
- `payload`
- `audit_id`
- `event_id`
- `correlation_id`
- `saved_at`
- `schema_version`

## 版本规则

同一个：

```text
entity_type + entity_id
```

每保存一次，版本号递增：

```text
1 -> 2 -> 3
```

读取规则：

- 未指定 version：读取最新版本
- 指定 version：读取对应版本
- 不存在：抛出 KeyError

## Audit 关联

PersistenceManager 保存对象时必须写：

- `persistence.save`

Audit metadata 必须包含：

- entity_type
- entity_id
- event_id
- mutates_business_state=false

## Event 关联

本阶段不发布新 Event。

持久化记录必须保留上游 `event_id`。

## 边界

禁止：

- 修改业务状态
- 调用业务 Engine 写入
- 接 UI
- 接真实数据库

P17 只提供可被未来阶段调用的数据持久化基础能力。
