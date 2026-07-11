# OMS HTTPS 上线步骤

目标域名：`api.wonderfulseki.cn`

## 上线前提

1. `wonderfulseki.cn` 注册局审核通过。
2. DNS 新增 `A` 记录：`api` → `47.243.38.102`。
3. 公网 80、443 安全组放行；8787 不放行。
4. `huangjia-oms.service` 保持监听 `127.0.0.1:8787`。

## 执行顺序

1. 部署 `deploy/nginx/huangjia-oms-http-bootstrap.conf.template`。
2. 执行 `nginx -t`，重载 Nginx。
3. 验证 `http://api.wonderfulseki.cn/api/oms/home?user_id=a2c82cb4` 返回 200。
4. 安装 `certbot` 与 Nginx 插件。
5. 签发 `api.wonderfulseki.cn` 正式证书。
6. 部署 `deploy/nginx/huangjia-oms-https.conf.template`。
7. 再次执行 `nginx -t`，重载 Nginx。
8. 验证 HTTP 自动跳转 HTTPS，HTTPS 无证书警告。
9. 执行 `certbot renew --dry-run` 验证自动续期。

## 生产验收

- Home：200、`status=ready`、`workspace=boss`、约 9KB。
- 在住：8。
- 房态：42。
- 销售：224。
- 合同：224。
- 财务：1278。
- Stay：172。
- 证书域名、有效期、证书链均正确。

禁止使用自签名证书、IP 证书、临时 tunnel 或直接暴露 8787。
