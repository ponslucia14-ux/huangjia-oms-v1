# OMS 数据质量生产快照冻结报告

## 一、冻结结论

- 阶段：P0.14.1 数据质量生产快照冻结
- 结论：PASS
- 激活状态：已激活
- Snapshot ID：`TS-20260711-V1`
- 生成时间：`2026-07-11T00:50:59+08:00`
- 生成人：`EMP001`（石磊）
- Health Score：`96.0 / 100`
- Quarantine：`0`
- 未解决异常：`0`

只有 PASS 快照能够写入 `ACTIVE_SNAPSHOT.json`。WARNING 和 FAIL 快照均不能激活为生产版本。

## 二、Current 数据范围

| 数据域 | Current 数量 | 数据版本 | 验收状态 |
| --- | ---: | --- | --- |
| Sales | 224 | `sha256:b101f55246145e5f738b4bb10ea1e087bf67fa8ddd8760bb28cb3e628d61c30e` | PASS |
| Finance | 1278 | `sha256:5d82c4735a81b8b725fb30301277ad88eec702d07327769e050261ef87f80990` | PASS |
| Room | 42 | `sha256:946fc4ddd9c3a12ada1644e5876a9a1a623dac198512d722fe076f653b96c37e` | PASS |
| Stay | 172 | `2026-07-10T15:40:40+08:00` | PASS |

补充事实：Finance settlement Current 为 11 条；当前在住为 8 条；照护师结构化生产事实源仍为 0，页面继续明确显示“暂无结构化生产数据”，不生成替代数据。

## 三、事实文件完整性锁

| 文件 | 文件 SHA256 | 大小（bytes） |
| --- | --- | ---: |
| `sales.json` | `d1011bea63ad221a18be42df897eb8a4ebef80eebb488ed72b4643739c2b8ca1` | 325649 |
| `finance.json` | `acbfa29e9da8e8352a3470b3e022b915dd8dd8503e7b92e8ecbbf008cb140ec1` | 3184416 |
| `room.json` | `d826b56c20c8ccecdc5bf5e8a75521ce6e8a964bf1ea906fa600d03087281bd6` | 117556 |
| `stay.json` | `0256d35c2a8362cb4c473ea80bd0dd00b4020e9b61d19d76222843352479ecde` | 493149 |

快照同时保存四个数据域的 Current `record_id` 清单。首页和分页接口只输出激活快照内的记录。

## 四、生产激活验证

- Production Truth Source：`/var/lib/huangjia-oms/truth_source`
- Snapshot：`/var/lib/huangjia-oms/truth_source/snapshots/TS-20260711-V1.json`
- Active Pointer：`/var/lib/huangjia-oms/truth_source/snapshots/ACTIVE_SNAPSHOT.json`
- Production Release：`/opt/huangjia-oms/releases/p0141-20260711-0058`
- systemd：`huangjia-oms.service = active`
- `/api/oms/home`：HTTP 200，`status=ready`
- 首页快照：`TS-20260711-V1 / PASS`
- 首页 Health Score：`96.0`
- 首页 Current：在住 8，房态 42

## 五、版本更新规则

1. Excel 或事实源发生变化时，生成新的 `TS-YYYYMMDD-Vn`，禁止覆盖 `TS-20260711-V1`。
2. 新版本必须重新完成数量、唯一 ID、追溯链、Quarantine 和异常校验。
3. 只有新快照为 PASS 时，才允许更新 Active Pointer。
4. 激活快照对应的任一事实文件 SHA256 不一致时，完整性状态立即变为 FAIL，旧快照不再作为当前生产数据输出。
5. 历史快照和历史事实版本保留，用于证明老板在任一时间点看到的数据版本。

## 六、下一验收门

`PENDING_DQ_SNAPSHOT` 已关闭。下一步仅进入飞书正式入口实机验收；本报告不代表飞书入口已经验收。
