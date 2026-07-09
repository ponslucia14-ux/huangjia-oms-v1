# OMS 登录入口修复方案

生成时间：2026-07-09

## 一、修复目标

P0 目标：

```text
石磊可以稳定进入 OMS。
```

本次修复只处理登录入口恢复，不修改业务 Engine，不修改业务数据，不扩大权限。

## 二、已确认问题

| 问题 | 现象 | 影响 |
| --- | --- | --- |
| Python 环境启动问题 | 系统 PATH 中 `python` 不可用 | OMS API 无法直接启动 |
| 前端入口不可达 | `oms-config.js` 指向失效 Cloudflare tunnel | `/api/oms/home` fetch 失败 |
| Feishu Auth 阻断入口 | Feishu Native Auth 失败后进入 `BLOCKED` | 老板无法进入 OMS |

## 三、修复内容

### 1. OMS 本地启动标准化

新增：

```text
start_oms.bat
```

启动方式：

```text
双击 start_oms.bat
```

脚本固定使用 bundled Python：

```text
%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

不依赖系统 PATH 中的 `python`。

启动后：

```text
OMS API:
http://127.0.0.1:8787/
```

### 2. 入口恢复

`oms_app/oms-config.js` 已切换为本机 API：

```text
OMS_AUTH_ENDPOINT    = http://127.0.0.1:8787/api/feishu/identity
OMS_HOME_ENDPOINT    = http://127.0.0.1:8787/api/oms/home
OMS_EXECUTE_ENDPOINT = http://127.0.0.1:8787/api/oms/execute
```

不再依赖当前不可用的 Cloudflare tunnel。

### 3. Local Owner Access

新增受控恢复入口：

```text
POST /api/oms/local-owner-access
```

用途：

```text
Feishu Auth 不可用时，允许石磊本机进入 OMS。
```

限制：

| 限制项 | 规则 |
| --- | --- |
| 访问来源 | 只接受 `127.0.0.1 / localhost` 本机请求 |
| 用户身份 | 固定校验 `user_id = a2c82cb4` |
| 权限 | 仍通过 Master Data / identity_enrichment 解析工作台 |
| EMP | 使用 `EMP001` 记录 |
| Audit | 写入 `login.recovery.request` 与 `login.recovery.success / failed` |
| fallback 用户 | 禁止 |
| 未绑定用户 | 继续返回 `identity_binding_required` |

### 4. 前端降级策略

前端启动顺序调整为：

```text
Feishu Auth 正常
→ 使用 Feishu user_id 进入 OMS

Feishu Auth 失败 / 非 Feishu 容器
→ 尝试 Local Owner Access
→ 成功后进入 OMS
→ 失败则 BLOCKED
```

Local Owner Access 只用于 V1.0 登录恢复，不替代正式飞书身份链路。

### 5. 本地静态入口

`feishu_auth_server.py` 现在支持本地打开：

```text
http://127.0.0.1:8787/
```

可直接加载：

- `index.html`
- `app.js`
- `styles.css`
- `oms-config.js`
- `contract.json`

## 四、Audit 保留方式

Audit 写入位置：

```text
live_runtime/audit_center/audit_events.jsonl
```

动作：

```text
login.recovery.request
login.recovery.success
login.recovery.failed
```

示例链路：

```text
Local Owner Access
→ EMP001
→ 石磊
→ Master Data identity check
→ Audit
→ /api/oms/home
```

## 五、验收方式

### 1. 重启电脑后启动

执行：

```text
start_oms.bat
```

预期：

```text
打开 http://127.0.0.1:8787/
```

### 2. `/api/oms/home`

请求：

```text
POST http://127.0.0.1:8787/api/oms/home
body: {"user_id":"a2c82cb4"}
```

预期：

```text
status = ready
source = OMS_TRUTH_SOURCE
entry = master_control_dashboard
workspace = boss
```

### 3. Local Owner Access

请求：

```text
POST http://127.0.0.1:8787/api/oms/local-owner-access
body: {"reason":"local_owner_access_recovery"}
```

预期：

```text
status = ready
payload.user_id = a2c82cb4
payload.workspace_key = boss
payload.source = local_owner_access
payload.audit_id 存在
```

### 4. Audit

确认：

```text
live_runtime/audit_center/audit_events.jsonl
```

包含：

```text
login.recovery.request
login.recovery.success
```

## 六、是否影响 V1.0

| 项目 | 判断 |
| --- | --- |
| V1.0 Tag | 不影响 |
| OMS 核心业务能力 | 不影响 |
| EMP 权限体系 | 保留 |
| Master Data | 保留 |
| Audit | 保留 |
| Feishu 正式链路 | 保留，后续可恢复 |
| 老板进入 OMS | 已提供本机恢复入口 |

结论：

```text
P0 登录入口已从“Feishu Auth 单点阻断”恢复为：

Feishu Auth 优先
+ Local Owner Access 兜底
+ 本机 bundled Python 一键启动

石磊可通过本机入口稳定进入 OMS。
```
