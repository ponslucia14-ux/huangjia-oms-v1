from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .execution_engine import ExecutionEngine
from .governance_engine import GovernanceEngine
from .health_check import OMSHealthChecker
from .master_data import OMSMasterData


DEFAULT_BOOTSTRAP_DOC = Path(__file__).resolve().parents[1] / "master_data" / "OMS_启动流程设计.md"


@dataclass(frozen=True)
class BootstrapStep:
    name: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


class PermissionEngine:
    """Startup-only permission registry backed by OMS Master Data."""

    def __init__(self, master_data: OMSMasterData):
        self.master_data = master_data
        self.permissions = master_data.role_permissions()

    def ready(self) -> bool:
        return bool(self.permissions)


class OMSBootstrap:
    """Initialize OMS infrastructure without entering any business module."""

    def __init__(self, *, require_feishu_api: bool = False):
        self.require_feishu_api = require_feishu_api
        self.master_data: OMSMasterData | None = None
        self.permission_engine: PermissionEngine | None = None
        self.governance_engine: GovernanceEngine | None = None
        self.execution_engine: ExecutionEngine | None = None

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        steps: list[BootstrapStep] = []
        health_result: dict[str, Any] | None = None

        try:
            config_path = OMSMasterData().config_path
            config = OMSMasterData._read_config(config_path)
            steps.append(BootstrapStep("Config", "OK", str(config_path) if config else "Config file not found; environment/default paths may be used."))

            self.master_data = OMSMasterData()
            employees = self.master_data.employees()
            steps.append(BootstrapStep("Master Data", "OK", f"{len(employees)} employees loaded."))

            identity_rows = self.master_data.feishu_identity_rows()
            mapped = sum(1 for row in identity_rows if row.get("user_id"))
            steps.append(BootstrapStep("Feishu Identity", "OK", f"{mapped}/{len(identity_rows)} user_id mapped."))

            self.permission_engine = PermissionEngine(self.master_data)
            if not self.permission_engine.ready():
                raise RuntimeError("Permission registry is empty.")
            steps.append(BootstrapStep("Permission Engine", "OK", f"{len(self.permission_engine.permissions)} permission subjects registered."))

            self.governance_engine = GovernanceEngine(self.master_data)
            steps.append(BootstrapStep("Governance Engine", "OK", self.governance_engine.__class__.__name__))

            self.execution_engine = ExecutionEngine(self.master_data)
            steps.append(BootstrapStep("Execution Engine", "OK", self.execution_engine.__class__.__name__))

            checker = OMSHealthChecker(
                master_data=self.master_data,
                require_feishu_api=self.require_feishu_api,
                probe_feishu_api=self.require_feishu_api,
            )
            health_result = checker.run()
            health_status = "PASS" if health_result["startup_allowed"] else "FAIL"
            steps.append(
                BootstrapStep(
                    "Health Check",
                    health_status,
                    f"pass={health_result['counts']['pass']} warning={health_result['counts']['warning']} fail={health_result['counts']['fail']}",
                )
            )
        except Exception as exc:
            steps.append(BootstrapStep("Bootstrap", "FAIL", str(exc)))

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        ready = bool(steps and all(step.status in {"OK", "PASS"} for step in steps))
        return {
            "schema_version": "oms.v1.bootstrap",
            "ready": ready,
            "status": "OMS Ready." if ready else "OMS Not Ready.",
            "elapsed_ms": elapsed_ms,
            "steps": [step.to_dict() for step in steps],
            "health_check": health_result,
            "scope": {
                "business_logic_executed": False,
                "sales_module_entered": False,
                "finance_module_entered": False,
                "startup_only": True,
            },
        }

    def render_summary(self, result: dict[str, Any]) -> str:
        lines = [
            "===================================",
            "OMS V1 Bootstrap",
            "",
        ]
        for step in result["steps"]:
            lines.append(f"{step['name']:<22} {step['status']}")
        lines.extend(
            [
                "",
                f"Elapsed .............. {result['elapsed_ms']} ms",
                result["status"],
                "===================================",
            ]
        )
        return "\n".join(lines)


def write_design_doc(path: str | Path = DEFAULT_BOOTSTRAP_DOC) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(
            [
                "# OMS 启动流程设计",
                "",
                "## 目标",
                "",
                "OMS Bootstrap 是系统统一启动引导层，只负责初始化、检查、注册和输出状态，不处理业务数据。",
                "",
                "## 启动顺序",
                "",
                "1. 读取 Master Data 配置。",
                "2. 加载 OMS 组织主数据。",
                "3. 加载飞书身份映射。",
                "4. 初始化权限注册表。",
                "5. 初始化 Governance Engine。",
                "6. 初始化 Execution Engine。",
                "7. 执行 OMS Health Check；默认离线检查，只有显式 `--require-feishu-api` 时同步探测飞书 API。",
                "8. 输出启动摘要。",
                "",
                "## 边界",
                "",
                "- 不进入销售模块。",
                "- 不进入财务模块。",
                "- 不解析业务输入。",
                "- 不生成执行动作。",
                "- 不写入业务数据。",
                "",
                "## 启动命令",
                "",
                "```powershell",
                "python -m oms_v1.bootstrap",
                "```",
                "",
                "需要完整飞书接口启动校验时使用：",
                "",
                "```powershell",
                "python -m oms_v1.bootstrap --require-feishu-api",
                "```",
                "",
                "## Ready 标准",
                "",
                "所有启动组件状态为 OK，Health Check 结果允许启动时，OMS 输出 `OMS Ready.`。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m oms_v1.bootstrap", description="Initialize OMS V1 infrastructure.")
    parser.add_argument("--json", action="store_true", help="Print JSON bootstrap result.")
    parser.add_argument("--require-feishu-api", action="store_true", help="Run realtime Feishu API checks and treat failures as startup blockers.")
    parser.add_argument("--write-design-doc", action="store_true", help="Write OMS_启动流程设计.md.")
    args = parser.parse_args(argv)

    if args.write_design_doc:
        write_design_doc()

    bootstrap = OMSBootstrap(require_feishu_api=args.require_feishu_api)
    result = bootstrap.run()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(bootstrap.render_summary(result))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
