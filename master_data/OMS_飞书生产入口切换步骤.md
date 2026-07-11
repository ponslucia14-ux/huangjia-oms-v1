# OMS 飞书生产入口切换步骤

## 切换目标

- 前端入口：`https://ponslucia14-ux.github.io/huangjia-oms-v1/`
- 生产 API：`https://api.wonderfulseki.cn`
- 飞书应用：`cli_aaac7e6da2b95cfc`

## 切换步骤

1. 完成 API 域名 DNS、HTTPS 和公网接口验收。
2. 核对 `oms_app/oms-config.prod.js` 仅指向 `https://api.wonderfulseki.cn`。
3. 发布带新资源版本号的 `index.html`、`app.js`、`styles.css`、`contract.json` 和配置文件到 GitHub Pages。
4. 在飞书开放平台确认 H5 入口为 GitHub Pages 正式地址。
5. 确认 JS 安全域名、H5 可信域名和 OAuth 回调域名与实际入口完全一致。
6. 发布飞书应用生产版本，并确认可用范围包含 EMP001。
7. 退出并重新登录飞书客户端，刷新工作台入口。

## 实机验收

EMP001 从飞书工作台进入后逐项验证：

- 首页工作台正常显示。
- 销售中心 224 条。
- 合同 224 条。
- 财务中心总数 1278 条，分页加载。
- 房态 42 条。
- Stay 172 条。
- 数据追溯按需加载。
- 所有请求都指向 `https://api.wonderfulseki.cn`。

在石磊实机确认前，EMP001 状态保持 `WAITING_FOR_PRODUCTION_API_PUBLIC_ACCESS`。
