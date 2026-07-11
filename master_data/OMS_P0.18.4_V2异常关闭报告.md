# OMS P0.18.4 V2异常关闭报告

执行原则：不修改原始Excel，不手工改数字，不修改V1。  
当前结论：`SUPERSEDED BY OMS_P0.18.4阻塞项重新评估报告`

## 一、Sales

冲突合同号：`NSEKI94131081`。

| 行 | 客户 | 签约日期 | 金额 |
| --- | --- | --- | ---: |
| 140 | 郝梓涵 | 2026-05-22 | 21,990 |
| 141 | 王雪 | 2026-05-23 | 24,000 |

从7.1至7.10的全部可用销售工作簿版本中，两条冲突始终同时存在。历史版本不能证明哪一位客户对应正确合同号，也不能证明错误记录应转Historical还是Quarantine。

处理结果：

- 两条继续保持`CONFLICT / QUARANTINE`。
- 不合并。
- 其余184条保持Sales Current候选。
- 需要原始纸质/电子合同或权威合同、收款记录确认正确客户。

状态：`BLOCKED`，Sales Current候选尚不能整体PASS。

## 二、Finance

- Finance Historical：470条。
- Quarantine：0。
- Data Quality：PASS。
- Finance Current：`NOT_INITIALIZED`。
- Cutover后由EMP004刘晶在OMS录入，EMP003张敬东复核。

状态：`CLOSED`。

## 三、Contract Stay Plan

1319条记录字段完整，进入Plan准入集。

7条不完整记录均保留原始文件、Sheet和行号，因缺少预产期或套餐等必要Plan字段而排除：

- 2024年1月：第25、26行
- 2024年2月：第22行
- 2024年3月：第35行
- 2024年7月：第43行
- 2025年6月：第48行
- 2026.5：第31行

处理结果：

- 7条进入`QUARANTINE / REQUIRED_PLAN_FIELDS_MISSING`。
- 不物理删除，不补写，不推算。
- 1319条准入Plan集合质量为PASS。
- 禁止该文件生成Actual Stay。

状态：`CLOSED_WITH_QUARANTINE`。

## 四、Actual Stay

最新可定位原始在住文件：`凰家母婴在住表最新4.13.xlsx`。

表内事实：

- Sheet：`房态表`
- 表内更新时间：2026-07-02
- 完整实际入住记录：33条
- 33条对应33位不同客户，不是重复客户造成
- 人工汇总：产妇30人
- 缺少实际日期：5条

解释结论：

- `33 vs 30`不是房间重复或客户重复造成。
- 明细与人工汇总存在真实一致性冲突，当前证据无法确定哪一侧正确。
- 5条缺日期记录不能作为Actual Stay，继续进入Quarantine；可在后续业务处理中转为Room Reservation或Plan，但本轮不猜测。
- 今日新增的`①凰家母婴 2021房态表June(2).xlsx`不包含标准在住表结构，不能替代尚丽娜的在住文件。

状态：`BLOCKED`。需要最新原始在住表，或由EMP008刘芳羽在OMS完成Cutover Current确认。

## 五、Semantic Memory

按域推进，不等待全部异常一起关闭：

| Domain | Memory状态 |
| --- | --- |
| Sales | 2条`TEMPORARY` |
| Finance | 7条`CONFIRMED` |
| Contract Stay Plan | 39条`CONFIRMED` |
| Actual Stay | 1条`TEMPORARY` |

总计：49条，其中46条`CONFIRMED`、3条`TEMPORARY`。

状态变更写入隔离候选库Audit，未写生产Truth Source。

## 六、V2决策

```text
Finance Current = NOT_INITIALIZED
Finance Historical = 470
Contract Stay Plan = 1319 PASS + 7 QUARANTINE
Sales = 184 candidates + 2 CONFLICT
Actual Stay = historical snapshot only; Current NOT_INITIALIZED
TS-20260711-V2 = NOT GENERATED
TS-20260711-V1 = ACTIVE
```

Sales正确客户和Actual Stay最新事实仍无足够证据。V2生成门保持BLOCKED。
