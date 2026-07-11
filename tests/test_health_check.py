import tempfile
import unittest
from pathlib import Path

from oms_v1.health_check import HealthItem, OMSHealthChecker
from oms_v1.master_data import OMSMasterData


EMPLOYEES = [
    ("EMP001", "石磊", "主理办", "主理人", "ROLE_OWNER", "LEVEL_0"),
    ("EMP002", "宗惠", "人力资源部", "HR", "ROLE_HR", "LEVEL_2"),
    ("EMP003", "张敬东", "财务部", "会计", "ROLE_ACCOUNTANT", "LEVEL_1"),
    ("EMP004", "刘晶", "财务部", "出纳", "ROLE_CASHIER", "LEVEL_3"),
    ("EMP005", "石昊盺", "行政部", "行政总监", "ROLE_ADMIN", "LEVEL_3"),
    ("EMP006", "杨欢欢", "市场销售部", "销售顾问", "ROLE_SALES", "LEVEL_3"),
    ("EMP007", "薛子渝", "市场销售部", "销售顾问", "ROLE_SALES", "LEVEL_3"),
    ("EMP008", "刘芳羽", "店总办公室", "店铺总监", "ROLE_STORE_MANAGER", "LEVEL_1"),
    ("EMP009", "尚丽娜", "店总办公室", "管家", "ROLE_BUTLER", "LEVEL_3"),
    ("EMP010", "陈晶辉", "产护部", "产护总监", "ROLE_NURSING_DIRECTOR", "LEVEL_2"),
    ("EMP011", "周志朋", "料理部", "料理总监", "ROLE_KITCHEN_DIRECTOR", "LEVEL_2"),
]


def write_organization(path: Path) -> None:
    blocks = ["# OMS 组织主数据"]
    for emp, name, department, position, role, level in EMPLOYEES:
        blocks.append(
            f"""
## {emp}

姓名：

{name}

部门：

{department}

岗位：

- {position}

系统角色：

{role}

权限等级：

{level}
""".strip()
        )
    path.write_text("\n\n---\n\n".join(blocks), encoding="utf-8")


def write_identity(path: Path, *, duplicate_user_id: bool = False) -> None:
    lines = [
        "| EMP | OMS 正式姓名 | 飞书名称 | 系统角色 | Department | Job Title | user_id | open_id | union_id | 工作邮箱 | 手机号 | Employee Status | 是否启用 | 入职日期 / 创建时间 |",
        "|------|--------------|----------|----------|------------|-----------|---------|---------|----------|----------|--------|-----------------|----------|--------------------|",
    ]
    for index, (emp, name, department, position, role, _level) in enumerate(EMPLOYEES, start=1):
        user_id = "duplicate_user" if duplicate_user_id and index in {1, 2} else f"user_{index:03d}"
        lines.append(
            f"| {emp} | {name} | {name} | {role} | {department} | {position} | {user_id} | open_{index:03d} | union_{index:03d} | -- | -- | 在职 | 是 | 2026-07-08 |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


class HealthCheckTests(unittest.TestCase):
    def _checker(self, tmp: str, *, duplicate_user_id: bool = False) -> OMSHealthChecker:
        root = Path(tmp)
        organization_path = root / "OMS_组织主数据.md"
        identity_path = root / "OMS_飞书身份映射.md"
        repo_root = root / "repo"
        (repo_root / "oms_v1").mkdir(parents=True)
        (repo_root / "tests").mkdir()
        (repo_root / "master_data").mkdir()
        (repo_root / "README.md").write_text("OMS V1\n", encoding="utf-8")
        (repo_root / "oms_v1" / "placeholder.py").write_text("name = '石磊'\n", encoding="utf-8")
        write_organization(organization_path)
        write_identity(identity_path, duplicate_user_id=duplicate_user_id)
        master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        checker = OMSHealthChecker(master_data=master_data, repo_root=repo_root)
        checker._feishu_api_permissions = lambda: HealthItem(
            "feishu_api_permission_status",
            "飞书接口权限是否存在非阻塞或阻塞问题",
            "pass",
            "info",
            "test",
        )
        return checker

    def test_health_check_passes_for_complete_master_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._checker(tmp).run()

            self.assertTrue(result["startup_allowed"])
            self.assertEqual(result["counts"]["fail"], 0)
            self.assertEqual(result["counts"]["pass"], 10)

    def test_duplicate_user_id_blocks_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._checker(tmp, duplicate_user_id=True).run()
            duplicate_check = {item["code"]: item for item in result["items"]}["duplicate_user_id"]

            self.assertFalse(result["startup_allowed"])
            self.assertEqual(duplicate_check["status"], "fail")
            self.assertTrue(duplicate_check["blocks_startup"])

    def test_writes_markdown_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            checker = self._checker(tmp)
            result = checker.run()
            report_path = Path(tmp) / "OMS_启动自检报告.md"

            checker.write_report(result, report_path)

            text = report_path.read_text(encoding="utf-8")
            self.assertIn("# OMS 启动自检报告", text)
            self.assertIn("python -m oms_v1.health_check", text)


if __name__ == "__main__":
    unittest.main()
