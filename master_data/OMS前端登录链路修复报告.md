# OMS 前端登录链路修复报告

生成时间：2026-07-09

## 一、当前问题

验收失败现象：

```text
飞书身份认证失败
feishu_auth_failed: Failed to fetch
状态：BLOCKED
```

后端 `/api/oms/home` 可用，但前端仍被 Feishu Auth 入口挡住，说明问题发生在浏览器启动链路，而不是 OMS Home 数据接口。

## 二、根因

| 检查项 | 发现 |
| --- | --- |
| 前端登录顺序 | `app.js` 启动时先执行 `bootstrapIdentity()` |
| Feishu Auth 失败行为 | 原链路会进入 `authFlowFailure(...)`，页面显示认证失败 |
| Local Owner Access | 后端接口存在，但前端失败链路未稳定落到该入口 |
| 前端 API 配置 | 曾指向不可达 Cloudflare tunnel |
| 缓存风险 | `index.html` 仍使用旧静态资源版本号，浏览器可能继续加载旧 `app.js / oms-config.js` |
| config 失败风险 | 如果 `oms-config.js` 未正确加载，`homeEndpoint` 曾为空 |

根因结论：

```text
Feishu Auth 失败后，前端没有稳定进入 Local Owner Access。
浏览器仍可能加载旧入口或旧配置，因此继续显示 BLOCKED。
```

## 三、修复内容

### 1. 前端登录链路修复

当前前端顺序已调整为：

```text
加载 contract.json
↓
bootstrapIdentity()
↓
优先 Feishu Auth
↓
Feishu Auth 失败 / 非 Feishu 容器
↓
Local Owner Access
↓
石磊 user_id = a2c82cb4
↓
fetch /api/oms/home
↓
进入 master_control_dashboard
```

### 2. Local Owner Access 前端接入

新增前端入口：

```text
window.OMS_LOCAL_OWNER_ACCESS_ENDPOINT
window.OMS_LOCAL_OWNER_ACCESS_ENABLED
requestLocalOwnerAccess()
```

触发条件：

```text
not_feishu_runtime_context
feishu_auth_failed:*
```

### 3. 默认本机 API 兜底

即使 `oms-config.js` 未加载，前端也默认使用：

```text
/api/feishu/identity
/api/oms/home
/api/oms/execute
/api/oms/local-owner-access
```

避免 `homeEndpoint` 为空导致前端卡死。

### 4. 静态资源缓存刷新

已更新静态资源版本号：

```text
oms-config.js?v=p0-login-recovery-v1-20260709
app.js?v=p0-login-recovery-v1-20260709
contract.json?v=p0-login-recovery-v1-20260709
```

确保浏览器不继续使用旧登录链路。

### 5. 后端 Local Owner Access

受控入口：

```text
POST /api/oms/local-owner-access
```

限制：

- 只接受本机 `127.0.0.1 / localhost`
- 只允许 `user_id = a2c82cb4`
- 必须通过 `identity_enrichment_layer` / Master Data 映射
- 写入 Audit
- 不创建 fallback 用户

Audit：

```text
login.recovery.request
login.recovery.success
login.recovery.failed
```

## 四、实际浏览器验收

验收地址：

```text
http://127.0.0.1:8787/
```

浏览器实际状态：

| 项目 | 结果 |
| --- | --- |
| `oms-config.js` | loaded |
| `app.js` | loaded |
| `appMount` | ready |
| `authState` | authenticated |
| `finalRender` | committed |
| `finalMode` | master_control |
| 页面标题 | 我现在应该做什么？ |
| 当前用户 | 主理办（你） |
| 当前角色 | 总览 / 决策 / 授权 |
| BLOCKED 文案 | 不存在 |
| `feishu_auth_failed` 文案 | 不存在 |

验收结论：

```text
浏览器打开 OMS 后，已进入石磊经营主控工作台。
截图中的 BLOCKED 状态已消失。
```

## 五、接口验收

### `/api/oms/local-owner-access`

结果：

```text
HTTP 200
status = ready
user = a2c82cb4
workspace = boss
audit_id 存在
```

### `/api/oms/home`

结果：

```text
HTTP 200
status = ready
entry = master_control_dashboard
workspace = boss
```

## 六、测试结果

相关测试：

```text
tests.test_feishu_auth_server
tests.test_native_app_ui
tests.test_contract_layer

29 tests OK
```

## 七、结论

```text
P0 前端登录链路已修复。

Feishu Auth 失败时：
不再直接 BLOCKED。

石磊本机入口：
可以通过 Local Owner Access 进入 master_control_dashboard。

后端 Home：
仍保持真实 user_id 边界。

Audit：
正常写入。
```

## 八、注意

当前稳定入口是：

```text
start_oms.bat
→ http://127.0.0.1:8787/
```

不要继续使用旧 Cloudflare tunnel 或旧 GitHub Pages 缓存页面做 P0 验收。
