from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_MASTER_DATA_CONFIG = Path(__file__).resolve().parents[1] / "master_data" / "sources.json"


ROLE_LABELS = {
    "ROLE_OWNER": "主理人",
    "ROLE_HR": "HR",
    "ROLE_ACCOUNTANT": "会计",
    "ROLE_CASHIER": "出纳",
    "ROLE_ADMIN": "行政总监",
    "ROLE_SALES": "销售顾问",
    "ROLE_STORE_MANAGER": "店铺总监",
    "ROLE_BUTLER": "管家",
    "ROLE_NURSING_DIRECTOR": "产护总监",
    "ROLE_KITCHEN_DIRECTOR": "料理总监",
}


ROLE_MODULES = {
    "ROLE_OWNER": ["all"],
    "ROLE_STORE_MANAGER": ["room_status_module"],
    "ROLE_CASHIER": ["finance_module"],
    "ROLE_BUTLER": ["service_module"],
    "ROLE_SALES": ["sales_module"],
}


@dataclass(frozen=True)
class Employee:
    emp: str
    name: str
    department: str
    positions: tuple[str, ...]
    role_code: str
    permission_level: str
    feishu_name: str = ""
    user_id: str = ""
    open_id: str = ""
    union_id: str = ""
    status: str = ""
    enabled: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role_code, self.positions[0] if self.positions else self.role_code)

    @property
    def match_terms(self) -> list[str]:
        values = [self.emp, self.name, self.feishu_name, self.department, self.role_code, self.role_label, *self.positions]
        return [value for value in dict.fromkeys(values) if value and value != "--"]


class OMSMasterData:
    """Read OMS organization and identity data from the official master-data files."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        organization_path: str | Path | None = None,
        feishu_identity_path: str | Path | None = None,
    ):
        self.config_path = Path(config_path or os.getenv("OMS_MASTER_DATA_CONFIG") or DEFAULT_MASTER_DATA_CONFIG)
        config = self._read_config(self.config_path)
        self.organization_path = Path(
            organization_path
            or os.getenv("OMS_ORGANIZATION_MASTER_DATA")
            or config.get("organization_master_data", "")
        )
        self.feishu_identity_path = Path(
            feishu_identity_path
            or os.getenv("OMS_FEISHU_IDENTITY_MAPPING_PATH")
            or config.get("feishu_identity_mapping", "")
        )
        self._employees: list[Employee] | None = None

    def employees(self) -> list[Employee]:
        if self._employees is None:
            employees = self._parse_organization()
            self._merge_feishu_identity(employees)
            self._employees = list(employees.values())
        return list(self._employees)

    def active_employees(self) -> list[Employee]:
        return [employee for employee in self.employees() if employee.status in {"", "在职", "Active"}]

    def employee_by_emp(self, emp: str) -> Employee:
        for employee in self.employees():
            if employee.emp == emp:
                return employee
        raise KeyError(f"Unknown EMP: {emp}")

    def employees_by_role(self, role_code: str) -> list[Employee]:
        return [employee for employee in self.employees() if employee.role_code == role_code]

    def employee_by_role(self, role_code: str) -> Employee:
        employees = self.employees_by_role(role_code)
        if not employees:
            raise KeyError(f"Unknown role code: {role_code}")
        return employees[0]

    def names_for_roles(self, role_codes: list[str]) -> list[str]:
        return [self.employee_by_role(role_code).name for role_code in role_codes]

    def final_authority_name(self) -> str:
        return self.employee_by_role("ROLE_OWNER").name

    def role_permissions(self) -> dict[str, dict[str, list[str]]]:
        permissions: dict[str, dict[str, list[str]]] = {}
        for employee in self.employees():
            modules = ROLE_MODULES.get(employee.role_code)
            if not modules:
                continue
            permissions[employee.name] = {
                "execute": modules,
                "approve": modules,
                "override": modules,
            }
        permissions["系统"] = {"execute": ["low_risk_automation"], "approve": [], "override": []}
        return permissions

    def module_owner(self, target_module: str) -> str:
        for employee in self.employees():
            if target_module in ROLE_MODULES.get(employee.role_code, []):
                return employee.name
        return self.final_authority_name()

    def feishu_identity_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "emp": employee.emp,
                "name": employee.name,
                "feishu_name": employee.feishu_name or employee.name,
                "role": employee.role_label,
                "role_code": employee.role_code,
                "department": employee.department,
                "job_title": employee.positions[0] if employee.positions else employee.role_label,
                "user_id": employee.user_id,
                "open_id": employee.open_id,
                "union_id": employee.union_id,
                "match_terms": employee.match_terms,
            }
            for employee in self.employees()
        ]

    @staticmethod
    def _read_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _parse_organization(self) -> dict[str, Employee]:
        if not self.organization_path.exists():
            raise FileNotFoundError(f"OMS organization master data not found: {self.organization_path}")
        text = self.organization_path.read_text(encoding="utf-8")
        blocks = re.split(r"\n##\s+", text)
        employees: dict[str, Employee] = {}
        for block in blocks:
            if not block.startswith("EMP"):
                continue
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            emp = lines[0]
            name = self._field_after(lines, "姓名：")
            department = self._field_after(lines, "部门：")
            role_code = self._field_after(lines, "系统角色：")
            permission_level = self._field_after(lines, "权限等级：")
            positions = self._list_after(lines, "岗位：")
            employees[emp] = Employee(
                emp=emp,
                name=name,
                department=department,
                positions=tuple(positions),
                role_code=role_code,
                permission_level=permission_level,
            )
        return employees

    def _merge_feishu_identity(self, employees: dict[str, Employee]) -> None:
        if not self.feishu_identity_path.exists():
            raise FileNotFoundError(f"OMS Feishu identity mapping not found: {self.feishu_identity_path}")
        for line in self.feishu_identity_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| EMP"):
                continue
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) < 14 or parts[0] == "EMP":
                continue
            emp = parts[0]
            if emp not in employees:
                continue
            employee = employees[emp]
            employees[emp] = Employee(
                emp=employee.emp,
                name=employee.name,
                department=employee.department,
                positions=employee.positions,
                role_code=employee.role_code,
                permission_level=employee.permission_level,
                feishu_name=parts[2],
                user_id=parts[6],
                open_id=parts[7],
                union_id=parts[8],
                status=parts[11],
                enabled=parts[12],
                metadata={"work_email": parts[9], "mobile": parts[10], "start_date": parts[13]},
            )

    @staticmethod
    def _field_after(lines: list[str], marker: str) -> str:
        for index, line in enumerate(lines):
            if line == marker and index + 1 < len(lines):
                return lines[index + 1]
            if line.startswith(marker):
                return line.removeprefix(marker).strip()
        return ""

    @staticmethod
    def _list_after(lines: list[str], marker: str) -> list[str]:
        values: list[str] = []
        for index, line in enumerate(lines):
            if line != marker:
                continue
            for next_line in lines[index + 1 :]:
                if next_line.endswith("：") or next_line.startswith("ROLE_") or next_line.startswith("LEVEL_"):
                    break
                if next_line.startswith("- "):
                    values.append(next_line[2:].strip())
                elif next_line:
                    values.append(next_line)
            break
        return values
