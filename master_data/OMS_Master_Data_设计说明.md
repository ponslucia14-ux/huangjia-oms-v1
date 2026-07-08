# OMS Master Data 设计说明

Version: 1.0
Status: Production
Owner: 石磊
Executor: 张照南

---

# 一、OMS 主数据包含哪些文件

## 1. OMS_组织主数据.md

路径：

`D:\凰家大脑\brain\03_organization\oms\OMS_组织主数据.md`

职责：

- OMS 唯一组织主数据。
- 维护 EMP 编号、正式姓名、部门、岗位、系统角色、权限等级。
- 所有用户、权限、审批、AI Agent、自动通知、老板驾驶舱都以此为组织来源。

## 2. OMS_飞书身份映射.md

路径：

`D:\凰家大脑\brain\03_organization\oms\OMS_飞书身份映射.md`

职责：

- OMS 唯一飞书身份源。
- 维护 EMP 到 user_id、open_id、union_id 的映射。
- 所有飞书审批、通知、待办、拉群、建群、日报、周报必须通过 user_id 调用。

## 3. master_data/sources.json

路径：

`D:\凰家母婴空间\OMS_V1\master_data\sources.json`

职责：

- 声明 OMS Master Data 的正式来源路径。
- 不复制人员数据。
- 禁止模块本地维护第二份人员名单。

## 4. oms_v1/master_data.py

路径：

`D:\凰家母婴空间\OMS_V1\oms_v1\master_data.py`

职责：

- OMS 统一主数据读取层。
- 解析组织主数据与飞书身份映射。
- 向各模块提供员工、角色、权限、模块负责人、飞书身份等查询能力。

---

# 二、每个文件负责什么

`OMS_组织主数据.md` 只负责组织事实。

包括：

- EMP 编号
- 正式姓名
- 部门
- 岗位
- 系统角色
- 权限等级

`OMS_飞书身份映射.md` 只负责飞书身份。

包括：

- EMP
- 正式姓名
- 飞书显示名称
- user_id
- open_id
- union_id
- 是否启用
- 员工状态

`sources.json` 只负责告诉 OMS 去哪里读正式数据。

`master_data.py` 只负责读取、解析、查询，不负责创造人员数据。

---

# 三、各模块如何引用

所有模块必须通过：

```python
from oms_v1.master_data import OMSMasterData

master_data = OMSMasterData()
```

典型引用方式：

- 用户管理：读取 `master_data.employees()`
- 权限系统：读取 `master_data.role_permissions()`
- 审批流：读取 `master_data.final_authority_name()` 和 `master_data.module_owner(...)`
- 飞书同步：读取 `master_data.feishu_identity_rows()`
- AI Agent：读取 EMP、角色、部门、岗位后分配任务
- 自动通知：通过 EMP 找 user_id，再调用飞书 API

禁止：

- 在模块中写死人员名单
- 在模块中写死 user_id
- 用姓名临时搜索飞书用户
- 在多个 JSON / YAML / Python 文件中维护重复组织数据

---

# 四、未来新增员工、部门、岗位时如何维护

新增员工：

1. 在 `OMS_组织主数据.md` 新增 EMP 编号。
2. 填写正式姓名、部门、岗位、系统角色、权限等级。
3. 在飞书后台创建或确认员工账号。
4. 更新 `OMS_飞书身份映射.md`，补齐 user_id、open_id、union_id。
5. 运行 OMS 测试与主数据扫描。

新增部门：

1. 先在 `OMS_组织主数据.md` 增加部门编码。
2. 再为相关员工修改部门字段。
3. 如涉及权限，更新权限等级或系统角色。
4. OMS 模块不得自行增加部门副本。

新增岗位：

1. 先在 `OMS_组织主数据.md` 增加岗位。
2. 如岗位需要系统权限，新增或调整系统角色。
3. 通过 `OMSMasterData` 暴露给业务模块。

---

# 五、未来新增飞书账号如何同步

新增飞书账号必须按以下顺序：

1. 飞书管理后台创建或启用员工。
2. 确认员工属于正式组织架构。
3. 读取真实 user_id、open_id、union_id。
4. 更新 `OMS_飞书身份映射.md`。
5. OMS 模块通过 `OMSMasterData` 自动读取新身份。

禁止：

- 先在代码里写 user_id
- 用测试 ID 代替正式 ID
- 通过昵称或模糊姓名匹配飞书用户
- 在飞书身份映射之外维护第二份飞书人员表

---

# 六、当前落地状态

已完成：

- 建立 `master_data/` 目录。
- 建立 `sources.json`。
- 建立 `oms_v1/master_data.py`。
- `feishu_mapping.py` 改为读取 Master Data。
- `governance_engine.py` 改为通过 Master Data 获取权限、模块负责人和最终负责人。
- 测试覆盖 Master Data 读取。

当前原则：

OMS 的地基是 Master Data。

业务模块只能引用，不得复制。
