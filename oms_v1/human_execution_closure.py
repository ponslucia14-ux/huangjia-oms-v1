from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .business_event_engine import BusinessEventEngine
from .feishu_mapping import DEFAULT_ENV_PATH
from .live_connector import DEFAULT_LIVE_ROOT
from .operating_center_source import OPERATING_CENTER_PEOPLE, OPERATING_CENTER_VERSION
from .schemas import now_iso


CORE_EXECUTION_WORKSPACES = ("boss", "huanhuan", "june", "liujie", "nana")


class HumanExecutionClosure:
    """Validate and apply Feishu user_id bindings for human execution closure."""

    def __init__(
        self,
        live_root: str | Path | None = None,
        operating_root: str | Path | None = None,
        env_path: str | Path | None = None,
    ):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")
        self.env_path = Path(env_path or os.getenv("OMS_FEISHU_ENV") or DEFAULT_ENV_PATH)

    def close(self) -> dict[str, Any]:
        env_values = self._identity_env_values()
        mapping = self._mapping_rows(env_values)
        missing = [row for row in mapping if not row["feishu_user_id"]]
        if missing:
            result = self._blocked_result(mapping, missing)
            self._write_audit(result)
            return result

        previous_env = {row["env_key"]: os.environ.get(row["env_key"]) for row in mapping}
        try:
            for row in mapping:
                os.environ[row["env_key"]] = row["feishu_user_id"]
            rebuild = BusinessEventEngine(self.live_root, self.operating_root).rebuild_from_saved_state()
        finally:
            for key, old_value in previous_env.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value
        workflow_tasks = self._read_jsonl(self.live_root / "business_events" / "workflow_distribution.jsonl")
        hr_items = self._read_jsonl(self.live_root / "hr_flow" / "hr_execution_items.jsonl")
        unassigned_tasks = [item for item in workflow_tasks if not item.get("assigned_user_id")]
        unassigned_hr = [item for item in hr_items if not item.get("executor_user_id")]
        complete = not unassigned_tasks and not unassigned_hr
        result = {
            "schema_version": "oms.v1.human_execution_closure",
            "created_at": now_iso(),
            "source_of_truth": "Feishu user_id environment mapping",
            "people_model_source": OPERATING_CENTER_VERSION,
            "closure_status": "complete" if complete else "blocked",
            "mapping_status": "complete",
            "required_workspaces": list(CORE_EXECUTION_WORKSPACES),
            "identity_mapping": mapping,
            "business_event_flow": rebuild,
            "workflow_task_count": len(workflow_tasks),
            "hr_execution_item_count": len(hr_items),
            "assigned_workflow_task_count": len(workflow_tasks) - len(unassigned_tasks),
            "assigned_hr_execution_count": len(hr_items) - len(unassigned_hr),
            "unassigned_workflow_task_count": len(unassigned_tasks),
            "unassigned_hr_execution_count": len(unassigned_hr),
            "human_execution_rate": round((len(hr_items) - len(unassigned_hr)) / len(hr_items), 4) if hr_items else 0,
            "policy": {
                "unresolved_user_id_allowed": False,
                "fallback_assignment_allowed": False,
                "group_only_assignment_allowed": False,
            },
        }
        self._write_audit(result)
        return result

    def _blocked_result(self, mapping: list[dict[str, Any]], missing: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "schema_version": "oms.v1.human_execution_closure",
            "created_at": now_iso(),
            "source_of_truth": "Feishu user_id environment mapping",
            "people_model_source": OPERATING_CENTER_VERSION,
            "closure_status": "blocked",
            "mapping_status": "missing_required_user_id",
            "required_workspaces": list(CORE_EXECUTION_WORKSPACES),
            "identity_mapping": mapping,
            "missing_env_keys": [row["env_key"] for row in missing],
            "missing_workspace_keys": [row["workspace_key"] for row in missing],
            "workflow_task_count": self._count_jsonl(self.live_root / "business_events" / "workflow_distribution.jsonl"),
            "hr_execution_item_count": self._count_jsonl(self.live_root / "hr_flow" / "hr_execution_items.jsonl"),
            "assigned_workflow_task_count": 0,
            "assigned_hr_execution_count": 0,
            "human_execution_rate": 0,
            "blocking_reason": "Required Feishu user_id values are not available from the real Feishu mapping/environment.",
            "next_required_action": "Populate the missing FEISHU_USER_ID_* values from real Feishu login/API output, then rerun human-execution.",
            "policy": {
                "unresolved_user_id_allowed": False,
                "fallback_assignment_allowed": False,
                "group_only_assignment_allowed": False,
            },
        }

    def _identity_env_values(self) -> dict[str, str]:
        values = self._read_env_file(self.env_path)
        for person in OPERATING_CENTER_PEOPLE.values():
            env_key = person["feishu_env"]
            env_value = os.getenv(env_key, "").strip()
            if env_value:
                values[env_key] = env_value
        return values

    def _mapping_rows(self, env_values: dict[str, str]) -> list[dict[str, Any]]:
        rows = []
        for workspace_key in CORE_EXECUTION_WORKSPACES:
            person = OPERATING_CENTER_PEOPLE[workspace_key]
            env_key = person["feishu_env"]
            user_id = env_values.get(env_key, "").strip()
            rows.append(
                {
                    "workspace_key": workspace_key,
                    "name": person["name"],
                    "role": person["role"],
                    "workspace": person["title"],
                    "env_key": env_key,
                    "feishu_user_id": user_id,
                    "binding_status": "mapped" if user_id else "missing",
                }
            )
        return rows

    def _read_env_file(self, path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
        return rows

    def _count_jsonl(self, path: Path) -> int:
        if not path.exists():
            return 0
        return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())

    def _write_audit(self, result: dict[str, Any]) -> None:
        path = self.live_root / "audit" / "human_execution_closure.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
