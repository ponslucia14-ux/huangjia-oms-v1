# OMS 登录入口恢复报告

生成时间：2026-07-09

## 一、当前问题

| 项目 | 真实状态 | 结果 |
| --- | --- | --- |
| Feishu 客户端 | 已运行，安装路径为 `D:\Feishu\...` | 正常 |
| OMS API 服务 | 排查开始时未监听 `8787 / 8080 / 8000 / 5173 / 3000` 等常用端口 | 未运行 |
| 本机 Python | 系统 PATH 中 `python` 不可用 | 启动阻断 |
| Codex bundled Python | `C:\Users\75859\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` 可用 | 可启动 |
| 本机 OMS API | 已用 bundled Python 临时拉起，监听 `http://127.0.0.1:8787`，PID `2908` | 可访问 |
| 当前前端 API 配置 | 指向 `https://statewide-separation-assessing-tab.trycloudflare.com/api/...` | 远端入口不可达 |
| Cloudflare tunnel | 未发现 `cloudflared` 运行进程 | 未运行 |
| 远端 `/api/oms/home` | 请求失败：`Failed to fetch / 基础连接已经关闭` | 不可用 |
| 本机 `/api/oms/home` 带石磊 user_id | POST `user_id=a2c82cb4` 返回 `200 / oms.home / ready` | 可用 |
| 本机 `/api/oms/home` 不带 user_id | 返回 `401 / identity_binding_required` | 身份边界生效 |

## 二、根因

当前不是 OMS 核心业务能力损坏。

真实阻断点是登录入口运行链断开：

1. OMS API 服务未随系统自动启动。
2. 系统 PATH 中没有可用 `python`，导致直接启动 `python -m oms_v1.feishu_auth_server` 失败。
3. 前端仍指向一个当前不可达的 Cloudflare tunnel 地址。
4. 飞书认证失败后，前端认证状态进入 `BLOCKED`，不会继续稳定进入 `/api/oms/home`。
5. 后端 `/api/oms/home` 本身可用，但要求必须提供已绑定的真实 `user_id`。

## 三、Feishu 认证链路影响

| 链路 | 状态 | 影响 |
| --- | --- | --- |
| Feishu Native `requestAccess` | 前端依赖飞书 H5 容器触发 | 失败会阻断 UI |
| `/api/feishu/identity` | 当前前端配置指向远端 tunnel | tunnel 不可达时 fetch 失败 |
| Auth State | 失败后进入 `BLOCKED` | 整个 OMS UI 入口被挡住 |
| `/api/oms/home` | 本机服务启动后可返回真实 home payload | 不依赖 Feishu code，但必须有真实 user_id |

判断：飞书认证失败会导致当前 OMS 前端不可进入；但 OMS home 数据接口没有损坏。

## 四、临时 V1.0 登录入口方案

目标：先让石磊进入 OMS，不破坏 EMP 权限、Audit、Master Data。

### 方案

建立受控的 V1.0 临时入口：

```text
石磊临时入口
→ 固定 user_id = a2c82cb4
→ Master Data / identity_enrichment 校验
→ 生成 login.recovery Audit
→ 调用本机 /api/oms/home
→ 返回石磊工作入口
```

### 必须遵守

| 要求 | 处理方式 |
| --- | --- |
| 不破坏 EMP 权限 | 入口只接受已在 Master Data / identity_enrichment 中绑定的 `user_id` |
| 不破坏 Audit | 每次临时登录必须写 `login.recovery.request` 与 `login.recovery.success / failed` |
| 不破坏 Master Data | 不新增假用户，不改人员表，不使用 fallback 身份 |
| 不绕过身份边界 | 未绑定 user_id 仍返回 `identity_binding_required` |
| 不影响 Feishu 正式链路 | 临时入口只作为 V1.0 恢复入口，Feishu Auth 修复后关闭 |

### 当前可用验证

```text
本机 API:
http://127.0.0.1:8787/api/oms/home

石磊 user_id:
a2c82cb4

验证结果:
HTTP 200
id = oms.home
status = ready
source = OMS_TRUTH_SOURCE
entry = master_control_dashboard
workspace = boss
```

## 五、是否影响 V1.0

| 项目 | 判断 |
| --- | --- |
| V1.0 核心能力 | 不受影响 |
| V1.0 Tag | 不受影响 |
| 生产访问能力 | 受影响 |
| 石磊进入 OMS | 当前被入口链路阻断 |
| 风险等级 | P0 |

结论：

```text
OMS V1.0 系统能力正常。
当前故障属于登录入口 / 运行入口故障。
若不恢复入口，石磊无法正常进入 OMS。
建议先启用受控临时 V1.0 登录入口，再恢复 Feishu 正式认证链路。
```
