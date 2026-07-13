from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .feishu_mapping import FeishuObjectSyncer
from .master_data import OMSMasterData
from .schemas import now_iso


DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[1] / "master_data" / "OMS_启动自检报告.md"
REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_EMP_IDS = {f"EMP{index:03d}" for index in range(1, 12)}
EXPECTED_ROLE_CODES = {
    "ROLE_OWNER",
    "ROLE_HR",
    "ROLE_ACCOUNTANT",
    "ROLE_CASHIER",
    "ROLE_ADMIN",
    "ROLE_SALES",
    "ROLE_STORE_MANAGER",
    "ROLE_BUTLER",
    "ROLE_NURSING_DIRECTOR",
    "ROLE_KITCHEN_DIRECTOR",
}
FORBIDDEN_TERMS = [
    "\u7ef4\u7ef4",
    "\u516d\u6708",
    "\u5a1c\u5a1c",
    "\u5c1a\u96e8\u5a1c",
    "\u5f20\u59d0",
    "\u5218\u59d0",
    "\u5468\u53a8",
    "\u5468\u5fd7\u660e",
    "\u0042\u004f\u0053\u0053",
]


@dataclass(frozen=True)
class HealthItem:
    code: str
    title: str
    status: str
    severity: str
    detail: str
    blocks_startup: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "status": self.status,
            "severity": self.severity,
            "detail": self.detail,
            "blocks_startup": self.blocks_startup,
        }


class OMSHealthChecker:
    """Run startup checks for OMS Master Data and Feishu identity readiness."""

    def __init__(
        self,
        *,
        master_data: OMSMasterData | None = None,
        repo_root: str | Path | None = None,
        require_feishu_api: bool = False,
        probe_feishu_api: bool = True,
    ):
        self.master_data = master_data or OMSMasterData()
        self.repo_root = Path(repo_root or REPO_ROOT)
        self.require_feishu_api = require_feishu_api
        self.probe_feishu_api = probe_feishu_api

    def run(self) -> dict[str, Any]:
        items: list[HealthItem] = []
        employees = []

        items.append(self._path_exists("organization_master_data_exists", "组织主数据是否存在", self.master_data.organization_path))
        items.append(self._path_exists("feishu_identity_mapping_exists", "飞书身份映射是否存在", self.master_data.feishu_identity_path))

        try:
            employees = self.master_data.employees()
            items.append(
                HealthItem(
                    "master_data_readable",
                    "Master Data 是否可被正常读取",
                    "pass",
                    "info",
                    f"Master Data 读取成功，员工记录 {len(employees)} 条。",
                )
            )
        except Exception as exc:
            items.append(
                HealthItem(
                    "master_data_readable",
                    "Master Data 是否可被正常读取",
                    "fail",
                    "critical",
                    f"Master Data 读取失败：{exc}",
                    True,
                )
            )
            return self._summary(items)

        items.extend(
            [
                self._employee_count(employees),
                self._duplicate_values("duplicate_emp", "EMP 是否重复", [employee.emp for employee in employees], "EMP"),
                self._duplicate_values("duplicate_user_id", "user_id 是否重复", [employee.user_id for employee in employees], "user_id"),
                self._missing_identity_fields(employees),
                self._forbidden_terms(),
                self._role_coverage(employees),
                self._feishu_api_permissions(),
            ]
        )
        return self._summary(items)

    def write_report(self, result: dict[str, Any], report_path: str | Path | None = None) -> Path:
        path = Path(report_path or DEFAULT_REPORT_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render_markdown(result), encoding="utf-8")
        return path

    def render_markdown(self, result: dict[str, Any]) -> str:
        rows = result["items"]
        lines = [
            "# OMS 启动自检报告",
            "",
            f"Generated At: {result['generated_at']}",
            f"Startup Allowed: {'是' if result['startup_allowed'] else '否'}",
            f"Pass: {result['counts']['pass']}",
            f"Warning: {result['counts']['warning']}",
            f"Fail: {result['counts']['fail']}",
            "",
            "## 检查项清单",
            "",
            "| Code | 检查项 | 状态 | 级别 | 是否阻塞启动 | 说明 |",
            "|------|--------|------|------|--------------|------|",
        ]
        for item in rows:
            lines.append(
                "| {code} | {title} | {status} | {severity} | {blocks} | {detail} |".format(
                    code=item["code"],
                    title=item["title"],
                    status=item["status"],
                    severity=item["severity"],
                    blocks="是" if item["blocks_startup"] else "否",
                    detail=str(item["detail"]).replace("|", "/"),
                )
            )
        lines.extend(
            [
                "",
                "## 启动结论",
                "",
                result["startup_decision"],
                "",
                "## 命令行检查",
                "",
                "```powershell",
                "python -m oms_v1.health_check",
                "```",
                "",
            ]
        )
        return "\n".join(lines)

    def _path_exists(self, code: str, title: str, path: Path) -> HealthItem:
        if path.exists():
            return HealthItem(code, title, "pass", "info", str(path))
        return HealthItem(code, title, "fail", "critical", f"文件不存在：{path}", True)

    def _employee_count(self, employees: list[Any]) -> HealthItem:
        actual = {employee.emp for employee in employees}
        missing = sorted(EXPECTED_EMP_IDS - actual)
        extra = sorted(actual - EXPECTED_EMP_IDS)
        if len(employees) == 11 and not missing and not extra:
            return HealthItem("official_employee_count", "11 名正式员工是否齐全", "pass", "info", "11 名正式员工齐全。")
        detail = f"当前 {len(employees)} 人；缺失 {missing or '无'}；额外 {extra or '无'}。"
        return HealthItem("official_employee_count", "11 名正式员工是否齐全", "fail", "critical", detail, True)

    def _duplicate_values(self, code: str, title: str, values: list[str], label: str) -> HealthItem:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for value in [item for item in values if item]:
            if value in seen:
                duplicates.add(value)
            seen.add(value)
        if not duplicates:
            return HealthItem(code, title, "pass", "info", f"{label} 无重复。")
        return HealthItem(code, title, "fail", "critical", f"{label} 重复：{', '.join(sorted(duplicates))}", True)

    def _missing_identity_fields(self, employees: list[Any]) -> HealthItem:
        missing: list[str] = []
        for employee in employees:
            fields = []
            if not employee.open_id:
                fields.append("open_id")
            if not employee.union_id:
                fields.append("union_id")
            if fields:
                missing.append(f"{employee.emp}:{employee.name}:{'/'.join(fields)}")
        if not missing:
            return HealthItem("open_union_id_presence", "open_id / union_id 是否缺失", "pass", "info", "open_id 与 union_id 均已填写。")
        return HealthItem("open_union_id_presence", "open_id / union_id 是否缺失", "warning", "warning", "；".join(missing))

    def _forbidden_terms(self) -> HealthItem:
        findings: list[str] = []
        roots = [
            self.repo_root / "oms_v1",
            self.repo_root / "oms_app",
            self.repo_root / "README.md",
            self.master_data.organization_path,
            self.master_data.feishu_identity_path,
        ]
        for root in roots:
            if root.is_file():
                files = [root]
            elif root.exists():
                files = [path for path in root.rglob("*") if path.is_file() and self._is_text_candidate(path)]
            else:
                continue
            for path in files:
                text = self._read_text(path)
                if text is None:
                    continue
                # “六月排房法”是正式业务名称，不是员工身份昵称。
                identity_text = text.replace("六月排房法", "排房方法").replace("六月排房规则", "排房规则")
                for term in FORBIDDEN_TERMS:
                    if term in identity_text:
                        try:
                            display_path = path.relative_to(self.repo_root)
                        except ValueError:
                            display_path = path
                        findings.append(f"{display_path}:{term}")
        if not findings:
            return HealthItem("forbidden_terms_absent", "禁用昵称是否残留", "pass", "info", "未发现禁用昵称残留。")
        return HealthItem("forbidden_terms_absent", "禁用昵称是否残留", "fail", "critical", "；".join(findings[:50]), True)

    def _role_coverage(self, employees: list[Any]) -> HealthItem:
        roles = {employee.role_code for employee in employees}
        missing = sorted(EXPECTED_ROLE_CODES - roles)
        permissions = self.master_data.role_permissions()
        employees_with_permissions = {employee.name for employee in employees if employee.role_code in {"ROLE_OWNER", "ROLE_STORE_MANAGER", "ROLE_CASHIER", "ROLE_BUTLER", "ROLE_SALES"}}
        missing_permissions = sorted(name for name in employees_with_permissions if name not in permissions)
        if not missing and not missing_permissions:
            return HealthItem("role_coverage", "权限角色是否齐全", "pass", "info", "系统角色与关键权限映射齐全。")
        detail = f"缺失角色 {missing or '无'}；缺失权限映射 {missing_permissions or '无'}。"
        return HealthItem("role_coverage", "权限角色是否齐全", "fail", "critical", detail, True)

    def _feishu_api_permissions(self) -> HealthItem:
        if not self.probe_feishu_api:
            return HealthItem(
                "feishu_api_permission_status",
                "飞书接口权限是否存在非阻塞或阻塞问题",
                "warning",
                "warning",
                "Bootstrap 默认离线启动，已跳过实时飞书 API 探测；运行 python -m oms_v1.health_check 可执行完整检查。",
            )
        syncer = FeishuObjectSyncer(master_data=self.master_data)
        if not syncer.env.get("FEISHU_APP_ID") or not syncer.env.get("FEISHU_APP_SECRET"):
            return HealthItem(
                "feishu_api_permission_status",
                "飞书接口权限是否存在非阻塞或阻塞问题",
                "warning",
                "warning",
                "未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET；启动可继续，但无法执行实时飞书权限探测。",
                self.require_feishu_api,
            )
        snapshot = syncer.fetch_snapshot()
        errors = snapshot.get("sync_errors") or []
        if not errors:
            return HealthItem(
                "feishu_api_permission_status",
                "飞书接口权限是否存在非阻塞或阻塞问题",
                "pass",
                "info",
                "飞书 API 探测成功，未发现权限错误。",
            )
        detail = json.dumps(errors, ensure_ascii=False)
        status = "fail" if self.require_feishu_api else "warning"
        severity = "critical" if self.require_feishu_api else "warning"
        return HealthItem(
            "feishu_api_permission_status",
            "飞书接口权限是否存在非阻塞或阻塞问题",
            status,
            severity,
            f"飞书 API 探测存在问题：{detail}",
            self.require_feishu_api,
        )

    def _summary(self, items: list[HealthItem]) -> dict[str, Any]:
        counts = {
            "pass": sum(1 for item in items if item.status == "pass"),
            "warning": sum(1 for item in items if item.status == "warning"),
            "fail": sum(1 for item in items if item.status == "fail"),
        }
        blockers = [item for item in items if item.blocks_startup and item.status == "fail"]
        startup_allowed = not blockers
        return {
            "schema_version": "oms.v1.startup_health_check",
            "generated_at": now_iso(),
            "startup_allowed": startup_allowed,
            "startup_decision": "OMS 可启动。" if startup_allowed else "OMS 不应启动；存在阻塞性健康检查失败。",
            "counts": counts,
            "items": [item.to_dict() for item in items],
        }

    @staticmethod
    def _is_text_candidate(path: Path) -> bool:
        if path.name == "health_check.py":
            return False
        return path.suffix.lower() in {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".csv", ".js"}

    @staticmethod
    def _read_text(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m oms_v1.health_check", description="Run OMS startup health checks.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Markdown report output path.")
    parser.add_argument("--json", action="store_true", help="Print JSON result instead of a concise summary.")
    parser.add_argument("--require-feishu-api", action="store_true", help="Treat Feishu API permission errors as startup blockers.")
    args = parser.parse_args(argv)

    checker = OMSHealthChecker(require_feishu_api=args.require_feishu_api)
    result = checker.run()
    report_path = checker.write_report(result, args.report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"OMS startup health check: {result['startup_decision']}")
        print(f"pass={result['counts']['pass']} warning={result['counts']['warning']} fail={result['counts']['fail']}")
        print(f"report={report_path}")
    return 0 if result["startup_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
