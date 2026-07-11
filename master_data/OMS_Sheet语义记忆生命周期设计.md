# OMS Sheet语义记忆生命周期设计

## 一、目标

Sheet语义记忆用于复用已经确认的业务含义，不替代Data Quality检查，不直接写入Truth Source。

## 二、版本模型

每条记忆必须包含：

- `memory_id`：同一文件模式、Sheet和Domain的稳定标识。
- `memory_version`：追加版本，格式为`<memory_id>-V<n>`。
- `memory_status`：`CONFIRMED`、`TEMPORARY`或`DEPRECATED`。
- `source_file_pattern`
- `source_sheet`
- `domain`
- `fact_type`
- `owner`
- 字段、结构、Sheet集合和质量指纹。

规则变化生成新版本，不覆盖旧版本。旧版本保留用于历史解释和Audit追踪。

## 三、状态生命周期

```text
TEMPORARY -> CONFIRMED -> DEPRECATED
CONFIRMED -> DEPRECATED
```

- `TEMPORARY`：候选规则，必须重新REVIEW，不得自动准入。
- `CONFIRMED`：真实EMP业务确认完成，且Data Quality未下降时允许自动识别。
- `DEPRECATED`：已失效，只保留历史，不参与自动匹配。

`DEPRECATED`不可恢复或覆盖；需要恢复业务规则时创建新版本。

## 四、识别与复审

首次无历史确认时执行全Sheet分析、候选生成和必要的业务确认。确认后保存新版本。

后续文件只有同时满足文件模式、Sheet、Domain、Sheet集合、字段指纹、结构指纹一致，且质量未下降，才可复用`CONFIRMED`规则。

出现Sheet增减、字段变化、结构变化、质量下降、临时规则或匹配歧义时，强制`REVIEW_REQUIRED`。

## 五、Audit

- 创建版本：`sheet.semantic_memory.created`
- 状态变化：`sheet.semantic_memory.status_changed`

Audit记录操作者EMP、原因、变更前后内容和结果。旧版本及其Audit不得删除。

## 六、四个首次记忆门槛

Sales Current、Finance Current、Room Current、Actual Stay仅在对应业务负责人完成Sheet签认后建立`CONFIRMED`记忆。当前确认表仍为PENDING，因此不得预写正式记忆。

## 七、发布门禁

- 当前生产快照：`TS-20260711-V1 / ACTIVE`
- 候选快照：`TS-20260711-V2 / NOT CREATED`
- 上线状态：`BLOCKED`

语义记忆确认本身不生成或激活Truth Source Snapshot。
