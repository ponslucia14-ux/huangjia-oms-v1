# OMS 运行时十一人身份解析修复报告

Date: 2026-07-10
Status: P0.10-RUNTIME-IDENTITY-FIX
Owner: 石磊
Executor: 张照南

---

## 一、修复范围

本轮只修复运行时身份解析，不新增业务页面，不新增后端业务模块，不重新绑定人员，不重新采集飞书身份，不建立第二份人员表，不 Commit。

修改范围：

- `oms_v1/operating_center_source.py`
- `tests/test_runtime_identity.py`
- 身份解析相关测试预期
- 本报告

当前工作区仍包含上一阶段运营中心真实化的未提交代码变更，本轮未继续扩展业务页面。

---

## 二、旧解析链

修复前运行时身份解析链：

```text
OMS
-> feishu_identity_bindings()
-> live_runtime/human_identity/identity_enrichment_layer.json
-> live_runtime/realworld_mapping/OMS_RealWorld_Mapping.json
-> live_runtime/realworld_mapping/feishu_object_snapshot.json
-> workspace
```

旧链问题：

1. 未优先读取 `OMSMasterData`。
2. 未优先读取正式 `OMS_飞书身份映射.md`。
3. 旧 partial mapping 可能阻断正式身份源。
4. `feishu_object_snapshot.json` 被当成身份主证据。
5. 快照中 11 个 user_id 存在，但姓名字段不完整，导致只解析出 5 人。

---

## 三、新解析链

修复后运行时身份解析链：

```text
OMS
-> OMSMasterData
-> D:\凰家大脑\brain\03_organization\oms\OMS_飞书身份映射.md
-> EMP
-> user_id / open_id / union_id
-> role_code
-> workspace
```

新链规则：

1. Master Data 中存在真实身份时，必须优先返回。
2. 旧 partial mapping 不再作为主源。
3. `feishu_object_snapshot.json` 只作为 Master Data 不可用时的诊断 fallback，不覆盖 Master Data。
4. 快照缺失、为空、过期，不会导致 11 名正式员工身份失效。
5. 未知 `user_id` 返回 `UNMAPPED_IDENTITY`。
6. 未知身份不得默认进入石磊工作台。
7. Local Owner Access 仍只作为飞书认证异常时的受控恢复入口。

---

## 四、十一人运行时验证

| EMP | 正式姓名 | user_id | role_code | workspace_key | 工作台 | 一级菜单配置 | 运行时解析 |
|---|---|---|---|---|---|---|---|
| EMP001 | 石磊 | a2c82cb4 | ROLE_OWNER | boss | 主理办工作台 | 经营总览、财务总览、客户总览、房态总览、风险预警、数据分析中心、我的待办 | PASS |
| EMP002 | 宗惠 | ef8a11c3 | ROLE_HR | songxue | 人事行政工作台 | 考勤管理、工资管理、员工档案、人事审批 | PASS |
| EMP003 | 张敬东 | 7611528c | ROLE_ACCOUNTANT | zhangjie | 财务总监工作台 | 财务总览、资金流水、利润报表、成本分析、预算管理、财务审批 | PASS |
| EMP004 | 刘晶 | 8eag4627 | ROLE_CASHIER | liujie | 财务工作台 | 待确认到账、待付款、日结管理、收支总览、财务报表 | PASS |
| EMP005 | 石昊昕 | 19d9f5c2 | ROLE_ADMIN | yaowei | 行政采购工作台 | 行政采购、报销、照护师工资决算 | PASS |
| EMP006 | 杨欢欢 | e83f88ga | ROLE_SALES | huanhuan | 销售工作台 | 新增签约、我的客户、销售分析 | PASS |
| EMP007 | 薛子渝 | ge8gb853 | ROLE_SALES | yuchun | 食材采购 + 销售工作台 | 食材采购、销售工作台 | PASS |
| EMP008 | 刘芳羽 | 39g7c1f2 | ROLE_STORE_MANAGER | june | 店总工作台 | 今日经营看板、销售工作台、排房工作台、今日必须处理、未来30天预产期、已生产待安排 | PASS |
| EMP009 | 尚丽娜 | 9dcg7e27 | ROLE_BUTLER | nana | 管家工作台 | 今日入住、在住妈妈、CRM客户管理 | PASS |
| EMP010 | 陈晶辉 | 49916de2 | ROLE_NURSING_DIRECTOR | chenchangyi | 产护工作台 | 今日入住、在住产护一览、套餐信息、入住/出馆日期、产康套餐内容、特殊护理要求 | PASS |
| EMP011 | 周志朋 | 7e6595fg | ROLE_KITCHEN_DIRECTOR | zhouchen | 料理工作台 | 今日入住、在住饮食一览、忌口管理、特殊餐管理、加餐管理 | PASS |

运行时结果：

```text
runtime_resolved: 11 / 11
unknown_user_id: UNMAPPED_IDENTITY
```

---

## 五、工作台入口预览

本轮只做入口预验证，不开发完整业务页面。二级菜单以 P0.10 工作台交付清单为下一阶段页面开发依据。

| 正式姓名 | EMP | 岗位 | workspace | 允许显示的一级菜单 | 允许显示的二级菜单 |
|---|---|---|---|---|---|
| 石磊 | EMP001 | 主理人 / CEO / 销售总监 / CFO | 主理办工作台 | 今日工作、销售驾驶舱、资金驾驶舱、经营驾驶舱、风险异常、待我审批、决策与授权、数据追溯、AI经营助手 | 经营总览、财务总览、客户总览、房态总览、风险预警、数据分析中心、我的待办 |
| 宗惠 | EMP002 | HR | 人事行政工作台 | 员工花名册、考勤导入、工资表、工资核算结果、待处理事项 | 考勤管理、工资管理、员工档案、人事审批 |
| 张敬东 | EMP003 | 会计 | 财务总监工作台 | 月度入账、现金账、实入账、财务报表、对账追溯 | 财务总览、资金流水、利润报表、成本分析、预算管理、财务审批 |
| 刘晶 | EMP004 | 出纳 | 财务工作台 | 今日收款、销售明细、日结、待付录入、转账执行、到账确认 | 待确认到账、待付款、日结管理、收支总览、财务报表 |
| 石昊昕 | EMP005 | 行政总监 | 行政采购工作台 | 行政采购报销、截图/凭证上传、自动分类结果、报销审核、照护师工资决算 | 行政采购、报销、照护师工资决算 |
| 杨欢欢 | EMP006 | 销售顾问 | 销售工作台 | 签约客户录入、合同手写字段录入、合同照片、到账确认后的提交、本人销售结果 | 新增签约、我的客户、销售分析 |
| 薛子渝 | EMP007 | 销售顾问 | 食材采购 + 销售工作台 | 食材采购报销、截图/凭证上传、自动分类结果、报销审核、销售签约录入 | 食材采购、销售工作台 |
| 刘芳羽 | EMP008 | 店铺总监 | 店总工作台 | 在住总览、排房表、空房、超卖风险、倒房期、已生未入住、入住/出馆安排、销售签约录入 | 今日经营看板、销售工作台、排房工作台、今日必须处理、未来30天预产期、已生产待安排 |
| 尚丽娜 | EMP009 | 管家 | 管家工作台 | 在住信息录入、入住评估、房号、客户与宝宝信息、照护师对应关系、离馆录入 | 今日入住、在住妈妈、CRM客户管理 |
| 陈晶辉 | EMP010 | 产护总监 | 产护工作台 | 在住客户、套餐与入住/出馆信息、产康套餐、照护安排、换照护师原因月报 | 今日入住、在住产护一览、套餐信息、入住/出馆日期、产康套餐内容、特殊护理要求 |
| 周志朋 | EMP011 | 料理总监 | 料理工作台 | 在住客户、套餐、入住/出馆日期、忌口、料理相关提醒 | 今日入住、在住饮食一览、忌口管理、特殊餐管理、加餐管理 |

---

## 六、测试结果

测试命令：

```powershell
C:\Users\75859\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests
```

测试结果：

```text
Ran 369 tests
OK
```

---

## 七、当前结论

| 项目 | 结果 |
|---|---|
| 权威身份记录数量 | 11 |
| 运行时可解析数量 | 11 |
| 缺失人员 | 无 |
| 未知 user_id 是否越权进入石磊工作台 | 否 |
| 旧 partial mapping 是否仍为主源 | 否 |
| snapshot 是否可覆盖 Master Data | 否 |
| 是否可以进入 11 人岗位工作台开发 | 可以，身份入口断点已修复 |

