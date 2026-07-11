# OMS 域名上线前准备报告

日期：2026-07-10

当前阶段：域名审核等待期 / Production API Public Access Preparation

目标域名：`wonderfulseki.cn`

拟用 API 子域名：`api.wonderfulseki.cn`

## 一、当前结论

域名仍处于注册局审核中，HTTPS 和飞书生产入口尚未切换。

等待期间已完成：

- EMP001 石磊工作台决策首屏打磨。
- 十一人 `identity → workspace → menu` 配置冻结。
- 开发环境与生产环境配置分离。
- Nginx HTTP/HTTPS 配置模板。
- HTTPS 上线步骤。
- 飞书生产入口切换步骤。

当前 EMP001 状态保持：

```text
WAITING_FOR_PRODUCTION_API_PUBLIC_ACCESS
```

## 二、EMP001 石磊工作台

### 首页首屏

首屏问题固定为：老板现在需要关注什么。

浏览器同源验收结果：

| 项目 | 实际结果 | 数据来源 |
|---|---:|---|
| 当前在住 | 8 位客户 | `OMS_TRUTH_SOURCE/stay.json` |
| 房态 | 42 间房 | `OMS_TRUTH_SOURCE/room.json` |
| 销售 | 224 条记录 | `OMS_TRUTH_SOURCE/sales.json` |
| 实收 | ¥15,272,118.6 | `OMS_TRUTH_SOURCE/finance.json` |
| 待收 | ¥4,000 | Finance Domain |
| 风险 | 暂无风险 | Home risk summary |

空任务、空业务流和空追溯区现在显示明确空状态，不再阻断整个页面。

### 中心页面

| 页面 | 浏览器验证 | 实际数据 |
|---|---|---:|
| 销售中心 | PASS | 销售 224、合同 224 |
| 财务中心 | PASS | 总数 1278，首批加载 500 |
| 运营中心 | PASS | 在住 8、房态 42、Stay 172 |
| 数据追溯 | PASS | 5 组来源，按需加载 |

照护师没有结构化生产事实源，页面明确显示“暂无结构化生产数据”，未生成替代数据。

## 三、十一人 Workspace 菜单冻结

菜单契约位置：`oms_app/contract.json → ui_render_contract.workspace_menu_profiles`

规则：服务端身份解析得到唯一 `workspace_key` 后，前端只挂载该 workspace 允许的菜单。

| Workspace | 身份 | 工作台 | 菜单 | 飞书身份状态 |
|---|---|---|---|---|
| `boss` | 石磊 | 主理办工作台 | 首页、销售、财务、运营、数据 | ready |
| `huanhuan` | 杨欢欢 | 销售工作台 | 首页、销售、数据 | ready / inferred |
| `june` | 刘芳羽 | 店总工作台 | 首页、销售、运营、数据 | ready |
| `liujie` | 刘晶 | 财务工作台 | 首页、财务、数据 | ready |
| `zhangjie` | 张敬东 | 财务总监工作台 | 首页、财务、数据 | pending user_id |
| `nana` | 尚丽娜 | 管家工作台 | 首页、运营、数据 | ready |
| `chenchangyi` | 陈晶辉 | 产护工作台 | 首页、运营、数据 | ready |
| `zhouchen` | 周志朋 | 料理工作台 | 首页、运营、数据 | pending user_id |
| `yaowei` | 石昊盺 | 行政采购工作台 | 首页、财务、运营、数据 | pending user_id |
| `songxue` | 宗惠 | 人事行政工作台 | 首页、运营、数据 | pending user_id |
| `yuchun` | 薛子渝 | 食材采购 + 销售工作台 | 首页、销售、运营、数据 | ready |

未绑定岗位没有生成 fallback user_id。菜单已冻结，身份完成绑定后自动生效。

## 四、开发与生产配置分离

| 文件 | 用途 | API |
|---|---|---|
| `oms-config.dev.js` | localhost / 127.0.0.1 | `http://127.0.0.1:8787` |
| `oms-config.prod.js` | GitHub Pages / 飞书 / 普通浏览器 | `https://api.wonderfulseki.cn` |
| `oms-config.js` | 根据 hostname 选择环境并校验 | 生产环境强制 HTTPS |

生产配置禁止：

- `127.0.0.1`
- `localhost`
- 临时 tunnel
- 本机 Truth Source 路径
- Local Owner Access

当前生产配置尚未发布，避免域名审核期间前端指向不可用 API。

## 五、域名上线材料

### Nginx

- `deploy/nginx/huangjia-oms-http-bootstrap.conf.template`
- `deploy/nginx/huangjia-oms-https.conf.template`

OMS API 继续由 systemd 管理并监听 `127.0.0.1:8787`。Nginx 对外监听 80/443，8787 不对公网开放。

### HTTPS

操作清单：`master_data/OMS_HTTPS上线步骤.md`

包含：

- DNS A 记录。
- ACME HTTP challenge。
- 正式证书签发。
- HTTP 自动跳转 HTTPS。
- 自动续期 dry-run。
- 公网 API 验收。

### 飞书

操作清单：`master_data/OMS_飞书生产入口切换步骤.md`

包含：

- GitHub Pages 静态资源发布。
- 生产 API 统一。
- 飞书 H5 入口及安全域名核对。
- 应用生产发布。
- EMP001 客户端实机验收。

## 六、域名审核通过后的执行顺序

```text
DNS: api.wonderfulseki.cn → 47.243.38.102
↓
HTTP 域名验证
↓
正式 HTTPS 证书
↓
公网 API 全量验证
↓
发布生产前端配置
↓
更新 GitHub Pages 资源版本
↓
飞书生产入口切换
↓
石磊实机验收
```

## 七、尚未完成

- 域名注册局审核通过。
- DNS 指向 `47.243.38.102`。
- 443 正式证书。
- GitHub Pages 生产配置发布。
- 飞书客户端最终实机验收。

在以上 Gate 完成前，不将 EMP001 标记为 PASS。

## 八、边界确认

- 未新增 Engine。
- 未新增 AI。
- 未修改业务规则。
- 未修改 Truth Source 事实。
- 未引入 Mock。
- 未 Commit。
