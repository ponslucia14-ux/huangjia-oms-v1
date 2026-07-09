# OMS V1.0 RC 第二轮验收报告

阶段：RC Round 2 真实运营数据补充验证  
执行日期：2026-07-09  
目标：关闭 RC-002 真实数据覆盖不足  
边界：只读验证，不修改原始文件，不修改业务数据，不自动执行，不发送通知

## 一、验收结论

```text
RC Round 2 result = PASS WITH SOURCE RISK
RC-002 = CLOSED
Blocking issue = 0
New blocking risk = 0
```

结论：

- 入住数据已完成 Stay Domain 补充验证。
- 房态数据已完成 Room Domain、Room Metrics、Alert 补充验证。
- 照护师数据已完成 Caregiver Domain、Resource Metrics 补充验证。
- Dashboard 可读取运营指标。
- AI Context 可读取运营指标和 Dashboard 数据。
- 未修改原始数据。
- 未修改业务状态。
- 未自动执行。

## 二、数据来源

| 数据范围 | 来源文件 | 文件格式 | 处理方式 |
|---|---|---|---|
| 入住数据 | `D:\Users\758595\xwechat_files\wxid_vlgopee1wc6922_c124\temp\RWTemp\2026-07\20a7455575f911e1d4d629cd13fcf618\d78dcc250f8d981f15a21524c1bc5490.jpg` | jpg | 按截图可见汇总与可见行进行只读结构化 |
| 房态数据 | 同上 | jpg | 按截图可见房间状态进行只读结构化 |
| 照护师数据 | 同上 | jpg | 按截图可见照护师人数进行只读结构化 |

来源文件状态：

| 项目 | 结果 |
|---|---|
| source_version | `2026.7.9_room_status_screenshot` |
| 文件存在 | true |
| 文件大小 | 262178 bytes |

截图可见汇总：

| 项目 | 结果 |
|---|---:|
| 当前在住 | 26 |
| 待入住 | 2 |
| 照护师人数 | 26 |

## 三、Adapter 状态

### 1. 入住数据 Adapter

| 项目 | 结果 |
|---|---|
| adapter_id | `adapter_rc2_stay_20260709` |
| source_system | `real_room_status_image` |
| source_version | `2026.7.9_room_status_screenshot` |
| target_domain | `Stay` |
| mapping_version | `stay.rc2.v1` |
| status | `COMPLETED` |

Validation：

| 指标 | 结果 |
|---|---:|
| record_count | 28 |
| valid_count | 28 |
| invalid_count | 0 |
| issues | 0 |

Mapping / Domain：

| 项目 | 结果 |
|---|---:|
| Domain Object | 28 |
| Audit | `data.import.request` → `data.import.completed` |
| Event | `data.adapter.completed` |

### 2. 房态数据 Adapter

| 项目 | 结果 |
|---|---|
| adapter_id | `adapter_rc2_room_20260709` |
| source_system | `real_room_status_image` |
| source_version | `2026.7.9_room_status_screenshot` |
| target_domain | `Room` |
| mapping_version | `room.rc2.v1` |
| status | `COMPLETED` |

Validation：

| 指标 | 结果 |
|---|---:|
| record_count | 39 |
| valid_count | 39 |
| invalid_count | 0 |
| issues | 0 |

Mapping / Domain：

| 项目 | 结果 |
|---|---:|
| Domain Object | 39 |
| Audit | `data.import.request` → `data.import.completed` |
| Event | `data.adapter.completed` |

### 3. 照护师数据 Adapter

| 项目 | 结果 |
|---|---|
| adapter_id | `adapter_rc2_caregiver_20260709` |
| source_system | `real_room_status_image` |
| source_version | `2026.7.9_room_status_screenshot` |
| target_domain | `Caregiver` |
| mapping_version | `caregiver.rc2.v1` |
| status | `COMPLETED` |

Validation：

| 指标 | 结果 |
|---|---:|
| record_count | 26 |
| valid_count | 26 |
| invalid_count | 0 |
| issues | 0 |

Mapping / Domain：

| 项目 | 结果 |
|---|---:|
| Domain Object | 26 |
| Audit | `data.import.request` → `data.import.completed` |
| Event | `data.adapter.completed` |

## 四、Metrics 输出

运营指标：

| metric_id | value |
|---|---:|
| `operations.current_stays` | 26 |
| `operations.room_utilization_rate` | 0.7222 |
| `operations.caregiver_status_counts` | `{"serving": 26}` |

Dashboard Query：

| 项目 | 结果 |
|---|---|
| dashboard_category | `operations_dashboard` |
| metric_count | 3 |
| data_status | `READY` |
| mutates_business_state | false |

## 五、Alert 验证

Alert Context：

| 项目 | 结果 |
|---|---|
| room_records | 39 |
| stay_records | 28 |
| required_available_rooms | 2 |

Alert Result：

| 指标 | 结果 |
|---|---:|
| alert_count | 0 |
| 业务状态修改 | false |

结论：

- 本轮未发现房间资源不足。
- 本轮未发现入住冲突。
- Alert Engine 可执行，且未修改业务状态。

## 六、AI Context 验证

| 项目 | 结果 |
|---|---:|
| metrics_count | 10 |
| dashboard_count | 1 |
| alerts_count | 0 |
| confidence | `high` |
| external_ai_called | false |
| mutates_business_state | false |

结论：

- AI Context 可读取运营 Metrics。
- AI Context 可读取运营 Dashboard 数据。
- AI 未调用真实外部 API。
- AI 未修改业务状态。

## 七、边界确认

| 边界项 | 结果 |
|---|---|
| 修改原始文件 | 未发生 |
| 修改业务数据 | 未发生 |
| 自动执行 | 未发生 |
| 发送通知 | 未发生 |
| 写生产业务状态 | 未发生 |

## 八、RC Issue 状态

### RC-001：飞书 API warning

| 项目 | 状态 |
|---|---|
| 当前状态 | 保留 |
| 是否阻塞 V1.0 | 否 |
| 本轮处理 | 未处理，继续记录 |

### RC-002：真实数据覆盖不足

| 项目 | 状态 |
|---|---|
| 当前状态 | CLOSED |
| 关闭依据 | 入住、房态、照护师三类运营数据已完成只读补充验证 |
| 验收结果 | PASS |

## 九、新增风险

### RC2-RISK-001：运营数据来源为截图

| 项目 | 内容 |
|---|---|
| 风险等级 | 中 |
| 说明 | 本轮入住、房态、照护师数据来自截图可见信息，不是结构化源文件 |
| 影响 | 不影响 RC-002 最小覆盖关闭；影响后续生产级自动导入稳定性 |
| 当前处理 | 记录风险，不修复 |

## 十、第二轮总表

| 验收项 | 结果 | 风险等级 |
|---|---|---|
| 入住数据 → Stay Domain | PASS | 低 |
| 入住数据 → Metrics | PASS | 低 |
| 入住数据 → Dashboard | PASS | 低 |
| 入住数据 → AI Context | PASS | 低 |
| 房态数据 → Room Domain | PASS | 低 |
| 房态数据 → Room Metrics | PASS | 低 |
| 房态数据 → Alert | PASS | 低 |
| 照护师数据 → Caregiver Domain | PASS | 低 |
| 照护师数据 → Resource Metrics | PASS | 低 |
| 原始文件保护 | PASS | 低 |
| 业务状态保护 | PASS | 低 |
| 数据源结构化程度 | PASS WITH RISK | 中 |

## 十一、最终判断

```text
RC Round 2 = PASS WITH SOURCE RISK
RC-002 = CLOSED
Blocking issue = 0
New risk = RC2-RISK-001
```

建议：

```text
进入 RC Issue 状态复核。
RC-001 保留不阻塞。
RC-002 已关闭。
后续生产上线前，应优先获取结构化入住/房态/照护师源文件。
```
