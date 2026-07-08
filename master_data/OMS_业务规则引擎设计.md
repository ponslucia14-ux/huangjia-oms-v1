# OMS 业务规则引擎设计

Version: 1.0
Status: P10 Draft
Owner: 石磊

---

# 一、目标

Business Rules Engine 是 OMS 的统一业务规则判断框架。

本阶段不是业务流程。

本阶段不是排房算法。

本阶段不是页面。

本阶段不是数据库。

本阶段只负责：

- 定义规则
- 判断规则
- 返回结果
- 返回优先级
- 返回命中原因

Rule Engine 不直接修改业务数据。

---

# 二、核心对象

## Rule Definition

规则定义，包含：

- rule_id
- name
- description
- priority
- evaluator
- enabled

## Rule Evaluation

规则判断输入，包含：

- action
- actor_emp_id
- domain
- required_fields
- data

## Rule Result

规则判断输出，包含：

- PASS
- WARNING
- REJECT
- reason
- priority
- metadata

## Rule Priority

数字越小，优先级越高。

当前第一批规则优先级：

| Priority | Rule |
|----------|------|
| 10 | 必填字段校验 |
| 20 | 角色权限校验 |
| 30 | 合同到账才生效 |
| 40 | 房间维修不可入住 |
| 50 | 房间停用不可入住 |

## Rule Reason

每条规则必须返回 reason。

reason 用于说明：

- 为什么通过
- 为什么警告
- 为什么拒绝

---

# 三、第一批规则

| Rule ID | 规则 | 结果 |
|---------|------|------|
| BR_REQUIRED_FIELDS | 必填字段校验 | 缺失字段时 REJECT |
| BR_ROLE_PERMISSION | 角色权限校验 | 非 EMP、未知 Domain、角色无权限时 REJECT |
| BR_CONTRACT_PAYMENT_CONFIRMED | 合同到账才生效 | 没有 confirmed payment 时 REJECT |
| BR_ROOM_MAINTENANCE_NOT_CHECKIN | 房间维修不可入住 | Room status 为 MAINTENANCE 时 REJECT |
| BR_ROOM_DISABLED_NOT_CHECKIN | 房间停用不可入住 | Room status 为 DISABLED 时 REJECT |

---

# 四、输出状态

| 状态 | 含义 |
|------|------|
| PASS | 规则通过 |
| WARNING | 非阻塞警告，需要业务层注意 |
| REJECT | 阻塞，业务层不得继续执行对应动作 |

整体结果按最高严重度返回：

REJECT 高于 WARNING。

WARNING 高于 PASS。

---

# 五、边界

Business Rules Engine 不做：

- 业务状态修改
- Audit 写入
- Event 发布
- 排房算法
- 自动派单
- 数据库存储
- 页面展示

业务模块必须先调用 Rule Engine。

Rule Engine 只返回判断结果，由业务模块决定是否继续执行。

---

# 六、当前调用方式

示例：

```python
from oms_v1.business_rules import BusinessRulesEngine, RuleContext

engine = BusinessRulesEngine()
result = engine.evaluate(
    RuleContext(
        action="check_in_room",
        actor_emp_id="EMP008",
        domain="Room",
        required_fields=("room_id",),
        data={"room_id": "room_001", "room": {"status": "RESERVED"}},
    )
)
```

返回：

- overall_status
- results
- reject_reasons
- warning_reasons
- mutates_business_state=False
