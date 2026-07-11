from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .audit_log import AuditEngine
from .master_data import OMSMasterData
from .operating_center_source import OPERATING_CENTER_PEOPLE, feishu_identity_bindings


EMP_WORKSPACE_KEYS = {
    "EMP001": "boss",
    "EMP002": "songxue",
    "EMP003": "zhangjie",
    "EMP004": "liujie",
    "EMP005": "yaowei",
    "EMP006": "huanhuan",
    "EMP007": "yuchun",
    "EMP008": "june",
    "EMP009": "nana",
    "EMP010": "chenchangyi",
    "EMP011": "zhouchen",
}


@dataclass(frozen=True)
class IdentityConsistencyRow:
    emp_id: str
    user_id: str
    feishu_name: str
    master_name: str
    mapping_name: str
    permission_name: str
    workspace_name: str
    audit_name: str
    role_code: str
    workspace_key: str
    responsibility_scope: str
    status: str
    conflicts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IdentityConsistencyChecker:
    """Validate the active 11-person identity chain against Feishu production identity."""

    def __init__(
        self,
        *,
        master_data: OMSMasterData | None = None,
        audit: AuditEngine | None = None,
        live_root: str | Path | None = None,
    ):
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine()
        self.live_root = live_root

    def check(self, *, write_audit: bool = False) -> dict[str, Any]:
        employees = {employee.emp: employee for employee in self.master_data.active_employees()}
        permissions = self.master_data.role_permissions()
        bindings = feishu_identity_bindings(live_root=self.live_root)
        rows: list[IdentityConsistencyRow] = []

        for emp_id, workspace_key in EMP_WORKSPACE_KEYS.items():
            employee = employees.get(emp_id)
            person = OPERATING_CENTER_PEOPLE.get(workspace_key, {})
            binding = bindings.get(workspace_key, {})
            feishu_name = employee.feishu_name if employee else ""
            master_name = employee.name if employee else ""
            mapping_name = str(binding.get("name") or "")
            permission_name = master_name if master_name in permissions else ""
            workspace_name = str(person.get("name") or "")
            role_code = employee.role_code if employee else ""
            user_id = employee.user_id if employee else ""
            conflicts: list[str] = []

            expected = feishu_name
            for surface, value in (
                ("master_data", master_name),
                ("identity_mapping", mapping_name),
                ("permission_system", permission_name),
                ("workspace_display", workspace_name),
            ):
                if not expected or value != expected:
                    conflicts.append(f"{surface}:{value or 'MISSING'}")
            if not user_id or str(binding.get("user_id") or "") != user_id:
                conflicts.append("feishu_user_id:MISMATCH")
            if not role_code:
                conflicts.append("role_code:MISSING")

            audit_name = expected if write_audit and not conflicts else ""
            status = "PASS" if not conflicts else "FAIL"
            if write_audit:
                self.audit.record(
                    emp_id=emp_id,
                    actor_name=expected or master_name or emp_id,
                    module="identity",
                    action="identity.consistency.checked",
                    reason="P0.13.4 Feishu production identity consistency validation",
                    result=status,
                    target_type="human_identity",
                    target_id=emp_id,
                    source="feishu_production_master_data",
                    metadata={
                        "workspace_key": workspace_key,
                        "role_code": role_code,
                        "user_id": user_id,
                        "conflicts": conflicts,
                    },
                )

            rows.append(
                IdentityConsistencyRow(
                    emp_id=emp_id,
                    user_id=user_id,
                    feishu_name=feishu_name,
                    master_name=master_name,
                    mapping_name=mapping_name,
                    permission_name=permission_name,
                    workspace_name=workspace_name,
                    audit_name=audit_name,
                    role_code=role_code,
                    workspace_key=workspace_key,
                    responsibility_scope="global" if role_code == "ROLE_OWNER" else "own_workspace",
                    status=status,
                    conflicts=tuple(conflicts),
                )
            )

        conflicts = [row.to_dict() for row in rows if row.status != "PASS"]
        return {
            "schema_version": "oms.v1.identity_consistency",
            "source_of_truth": "Feishu production identity",
            "required_count": len(EMP_WORKSPACE_KEYS),
            "pass_count": len(rows) - len(conflicts),
            "conflict_count": len(conflicts),
            "status": "PASS" if not conflicts and len(rows) == 11 else "FAIL",
            "rows": [row.to_dict() for row in rows],
            "identity_conflicts": conflicts,
        }
