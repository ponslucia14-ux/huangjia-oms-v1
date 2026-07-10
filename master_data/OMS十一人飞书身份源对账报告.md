# OMS 十一人飞书身份源对账报告

Date: 2026-07-10
Status: P0.10-IDENTITY-RECONCILIATION
Owner: 石磊
Executor: 张照南

---

## 一、对账结论

本轮只做身份源对账，不新增身份绑定，不重新建立第二份人员表，不进入岗位菜单开发，不 Commit。

结论：

1. 权威身份文件 `OMS_飞书身份映射.md` 中仍有 11 条正式记录。
2. 11 人均有唯一 `user_id`，缺失 `user_id` 为 0。
3. 11 人均有 `open_id` 与 `union_id`，缺失为 0。
4. `OMSMasterData` 可从 `master_data/sources.json` 指向的权威文件读取 11 人。
5. 当前生产运行时工作台解析函数 `feishu_identity_bindings()` 只能解析 5 人。
6. P0.10 早前“只有 5/11 有绑定证据”的说法，是把运行时快照解析结果误当成权威身份源结论，属于数据源优先级判断错误。

最终判断：

- 此前“11/11 身份映射完成”的结论真实有效。
- 不需要重新绑定人员。
- 需要修正运行时身份解析优先级：工作台入口应优先读取 `OMS_飞书身份映射.md` / `OMSMasterData`，运行时快照只能作为补充证据。
- 在运行时解析修正前，不建议直接进入 11 人岗位工作台实机验收。

---

## 二、核对来源

| 来源 | 路径 / 模块 | 核对结果 |
|---|---|---|
| OMS 组织主数据 | `D:\凰家大脑\brain\03_organization\oms\OMS_组织主数据.md` | 11 名正式员工存在，EMP 编号以此为准 |
| OMS 飞书身份映射 | `D:\凰家大脑\brain\03_organization\oms\OMS_飞书身份映射.md` | 11 条正式身份记录，user_id / open_id / union_id 完整 |
| OMS Master Data 读取结果 | `oms_v1.master_data.OMSMasterData().feishu_identity_rows()` | 读取 11 条，唯一 user_id 11，缺失 user_id 0，缺失 open_id / union_id 0 |
| 当前生产身份快照 | `live_runtime\realworld_mapping\feishu_object_snapshot.json` | 包含 11 个 user_id / open_id / union_id，但快照行缺少姓名；只有聊天成员等补充行能解析出 5 人姓名 |
| P0.10 覆盖矩阵当前使用的数据源 | `feishu_identity_bindings()` 运行时解析结果 | 只返回 5 人；未优先使用正式 Master Data 身份映射 |

---

## 三、逐人身份源对账表

| EMP | 正式姓名 | 部门 | 岗位 | user_id | open_id | union_id | 当前工作台角色 | 权威来源文件 | 生产运行时是否可解析 | P0.10 为什么判定有证据或无证据 | 最终结论 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EMP001 | 石磊 | 主理办 | 主理人 / CEO / 销售总监 / CFO | a2c82cb4 | ou_1af1e4cd883fe033c74e7451f49ec4a7 | on_1ab47bfda29ef528a0d254ec55b58abe | 主理办工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 是，解析为 boss | 运行时快照存在可匹配姓名与 user_id | PASS |
| EMP002 | 宗惠 | 人力资源部 | HR | ef8a11c3 | ou_eb1403cda0e322323d26a8781b9aa1e2 | on_9752563036cac8407f384555968dd732 | HR 工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 否，当前解析函数返回 identity_binding_required | P0.10 只看运行时快照姓名证据，未读正式身份映射 | FAIL：身份源 PASS，运行时解析 FAIL |
| EMP003 | 张敬东 | 财务部 | 会计 | 7611528c | ou_90c4aafde4f068a52696da75a9f5c2b2 | on_df69cec5fbdfc30d6d5d8a5f3951675c | 会计工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 否，当前解析函数返回 identity_binding_required | P0.10 只看运行时快照姓名证据，未读正式身份映射 | FAIL：身份源 PASS，运行时解析 FAIL |
| EMP004 | 刘晶 | 财务部 | 出纳 | 8eag4627 | ou_7796000524ab8859d6fd680cf6c8dc1f | on_23caccf11e39a26a0beb28f85e4b7b46 | 出纳工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 是，解析为 liujie | 运行时快照存在可匹配姓名与 user_id | PASS |
| EMP005 | 石昊昕 | 行政部 | 行政总监 | 19d9f5c2 | ou_e78d94e267c006e7f8fd64d684ef467d | on_4e91751058534eaeb80ed84ff50e87a8 | 行政采购工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 是，解析为 yaowei | 运行时快照存在飞书显示名“石昊盺”，代码兼容该显示名 | PASS |
| EMP006 | 杨欢欢 | 市场销售部 | 销售顾问 | e83f88ga | ou_024effa4dffb841ae8e58c4b0ed7f854 | on_06c3478b2a67594e5cf910b0525352cd | 销售工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 否，当前解析函数返回 identity_binding_required | P0.10 只看运行时快照姓名证据，未读正式身份映射 | FAIL：身份源 PASS，运行时解析 FAIL |
| EMP007 | 薛子渝 | 市场销售部 | 销售顾问 | ge8gb853 | ou_518d09fcdf7fd1a020396baf98466553 | on_0b7dc423caf6adb4810989d70690958e | 食材采购 + 销售工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 否，当前解析函数返回 identity_binding_required | P0.10 只看运行时快照姓名证据，未读正式身份映射 | FAIL：身份源 PASS，运行时解析 FAIL |
| EMP008 | 刘芳羽 | 店总办公室 | 店铺总监 | 39g7c1f2 | ou_5524c2b3c3216a7750aa2ab87b584970 | on_18d241a937b475d488418f480d07facf | 店总工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 是，解析为 june | 运行时快照存在可匹配姓名与 user_id | PASS |
| EMP009 | 尚丽娜 | 店总办公室 | 管家 | 9dcg7e27 | ou_5ffba8b5e759c13dab675255dba0718c | on_12957a39627be7f165d12993fe243907 | 管家工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 是，解析为 nana | 运行时快照存在可匹配姓名与 user_id | PASS |
| EMP010 | 陈晶辉 | 产护部 | 产护总监 | 49916de2 | ou_35b4fee4c7240955c1c4ceeac85cdc4f | on_54f465e7b757b57fbf433a7647c58b6f | 产护工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 否，当前解析函数返回 identity_binding_required | P0.10 只看运行时快照姓名证据，未读正式身份映射 | FAIL：身份源 PASS，运行时解析 FAIL |
| EMP011 | 周志朋 | 料理部 | 料理总监 | 7e6595fg | ou_6bdce13776383bccc9ca56e1c998a2bd | on_c5b142a4b98ebf4ffb1fec435afbb622 | 料理工作台 | OMS_组织主数据.md + OMS_飞书身份映射.md | 否，当前解析函数返回 identity_binding_required | P0.10 只看运行时快照姓名证据，未读正式身份映射 | FAIL：身份源 PASS，运行时解析 FAIL |

---

## 四、矛盾根因

P0.10 只识别出 5 人的原因：

1. P0.10 检查使用了 `feishu_identity_bindings()` 的当前运行时结果。
2. 该函数当前读取顺序是：
   - `live_runtime\human_identity\identity_enrichment_layer.json`
   - `live_runtime\realworld_mapping\OMS_RealWorld_Mapping.json`
   - `live_runtime\realworld_mapping\feishu_object_snapshot.json`
3. 当前没有 `identity_enrichment_layer.json`。
4. `OMS_RealWorld_Mapping.json` 是旧的 partial 文件，未提供有效 user_id。
5. `feishu_object_snapshot.json` 虽然有 11 个 user_id / open_id / union_id，但 `users` / `org_users` 行没有姓名字段。
6. 只有 5 人能通过聊天成员等补充行匹配姓名，因此运行时函数只返回 5 个 workspace binding。
7. P0.10 没有把 `D:\凰家大脑\brain\03_organization\oms\OMS_飞书身份映射.md` 作为身份权威源参与判断，这是错误路径和数据源优先级错误。

---

## 五、明确回答

### 1. P0.10 为什么只识别出 5 人？

因为 P0.10 使用了当前运行时 `feishu_identity_bindings()` 的输出。该输出只基于运行时快照可匹配姓名的 5 人，没有优先读取正式 `OMS_飞书身份映射.md`。

### 2. 是否读取了旧文件或错误路径？

是。P0.10 对身份绑定的判断读取了运行时快照路径和旧 partial mapping，而不是以 `master_data/sources.json` 指向的正式身份文件为准。

### 3. OMS_飞书身份映射.md 中是否仍有 11 条正式记录？

是。文件中有 11 条正式身份映射，`user_id` 唯一数为 11，缺失 `user_id` 为 0，缺失 `open_id / union_id` 为 0。

### 4. 生产运行时是否能按 11 个 user_id 返回对应 EMP？

当前不能。按 11 个正式 user_id 调用 `workspace_key_for_feishu_identity()`，目前只有 5 个能返回工作台 key，6 个返回 `identity_binding_required`。

### 5. 之前“11/11 身份映射完成”的结论是否真实有效？

真实有效。该结论针对权威身份源与 `OMSMasterData` 成立；当前问题是运行时工作台解析未使用权威身份源，不是身份映射缺失。

---

## 六、处理结论

权威身份文件确实已有 11 人，因此：

1. 不重新绑定人员。
2. 不从飞书后台重复采集身份。
3. 不建立第二份人员表。
4. 已修正 P0.10 覆盖矩阵和 11 人工作台交付清单中的身份判断。
5. 下一步应先修正运行时身份解析：`feishu_identity_bindings()` 必须优先读取 `OMSMasterData` / `OMS_飞书身份映射.md`。
6. 修正后再进入 11 人岗位工作台菜单开发。

---

## 七、当前状态

| 项目 | 数量 / 结论 |
|---|---|
| 权威身份记录数量 | 11 |
| Master Data 可读取数量 | 11 |
| 权威 user_id 唯一数 | 11 |
| 权威 open_id / union_id 完整数量 | 11 |
| 当前运行时可解析数量 | 5 |
| 当前运行时不可解析人员 | 宗惠、张敬东、杨欢欢、薛子渝、陈晶辉、周志朋 |
| 是否存在缺失身份字段 | 否 |
| 是否存在身份源矛盾 | 否，矛盾来自运行时读取优先级 |
| 是否可以进入 11 人岗位工作台开发 | 暂不建议；应先修正运行时身份解析 |

