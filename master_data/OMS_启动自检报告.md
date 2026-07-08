# OMS 启动自检报告

Generated At: 2026-07-08T16:30:01+08:00
Startup Allowed: 是
Pass: 9
Warning: 1
Fail: 0

## 检查项清单

| Code | 检查项 | 状态 | 级别 | 是否阻塞启动 | 说明 |
|------|--------|------|------|--------------|------|
| organization_master_data_exists | 组织主数据是否存在 | pass | info | 否 | D:\凰家大脑\brain\03_organization\oms\OMS_组织主数据.md |
| feishu_identity_mapping_exists | 飞书身份映射是否存在 | pass | info | 否 | D:\凰家大脑\brain\03_organization\oms\OMS_飞书身份映射.md |
| master_data_readable | Master Data 是否可被正常读取 | pass | info | 否 | Master Data 读取成功，员工记录 11 条。 |
| official_employee_count | 11 名正式员工是否齐全 | pass | info | 否 | 11 名正式员工齐全。 |
| duplicate_emp | EMP 是否重复 | pass | info | 否 | EMP 无重复。 |
| duplicate_user_id | user_id 是否重复 | pass | info | 否 | user_id 无重复。 |
| open_union_id_presence | open_id / union_id 是否缺失 | pass | info | 否 | open_id 与 union_id 均已填写。 |
| forbidden_terms_absent | 禁用昵称是否残留 | pass | info | 否 | 未发现禁用昵称残留。 |
| role_coverage | 权限角色是否齐全 | pass | info | 否 | 系统角色与关键权限映射齐全。 |
| feishu_api_permission_status | 飞书接口权限是否存在非阻塞或阻塞问题 | warning | warning | 否 | 飞书 API 探测存在问题：[{"target": "approvals", "endpoint": "https://open.feishu.cn/open-apis/approval/v4/approvals", "status_code": 400, "error": "{\"code\": 99991663, \"msg\": \"Invalid access token for authorization. Please make a request with token attached.\", \"error\": {\"message\": \"Refer to the documentation to fix the error: https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-fix-99991663-error\", \"log_id\": \"20260708162959ADCA453D2E20D74D18A2\", \"troubleshooter\": \"排查建议查看(Troubleshooting suggestions): https://open.feishu.cn/search?from=openapi&log_id=20260708162959ADCA453D2E20D74D18A2&code=99991663&method_id=7143131115984814081\"}}"}] |

## 启动结论

OMS 可启动。

## 命令行检查

```powershell
python -m oms_v1.health_check
```
