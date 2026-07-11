# Cutover首次业务动作确认表

## 一、确认状态

本表确认Cutover时每个Current由谁产生、谁复核以及什么事件代表完成。责任绑定依据OMS Master Data和生产数据责任矩阵。

当前仅完成责任与动作定义；员工实际确认和执行必须在Cutover前后按表记录。

## 二、四域首次动作

| Domain | 创建/确认人 | 复核人 | 首次业务动作 | 完成事件 | 权限要求 | 当前状态 |
| --- | --- | --- | --- | --- | --- | --- |
| Sales Current | EMP006 杨欢欢 | EMP003 张敬东（重大金额） | 在OMS确认或创建首条真实合同及收款状态 | `sales.current.published` | ROLE_SALES责任范围；重大金额复核 | RESPONSIBILITY_CONFIRMED / EMP_ACK_PENDING |
| Finance Current | EMP004 刘晶 | EMP003 张敬东 | 在OMS录入期初资金状态或首笔真实财务业务 | `finance.current.published` | ROLE_CASHIER创建；ROLE_ACCOUNTANT复核 | RESPONSIBILITY_CONFIRMED / EMP_ACK_PENDING |
| Room Current | EMP008 刘芳羽 | EMP009 尚丽娜核对资料 | 在OMS逐房确认42间房Cutover状态 | `room.current.published` | ROLE_STORE_MANAGER发布 | RESPONSIBILITY_CONFIRMED / EMP_ACK_PENDING |
| Actual Stay Current | EMP008 刘芳羽 | EMP009 尚丽娜核对资料 | 在OMS办理或确认首条真实入住 | `stay.actual.published` | ROLE_STORE_MANAGER发布 | RESPONSIBILITY_CONFIRMED / EMP_ACK_PENDING |

## 三、签认字段

每个Domain在Cutover前必须补齐：

- `actor_emp_id`
- `actor_feishu_user_id`
- `actor_name`
- `role_code`
- `workspace`
- `acknowledged_at`
- `first_action_window`
- `backup_operator_emp_id`
- `approver_emp_id`
- `status`

状态：`PENDING_ACK / ACKNOWLEDGED / EXECUTED / FAILED`。

## 四、共同规则

1. 查看动作不能生成Current。
2. 创建、修改、审核和发布必须分离。
3. 所有写入必须经过权限校验并记录reason。
4. 所有首次Current必须关联Cutover ID、Audit和Event。
5. 无责任人不得由EMP001石磊或其他员工临时代录。
6. 失败后由原责任人重试，不允许Excel覆盖Current。

## 五、EMP001石磊批准

| 项目 | 状态 |
| --- | --- |
| 责任绑定 | CONFIRMED_BY_MASTER_DATA |
| EMP本人确认 | PENDING |
| Cutover Date | NOT SET |
| EMP001批准 | PENDING |

本表未执行任何业务动作，未生成Current。
