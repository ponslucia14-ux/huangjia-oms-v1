# OMS Business Correction机制设计

## 一、目标

Business Correction用于处理人工编号重复、字段格式错误和有充分证据的明显录入错误。它生成派生修正，不覆盖原始文件或原始值。

## 二、适用范围

- `DUPLICATE_IDENTIFIER`
- `FIELD_FORMAT_ERROR`
- `OBVIOUS_ENTRY_ERROR`

不适用：

- `AMOUNT_DISPUTE`
- `CUSTOMER_OWNERSHIP_DISPUTE`
- `PAYMENT_FACT_DISPUTE`

出现上述事实争议时必须继续Review或Quarantine。

## 三、处理链

```text
原始记录
-> Correction Assessment
-> Correction Proposal
-> 业务确认
-> Derived Corrected Record
-> Data Quality复验
-> Current候选
```

## 四、记录字段

- `correction_id`
- `domain`
- `entity_id`
- `field_name`
- `original_value`
- `corrected_value`
- `correction_type`
- `correction_reason`
- `requested_by_emp_id`
- `confirmed_by_emp_id`
- `source_file`
- `source_sheet`
- `source_row`
- `requested_at`
- `applied_at`
- `correlation_id`
- `audit_id`
- `event_id`

## 五、数据保护

1. 原始Excel保持不变。
2. 原始值保存在`source_original_values`。
3. 新值只存在于派生记录。
4. 未确认Correction状态为`PROPOSED`，不得进入Current。
5. Correction应用后仍必须重新通过Data Quality。

## 六、Audit与Event

Audit：

- `business.correction.propose`
- `business.correction.apply`

Event：

- `business.correction.proposed`
- `business.correction.applied`

Audit必须记录原值、新值、操作EMP、确认EMP、原因和时间。

## 七、NSEKI94131081重新评估

已知两条记录：

- 郝梓涵，2026-05-22，21,990元
- 王雪，2026-05-23，24,000元

两条记录客户、日期和金额字段各自完整；当前发现的是标识符重复，没有证据表明金额、客户归属或付款事实存在争议。

因此：

```text
assessment = ELIGIBLE_FOR_CORRECTION
correction_type = DUPLICATE_IDENTIFIER
proposal = NSEKI94131081-A / NSEKI94131081-B
application_status = PENDING_BUSINESS_CONFIRMATION
```

`-A/-B`只区分两条派生业务记录，不裁决客户、金额或付款事实。业务确认前两条仍保持Quarantine。
