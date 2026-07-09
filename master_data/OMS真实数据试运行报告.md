# OMS 真实数据试运行报告

阶段：P29 Real Data Pilot  
试运行日期：2026-07-09  
范围：销售签约数据、财务收款数据  
模式：只读试运行

## 一、试运行边界

- 本阶段只验证真实文件进入 OMS 的最小闭环。
- 不修改原始文件。
- 不修改业务状态。
- 不自动执行业务。
- 不自动发送通知。
- 不接 UI。
- 不接生产数据库。

本次链路：

```text
真实文件
↓
只读解析
↓
Data Adapter
↓
Validation
↓
Mapping
↓
Domain Object
↓
Metrics
```

## 二、数据来源

| 数据类型 | 来源文件 | 文件格式 | 本次处理 |
|---|---|---:|---|
| 销售签约数据 | `D:\Users\758595\xwechat_files\wxid_vlgopee1wc6922_c124\msg\file\2026-07\2026年销售明细表（经验为王7.9）.xlsx` | xlsx | 读取 3 个合同明细工作表 |
| 财务收款数据 | `D:\Users\758595\xwechat_files\wxid_vlgopee1wc6922_c124\temp\RWTemp\2026-07\af9f7870a5212593ebc5c2ffa04ffc13\f70259cc429de1933d7041bf77cc7d15.png` | png | 按截图可见行提取收款、待收、待付 |
| 房态截图 | `D:\Users\758595\xwechat_files\wxid_vlgopee1wc6922_c124\temp\RWTemp\2026-07\20a7455575f911e1d4d629cd13fcf618\d78dcc250f8d981f15a21524c1bc5490.jpg` | jpg | 已收到，但不在 P29 第一批接入范围 |

文件状态：

| 文件 | 状态 | 大小 |
|---|---|---:|
| 销售明细 7.9 | 存在 | 226026 bytes |
| 财务日报截图 7.9 | 存在 | 88843 bytes |
| 房态截图 7.9 | 存在 | 本阶段未导入 |

## 三、字段映射

### 1. 销售签约数据

Adapter：

| 字段 | 值 |
|---|---|
| adapter_id | `adapter_real_pilot_sales_20260709` |
| source_system | `real_sales_xlsx` |
| source_version | `2026_sales_detail_7.9` |
| target_domain | `Contract` |
| mapping_version | `contract.real_pilot.v1` |

字段映射：

| 外部字段 | OMS Domain 字段 |
|---|---|
| 合同编号 / 生成编号 | `contract_id` |
| 客户姓名 | `customer_name` |
| 签约日期 | `signed_date` |
| 合同金额 | `contract_amount` |
| 已收字段 | `received_amount` |
| 未收字段 | `unpaid_amount` |
| 销售人员 | `sales_owner` |
| 套系 | `package` |
| 工作表 | `source_sheet` |
| 工作表类型 | `source_sheet_type` |
| 行号 | `row_id` |
| 事件类型 | `event_type` |

### 2. 财务收款数据

Adapter：

| 字段 | 值 |
|---|---|
| adapter_id | `adapter_real_pilot_finance_20260709` |
| source_system | `finance_daily_report_image` |
| source_version | `2026.7.9_screenshot` |
| target_domain | `Payment` |
| mapping_version | `payment.real_pilot.v1` |

字段映射：

| 外部字段 | OMS Domain 字段 |
|---|---|
| 项目 | `payment_item` |
| 金额 | `amount` |
| 类型 | `payment_type` |
| 日期 | `record_date` |
| 品牌/业务线 | `brand` |
| 来源区块 | `source_section` |
| 来源文件 | `source_file` |

## 四、校验结果

| 数据类型 | 状态 | 记录数 | 有效数 | 无效数 | 异常 |
|---|---|---:|---:|---:|---:|
| 销售签约 | `COMPLETED` | 223 | 223 | 0 | 0 |
| 财务收款 | `COMPLETED` | 15 | 15 | 0 | 0 |

Audit：

| 数据类型 | Audit |
|---|---|
| 销售签约 | `data.import.request` → `data.import.completed` |
| 财务收款 | `data.import.request` → `data.import.completed` |

Event：

| 数据类型 | Event |
|---|---|
| 销售签约 | `data.adapter.completed` |
| 财务收款 | `data.adapter.completed` |

业务状态写入：

| 项目 | 结果 |
|---|---|
| mutates_business_state | `false` |
| production_system_connected | `false` |

## 五、导入结果

### 1. 销售签约数据

| 指标 | 结果 |
|---|---:|
| Domain Object 数量 | 223 |
| 合同金额合计 | 4675582 |
| 已收字段合计 | 1712580 |
| 未收字段合计 | 723074 |

按来源工作表：

| 来源类型 | 记录数 | 合同金额 |
|---|---:|---:|
| `inner_store_contract` | 181 | 4478084 |
| `external_caregiver_contract` | 5 | 59800 |
| `meal_contract` | 37 | 137698 |

### 2. 财务收款数据

| 指标 | 结果 |
|---|---:|
| Domain Object 数量 | 15 |
| 今日收款 | 31490.00 |
| 待收金额 | 37580.00 |
| 待付款金额 | 276993.08 |

按类型：

| 类型 | 记录数 | 金额 |
|---|---:|---:|
| `received` | 4 | 31490.00 |
| `receivable` | 2 | 37580.00 |
| `payable` | 9 | 276993.08 |

## 六、异常数据

| 类型 | 数量 | 说明 |
|---|---:|---|
| 销售校验异常 | 0 | 必填字段满足本次 Adapter 校验 |
| 财务校验异常 | 0 | 截图可见行满足本次 Adapter 校验 |
| 超出范围数据 | 1 | 房态截图已收到，但 P29 第一批只接销售与财务 |
| 来源限制 | 1 | 财务源为截图，本阶段只按可见行提取；后续正式接入应优先使用表格或系统记录 |

## 七、生成指标

Metrics 输出：

| metric_id | value |
|---|---:|
| `sales.today_receptions` | 0 |
| `sales.today_contracts` | 223 |
| `sales.deal_amount` | 4675582 |
| `sales.conversion_rate` | 0 |
| `funds.today_received` | 31490.00 |
| `funds.receivable_amount` | 37580.00 |
| `funds.payable_amount` | 276993.08 |
| `operations.current_stays` | 0 |
| `operations.room_utilization_rate` | 0 |
| `operations.caregiver_status_counts` | `{}` |

说明：

- P29 第一批未接入住、房态、照护师数据，所以经营类后 3 项为 0 或空对象。
- 销售接待数没有进入本次输入源，所以转化率为 0。
- 本次销售指标中的签约数代表读取到的合同类记录总数，不代表单日新增签约数。

## 八、试运行结论

| 项目 | 结果 |
|---|---|
| 销售真实文件进入 Adapter | PASS |
| 财务真实文件进入 Adapter | PASS |
| Validation | PASS |
| Mapping | PASS |
| Domain Object 生成 | PASS |
| Metrics 生成 | PASS |
| 原始数据修改 | 未发生 |
| 业务自动执行 | 未发生 |
| 通知发送 | 未发生 |

P29 第一批真实数据试运行结论：

```text
Real Data Pilot = PASS
Scope = sales contracts + finance received/pending records
Mode = read-only
Production readiness = pilot passed, not full production ingestion
```
