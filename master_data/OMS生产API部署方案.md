# OMS 生产 API 部署方案

Version: 1.0
Status: Draft for 石磊 Review
Owner: 石磊
Last Update: 2026-07-10

---

# 一、结论

当前阻塞点不是页面、菜单、Adapter 或 Truth Source。

真正阻塞点是：

生产 API 尚未部署。

`127.0.0.1` 只能用于本机开发调试，不能作为飞书生产 API。

飞书客户端、GitHub Pages、普通浏览器都无法稳定访问 石磊 电脑本机的 `127.0.0.1`。

因此，OMS 生产 API 必须部署为公网 HTTPS 服务。

推荐正式架构：

```text
飞书客户端
GitHub Pages
浏览器
        ↓
统一公网 HTTPS API
        ↓
OMS Production API
        ↓
Production Adapter
        ↓
OMS_TRUTH_SOURCE
        ↓
销售 / 财务 / 房态 / 入住 / 照护师
```

---

# 二、OMS 最终生产 API 部署在哪里

## 推荐方案

部署到一台 石磊 控制的云服务器。

生产 API 域名建议为：

```text
https://api.huangjia-oms.com
```

如果正式域名暂未购买或备案，第一阶段可先使用云服务器 HTTPS 临时域名，后续再绑定正式域名。

正式域名确认前，本文统一称为：

```text
OMS_PRODUCTION_API
```

## 为什么不使用 localhost

`localhost` / `127.0.0.1` 的含义是当前设备自己。

在 石磊 电脑上：

```text
127.0.0.1 = 石磊 电脑
```

在飞书客户端里：

```text
127.0.0.1 = 飞书客户端所在设备
```

在员工手机里：

```text
127.0.0.1 = 员工手机
```

所以飞书生产环境不能依赖 `127.0.0.1`。

## 为什么推荐云服务器

云服务器适合 OMS 当前阶段：

- 可部署 Python API。
- 可挂载受控生产数据目录。
- 可配置 HTTPS。
- 可限制访问来源。
- 可保留审计日志。
- 可做定时备份。
- 不需要把真实客户、财务、合同数据放进 GitHub。

## 备选方案

### 飞书云函数

可行，但不作为第一推荐。

原因：

- 真实 Excel / Truth Source 存储需要重新设计。
- 函数冷启动和运行限制会增加复杂度。
- 审计日志、备份、文件导入、权限隔离不如独立服务器直观。

### GitHub Pages 直读 JSON

禁止。

原因：

- GitHub Pages 是公开静态托管。
- 真实客户、合同、财务、房态数据不得上传 GitHub。
- 即使仓库私有，Pages 发布内容也不应作为生产敏感数据源。

### 石磊 电脑内网穿透

不推荐作为生产方案。

只能作为临时演示。

原因：

- 依赖 石磊 电脑开机。
- 网络不稳定。
- 安全边界弱。
- 不适合作为 11 名员工长期工作入口。

---

# 三、GitHub Pages 如何访问生产 API

GitHub Pages 只负责承载静态 H5 前端。

前端配置：

```javascript
window.OMS_PRODUCTION_ENDPOINT = "https://api.huangjia-oms.com/api/oms/production";
```

访问链路：

```text
https://ponslucia14-ux.github.io/huangjia-oms-v1/
        ↓
fetch("https://api.huangjia-oms.com/api/oms/production/sales")
        ↓
OMS Production API
        ↓
OMS_TRUTH_SOURCE
```

GitHub Pages 不保存真实生产数据。

GitHub Pages 只保存：

- HTML
- CSS
- JavaScript
- API Contract
- 前端配置模板

禁止保存：

- 真实 Excel
- 真实客户 JSON
- 真实财务 JSON
- 真实合同 JSON
- 真实房态 JSON
- token
- 密码

---

# 四、飞书客户端如何访问生产 API

飞书客户端打开的是同一个 H5 页面。

飞书工作台入口：

```text
飞书工作台
        ↓
OMS H5 页面
        ↓
https://ponslucia14-ux.github.io/huangjia-oms-v1/
        ↓
https://api.huangjia-oms.com/api/oms/production/*
```

飞书客户端不访问 `127.0.0.1`。

飞书客户端必须访问公网 HTTPS API。

生产 API 必须支持：

- HTTPS
- CORS 白名单
- 飞书身份校验
- EMP -> user_id -> role 权限解析
- 只返回当前角色允许看的数据

生产 API CORS 白名单至少包括：

```text
https://ponslucia14-ux.github.io
https://fepatfrt2v.feishu.cn
```

后续如绑定正式前端域名，再加入正式域名。

---

# 五、统一 API 如何保证所有模块读取同一套数据

生产 API 是唯一对外数据出口。

所有模块必须通过同一个 API 服务读取。

```text
OMS_TRUTH_SOURCE
        ↓
Production Adapter
        ↓
OMS Production API
        ↓
销售 / 财务 / 房态 / 入住 / 照护师 / Dashboard / Metrics / AI Context
```

## API 分组

建议第一阶段提供以下生产端点：

```text
GET /api/oms/production/sales
GET /api/oms/production/finance
GET /api/oms/production/rooms
GET /api/oms/production/stays
GET /api/oms/production/contracts
GET /api/oms/production/caregivers
GET /api/oms/production/dashboard
GET /api/oms/production/metrics
```

## 数据源边界

```text
sales.json
    销售事实

finance.json
    财务事实

room.json
    房间与房态事实

stay.json
    入住、待入住、出馆、入住计划

customer.json
    客户身份

contract.json
    合同、套餐、计划金额
```

照护师现阶段不建立独立事实源。

照护师相关数据先从：

- Stay
- Room
- Finance
- 工资决算数据

中读取。

未来数据积累稳定后，再建立独立 caregiver truth source。

---

# 六、生产部署后三端是否完全一致

生产部署完成后，三端必须一致。

```text
GitHub Pages
飞书客户端
普通浏览器
        ↓
同一个 HTTPS API
        ↓
同一套 Truth Source
```

三端差异只允许存在于：

- 屏幕尺寸
- 飞书容器能力
- 当前登录身份
- 权限范围

不允许存在：

- 不同数据源
- 不同 JSON
- 不同统计口径
- 本地页面一套数据
- 飞书页面另一套数据

验收标准：

同一账号、同一时间、同一筛选条件下：

```text
GitHub Pages 显示数据
=
飞书客户端显示数据
=
浏览器显示数据
=
OMS Production API 返回数据
=
OMS_TRUTH_SOURCE
```

---

# 七、部署阶段划分

## Phase 1：生产 API 最小部署

目标：

让飞书客户端不再依赖 `127.0.0.1`。

范围：

- 云服务器
- HTTPS
- OMS API 服务
- CORS
- 读取 OMS_TRUTH_SOURCE
- 销售 / 财务 / 房态 / 签约客户四个只读端点

不做：

- 新页面
- 新业务模块
- 自动写入
- 复杂审批

## Phase 2：身份与权限接入

目标：

飞书真实用户进入对应权限视图。

范围：

- 飞书 user_id 校验
- EMP 映射
- 角色权限
- 石磊老板视图
- 其他员工只读或可操作范围

## Phase 3：生产写入与审计

目标：

可执行业务动作。

范围：

- 表单提交
- 审批
- 到账确认
- 入住变更
- 审计日志
- Event Bus

---

# 八、生产 API 安全要求

生产 API 必须满足：

1. 全站 HTTPS。
2. 禁止匿名访问敏感数据。
3. 飞书身份必须校验。
4. 数据权限按 EMP / role 控制。
5. 所有写操作必须 Audit Log。
6. 真实数据不得进入 GitHub Pages。
7. 生产服务器不得暴露 `.git`。
8. API token、飞书密钥、数据库密码必须放在服务器环境变量或密钥管理中。
9. 定期备份 Truth Source。
10. 日志不得泄露手机号、完整客户隐私和财务敏感字段。

---

# 九、当前状态

已完成：

- 四份 Excel 已结构化进入本地 Truth Source。
- 前端页面已具备展示能力。
- 本地 API 可返回真实数据。
- GitHub Pages 可承载 H5 前端。

未完成：

- 生产 API 尚未部署。
- 飞书客户端仍不能稳定访问生产数据。
- `127.0.0.1` 仍只是本地调试入口。

当前阻塞：

```text
缺少公网 HTTPS OMS Production API
```

---

# 十、下一步建议

立即暂停页面继续开发。

下一步只做：

```text
Production API Deployment
```

建议最小实施顺序：

1. 购买或确认云服务器。
2. 确认正式 API 域名。
3. 部署 OMS API 服务。
4. 配置 HTTPS。
5. 配置 CORS 白名单。
6. 上传或同步受控 Truth Source 到服务器私有目录。
7. 配置生产环境变量。
8. 验证：
   - GitHub Pages -> API
   - 飞书客户端 -> API
   - 浏览器 -> API
9. 四份 Excel 页面重新做飞书实机验收。

在第 8 步通过前，不宣布 OMS 飞书端生产交付完成。
