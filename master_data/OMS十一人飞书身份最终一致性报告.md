# OMS 十一人飞书身份最终一致性报告

检查编号：P0.13.4  
检查时间：2026-07-10  
检查状态：PASS  
通过数量：11/11  
活动冲突：0  

## 一、最终结论

OMS 当前活动身份链已统一为：

```text
Feishu user_id
-> Feishu 生产真实姓名
-> EMP 编号
-> role_code
-> workspace
-> responsibility_scope
```

11 名在职人员均具备唯一 user_id、唯一 EMP、唯一 role_code 和唯一 workspace。活动身份解析来源固定为 `feishu_production_master_data`，不再优先读取旧 runtime enrichment、昵称或岗位代称。

## 二、生产证据

| 证据 | 数量 | 结果 |
|---|---:|---|
| 飞书 Windows 客户端生产通讯录逐部门实机核对 | 11 | PASS |
| 飞书 Production Contact API 的 user_id/open_id/union_id 比对 | 11 | PASS |
| OMS 组织主数据 | 11 | PASS |
| OMS 飞书正式身份映射 | 11 | PASS |
| OMS 权限主体名册 | 11 | PASS |
| OMS workspace 显示姓名 | 11 | PASS |
| 本次 append-only Audit 记录 | 11 | PASS |

Contact API 当前字段权限未返回姓名、部门和岗位，因此 ID 三元组由 API 校验，姓名由飞书客户端生产通讯录实机确认。两类证据共同构成本次生产身份基线。

## 三、十一人逐项核对

| EMP | 飞书 user_id | 飞书正式姓名 | OMS Master Data | 身份映射 | role_code | workspace | 权限姓名 | Audit 姓名 | 结果 |
|---|---|---|---|---|---|---|---|---|---|
| EMP001 | `a2c8***cb4` | 石磊 | 石磊 | 石磊 | ROLE_OWNER | boss / 主理办工作台 | 石磊 | 石磊 | PASS |
| EMP002 | `ef8a***1c3` | 宗惠 | 宗惠 | 宗惠 | ROLE_HR | songxue / 人事行政工作台 | 宗惠 | 宗惠 | PASS |
| EMP003 | `7611***28c` | 张敬东 | 张敬东 | 张敬东 | ROLE_ACCOUNTANT | zhangjie / 财务总监工作台 | 张敬东 | 张敬东 | PASS |
| EMP004 | `8eag***627` | 刘晶 | 刘晶 | 刘晶 | ROLE_CASHIER | liujie / 财务工作台 | 刘晶 | 刘晶 | PASS |
| EMP005 | `19d9***5c2` | 石昊盺 | 石昊盺 | 石昊盺 | ROLE_ADMIN | yaowei / 行政采购工作台 | 石昊盺 | 石昊盺 | PASS |
| EMP006 | `e83f***8ga` | 杨欢欢 | 杨欢欢 | 杨欢欢 | ROLE_SALES | huanhuan / 销售工作台 | 杨欢欢 | 杨欢欢 | PASS |
| EMP007 | `ge8g***853` | 薛子渝 | 薛子渝 | 薛子渝 | ROLE_SALES | yuchun / 食材采购 + 销售工作台 | 薛子渝 | 薛子渝 | PASS |
| EMP008 | `39g7***1f2` | 刘芳羽 | 刘芳羽 | 刘芳羽 | ROLE_STORE_MANAGER | june / 店总工作台 | 刘芳羽 | 刘芳羽 | PASS |
| EMP009 | `9dcg***e27` | 尚丽娜 | 尚丽娜 | 尚丽娜 | ROLE_BUTLER | nana / 管家工作台 | 尚丽娜 | 尚丽娜 | PASS |
| EMP010 | `4991***de2` | 陈晶辉 | 陈晶辉 | 陈晶辉 | ROLE_NURSING_DIRECTOR | chenchangyi / 产护工作台 | 陈晶辉 | 陈晶辉 | PASS |
| EMP011 | `7e65***5fg` | 周志朋 | 周志朋 | 周志朋 | ROLE_KITCHEN_DIRECTOR | zhouchen / 料理工作台 | 周志朋 | 周志朋 | PASS |

## 四、七个身份表面检查

| 检查面 | 结果 | 事实 |
|---|---|---|
| 飞书 user_id 对应姓名 | PASS | 11 个 user_id 唯一；生产通讯录姓名已逐人核对 |
| OMS Master Data 姓名 | PASS | 11/11 与飞书正式姓名一致 |
| 飞书身份映射姓名 | PASS | 11/11 与飞书正式姓名一致 |
| 权限系统姓名 | PASS | 11 个 EMP 均注册为权限主体；无额外权限被授予 |
| 工作台显示姓名 | PASS | 11/11 使用正式姓名，不使用昵称或岗位代称 |
| Audit 记录姓名 | PASS | 已追加 11 条 `identity.consistency.checked`，actor_name 全部为正式姓名 |
| 数据责任 Owner 姓名 | PASS | 已分配责任的 6 人姓名一致；其余 5 人当前无 Truth Source Owner 分配，不构成身份冲突 |

## 五、数据责任核对

| 数据责任身份 | EMP | 正式姓名 | 状态 |
|---|---|---|---|
| 最终经营责任 / 跨域裁决 | EMP001 | 石磊 | PASS |
| 销售与签约客户数据主责 | EMP006 | 杨欢欢 | PASS |
| 房态、入住运营事实主责 | EMP008 | 刘芳羽 | PASS |
| 财务日常维护 | EMP004 | 刘晶 | PASS |
| 财务复核 | EMP003 | 张敬东 | PASS |
| 入住资料与房态备份维护 | EMP009 | 尚丽娜 | PASS |

EMP002、EMP005、EMP007、EMP010、EMP011 当前未被《OMS生产数据责任矩阵》指定为生产 Truth Source Owner；其工作台责任范围仍为 `own_workspace`。该状态是责任分配状态，不是姓名或身份冲突。

## 六、IDENTITY_CONFLICT 处理记录

| Conflict | 发现值 | 飞书生产值 | 处理 | 状态 |
|---|---|---|---|---|
| IDENTITY_CONFLICT-EMP005-NAME | 石昊昕 | 石昊盺 | 飞书生产姓名覆盖 OMS 活动正式姓名；旧名保留为历史 alias | RESOLVED |
| IDENTITY_CONFLICT-RUNTIME-STALE | runtime enrichment 仅 7/11，含旧昵称和旧 user_id | 正式映射 11/11 | 活动解析改为优先读取正式飞书主数据；旧文件仅保留历史证据 | RESOLVED |

历史 Audit 与历史快照不做覆盖或删除。历史名称只能用于追溯，不能参与当前授权、路由或工作台显示。

## 七、系统校验输出

```text
source_of_truth = Feishu production identity
required_count = 11
pass_count = 11
conflict_count = 0
status = PASS
permission_subject_count = 11
active_binding_count = 11
active_binding_source = feishu_production_master_data
```

## 八、上线 Gate

P0.13.4 身份一致性 Gate：PASS。

本报告只关闭身份一致性阻塞。正式上线仍须同时满足数据可信验收、生产入口与其他独立 Gate。
