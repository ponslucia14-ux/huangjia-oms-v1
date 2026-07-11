# OMS 服务器连接恢复报告

生成时间：2026-07-10

## 一、目标

恢复家里电脑到 OMS 生产服务器的连接，并确认昨天中断位置。

目标服务器：

```text
公网 IP: 47.243.38.102
系统: Ubuntu
用户: ecs-user
目标目录: /opt/huangjia-oms
```

本阶段只恢复服务器连接，不重新部署，不处理 systemd / Nginx / HTTPS。

## 二、SSH 密钥恢复

本轮提供生产密钥：

```text
C:\Users\75859\Downloads\OMS-PROD-02.pem
```

本机已复制并收紧权限到：

```text
C:\Users\75859\.ssh\OMS-PROD-02.pem
```

密钥指纹：

```text
2048 SHA256:XcAaAR5KT5Xvqn1XDqkUPMbfxUXuBGaSztYSB2op0Kg
```

## 三、SSH 恢复结果

执行：

```text
ssh -i C:\Users\75859\.ssh\OMS-PROD-02.pem ecs-user@47.243.38.102
```

结果：

```text
PASS
```

服务器返回：

```text
hostname: iZj6c1akepms0klcxs8vunZ
user: ecs-user
home: /home/ecs-user
```

结论：

```text
家里电脑已恢复 SSH 到生产服务器。
```

## 四、OMS 目录状态

目标目录：

```text
/opt/huangjia-oms
```

结果：

```text
PASS
```

目录结构：

```text
/opt/huangjia-oms/current
/opt/huangjia-oms/releases
/opt/huangjia-oms/venv
```

当前 release：

```text
/opt/huangjia-oms/current
→ /opt/huangjia-oms/releases/74cb488884770228cef4635e1ec5e9f2c085101a
```

Python：

```text
Python 3.12.3
```

## 五、Truth Source 状态

Truth Source 路径：

```text
/opt/huangjia-oms/current/OMS_TRUTH_SOURCE
→ /var/lib/huangjia-oms/truth_source
```

结果：

```text
PASS
```

当前文件：

| 文件 | 状态 | 大小 |
|---|---|---:|
| `manifest.json` | exists | 1050 |
| `sales.json` | exists | 323292 |
| `finance.json` | exists | 3184416 |
| `room.json` | exists | 65384 |
| `events.jsonl` | exists | 3747442 |
| `stay.json` | exists | 252628 |
| `contract.json` | exists | 212572 |
| `customer.json` | exists | 160618 |

核心计数：

| Domain | 计数 |
|---|---:|
| Sales entities | 224 |
| Finance entities | 1278 |
| Financial events | 1278 |
| Settlement records | 11 |
| Room entities | 0 |
| Events jsonl lines | 1278 |

更新时间：

```text
2026-07-10T17:04:47+08:00
```

## 六、当前服务器进程状态

监听端口：

```text
22 only
```

未发现监听：

```text
80
443
8787
```

进程检查：

```text
未发现 oms_v1.feishu_auth_server
未发现 OMS API python 进程
未发现 nginx 进程
```

systemd 候选：

```text
未发现 oms / huangjia / nginx 相关已运行 service
```

## 七、当前 API 状态

服务器本机探测：

| 地址 | 状态 |
|---|---|
| `http://127.0.0.1:8787/api/oms/home` | FAIL，connection refused |
| `http://127.0.0.1/api/oms/home` | FAIL，connection refused |

公网探测：

| 地址 | 状态 |
|---|---|
| `http://47.243.38.102/api/oms/home` | 502 Bad Gateway |
| `https://47.243.38.102/api/oms/home` | TLS / connection error |
| `http://47.243.38.102:8787/api/oms/home` | timeout |

结论：

```text
生产服务器代码和 Truth Source 仍在。
当前 OMS API 没有运行。
当前不是数据丢失问题，而是服务进程未启动 / 反向代理未接通。
```

## 八、当前真实状态

```text
SSH: PASS
服务器: PASS
/opt/huangjia-oms: PASS
release: PASS
Truth Source: PASS
OMS API: DOWN
Nginx: DOWN / not running
HTTPS API: DOWN
```

## 九、下一步位置

昨天中断位置已恢复到：

```text
生产服务器已连接
代码与 Truth Source 已确认存在
下一步应从“启动 OMS API 服务”继续
```

不要重新开始部署。

下一步只需要继续：

```text
启动当前 release 的 OMS API
验证 /api/oms/home status=ready
再进入 systemd / Nginx / HTTPS
```

## 十、Truth Source 补充检查与 API 启动结果（2026-07-10 19:40）

按本轮要求，未配置 systemd，未配置 Nginx，未配置 HTTPS。

### 1. room.json 检查结果

服务器 Truth Source：

```text
/var/lib/huangjia-oms/truth_source/room.json
```

原始状态：

```text
entities = 0
room_records = 42
caregiver_records = 0
```

判断：

```text
room.json 不是无房间数据。
实际房间资源存在于 room_records。
但通用 entities 字段为空，会导致部分 Domain / Manifest 口径误判 room = 0。
```

已执行数据级修正：

```text
room.entities ← room.room_records
```

修正后：

```text
room_entities = 42
room_records = 42
```

备份：

```text
/var/lib/huangjia-oms/truth_source/_backup_before_room_entity_fix_20260710_194028
```

### 2. Stay 检查结果

服务器 Truth Source：

```text
/var/lib/huangjia-oms/truth_source/stay.json
```

原始状态：

```text
entities = 0
stay_records = 172
```

已执行数据级修正：

```text
stay.entities ← stay.stay_records
```

修正后：

```text
stay_entities = 172
stay_records = 172
```

### 3. Caregiver 检查结果

当前服务器 Truth Source：

```text
caregiver.json = missing
room.caregiver_records = 0
stay.caregiver_records = 0
```

判断：

```text
照护师事实源当前未落成结构化文件。
未伪造 caregiver 数据。
```

### 4. Manifest 修正结果

当前 manifest counts：

```text
room_entities = 42
room_records = 42
stay_entities = 172
stay_records = 172
caregiver_records = 0
sales_entities = 224
finance_entities = 1278
financial_events = 1278
settlement_records = 11
business_events = 1278
```

### 5. API 启动结果

使用当前 release 启动：

```text
/opt/huangjia-oms/current
→ /opt/huangjia-oms/releases/74cb488884770228cef4635e1ec5e9f2c085101a
```

启动方式：

```text
OMS_TRUTH_SOURCE_ROOT=/var/lib/huangjia-oms/truth_source
OMS_LIVE_ROOT=/var/lib/huangjia-oms/live_runtime
/opt/huangjia-oms/venv/bin/python -m oms_v1.feishu_auth_server --host 127.0.0.1 --port 8787
```

当前进程：

```text
pid = 2845
listen = 127.0.0.1:8787
```

### 6. curl 验证

请求：

```text
http://127.0.0.1:8787/api/oms/home?user_id=a2c82cb4
```

结果：

```text
HTTP 200
status = ready
home_type = boss_master_control_interface
current_user.user_id = a2c82cb4
runtime_source.truth_root = /var/lib/huangjia-oms/truth_source
```

返回核心计数：

```text
room_entities = 42
sales_entities = 224
finance_entities = 1278
financial_events = 1278
business_events = 1278
```

### 7. 仍需记录的事实

当前 `/api/oms/home` 的 `source_evidence_available_data` 中：

```text
resident_data = 0
room_status_data = 0
```

原因：

```text
当前 Home UI 读取旧 work_items 口径生成 resident_data / room_status_data。
Truth Source 中 Room / Stay 实体已经存在，但 Home UI 尚未把 room_records / stay_records 映射到这两个展示列表。
```

本次不修 UI，不改数据链，只记录风险。

### 8. 当前状态

```text
SSH = PASS
Truth Source = PASS with caveat
Room entities = PASS, 42
Stay entities = PASS, 172
Caregiver source = MISSING, not fabricated
OMS API = RUNNING
/api/oms/home?user_id=a2c82cb4 = READY
systemd = NOT CONFIGURED
Nginx = NOT CONFIGURED
HTTPS = NOT CONFIGURED
```
