# OMS V1.0 生产架构修正方案

Generated At: 2026-07-09 23:25 (Asia/Shanghai)

## 一、唯一生产入口

### 1. 入口结论

V1.0 必须只保留一个老板生产入口：

```text
飞书客户端工作台
→ 凰家 OMS 应用
→ OMS 前端
→ OMS Production API
→ OMS_TRUTH_SOURCE
```

GitHub Pages 可以作为静态前端托管位置，但不能被定义为老板直接生产入口。

本机 `http://127.0.0.1:8787/` 只能作为本地维护入口，不能作为生产入口。

### 2. 老板访问地址

| 项目 | 目标定义 |
|---|---|
| 老板生产访问方式 | 飞书客户端 → 工作台 → 凰家 OMS |
| 老板生产 URL | 飞书工作台应用绑定的 WebApp URL |
| 浏览器直开 GitHub Pages | 禁止作为生产验收入口 |
| Local Owner Access | 仅应急维护，不作为生产入口 |

### 3. 前端部署位置

| 项目 | 目标定义 |
|---|---|
| 前端托管 | GitHub Pages 或等效静态托管 |
| 前端唯一版本 | 以 `gh-pages` 实际发布版本为准 |
| 版本标识 | `index.html` 必须带明确 asset version |
| 禁止状态 | main 已更新但 gh-pages 未更新；浏览器加载旧 app.js |

### 4. API 部署位置

| 项目 | 当前问题 | 修正目标 |
|---|---|---|
| 当前 API | `http://127.0.0.1:8787` | 不允许作为生产 API |
| 生产 API | 未固定 | 必须提供稳定 HTTPS API |
| 飞书入口 API | 当前继承 `oms-config.js` 本机地址 | 必须指向同一个 Production API |
| GitHub Pages API | 当前也指向本机地址 | 不作为生产入口；如保留预览，必须清楚标注 |

### 5. 唯一入口验收标准

```text
飞书客户端点击 OMS
→ 加载指定前端版本
→ 调用同一个 Production API
→ 返回同一份 OMS_TRUTH_SOURCE 数据
→ 老板进入同一个工作台
```

验收必须以飞书客户端实机为准，不再以 GitHub Pages 浏览器页面单独通过作为生产通过。

## 二、生产数据链

### 1. 总原则

V1.0 数据必须遵循：

```text
原始业务数据
→ Data Adapter
→ Domain / Engine
→ Contract
→ 页面
```

页面不得直接解释 Excel、截图、legacy runtime 或临时事件流。

### 2. 销售数据链

```text
销售原始数据
→ Sales Data Adapter
→ Sales Domain
→ Contract: sales payload
→ 老板工作台 / 销售中心
```

| 层级 | 要求 |
|---|---|
| 原始数据 | 销售明细、签约客户表、合同数据 |
| Adapter | 字段标准化、版本记录、导入结果记录 |
| Domain | `Sales` / contract / customer / stage |
| Contract | 固定输出签约数、客户列表、成交金额、转化状态 |
| 页面 | 只展示 Contract 输出，不直读 raw row |

销售中心必须能回答：

- 今天/本月新增签约多少；
- 成交金额是多少；
- 每条记录来自哪个源文件/哪一行；
- 客户当前阶段是什么。

### 3. 财务数据链

```text
财务原始数据
→ Finance Data Adapter
→ Payment / Finance
→ Contract: finance payload
→ 老板工作台 / 财务中心
```

| 层级 | 要求 |
|---|---|
| 原始数据 | 财务日报、银行流水、收款记录、待收待付表 |
| Adapter | 收入/支出/应收/应付分类 |
| Payment / Finance | 形成 `Finance`、`Payment`、`Settlement` 口径 |
| Contract | 固定输出今日收款、待收金额、待付金额、支出、余额 |
| 页面 | 金额必须来自 Finance/Payment，不得由 UI 自行计算 |

财务中心必须能回答：

- 今日收款多少；
- 待收金额多少；
- 待付金额多少；
- 每一笔是否可追溯到来源；
- 页面金额与财务源文件是否一致。

### 4. 运营数据链

运营中心必须补齐三个真实 Domain：

```text
入住 → Stay
房态 → Room
照护师 → Caregiver
```

当前不能再用 `business_event_flow` / `hr_execution_flow` 冒充真实运营数据。

#### 4.1 入住：Stay

```text
入住原始数据
→ Stay Adapter
→ Stay Domain
→ Contract: stay payload
→ 运营中心 / 首页状态
```

必须输出：

- 当前在住人数；
- 今日入住；
- 今日出馆；
- 即将入住；
- 每位客户对应房间、入住日期、出馆日期、管家/照护师。

#### 4.2 房态：Room

```text
房态原始数据
→ Room Adapter
→ Room Domain
→ Contract: room payload
→ 运营中心 / 房态详情
```

必须输出：

- 房间总数；
- 可用房；
- 已入住；
- 清洁中；
- 维修/停用；
- 每个房间当前状态。

#### 4.3 照护师：Caregiver

```text
照护师原始数据
→ Caregiver Adapter
→ Caregiver Domain
→ Contract: caregiver payload
→ 运营中心 / 人效状态
```

必须输出：

- 在岗照护师；
- 已分配照护师；
- 空闲/可分配照护师；
- 每位照护师当前服务对象；
- 照护师状态来源。

## 三、必须移除 / 禁用

### 1. 移除 localhost 生产依赖

生产前端不得配置：

```text
http://127.0.0.1:8787/api/oms/home
http://localhost:8787/api/oms/home
```

本机 API 只能用于：

- 本地开发；
- 本地排障；
- 应急维护。

### 2. 移除不明 legacy_runtime 展示

页面不得直接展示：

```text
migration_source = legacy_runtime
```

作为生产可信数据。

legacy_runtime 只能作为：

- 迁移输入；
- 审计参考；
- 待校准数据。

必须通过 Adapter 重新进入 Domain 后，才能进入生产页面。

### 3. 移除非事实运营数据

运营中心禁止用以下数据冒充真实运营状态：

- business_event_flow；
- workflow_distribution；
- hr_execution_flow；
- derived runtime task；
- 截图 OCR / 手工推断记录。

这些数据可以作为追溯链和任务链，但不能替代：

- Stay；
- Room；
- Caregiver。

### 4. 禁止 UI 生成经营事实

页面不得：

- 自行汇总真实金额；
- 自行推断在住人数；
- 自行判断房态；
- 自行拼接照护师状态；
- 将缺失字段自动补成正常数据。

## 四、唯一事实源定义

### 1. 唯一事实源

```text
OMS_TRUTH_SOURCE
```

是 V1.0 唯一数据事实源。

### 2. 事实源必须包含

| 文件 | 目标内容 | 当前状态 |
|---|---|---|
| `sales.json` | Sales Domain / 合同 / 客户 / 成交金额 | 有数据，但需去 legacy_runtime 化 |
| `finance.json` | Finance / Payment / Settlement | 有数据，但金额口径需校准 |
| `room.json` | Room Domain + Stay Domain + Caregiver Domain | 当前不完整 |
| `events.jsonl` | 业务事件追溯 | 可用，但不能替代 Domain |
| `manifest.json` | 数据版本、计数、来源版本 | 可用，但需反映真实生产状态 |

### 3. 页面读取规则

```text
OMS_TRUTH_SOURCE
→ API
→ Contract
→ UI
```

禁止：

```text
UI → Excel
UI → legacy_runtime
UI → event_flow 直接当业务事实
UI → mock / fallback
```

### 4. 事实源验收标准

| Domain | V1.0 最低验收 |
|---|---|
| Sales | 有签约记录、金额、来源行、阶段 |
| Finance | 有收款、待收、待付、来源流水 |
| Stay | 有当前在住、入住、出馆 |
| Room | 有房间状态、房间资源 |
| Caregiver | 有照护师状态、分配关系 |

## 五、修正实施顺序建议

### Step 1：锁定唯一生产入口

输出：

- 飞书入口 URL；
- 生产 API URL；
- 前端版本号；
- 禁止直开入口说明。

### Step 2：替换生产 API 配置

输出：

- 前端 `OMS_HOME_ENDPOINT` 指向 Production API；
- `127.0.0.1` 仅保留在 local config；
- 飞书入口与 GitHub Pages 预览不再混用数据链。

### Step 3：重建运营 Domain 数据

输出：

- Stay Adapter；
- Room Adapter；
- Caregiver Adapter；
- `room.json` 真实实体非 0。

### Step 4：销售/财务去 legacy_runtime 化

输出：

- 真实 Adapter 导入记录；
- 明确 source_file / row_id；
- Contract 输出金额和数量。

### Step 5：页面重新验收

只验收：

```text
飞书生产入口
→ 生产 API
→ OMS_TRUTH_SOURCE
→ Contract
→ 页面
```

## 六、P0.7 结论

```text
当前 V1.0 不能继续按“已上线产品”推进。

必须先完成：
1. 唯一生产入口锁定；
2. localhost 生产依赖移除；
3. 运营 Stay / Room / Caregiver 真实数据补齐；
4. 销售 / 财务数据从 legacy_runtime 转为 Adapter 生产链；
5. 页面只读 Contract 输出。
```

本方案仅定义修正方向，未写代码，未修改系统。
