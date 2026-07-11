# OMS Cutover Readiness Check报告

检查阶段：P0.18.1  
检查时间：2026-07-11（Asia/Shanghai）  
结论：`FAIL / CUTOVER BLOCKED`

## 一、结论摘要

| 检查域 | 结果 | 结论 |
| --- | --- | --- |
| 数据准备 | FAIL | V2未生成，初始化迁移及新口径验收未完成 |
| 身份权限 | PASS | 11/11飞书身份、EMP、role_code、workspace一致 |
| 生产环境 | PASS | HTTPS、API、飞书入口现场可用 |
| 业务准备 | FAIL | 责任人已定义，但四域首次签认和Cutover首操确认仍为PENDING |
| 回退准备 | FAIL | V1与release存在，但服务器未发现独立备份证据 |

```text
cutover_readiness = FAIL
cutover_date = NOT SET
blocking_gate_count = 3
```

## 二、数据准备

### 2.1 Snapshot状态

| 项目 | 实际状态 | 结果 |
| --- | --- | --- |
| 当前激活Snapshot | `TS-20260711-V1 / ACTIVE` | PASS（仅证明现有基线存在） |
| 候选Snapshot | `TS-20260711-V2 / NOT GENERATED` | FAIL |
| V2文件 | 本机及服务器均未发现 | FAIL |
| V1完整性引用 | 本机ACTIVE指针存在，hash已记录 | PASS |

### 2.2 数据质量

公网API当前仍返回V1数据健康状态`PASS / 96`，并展示：

- Resident：8
- Room：42
- Sales：224
- Financial Events：1278

该状态属于旧V1口径，不能代表P0.17后重新定义的初始化迁移策略已通过。根据最新评估：

- Sales Current：`CONDITIONAL`
- Finance Current：`NOT_INITIALIZED`
- Room Current：`NOT_INITIALIZED`
- Actual Stay Current：`NOT_INITIALIZED`

因此当前API中的V1 PASS不得作为Cutover Readiness PASS证据。

### 2.3 初始迁移

| Domain | 迁移策略 | 当前准备结果 |
| --- | --- | --- |
| Sales | Current条件准入或Historical | 业务签认与对账PENDING |
| Finance | Historical迁移，OMS生成Current | Historical迁移快照未冻结 |
| Room | Master Data/Historical迁移，OMS生成Current | 初始化快照未冻结 |
| Actual Stay | Contract Plan/Historical迁移，OMS生成Current | Plan/Historical签认未冻结 |

数据准备结论：`FAIL`。

## 三、身份权限

### 3.1 身份一致性

《OMS十一人飞书身份最终一致性报告》显示：

- 11/11具有唯一飞书user_id
- 11/11具有唯一EMP
- 11/11正式姓名一致
- 11/11具有唯一role_code
- 11/11具有唯一workspace
- `IDENTITY_CONFLICT = 0`

### 3.2 权限链

权限链已定义为：

```text
Feishu user_id
-> EMP
-> role_code
-> workspace
-> responsibility_scope
```

不存在虚拟用户、fallback身份或岗位代称作为正式身份的准入规则。

身份权限结论：`PASS`。

## 四、生产环境

### 4.1 HTTPS与DNS实测

| 项目 | 实测结果 | 状态 |
| --- | --- | --- |
| DNS | `api.wonderfulseki.cn -> 47.243.38.102` | PASS |
| HTTPS | 正式证书有效，截止2026-10-09 | PASS |
| Nginx | `active`，配置检查成功 | PASS |
| OMS systemd | `enabled + active` | PASS |
| 运行用户 | `ecs-user` | PASS |
| API进程 | `huangjia-oms.service`, PID 15719 | PASS |

### 4.2 API实测

```text
GET https://api.wonderfulseki.cn/api/oms/home?user_id=a2c82cb4
HTTP 200
contract status = ready
current_user.workspace_key = boss
current_user.emp_id = EMP001
current_user.name = 石磊
snapshot = TS-20260711-V1
```

生产配置统一指向：`https://api.wonderfulseki.cn`。

### 4.3 飞书入口实测

2026-07-11现场读取飞书客户端窗口：

- OMS每日工作台成功加载
- 身份显示：石磊
- 可见入口：首页工作台、销售中心、财务中心、运营中心、数据追溯
- 未出现`BLOCKED`或登录失败页面
- 页面当前显示V1 Snapshot

生产环境结论：`PASS`。该结论只表示通道可用，不表示数据已具备Cutover条件。

## 五、业务准备

### 5.1 责任人

| Domain | 主责任人 | 复核/备份 | 责任定义 |
| --- | --- | --- | --- |
| Sales | EMP006 杨欢欢 | EMP003 张敬东复核金额 | 已定义 |
| Finance | EMP004 刘晶 | EMP003 张敬东复核 | 已定义 |
| Room | EMP008 刘芳羽 | EMP009 尚丽娜备份核对 | 已定义 |
| Actual Stay | EMP008 刘芳羽 | EMP009 尚丽娜备份核对 | 已定义 |

### 5.2 未完成项

- Sales候选Sheet业务签认：PENDING
- Finance Historical迁移范围确认：PENDING
- Room Master Data/Historical迁移范围确认：PENDING
- Contract Stay Plan/Historical迁移范围确认：PENDING
- 四域Cutover首次操作确认：PENDING
- Cutover Date业务批准：PENDING

责任人存在不等于业务已准备完成。

业务准备结论：`FAIL`。

## 六、回退准备

### 6.1 Snapshot

- `TS-20260711-V1`文件和ACTIVE指针存在。
- V2尚未生成，不存在可回退的V2候选基线。
- V1不得被覆盖。

Snapshot回退准备：`PARTIAL`。

### 6.2 Release

- 本地Release Tag：`v1.0.0`
- Tag Commit：`4e89650d3084c20a36a3cacbf18db84110689c85`
- 服务器当前release：`/opt/huangjia-oms/releases/p0141-20260711-0058`

Release基线存在，但本地工作区包含大量未提交修改，不具备清晰的新Cutover release标记。

Release回退准备：`WARNING`。

### 6.3 Backup

在服务器`/opt/huangjia-oms`与`/var/lib/huangjia-oms`范围内未发现明确命名的独立backup文件或备份清单证据。

缺少以下验收证据：

- Cutover前Truth Source备份
- Domain存储备份
- Audit/Event备份
- 配置备份
- 恢复演练记录

Backup准备：`FAIL`。

回退准备总体结论：`FAIL`。

## 七、阻塞项

| ID | 阻塞项 | 风险等级 |
| --- | --- | --- |
| CUTOVER-BLOCK-001 | TS-20260711-V2未生成，初始迁移未冻结 | P0 |
| CUTOVER-BLOCK-002 | 四域迁移范围及首次操作仍未完成业务确认 | P0 |
| CUTOVER-BLOCK-003 | 缺少可验证的Cutover前独立备份与恢复证据 | P0 |
| CUTOVER-RISK-001 | 公网页面仍将旧V1口径展示为Current PASS | 高 |
| CUTOVER-RISK-002 | 本地工作区未清洁，Cutover release边界不明确 | 高 |

## 八、Cutover Date决策

Cutover Date当前不得确定。

只有以下项目全部关闭后才可安排日期：

1. V2按最新迁移策略生成并PASS。
2. 四域迁移范围及Cutover首次操作获得业务确认。
3. 独立备份完成并验证可恢复。
4. Cutover release边界冻结。
5. 飞书端重新确认读取待切换Snapshot和OMS Domain Current策略。

## 九、最终状态

```text
TS-20260711-V1 = ACTIVE
TS-20260711-V2 = NOT GENERATED
identity_readiness = PASS
production_environment_readiness = PASS
data_readiness = FAIL
business_readiness = FAIL
rollback_readiness = FAIL
cutover_readiness = FAIL
cutover_date = NOT SET
cutover = BLOCKED
```

本检查未修改Snapshot、业务数据、服务器服务或生产入口。
