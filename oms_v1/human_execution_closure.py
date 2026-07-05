from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .business_event_engine import BusinessEventEngine
from .feishu_mapping import DEFAULT_ENV_PATH
from .human_identity import HumanIdentityLayer
from .live_connector import DEFAULT_LIVE_ROOT
from .operating_center_source import OPERATING_CENTER_PEOPLE, OPERATING_CENTER_VERSION, feishu_identity_bindings
from .schemas import now_iso


CORE_EXECUTION_WORKSPACES = tuple(OPERATING_CENTER_PEOPLE)


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
        human_identity_table = HumanIdentityLayer(self.live_root).rebuild(apply_to_mapping=True)
        env_values = self._identity_env_values()
        mapping = self._mapping_rows(env_values)
        missing = [row for row in mapping if not row["feishu_user_id"]]

        rebuild = BusinessEventEngine(self.live_root, self.operating_root).rebuild_from_saved_state()
        workflow_tasks = self._read_jsonl(self.live_root / "business_events" / "workflow_distribution.jsonl")
        hr_items = self._read_jsonl(self.live_root / "hr_flow" / "hr_execution_items.jsonl")
        unassigned_tasks = [item for item in workflow_tasks if not item.get("assigned_user_id")]
        unassigned_hr = [item for item in hr_items if not item.get("executor_user_id")]
        complete = not missing and not unassigned_tasks and not unassigned_hr
        result = {
            "schema_version": "oms.v1.human_execution_closure",
            "created_at": now_iso(),
            "source_of_truth": "FEISHU_ORG_USERS realworld mapping",
            "people_model_source": OPERATING_CENTER_VERSION,
            "human_identity_layer": {
                "schema_version": human_identity_table["schema_version"],
                "path": str(self.live_root / "human_identity" / "human_identity_table.json"),
                "mapped_identity_count": human_identity_table["summary"]["mapped_identity_count"],
                "missing_identity_count": human_identity_table["summary"]["missing_identity_count"],
                "inferred_role_mapping_count": human_identity_table["summary"]["inferred_role_mapping_count"],
            },
            "identity_enrichment_layer": human_identity_table["identity_enrichment_layer"],
            "closure_status": "complete" if complete else "blocked",
            "mapping_status": "complete" if not missing else "missing_required_user_id",
            "required_workspaces": list(CORE_EXECUTION_WORKSPACES),
            "identity_mapping": mapping,
            "missing_env_keys": [row["env_key"] for row in missing],
            "missing_workspace_keys": [row["workspace_key"] for row in missing],
            "business_event_flow": rebuild,
            "workflow_task_count": len(workflow_tasks),
            "hr_execution_item_count": len(hr_items),
            "assigned_workflow_task_count": len(workflow_tasks) - len(unassigned_tasks),
            "assigned_hr_execution_count": len(hr_items) - len(unassigned_hr),
            "unassigned_workflow_task_count": len(unassigned_tasks),
            "unassigned_hr_execution_count": len(unassigned_hr),
            "human_execution_rate": round((len(hr_items) - len(unassigned_hr)) / len(hr_items), 4) if hr_items else 0,
            "metadata_enrichment_status": (
                "complete"
                if human_identity_table["identity_enrichment_layer"]["summary"]["metadata_missing_count"] == 0
                else "partial"
            ),
            "policy": {
                "missing_required_user_id_allowed": False,
                "fallback_assignment_allowed": False,
                "group_only_assignment_allowed": False,
                "metadata_missing_blocks_execution": False,
                "identity_incomplete_handling": "enrich_and_mark_confidence",
            },
        }
        if missing:
            result["blocking_reason"] = "Some workflow execution paths still need real Feishu user_id values; metadata is enriched and no longer blocks execution."
            result["next_required_action"] = "Provide a real Feishu user_id evidence source for the remaining workspaces, then rerun human-execution."
        self._write_audit(result)
        return result

    def _blocked_result(self, mapping: list[dict[str, Any]], missing: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "schema_version": "oms.v1.human_execution_closure",
            "created_at": now_iso(),
            "source_of_truth": "FEISHU_ORG_USERS realworld mapping",
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
            "blocking_reason": "Required Feishu user_id values are not available from FEISHU_ORG_USERS realworld mapping.",
            "next_required_action": "Expose the missing users through Feishu organization user APIs, then rerun human-execution.",
            "policy": {
                "missing_required_user_id_allowed": False,
                "fallback_assignment_allowed": False,
                "group_only_assignment_allowed": False,
            },
        }

    def _identity_env_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for workspace_key, identity in feishu_identity_bindings(live_root=self.live_root).items():
            person = OPERATING_CENTER_PEOPLE[workspace_key]
            if identity.get("user_id"):
                values[person["feishu_env"]] = identity["user_id"]
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
