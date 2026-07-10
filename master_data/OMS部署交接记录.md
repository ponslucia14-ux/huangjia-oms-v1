# OMS 部署交接记录

Version: 2026-07-10
Status: Handoff
Owner: 石磊
Executor: 张照南

---

# 一、今天完成内容

## GitHub / 本地 OMS

1. 完成 OMS 生产 API 部署方案梳理。
2. 完成 4 份 Excel 生产事实源消化与导入报告：
   - 2026年销售明细表（经验为王7.10）
   - 2026年财务报表（7月）
   - 凰家房态表
   - 凰家签约客户一览表
3. 完成 Truth Source 拆分口径：
   - sales.json
   - finance.json
   - room.json
   - stay.json
   - customer.json
   - contract.json
4. 完成运行时 11 人身份解析修复与岗位菜单规范。
5. 完成飞书前端覆盖矩阵、11 人工作台交付清单。
6. 完成生产 API 服务器第二步临时运行验证。

## 服务器

1. 已完成 SSH 登录与基础环境初始化。
2. 已创建 OMS 基础目录：
   - /opt/huangjia-oms
   - /var/lib/huangjia-oms
   - /var/lib/huangjia-oms/truth_source
   - /var/log/huangjia-oms
   - /etc/huangjia-oms
3. 已部署当前 main 归档：
   - commit: 74cb488884770228cef4635e1ec5e9f2c085101a
   - current: /opt/huangjia-oms/current
4. 已创建 Python venv：
   - /opt/huangjia-oms/venv
5. 已复制受控 Truth Source 到服务器：
   - /var/lib/huangjia-oms/truth_source
6. 已临时启动 OMS API：
   - 127.0.0.1:8787
7. 服务器本机 curl 已验证：
   - /api/oms/home?user_id=a2c82cb4
   - HTTP 200
   - status = ready

---

# 二、当前服务器状态

| 项目 | 当前值 |
|---|---|
| 公网 IP | 47.243.38.102 |
| 系统 | Ubuntu 24.04 |
| 登录用户 | ecs-user |
| 主机名 | iZj6c1akepms0klcxs8vunZ |
| 源码目录 | /opt/huangjia-oms/current |
| Release | /opt/huangjia-oms/releases/74cb488884770228cef4635e1ec5e9f2c085101a |
| Python | Python 3.12.3 |
| venv | /opt/huangjia-oms/venv |
| Truth Source | /var/lib/huangjia-oms/truth_source |
| Truth Source 文件数 | 14 |
| Truth Source 大小 | 7.7M |
| API 监听 | 127.0.0.1:8787 |
| API 启动方式 | nohup 临时运行 |
| API 日志 | /var/log/huangjia-oms/api.log |
| API PID | /var/log/huangjia-oms/api.pid |

## 已完成步骤

1. SSH 登录。
2. 基础包与目录初始化。
3. Python venv 创建。
4. 当前 main 源码部署。
5. 受控 Truth Source 复制。
6. OMS API 临时启动。
7. 服务器本机 API 验证通过。

## 未完成步骤

1. Nginx 未安装。
2. HTTPS 未配置。
3. 域名未配置。
4. systemd 服务未创建。
5. GitHub Pages / 飞书客户端尚未切换到公网生产 API。
6. 生产 API 尚未对公网开放。

## 当前运行状态

API 进程以 nohup 临时运行。

验证命令：

```bash
curl -sS -i 'http://127.0.0.1:8787/api/oms/home?user_id=a2c82cb4'
```

期望结果：

```text
HTTP/1.0 200 OK
status = ready
source = OMS_TRUTH_SOURCE
truth_root = /var/lib/huangjia-oms/truth_source
```

---

# 三、当前 GitHub 状态

当前分支：

```text
main
```

当前已部署到服务器的 commit：

```text
74cb488884770228cef4635e1ec5e9f2c085101a
```

本交接记录提交后，GitHub 应包含：

1. 可公开的 OMS 代码。
2. 可公开的测试。
3. 可公开的设计文档。
4. 可公开的导入报告。
5. 可公开的部署交接记录。

GitHub 不应包含：

1. OMS_TRUTH_SOURCE 真实生产数据目录。
2. 原始 Excel。
3. 生产 JSON 数据文件。
4. SSH 私钥。
5. 服务器密钥、Token、密码。
6. 服务器运行时配置。

---

# 四、当前工作区状态

## 应提交

以下属于可同步到 GitHub 的交付物：

1. OMS 代码修正。
2. OMS 测试修正。
3. Master Data 文档。
4. 生产 API 部署方案。
5. Excel 生产数据导入报告。
6. 运行时身份解析报告。
7. 11 人岗位菜单规范。
8. 本交接记录。

## 故意保留不提交

以下文件或目录不应提交：

1. OMS_TRUTH_SOURCE/
2. verification_screenshots/
3. 原始 Excel 文件。
4. C:\Users\75859\Downloads\OMS-PROD-01.pem
5. C:\Users\75859\Downloads\sekirai.pem
6. 服务器 /var/lib/huangjia-oms/live_runtime/realworld_mapping/OMS_RealWorld_Mapping.json

## 不能提交的原因

1. OMS_TRUTH_SOURCE 是真实生产数据，只允许保存在受控本地目录和服务器受控目录。
2. 原始 Excel 含真实客户、合同、财务、房态数据，不上传 GitHub。
3. 私钥是服务器登录凭证，禁止进入 GitHub。
4. verification_screenshots 可能包含真实业务页面截图，暂不上传。
5. 服务器运行时身份映射属于生产运行配置，不作为仓库源代码提交。

---

# 五、下一步第一条命令

家里电脑继续时，先不要安装 Nginx / HTTPS / systemd。

第一条命令是先验证服务器当前 API 状态：

```bash
ssh -i <家里电脑上的OMS-PROD-01.pem路径> ecs-user@47.243.38.102
```

进入服务器后执行：

```bash
curl -sS -i 'http://127.0.0.1:8787/api/oms/home?user_id=a2c82cb4'
```

如果返回 HTTP 200 且 status=ready，再继续下一步部署决策。

---

# 六、停止点

今天停止在：

```text
OMS API 已完成临时运行验证；下一步尚未进入 Nginx / HTTPS / systemd / 公网接入。
```

说明：

石磊 口径中写的是“OMS API 部署第二步开始前”。实际执行状态是第二步已经完成临时验证，但尚未进入长期生产化步骤。为避免丢失现场，服务器当前临时 API 不回滚。

---

# 七、是否存在阻塞

## 无代码阻塞

当前 OMS API 能在服务器本机运行，并返回 ready。

## 需要注意

1. 服务器 API 当前只监听 127.0.0.1，飞书和浏览器还不能公网访问。
2. 当前 API 是 nohup 临时运行，不是系统服务；服务器重启后不会自动恢复。
3. 家里电脑若没有 SSH 私钥，无法直接登录服务器。私钥不得通过 GitHub 同步。
4. GitHub Pages / 飞书客户端尚未切换生产 API。
5. Nginx、HTTPS、systemd 必须等 石磊 回家后确认再继续。

---

# 八、多设备同步结论

GitHub 同步后，家里电脑可以通过以下方式接续：

1. git pull 最新 main。
2. 阅读本文件。
3. 使用本文件中的 SSH 与 curl 命令复核服务器。
4. 从 Nginx / HTTPS / systemd / 公网接入前继续。

真实生产数据不通过 GitHub 同步。服务器上的 Truth Source 已保存在：

```text
/var/lib/huangjia-oms/truth_source
```

本地真实数据仍保留在：

```text
OMS_TRUTH_SOURCE/
```

---

Last Update: 2026-07-10
