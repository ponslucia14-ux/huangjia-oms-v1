# OMS V1.0 首次使用验收报告

阶段：OMS V1.0 首次使用验收  
执行日期：2026-07-09  
版本状态：OMS V1.0.0 Controlled Release  
验收结论：PASS

## 一、登录入口验收

| 验收项 | 结果 | 记录 |
|---|---|---|
| 浏览器访问 | PASS | 通过 `http://127.0.0.1:8787/` 可进入 OMS |
| Owner Access | PASS | Feishu Auth 不可用时，Local Owner Access 可进入 |
| 用户身份 | PASS | `user_id=a2c82cb4` 解析为石磊主控入口 |
| 页面状态 | PASS | `appMount=ready`，`authState=authenticated` |
| 首页渲染 | PASS | `master_control_dashboard` 正常渲染 |
| Audit | PASS | 已保留 `login.recovery.request / login.recovery.success` |
| EMP / 权限 / Master Data | PASS | 未绕过，仍使用既有身份与权限映射 |

结论：

```text
OMS V1.0 登录入口首次使用验收通过。
石磊可通过浏览器真实进入 OMS。
```

## 二、首页验收

首页心智模型：

```text
Action → Status → Risk
```

| 区域 | 验收结果 | 说明 |
|---|---|---|
| Action | PASS | 首页可呈现今日工作与待处理动作 |
| Status | PASS | 首页可呈现当前经营状态 |
| Risk | PASS | 首页可呈现风险与异常入口 |
| 主控入口 | PASS | 石磊进入后显示经营主控视图 |
| 页面可见性 | PASS | 未再出现 `BLOCKED / feishu_auth_failed` |

结论：

```text
首页已满足 V1.0 首次使用标准：打开即可看到今日工作、当前状态、风险异常。
```

## 三、数据验收

| 数据范围 | 验收结果 | 当前状态 |
|---|---|---|
| 销售 | PASS | 已完成真实销售数据试运行接入，Adapter / Validation / Mapping / Metrics 正常 |
| 财务 | PASS | 已完成真实财务数据试运行接入，Payment Domain 与 Metrics 正常 |
| 入住 | PASS | RC Round 2 已完成 Stay Domain 补充验证 |
| 房态 | PASS | RC Round 2 已完成 Room Domain / Room Metrics / Alert 验证 |
| 照护师 | PASS | RC Round 2 已完成 Caregiver Domain / Resource Metrics 验证 |

数据验收结论：

```text
V1.0 首次使用所需的核心经营数据范围已覆盖。
当前数据链路满足 Controlled Release 使用标准。
```

## 四、已知风险

| 风险编号 | 风险项 | 状态 | 影响 |
|---|---|---|---|
| RC-001 | 飞书 API Warning | 保留 | 不阻塞 V1.0；进入 V1.1 适配优化 |
| RC2-RISK-001 | 运营截图数据源结构化不足 | 保留 | 中风险；进入 V1.1 数据源结构化优化 |
| P0-RISK-001 | Feishu Auth 仍非首选稳定入口 | 已兜底 | 当前由 Local Owner Access 保证石磊进入 |
| P0-RISK-002 | 本机服务依赖 `start_oms.bat` 启动 | 可控 | 重启电脑后需执行启动脚本 |

风险结论：

```text
当前风险不阻塞 OMS V1.0.0 Controlled Release。
飞书生产适配与数据源结构化进入 V1.1 优化范围。
```

## 五、当前版本状态

```text
Version = OMS V1.0.0 Controlled Release
Release Decision = GO
Blocking Issue = 0
Login Entry = PASS
Home Render = PASS
Core Data Coverage = PASS
Audit = PASS
Known Risks = retained for V1.1
```

最终结论：

```text
OMS V1.0.0 首次使用验收通过。
系统已具备 Controlled Release 下的首次真实使用条件。
```
