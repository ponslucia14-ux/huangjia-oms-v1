from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .business_event_engine import BusinessEventEngine
from .live_connector import DEFAULT_LIVE_ROOT
from .operating_center_source import (
    OPERATING_CENTER_PEOPLE,
    OPERATING_CENTER_VERSION,
    feishu_identity_bindings,
    workspace_key_for_feishu_identity,
)
from .schemas import now_iso
from .truth_source import TruthSourceStore


CORE_FUSION_SCHEMA_VERSION = "oms.v1.core_fusion"
CORE_FUSION_FLOW = "DATA -> IDENTITY -> WORKFLOW -> WORK_ENTRY -> UI"
BOSS_MASTER_CONTROL_ENTRY_TYPE = "master_control_dashboard"
CORE_FUSION_ENTRY_ITEM_LIMIT = 100


class CoreFusionLayer:
    """Fuse data, identity, workflow, and work entry into one runtime view."""

    def __init__(self, live_root: str | Path | None = None, operating_root: str | Path | None = None):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")
        self.fusion_root = self.live_root / "core_fusion"
        self.truth_store = TruthSourceStore(self.live_root, self.operating_root)

    def rebuild_from_saved_state(self, *, user_id: str | None = None) -> dict[str, Any]:
        business_summary = BusinessEventEngine(self.live_root, self.operating_root).rebuild_from_saved_state()
        identities = self._identity_fusion()
        events = self.truth_store.read_events()
        workflow_tasks = self._read_jsonl(self.live_root / "business_events" / "workflow_distribution.jsonl")
        hr_items = self._read_jsonl(self.live_root / "hr_flow" / "hr_execution_items.jsonl")
        task_by_event = {str(item.get("business_event_id") or ""): item for item in workflow_tasks}
        hr_by_event = {str(item.get("business_event_id") or ""): item for item in hr_items}

        fused_events = [
            self._fused_event(event, task_by_event.get(str(event.get("business_event_id") or ""), {}), hr_by_event.get(str(event.get("business_event_id") or ""), {}), identities)
            for event in events
        ]
        unified_tasks = [
            self._unified_task(event, task_by_event.get(str(event.get("business_event_id") or ""), {}), hr_by_event.get(str(event.get("business_event_id") or ""), {}), identities)
            for event in events
        ]
        validation = self._validation(identities, fused_events, unified_tasks)
        work_entry = self.work_entry_for_user(user_id, unified_tasks=unified_tasks) if user_id else None
        state = {
            "schema_version": CORE_FUSION_SCHEMA_VERSION,
            "created_at": now_iso(),
            "mode": "single_runtime_system",
            "flow": CORE_FUSION_FLOW,
            "source_of_truth": "OMS_TRUTH_SOURCE + FEISHU_ORG_USERS realworld mapping",
            "truth_source": self.truth_store.summary(),
            "people_model_source": OPERATING_CENTER_VERSION,
            "business_event_flow": business_summary,
            "identity_fusion": identities,
            "counts": {
                "business_events": len(fused_events),
                "unified_tasks": len(unified_tasks),
                "mapped_identities": sum(1 for item in identities["workspaces"].values() if item["user_id_status"] == "mapped"),
                "missing_identities": sum(1 for item in identities["workspaces"].values() if item["user_id_status"] != "mapped"),
                "assigned_tasks": sum(1 for item in unified_tasks if item["identity"]["user_id_status"] == "mapped"),
                "pending_identity_tasks": sum(1 for item in unified_tasks if item["identity"]["user_id_status"] != "mapped"),
            },
            "work_entry": work_entry,
            "validation": validation,
            "paths": {
                "identity_fusion": str(self.fusion_root / "identity_fusion.json"),
                "single_business_event_stream": str(self.fusion_root / "single_business_event_stream.jsonl"),
                "unified_task_stream": str(self.fusion_root / "unified_task_stream.jsonl"),
                "core_fusion_state": str(self.fusion_root / "core_fusion_state.json"),
            },
        }
        self._write_state(state, identities, fused_events, unified_tasks)
        return state

    def work_entry_for_user(self, user_id: str | None, *, unified_tasks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        raw_user_id = str(user_id or "").strip()
        workspace_key, identity_source = workspace_key_for_feishu_identity({raw_user_id}, live_root=self.live_root)
        if not raw_user_id or not workspace_key:
            return {
                "entry_status": "blocked",
                "error_type": "identity_binding_required",
                "user_id": raw_user_id,
                "identity_source": identity_source,
                "workspace_key": "",
                "tasks": [],
                "task_count": 0,
            }
        tasks = unified_tasks if unified_tasks is not None else self._read_jsonl(self.fusion_root / "unified_task_stream.jsonl")
        visible = tasks if workspace_key == "boss" else [task for task in tasks if task.get("workspace_key") == workspace_key]
        person = OPERATING_CENTER_PEOPLE[workspace_key]
        if workspace_key == "boss":
            return self._boss_master_control_entry(raw_user_id, identity_source, visible)
        visible_tasks = self._limit_items(visible)
        return {
            "entry_status": "ready",
            "entry_type": "personal_workspace",
            "user_id": raw_user_id,
            "identity_source": identity_source,
            "workspace_key": workspace_key,
            "workspace": person["title"],
            "role": person["role"],
            "name": person["name"],
            "task_count": len(visible),
            "task_visible_count": len(visible_tasks),
            "tasks": visible_tasks,
        }

    def _boss_master_control_entry(self, user_id: str, identity_source: str, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        person = OPERATING_CENTER_PEOPLE["boss"]
        unfinished = [task for task in tasks if task.get("execution_status") != "completed" and task.get("status") != "completed"]
        visible_tasks = self._limit_items(tasks)
        visible_unfinished = self._limit_items(unfinished)
        return {
            "entry_status": "ready",
            "entry_type": BOSS_MASTER_CONTROL_ENTRY_TYPE,
            "control_user_type": "system_level_control_user",
            "user_id": user_id,
            "identity_source": identity_source,
            "workspace_key": "boss",
            "workspace": person["title"],
            "role": person["role"],
            "name": person["name"],
            "task_count": len(tasks),
            "unfinished_task_count": len(unfinished),
            "hierarchy": {
                "layer_1": "BOSS Master Control",
                "layer_2": "Business Workspaces",
                "layer_3": "Execution Layer",
            },
            "permissions": {
                "view_all_user_workspaces": True,
                "view_all_workflows": True,
                "control_task_assignment": True,
                "view_global_risk": True,
            },
            "business_flows": self._business_flow_summary(tasks),
            "workspace_matrix": self._workspace_matrix(tasks),
            "risk_register": self._risk_register(tasks),
            "execution_status": self._execution_status(tasks),
            "unfinished_task_visible_count": len(visible_unfinished),
            "task_visible_count": len(visible_tasks),
            "unfinished_tasks": visible_unfinished,
            "tasks": visible_tasks,
        }

    def _business_flow_summary(self, tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        flow_map = {
            "room_event": ("room_flow", "房态流"),
            "finance_event": ("finance_flow", "财务流"),
            "sales_event": ("sales_flow", "销售流"),
            "service_event": ("service_flow", "服务流"),
            "hr_event": ("hr_flow", "人效流"),
        }
        summary = {
            key: {"label": label, "task_count": 0, "unfinished_count": 0, "risk_count": 0}
            for _, (key, label) in flow_map.items()
        }
        for task in tasks:
            key, label = flow_map.get(str(task.get("event_type") or ""), ("other_flow", "其他流"))
            if key not in summary:
                summary[key] = {"label": label, "task_count": 0, "unfinished_count": 0, "risk_count": 0}
            summary[key]["task_count"] += 1
            if task.get("execution_status") != "completed" and task.get("status") != "completed":
                summary[key]["unfinished_count"] += 1
            if self._is_risk_task(task):
                summary[key]["risk_count"] += 1
        return summary

    def _workspace_matrix(self, tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        matrix: dict[str, dict[str, Any]] = {}
        for workspace_key, person in OPERATING_CENTER_PEOPLE.items():
            workspace_tasks = [task for task in tasks if task.get("workspace_key") == workspace_key]
            matrix[workspace_key] = {
                "name": person["name"],
                "role": person["role"],
                "workspace": person["title"],
                "task_count": len(workspace_tasks),
                "unfinished_count": sum(1 for task in workspace_tasks if task.get("execution_status") != "completed" and task.get("status") != "completed"),
                "risk_count": sum(1 for task in workspace_tasks if self._is_risk_task(task)),
            }
        return matrix

    def _risk_register(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        risk_tasks = [task for task in tasks if self._is_risk_task(task)]
        return {
            "risk_count": len(risk_tasks),
            "pending_identity_count": sum(1 for task in tasks if task.get("identity", {}).get("user_id_status") != "mapped"),
            "blocked_count": sum(1 for task in tasks if task.get("status") in {"blocked", "pending_identity_binding"}),
            "items_total_count": len(risk_tasks),
            "items_visible_count": min(len(risk_tasks), CORE_FUSION_ENTRY_ITEM_LIMIT),
            "items": self._limit_items(risk_tasks),
        }

    def _limit_items(self, items: list[dict[str, Any]], limit: int = CORE_FUSION_ENTRY_ITEM_LIMIT) -> list[dict[str, Any]]:
        if len(items) <= limit:
            return items
        return items[:limit]

    def _execution_status(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for task in tasks:
            status = str(task.get("execution_status") or task.get("status") or "unknown")
            counts[status] = counts.get(status, 0) + 1
        return {
            "total": len(tasks),
            "by_status": counts,
            "completed": counts.get("completed", 0),
            "unfinished": sum(count for status, count in counts.items() if status != "completed"),
        }

    def _is_risk_task(self, task: dict[str, Any]) -> bool:
        return (
            task.get("priority") in {"high", "urgent"}
            or task.get("status") in {"blocked", "attention_required", "pending_identity_binding"}
            or task.get("execution_status") in {"needs_user_binding", "blocked", "attention_required"}
            or task.get("identity", {}).get("user_id_status") != "mapped"
        )

    def _identity_fusion(self) -> dict[str, Any]:
        bindings = feishu_identity_bindings(live_root=self.live_root)
        workspaces: dict[str, dict[str, Any]] = {}
        user_index: dict[str, str] = {}
        for workspace_key, person in OPERATING_CENTER_PEOPLE.items():
            identity = bindings.get(workspace_key, {})
            user_id = str(identity.get("user_id") or "")
            open_id = str(identity.get("open_id") or "")
            item = {
                "workspace_key": workspace_key,
                "user_id": user_id,
                "open_id": open_id,
                "union_id": str(identity.get("union_id") or ""),
                "user_id_status": "mapped" if user_id else "missing_required_user_id",
                "role": person["role"],
                "department": person["unit"],
                "execution_rights": self._execution_rights(workspace_key),
                "workspace": person["title"],
                "name": person["name"],
                "source": identity.get("source") or "feishu_org_users_required",
                "binding_confidence": identity.get("binding_confidence") or "",
                "metadata_status": identity.get("metadata_status") or "enriched",
                "metadata_source": "identity_enrichment_layer" if identity.get("source") == "identity_enrichment_layer" else "operating_center_v1_1",
            }
            workspaces[workspace_key] = item
            for identity_id in [user_id, open_id, item["union_id"]]:
                if identity_id:
                    user_index[identity_id] = workspace_key
        return {
            "schema_version": "oms.v1.identity_fusion",
            "source": "FEISHU_ORG_USERS",
            "policy": {
                "anonymous_execution_allowed": False,
                "fallback_identity_allowed": False,
                "group_inferred_user_allowed": False,
                "user_id_required_for_execution": True,
                "metadata_missing_blocks_execution": False,
            },
            "workspaces": workspaces,
            "user_index": user_index,
        }

    def _execution_rights(self, workspace_key: str) -> dict[str, Any]:
        return {
            "scope": "global_oversight" if workspace_key == "boss" else "own_workspace",
            "can_receive_tasks": True,
            "can_execute_workflow": True,
            "can_view_other_workspaces": workspace_key == "boss",
        }

    def _fused_event(
        self,
        event: dict[str, Any],
        task: dict[str, Any],
        hr_item: dict[str, Any],
        identities: dict[str, Any],
    ) -> dict[str, Any]:
        workspace_key = str(event.get("assignment", {}).get("workspace_key") or task.get("workspace_key") or hr_item.get("workspace_key") or "")
        identity = identities["workspaces"].get(workspace_key, {})
        return {
            "schema_version": "oms.v1.core_fusion_event",
            "core_event_id": self._stable_id("cf_evt", event.get("business_event_id")),
            "business_event_id": event.get("business_event_id") or "",
            "flow": CORE_FUSION_FLOW,
            "trace_chain": self._trace_chain(event, task, hr_item),
            "data_trace": self._data_trace(event, task, hr_item),
            "identity_trace": self._identity_trace(workspace_key, identity),
            "workflow_trace": self._workflow_trace(task, hr_item),
            "work_entry_trace": self._work_entry_trace(workspace_key, identity),
            "event": event,
        }

    def _unified_task(
        self,
        event: dict[str, Any],
        task: dict[str, Any],
        hr_item: dict[str, Any],
        identities: dict[str, Any],
    ) -> dict[str, Any]:
        workspace_key = str(event.get("assignment", {}).get("workspace_key") or task.get("workspace_key") or hr_item.get("workspace_key") or "")
        identity = identities["workspaces"].get(workspace_key, {})
        user_id = str(identity.get("user_id") or "")
        user_status = str(identity.get("user_id_status") or "missing_required_user_id")
        task_status = (
            "pending_identity_binding"
            if user_status != "mapped"
            else str(event.get("status") or task.get("distribution_status") or "assigned")
        )
        return {
            "schema_version": "oms.v1.unified_task",
            "task_id": self._stable_id("uft", event.get("business_event_id")),
            "business_event_id": event.get("business_event_id") or "",
            "flow": CORE_FUSION_FLOW,
            "event_type": event.get("event_type") or "",
            "event_action": event.get("event_action") or "",
            "event_name": event.get("event_name") or "",
            "title": event.get("title") or event.get("event_name") or "",
            "priority": event.get("priority") or task.get("priority") or "normal",
            "status": task_status,
            "execution_status": "needs_user_binding" if user_status != "mapped" else str(hr_item.get("execution_status") or "assigned"),
            "next_action": event.get("next_action") or task.get("next_action") or "",
            "workspace_key": workspace_key,
            "workspace": identity.get("workspace") or task.get("workspace") or "",
            "role": identity.get("role") or task.get("role") or "",
            "name": identity.get("name") or task.get("name") or "",
            "assigned_user_id": user_id,
            "executor_user_id": user_id,
            "identity": self._identity_trace(workspace_key, identity),
            "trace_chain": self._trace_chain(event, task, hr_item),
            "data": self._data_trace(event, task, hr_item),
            "workflow": self._workflow_trace(task, hr_item),
            "work_entry": self._work_entry_trace(workspace_key, identity),
            "source_evidence": event.get("source_evidence") or {},
            "event_chain": event.get("event_chain") or {},
            "display_fields": self._display_fields(event, identity),
        }

    def _trace_chain(self, event: dict[str, Any], task: dict[str, Any], hr_item: dict[str, Any]) -> dict[str, Any]:
        evidence = event.get("source_evidence") if isinstance(event.get("source_evidence"), dict) else {}
        chain = event.get("trace_chain") if isinstance(event.get("trace_chain"), dict) else event.get("event_chain")
        chain = dict(chain) if isinstance(chain, dict) else {}
        source_file = chain.get("source_file") or evidence.get("source_file") or ""
        source_sheet = chain.get("source_sheet") or evidence.get("source_sheet") or ""
        source_row = chain.get("source_row") or evidence.get("row_number") or ""
        source_record_id = chain.get("source_record_id") or evidence.get("record_id") or event.get("source_record_id") or ""
        ingestion_event_id = chain.get("ingestion_event_id") or evidence.get("ingestion_event_id") or ""
        business_event_id = chain.get("business_event_id") or event.get("business_event_id") or ""
        workflow_task_id = chain.get("workflow_task_id") or task.get("workflow_task_id") or ""
        hr_execution_id = chain.get("hr_execution_id") or hr_item.get("hr_execution_id") or ""
        trace_status = (
            "traceable"
            if all([source_file, source_row, source_record_id, ingestion_event_id, business_event_id, workflow_task_id, hr_execution_id])
            else "partial_trace"
        )
        return {
            "source_file": source_file,
            "source_sheet": source_sheet,
            "source_row": source_row,
            "row_id": chain.get("row_id") or evidence.get("row_id") or "",
            "source_record_id": source_record_id,
            "ingestion_event_id": ingestion_event_id,
            "business_event_id": business_event_id,
            "workflow_task_id": workflow_task_id,
            "hr_execution_id": hr_execution_id,
            "trace_status": trace_status,
        }

    def _data_trace(self, event: dict[str, Any], task: dict[str, Any] | None = None, hr_item: dict[str, Any] | None = None) -> dict[str, Any]:
        evidence = event.get("source_evidence") if isinstance(event.get("source_evidence"), dict) else {}
        chain = self._trace_chain(event, task or {}, hr_item or {})
        return {
            "source_type": event.get("source_type") or evidence.get("source_type") or "",
            "source_file": chain["source_file"],
            "source_sheet": chain["source_sheet"],
            "source_row": chain["source_row"],
            "row_id": chain["row_id"],
            "record_id": chain["source_record_id"],
            "ingestion_event_id": chain["ingestion_event_id"],
            "business_event_id": chain["business_event_id"],
            "workflow_task_id": chain["workflow_task_id"],
            "hr_execution_id": chain["hr_execution_id"],
            "trace_status": chain["trace_status"],
        }

    def _identity_trace(self, workspace_key: str, identity: dict[str, Any]) -> dict[str, Any]:
        return {
            "workspace_key": workspace_key,
            "user_id": identity.get("user_id") or "",
            "open_id": identity.get("open_id") or "",
            "union_id": identity.get("union_id") or "",
            "user_id_status": identity.get("user_id_status") or "missing_required_user_id",
            "role": identity.get("role") or "",
            "department": identity.get("department") or "",
            "execution_rights": identity.get("execution_rights") or {},
            "workspace": identity.get("workspace") or "",
            "name": identity.get("name") or "",
            "source": identity.get("source") or "feishu_org_users_required",
            "binding_confidence": identity.get("binding_confidence") or "",
            "metadata_status": identity.get("metadata_status") or "enriched",
            "metadata_source": identity.get("metadata_source") or "identity_enrichment_layer",
        }

    def _workflow_trace(self, task: dict[str, Any], hr_item: dict[str, Any]) -> dict[str, Any]:
        trace_chain = task.get("trace_chain") if isinstance(task.get("trace_chain"), dict) else hr_item.get("trace_chain")
        trace_chain = trace_chain if isinstance(trace_chain, dict) else {}
        return {
            "workflow_task_id": task.get("workflow_task_id") or "",
            "distribution_status": task.get("distribution_status") or "",
            "hr_execution_id": hr_item.get("hr_execution_id") or "",
            "execution_status": hr_item.get("execution_status") or "",
            "trace_chain": trace_chain,
            "task_trace_status": "traceable" if task or hr_item else "missing_workflow_trace",
        }

    def _work_entry_trace(self, workspace_key: str, identity: dict[str, Any]) -> dict[str, Any]:
        mapped = identity.get("user_id_status") == "mapped"
        return {
            "entry_type": "personal_workspace",
            "entry_key": f"personal_workspace:{workspace_key}",
            "visible_to_user_id": identity.get("user_id") or "",
            "entry_status": "ready" if mapped else "pending_identity_binding",
            "ui_scope": "current_user_only",
        }

    def _display_fields(self, event: dict[str, Any], identity: dict[str, Any]) -> list[dict[str, str]]:
        data = self._data_trace(event)
        return [
            {"label": "数据来源", "value": str(data["source_file"] or data["source_type"] or "local_live_runtime")},
            {"label": "业务事件", "value": str(event.get("event_name") or event.get("event_action") or "")},
            {"label": "执行人", "value": str(identity.get("name") or "")},
            {"label": "工作入口", "value": str(identity.get("workspace") or "")},
        ]

    def _display_fields(self, event: dict[str, Any], identity: dict[str, Any]) -> list[dict[str, str]]:
        data = self._data_trace(event)
        return [
            {"label": "Excel来源", "value": str(data["source_file"] or data["source_type"] or "local_live_runtime")},
            {"label": "业务事件", "value": str(event.get("event_name") or event.get("event_action") or "")},
            {"label": "执行人", "value": str(identity.get("name") or "")},
            {"label": "工作台", "value": str(identity.get("workspace") or "")},
        ]

    def _validation(self, identities: dict[str, Any], fused_events: list[dict[str, Any]], unified_tasks: list[dict[str, Any]]) -> dict[str, Any]:
        missing_identity_tasks = [item for item in unified_tasks if item["identity"]["user_id_status"] != "mapped"]
        untraceable_data = [item for item in fused_events if item["data_trace"]["trace_status"] != "traceable"]
        return {
            "identity_traceable": not missing_identity_tasks,
            "data_traceable": not untraceable_data,
            "task_traceable": all(item.get("business_event_id") and item.get("task_id") for item in unified_tasks),
            "single_flow_enforced": True,
            "anonymous_execution_paths": 0,
            "fallback_identity_paths": 0,
            "missing_identity_task_count": len(missing_identity_tasks),
            "untraceable_data_event_count": len(untraceable_data),
            "status": "complete" if not missing_identity_tasks and not untraceable_data else "blocked",
        }

    def _write_state(
        self,
        state: dict[str, Any],
        identities: dict[str, Any],
        fused_events: list[dict[str, Any]],
        unified_tasks: list[dict[str, Any]],
    ) -> None:
        self.fusion_root.mkdir(parents=True, exist_ok=True)
        (self.fusion_root / "identity_fusion.json").write_text(json.dumps(identities, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.fusion_root / "core_fusion_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_jsonl(self.fusion_root / "single_business_event_stream.jsonl", fused_events)
        self._write_jsonl(self.fusion_root / "unified_task_stream.jsonl", unified_tasks)

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
        return rows

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _stable_id(self, prefix: str, value: Any) -> str:
        digest = hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"
