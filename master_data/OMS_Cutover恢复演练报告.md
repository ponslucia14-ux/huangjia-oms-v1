# OMS Cutover恢复演练报告

演练时间：2026-07-11 16:18（Asia/Shanghai）  
演练方式：生产服务器隔离恢复，不中断当前服务  
结果：`PASS`

## 一、演练范围

- Release恢复
- 受控配置恢复
- Truth Source与Snapshot恢复
- Live Runtime恢复
- 隔离API启动与业务响应验证
- 原生产服务连续性验证

## 二、演练环境

| 项目 | 值 |
| --- | --- |
| 服务器 | `47.243.38.102` |
| 当前release | `/opt/huangjia-oms/releases/p0141-20260711-0058` |
| 生产服务 | `huangjia-oms.service` |
| 生产端口 | `127.0.0.1:8787` |
| 演练端口 | `127.0.0.1:8798` |
| 备份目录 | `/var/backups/huangjia-oms/CUTOVER-DRILL-20260711-161803` |
| 隔离恢复目录 | `/var/tmp/huangjia-oms-restore-20260711-161803` |

## 三、备份内容

| 文件 | 内容 | 大小 | SHA-256 |
| --- | --- | --- | --- |
| `release.tar.gz` | 当前正式release | 约1.1MB | `5c56abf55f1a04f97745f4b61e4092fa775f88c14dfac063595526dc5be9feeb` |
| `oms-api.env` | 受控生产配置 | 712 bytes | `957faeeda3fe9e2abb91b8710e7b251df7561b8f5fbe0b06f21a30ca557041b7` |
| `truth_source.tar.gz` | Truth Source与Snapshot | 约313KB | `3e62d91a674e42488202c4cc3671904400c9e3de3962d70db96455f4b0527166` |
| `live_runtime.tar.gz` | Live Runtime | 约805KB | `9dd698525a46052e3af38d17ffbf8ce0a682d187209d0c7def6ebfdab8ec4ecf` |

配置文件权限保持为`600`，报告不记录任何密钥值。

## 四、恢复验证

### 4.1 Release

从`release.tar.gz`恢复到隔离目录，Python模块可加载，API可启动。

结果：`PASS`。

### 4.2 配置

从备份恢复环境配置，在隔离进程中覆盖Truth Source、Live Runtime和Operating Root指向恢复目录。

结果：`PASS`。

### 4.3 Snapshot

原始与恢复后的`TS-20260711-V1.json` SHA-256一致：

`0cfd7ceed24b52b42e2723898e3e841aa4e5967a167e4b3799ed0600d3a2a4d2`

结果：`PASS`。

### 4.4 API

恢复环境在`127.0.0.1:8798`启动，返回：

```json
{
  "status": "ready",
  "emp_id": "EMP001",
  "workspace": "boss",
  "snapshot": "TS-20260711-V1",
  "resident_count": 8,
  "room_count": 42
}
```

结果：`PASS`。

## 五、生产连续性

演练期间：

- `huangjia-oms.service = active`
- 生产`127.0.0.1:8787`持续返回HTTP 200
- 未重启systemd
- 未修改Nginx
- 未修改生产Snapshot
- 未覆盖生产配置

演练结束后，8798临时进程已停止，端口返回`000`。

结果：`PASS`。

## 六、校验结果

四个备份文件执行`sha256sum -c`全部为`OK`。

```text
release_restore = PASS
config_restore = PASS
snapshot_restore = PASS
runtime_restore = PASS
api_restore = PASS
production_continuity = PASS
```

## 七、保留项

- 备份包保留在服务器`/var/backups/huangjia-oms/CUTOVER-DRILL-20260711-161803`。
- Cutover正式执行前必须基于当时release和最终PASS Snapshot重新生成备份，不能只依赖本次演练包。
- 本次演练证明恢复流程可行，不代表V2数据已准备完成。

## 八、结论

恢复演练阻塞项关闭。Cutover仍受V2未生成和EMP业务确认未完成阻塞。
