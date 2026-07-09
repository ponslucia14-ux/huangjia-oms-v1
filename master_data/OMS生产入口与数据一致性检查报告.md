# OMS 生产入口与数据一致性检查报告

Generated At: 2026-07-09 23:15 (Asia/Shanghai)

## 一、入口清单

| 入口 | 地址 | 前端版本 | 数据来源 | 是否生产入口 | 当前结论 |
|---|---|---|---|---|---|
| GitHub Pages 静态入口 | `https://ponslucia14-ux.github.io/huangjia-oms-v1/` | `main=6717275`; `gh-pages=75cda9a`; `app.js?v=p05-owner-workbench-v3-20260709-55ddc9e` | 前端配置指向 `http://127.0.0.1:8787/api/oms/home` | 不是完整生产入口 | 只能证明静态页面可访问；真实数据依赖当前访问设备本机 API。 |
| 飞书工作台入口 | `feishu_webapp.json.web_url=https://ponslucia14-ux.github.io/huangjia-oms-v1/`; `app_id=cli_aaac7e6da2b95cfc` | 配置上应加载 GitHub Pages 静态版本；客户端实际版本未取得实机证据 | 当前 `oms-config.js` 仍指向 `127.0.0.1:8787` 本机 API | 目标生产入口，但未完成一致性证明 | 飞书容器入口与 GitHub Pages 使用同一静态 URL，但 API 仍为本机地址；移动端/非本机环境无法等价访问真实数据。 |
| 本地浏览器入口 | `http://127.0.0.1:8787/` | 由本机 `oms_app` 文件直接服务；当前 main `6717275` | `D:\OMS_V1\OMS_TRUTH_SOURCE` + `D:\OMS_V1\live_runtime` | 临时老板入口 | 可用，但属于 Local Owner Access / 本机恢复入口，不是组织生产入口。 |
| 本机 API 入口 | `http://127.0.0.1:8787/api/oms/home?user_id=a2c82cb4` | 后端 `oms_v1.feishu_auth_server` | `OMS_TRUTH_SOURCE`，并混入 `live_runtime` 事件/执行链 | 数据服务入口，不是用户入口 | 返回 `status=ready`，但数据覆盖不完整。 |
| 旧 Cloudflare / Tunnel 入口 | 历史文档中出现 `trycloudflare.com` | 当前配置未使用 | 不可确认 | 否 | 已不应作为生产入口。 |
| 直接文件入口 | `D:\OMS_V1\oms_app\index.html` | 本地静态文件 | 无稳定 API 上下文 | 否 | 仅开发/排查用。 |

## 二、数据来源检查

| 数据域 | 当前来源 | 是否真实业务数据 | 是否 `OMS_TRUTH_SOURCE` | 是否测试/Mock | 是否历史快照/迁移 | 当前结论 |
|---|---|---:|---:|---:|---:|---|
| 销售 | `OMS_TRUTH_SOURCE/sales.json` | 部分是 | 是 | 未发现 Mock | 是，`migration_source=legacy_runtime` | 有销售数据，但来源证据不完整，不是完整生产链路。 |
| 财务 | `OMS_TRUTH_SOURCE/finance.json` | 部分是 | 是 | 未发现 Mock | 是，`migration_source=legacy_runtime` | 有财务数据和事件，但金额口径需复核。 |
| 入住 / Stay | `OMS_TRUTH_SOURCE/room.json` + event flow | 否，实体为空 | 文件存在 | 未发现 Mock | 事件链路存在 | `resident_data=0`，不能证明真实入住数据进入页面。 |
| 房态 / Room | `OMS_TRUTH_SOURCE/room.json` + event flow | 否，实体为空 | 文件存在 | 未发现 Mock | 事件链路存在 | `room_entities=0`，当前房态页不具备真实房态验收条件。 |
| 照护师 / Caregiver | `hr_execution_flow` | 仅执行链路 | 部分来自 runtime/event | 未发现 Mock | 是 | 可见的是人效执行链，不是照护师资源主数据。 |
| 业务事件 | `OMS_TRUTH_SOURCE/events.jsonl` | 部分是 | 是 | 未发现 Mock | 是 | 9749 条事件可用，但不能替代 Domain 实体。 |

### 关键统计

| 项目 | 数值 |
|---|---:|
| `sales.work_items` | 1327 |
| `sales.entities` | 1876 |
| `sales.source_evidence_present` | 500 |
| `sales.source_evidence_missing` | 2703 |
| `finance.work_items` | 3170 |
| `finance.entities` | 3170 |
| `finance.financial_events` | 3170 |
| `finance.source_evidence_present` | 1500 |
| `finance.source_evidence_missing` | 8010 |
| `finance_amount_count` | 1996 |
| `finance_amount_sum` | 74300575.98 |
| `room.work_items` | 0 |
| `room.entities` | 0 |
| `events.jsonl` | 9749 |

## 三、页面数据核对

### 1. 销售中心

| 检查项 | 当前页面/API 结果 | 结论 |
|---|---|---|
| 成交/签约记录 | `/api/oms/home` 返回 `sales_contract_data=1327`; `sales_schema.contracts=1327` | 有数据。 |
| 金额 | 当前 `sales_schema` 未给出明确成交金额字段；销售记录多为客户/套餐/日期 | 金额口径不足。 |
| 来源 | `OMS_TRUTH_SOURCE/sales.json`; `migration_source=legacy_runtime` | 不是完整生产源证明。 |
| 风险 | 证据链只有部分记录完整，`source_evidence_missing` 高 | 中风险。 |

### 2. 财务中心

| 检查项 | 当前页面/API 结果 | 结论 |
|---|---|---|
| 收款 | `finance_schema.collected=73490.0` | 有口径，但需与日报/银行流水逐项核对。 |
| 待收 | `finance_schema.receivable=3170` | 有口径，但看起来像条数/事件数，非明确金额。 |
| 待付 | 页面当前未明确输出待付金额字段；`finance_schema.expenses=2119287.0` | 待付口径不清。 |
| 总收入 | `finance_schema.income=61271879.98`; financial amount sum 脚本统计 `74300575.98` | 存在金额口径差异，需要校准。 |
| 来源 | `OMS_TRUTH_SOURCE/finance.json`; `migration_source=legacy_runtime` | 数据存在，但非最终生产会计口径。 |

### 3. 运营中心

| 检查项 | 当前页面/API 结果 | 结论 |
|---|---|---|
| 入住 | `resident_data=0`; `resident_flow_schema.resident_count=0` | 不通过。 |
| 房态 | `room_status_data=0`; `room_status_records=0`; `room.entities=0` | 不通过。 |
| 照护师 | `hr_schema.on_duty_staff=5`; `hr_execution_flow=9749` | 有人效执行链，但不是照护师资源实体。 |
| 页面显示 | 运营中心可显示 12 条记录，但来源主要是 `business_event_flow/hr_execution_flow` | 显示不等于真实房态/入住落地。 |

## 四、唯一生产入口判断

V1.0 当前不能确认唯一生产入口。

当前实际存在三种入口心智：

1. GitHub Pages：可打开静态 UI，但不是完整生产入口，因为 API 指向本机 `127.0.0.1`。
2. 飞书入口：目标应为唯一生产入口，但当前未取得客户端实机一致性证据，且使用同一静态 URL 时仍会继承本机 API 配置。
3. 本地入口：老板当前可用入口，但属于 Local Owner Access 恢复入口，不应作为组织生产入口。

建议 V1.0 唯一老板生产入口必须最终锁定为：

```text
飞书客户端工作台 OMS
→ 同一套前端版本
→ 同一生产 API 地址
→ 同一 OMS_TRUTH_SOURCE / production data adapter
```

当前不满足。

## 五、问题列表

| 编号 | 问题 | 证据 | 风险等级 | 是否阻塞 P0.6 |
|---|---|---|---|---|
| P0.6-001 | GitHub Pages 与飞书入口未证明一致 | 飞书入口只在 `feishu_webapp.json` 中声明，未取得客户端加载版本和数据结果 | 高 | 是 |
| P0.6-002 | 静态前端配置指向本机 API | `oms-config.js`: `OMS_HOME_ENDPOINT=http://127.0.0.1:8787/api/oms/home` | 高 | 是 |
| P0.6-003 | GitHub Pages 不是完整生产入口 | 线上静态页面依赖访问设备本机 API；非本机/移动端无法等价运行 | 高 | 是 |
| P0.6-004 | 运营中心数据不是真实 Stay/Room/Caregiver 实体 | `resident_data=0`; `room_status_data=0`; `room.entities=0` | 高 | 是 |
| P0.6-005 | 财务金额口径不一致 | `finance_schema.income=61271879.98`; financial amount sum 脚本统计 `74300575.98` | 中 | 是 |
| P0.6-006 | 销售/财务证据链不完整 | sales missing evidence 2703；finance missing evidence 8010 | 中 | 是 |
| P0.6-007 | 页面存在“可见但语义不准”风险 | 运营中心用事件/人效记录替代房态/入住实体 | 高 | 是 |
| P0.6-008 | 当前老板入口混用 Local Owner Access 与飞书策略 | `feishu_webapp.json` 禁止 direct URL；`oms-config.js` 开启 local owner access | 中 | 是 |

## 六、当前结论

```text
GitHub Pages 静态页面 = 可访问
本地 API = 可返回 ready
飞书生产入口一致性 = 未证明
页面数据真实性 = 部分成立
运营中心真实房态/入住/照护师数据 = 不成立
唯一生产入口 = 未锁定
P0.6 状态 = FAIL / 需先统一入口与数据口径
```

本报告只定位问题，未进行修复。
