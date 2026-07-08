# OMS V1

阶段目标：只打通 `输入 -> 结构化 JSON`。

本阶段只包含两个部分：

- `OMS_InputHub`：统一输入入口，把微信群文本、文件、图片等包装成标准输入信封。
- `OMS_DataParser`：OCR/文本抽取 + 结构化解析引擎，把合同、收款、报销、备注解析成 JSON。

本阶段不做 UI、不做业务页面、不做后续模块。

## 第二阶段：业务事件模型

第二阶段新增：

- `EventEngine`：把结构化 JSON 转成业务事件；
- Multi-Event 拆解：一条输入可以拆成多个业务事件；
- Event Stream：统一输出 `输入 -> 解析 -> 事件 -> 分发`。

事件标准结构：

```json
{
  "event_type": "",
  "source": "",
  "entity": "",
  "action": "",
  "payload": {},
  "timestamp": ""
}
```

当前事件类型：

| 事件 | 订阅模块 |
|---|---|
| `sales_event` | `sales_module` |
| `financial_event` | `finance_module` |
| `room_status_event` | `room_status_module` |
| `service_event` | `service_module` |

## 第三阶段：业务决策引擎

第三阶段新增：

- `DecisionEngine`：把业务事件转成系统建议动作；
- 房态决策：排房建议、风险预警、调度建议；
- 财务决策：待付款、对账、服务金额拆分、异常/重复风险；
- 服务决策：入住准备、服务异常、跨岗位协调、延迟风险。

决策标准结构：

```json
{
  "event_id": "",
  "decision_type": "",
  "recommended_action": "",
  "priority": "",
  "risk_level": "",
  "reason": ""
}
```

原则：只给建议，不直接执行；所有建议允许 石磊/刘芳羽/刘晶/尚丽娜人工覆盖。

## 第四阶段：自动执行层

第四阶段新增：

- `ExecutionEngine`：把决策建议转成可回滚的执行动作；
- 房态执行：排房计划、调房任务、超卖风险标记、入住计划、风险提醒；
- 财务执行：日结/对账任务、待付款、服务金额拆分、异常收款标记；
- 服务执行：入住任务、服务安排、产护/厨房协同、出馆/跟进任务。

执行标准结构：

```json
{
  "action_type": "",
  "target_module": "",
  "execution_result": "",
  "status": "success / failed / pending",
  "timestamp": "",
  "rollback_supported": true
}
```

当前执行边界：生成动作记录、任务、风险标记和待终审项；不绕过 `DecisionEngine`，不直接修改正式财务、房态或服务源表。所有动作支持回滚，并允许 石磊/刘芳羽/刘晶/尚丽娜人工覆盖。

## 第五阶段：治理层

第五阶段新增：

- `GovernanceEngine`：判断执行动作是否可以自动放行，还是必须人工审批；
- 权限角色系统：石磊、刘芳羽、刘晶、尚丽娜、系统；
- 三层权限：自动执行层、人工确认层、石磊 终审层；
- 责任链：记录谁批准、谁执行、谁覆盖。

治理标准结构：

```json
{
  "action_id": "",
  "allowed": true,
  "approval_required": false,
  "required_roles": [],
  "risk_level": "low / medium / high / critical",
  "reason": "",
  "override_policy": ""
}
```

治理原则：

- 系统可以做事，但必须可控；
- 系统可以建议，但不能越权；
- 所有关键动作必须有责任链；
- 石磊 是最终决策点。

当前 OMS V5 定位：可控自动化系统（Controlled Autonomy System）。

## 第六阶段：真实接入层

第六阶段新增：

- `LiveConnector`：把通过治理层的动作同步到真实业务接入层；
- 飞书接入 outbox：销售提报、排房任务、任务系统待同步；
- Excel 接入台账：刘晶日结、刘芳羽排房、石昊昕报销、CRM 历史数据；
- 人工流接入：微信提报流、人工确认、石磊 审批回写的待处理队列；
- 审计日志：每次同步都有 audit log 和 rollback plan。

真实接入输出结构：

```json
{
  "sync_target": "",
  "sync_type": "",
  "sync_result": "",
  "status": "success / failed / pending",
  "rollback_supported": true,
  "audit_log": ""
}
```

接入原则：

- OMS 不能替代飞书、Excel、微信；
- OMS 只做同步、结构化和增强；
- 所有写入必须可回滚，并保留 audit log；
- 真实系统永远是最终真相源：飞书 / Excel / 微信 > OMS 推理结果。

当前边界：Excel 先写入本机 Excel-compatible CSV 同步台账；飞书和微信在未配置真实 API/授权前写入 outbox，状态为 `pending`，不伪造外部系统成功。

## 第七阶段：真实运营融合阶段

第七阶段新增：

- `OMS_OperationalCore`：把执行、治理、真实接入结果转成日常岗位工作队列；
- Operating Mode：从工具辅助升级为默认运营入口；
- 角色工作视图：刘芳羽、刘晶、销售、尚丽娜、石磊；
- 旧系统降级策略：Excel 只读历史，微信只作为输入来源；
- 管理切换门槛：不伪造“已经停用 Excel/微信群”，需要 石磊 组织切换确认。

运行原则：

- OMS 不是工具，是工作入口；
- Excel 不是系统，只是历史；
- 微信不是系统，只是输入；
- OMS 必须成为默认路径；
- 人不绕过系统，系统也不绕过人。

当前边界：代码已具备 Operating Mode 和岗位队列，但“刘芳羽不再用 Excel 排房、刘晶不再手工做日结、销售不再群里报数据、石磊直接看 OMS”需要真实组织切换后才可标记完成。

## 第八阶段：组织切换层

第八阶段新增：

- `AdoptionEngine`：评估组织是否从旧入口迁移到 OMS；
- 四类迁移对象：刘芳羽、刘晶、销售、尚丽娜；
- 迁移状态：`not_started` / `partial` / `active` / `full`；
- 绕行记录：`bypass_log`；
- 人工覆盖记录：`manual_override_log`；
- 迁移任务和推荐动作。

组织切换原则：

- 不强制替代，而是默认迁移；
- 人可以绕开系统，但系统必须记录；
- 切换是行为变化，不是功能上线；
- 目标不是让系统更强，而是让人开始依赖系统。

当前边界：AdoptionEngine 能评估和推动迁移，但是否进入 `full` adoption 取决于 石磊 的组织切换命令和岗位真实使用情况。

## 第九阶段：真实运行切换

第九阶段新增：

- `SystemSwitchController`：控制 OMS 从工具模式切换为唯一运营系统模式；
- 四个切换状态：`PRE_SWITCH` / `SOFT_SWITCH` / `HARD_SWITCH` / `FULL_OPERATING`；
- 岗位切换动作：刘芳羽房态、刘晶财务、销售输入、尚丽娜服务；
- 强切换授权：`HARD_SWITCH` 和 `FULL_OPERATING` 需要 石磊 明确授权；
- 绕行监控：继续保留 `bypass_log` 和 `manual_override_log`。

切换原则：

- Excel / 微信 / 旧系统 = 历史；
- OMS = 现在；
- 系统不再辅助业务，系统就是业务运行环境；
- 所有绕行继续记录，用于识别切换完成度；
- FULL_OPERATING 必须同时满足 石磊 授权和四个岗位 full adoption。

## 第十阶段：现实锁定层

第十阶段新增：

- `RealityLock`：锁定 OMS 与凰家现实之间的最终关系；
- 四个锁定状态：`LOCKED` / `UNLOCKED` / `READONLY` / `MIGRATION`；
- 最终主架构冻结：禁止新增阶段、禁止新增核心架构层、禁止改变链路顺序；
- 全链路追踪要求：event / decision / execution / governance / adoption / switch trace；
- 扩展边界：后续只能作为子模块扩展，不再改变主架构。

最终运行原则：

- OMS 不再是项目，OMS = 企业运行方式本身；
- Excel / 微信 / 飞书 = 外围接口；
- OMS = 唯一事实解释系统；
- 人 = 执行节点，系统 = 决策与结构节点；
- 石磊 = 最终现实定义者。

当前边界：只有 `SystemSwitchController` 达到 `FULL_OPERATING` 且无 blockers 时才会进入 `LOCKED`。当前样例仍处于迁移状态，因此 RealityLock 输出 `MIGRATION`。

## 快速使用

```powershell
$py='C:\Users\75859\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m oms_v1 parse --text "刘晶收到张三尾款 20000 元，7月2日到账，备注：合同HJM20260702" --pretty
```

Windows 可直接使用启动器：

```powershell
& "D:\凰家母婴空间\OMS_V1\run_oms_v1.cmd" parse --text "刘晶收到张三尾款 20000 元，7月2日到账，备注：合同HJM20260702" --pretty
```

从文件解析：

```powershell
& $py -m oms_v1 parse --file "D:\path\to\message.txt" --source wechat --group "财务群" --sender "石昊昕" --pretty
```

批量解析目录：

```powershell
& $py -m oms_v1 batch --input-dir "D:\path\to\inputs" --output-dir "D:\path\to\json_out"
```

生成业务事件流：

```powershell
& $py -m oms_v1 events --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --pretty
```

生成决策建议流：

```powershell
& $py -m oms_v1 decisions --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --pretty
```

生成执行动作流：

```powershell
& $py -m oms_v1 execute --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --pretty
```

生成治理判断流：

```powershell
& $py -m oms_v1 govern --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --pretty
```

生成真实接入同步流：

```powershell
& $py -m oms_v1 live --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --pretty
```

生成日常运营工作流：

```powershell
& $py -m oms_v1 operate --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --pretty
```

生成组织切换评估：

```powershell
& $py -m oms_v1 adopt --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --pretty
```

生成真实运行切换状态：

```powershell
& $py -m oms_v1 switch --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --requested-state SOFT_SWITCH --pretty
```

生成现实锁定状态：

```powershell
& $py -m oms_v1 lock --file "D:\凰家母婴空间\OMS_V1\sample_inputs\multi_event_wechat.txt" --pretty
```

## 输出原则

所有输出必须是 JSON。每条输出都包含：

- 输入来源；
- 文本/OCR 抽取状态；
- 文档类型判断；
- 结构化字段；
- 置信度和备选类型；
- 缺失字段和待人工复核项；
- 规则版本和审计时间。

## 当前支持

| 输入 | 当前状态 |
|---|---|
| 纯文本 | 支持 |
| `.txt` / `.md` | 支持 |
| `.docx` | 支持文本抽取 |
| `.pdf` | 支持文本抽取 |
| 图片 | 预留 OCR 接口；本机未安装 OCR 引擎时返回 `ocr_unavailable` |

## 当前识别类型

| 类型 | 用途 |
|---|---|
| `contract` | 合同/签约 |
| `payment` | 收款/到账/定金/尾款 |
| `reimbursement` | 报销/采购/费用 |
| `note` | 普通备注 |
| `unknown` | 暂无法判断 |
