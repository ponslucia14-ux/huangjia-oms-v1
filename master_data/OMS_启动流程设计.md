# OMS 启动流程设计

## 目标

OMS Bootstrap 是系统统一启动引导层，只负责初始化、检查、注册和输出状态，不处理业务数据。

## 启动顺序

1. 读取 Master Data 配置。
2. 加载 OMS 组织主数据。
3. 加载飞书身份映射。
4. 初始化权限注册表。
5. 初始化 Governance Engine。
6. 初始化 Execution Engine。
7. 执行 OMS Health Check；默认离线检查，只有显式 `--require-feishu-api` 时同步探测飞书 API。
8. 输出启动摘要。

## 边界

- 不进入销售模块。
- 不进入财务模块。
- 不解析业务输入。
- 不生成执行动作。
- 不写入业务数据。

## 启动命令

```powershell
python -m oms_v1.bootstrap
```

需要完整飞书接口启动校验时使用：

```powershell
python -m oms_v1.bootstrap --require-feishu-api
```

## Ready 标准

所有启动组件状态为 OK，Health Check 结果允许启动时，OMS 输出 `OMS Ready.`。
