from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .operating_center_source import OPERATING_CENTER_PEOPLE, OPERATING_CENTER_VERSION
from .schemas import now_iso


BUSINESS_EVENT_SCHEMA_VERSION = "oms.v1.business_event_flow"
BUSINESS_EVENT_SOURCE_FILES = (
    "daily_work_items.jsonl",
    "excel_work_items.jsonl",
    "finance_work_items.jsonl",
)


class BusinessEventEngine:
    """Build event-driven business and HR execution flows from real runtime work items."""

    def __init__(self, live_root: str | Path | None = None, operating_root: str | Path | None = None):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")
        self.event_root = self.live_root / "business_events"
        self.hr_root = self.live_root / "hr_flow"

    def rebuild_from_saved_state(self) -> dict[str, Any]:
        work_items = self._read_saved_work_items()
        financial_events = self._read_jsonl(self.live_root / "finance" / "financial_events.jsonl")
        business_events = self._business_events(work_items, financial_events)
        workflow_tasks = [self._workflow_task(event) for event in business_events]
        hr_items = [self._hr_execution_item(event, task) for event, task in zip(business_events, workflow_tasks)]
        self._write_jsonl(self.event_root / "business_event_flow.jsonl", business_events)
        self._write_jsonl(self.event_root / "workflow_distribution.jsonl", workflow_tasks)
        self._write_jsonl(self.hr_root / "hr_execution_items.jsonl", hr_items)
        summary = {
            "schema_version": BUSINESS_EVENT_SCHEMA_VERSION,
            "source_of_truth": "local_live_runtime",
            "people_model_source": OPERATING_CENTER_VERSION,
            "created_at": now_iso(),
            "business_event_count": len(business_events),
            "workflow_task_count": len(workflow_tasks),
            "hr_execution_item_count": len(hr_items),
            "event_type_counts": self._count_by(business_events, "event_type"),
            "workspace_counts": self._count_by(workflow_tasks, "workspace_key"),
            "flow": "Excel/finance/runtime -> business_event_flow -> workflow_distribution -> hr_execution_items -> personal_workspace",
            "paths": {
                "business_event_flow": str(self.event_root / "business_event_flow.jsonl"),
                "workflow_distribution": str(self.event_root / "workflow_distribution.jsonl"),
                "hr_execution_items": str(self.hr_root / "hr_execution_items.jsonl"),
            },
        }
        self._append_jsonl(self.live_root / "audit" / "business_event_flow.jsonl", summary)
        return summary

    def _business_events(self, work_items: list[dict[str, Any]], financial_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events = [self._event_from_work_item(item) for item in work_items]
        seen_records = {event.get("source_record_id") for event in events if event.get("source_record_id")}
        for event in financial_events:
            record_id = str(event.get("record_id") or "")
            if record_id and record_id in seen_records:
                continue
            events.append(self._event_from_financial_event(event))
        return events

    def _event_from_work_item(self, item: dict[str, Any]) -> dict[str, Any]:
        source_record = self._source_record(item)
        evidence = self._source_evidence(item, source_record)
        assignment = self._assignment_from_item(item, source_record)
        source_type = str(source_record.get("source_type") or evidence.get("source_type") or item.get("action_type") or "")
        event_type = self._event_type(source_type, item, source_record)
        event_id = self._stable_id("bevt", evidence.get("trace_id") or item.get("work_item_id") or item.get("action_id") or source_type)
        return {
            "schema_version": "oms.v1.business_event",
            "business_event_id": event_id,
            "event_type": event_type,
            "source_type": source_type,
            "source_of_truth": evidence.get("truth_source") or item.get("source_of_truth") or "local_live_runtime",
            "source_evidence": evidence,
            "source_record_id": str(source_record.get("record_id") or item.get("action_id") or ""),
            "source_work_item_id": str(item.get("work_item_id") or item.get("action_id") or ""),
            "title": str(item.get("daily_process") or item.get("action_type") or event_type),
            "status": str(item.get("status") or ""),
            "priority": self._priority(item, event_type),
            "risk_level": self._risk_level(item),
            "assignment": assignment,
            "event_chain": self._event_chain(evidence, event_id, assignment),
            "next_action": str(item.get("next_operator_action") or ""),
            "created_at": now_iso(),
        }

    def _event_from_financial_event(self, event: dict[str, Any]) -> dict[str, Any]:
        evidence = event.get("source_evidence") if isinstance(event.get("source_evidence"), dict) else {}
        assignment = event.get("assignment") if isinstance(event.get("assignment"), dict) else {}
        source_type = str(event.get("source_type") or evidence.get("source_type") or "financial_event")
        event_type = self._event_type(source_type, event, event)
        event_id = self._stable_id("bevt", evidence.get("trace_id") or event.get("financial_event_id") or event.get("record_id") or source_type)
        return {
            "schema_version": "oms.v1.business_event",
            "business_event_id": event_id,
            "event_type": event_type,
            "source_type": source_type,
            "source_of_truth": evidence.get("truth_source") or event.get("source_of_truth") or "Finance Excel",
            "source_evidence": evidence,
            "source_record_id": str(event.get("record_id") or ""),
            "source_work_item_id": "",
            "title": str(event.get("event_type") or event_type),
            "status": str(event.get("truth_status") or "source_verified"),
            "priority": "normal",
            "risk_level": "low",
            "assignment": self._canonical_assignment(assignment),
            "event_chain": self._event_chain(evidence, event_id, self._canonical_assignment(assignment)),
            "next_action": "route_financial_event_to_workspace",
            "created_at": now_iso(),
        }

    def _workflow_task(self, event: dict[str, Any]) -> dict[str, Any]:
        assignment = event["assignment"]
        return {
            "schema_version": "oms.v1.workflow_distribution_task",
            "workflow_task_id": self._stable_id("wft", event["business_event_id"]),
            "business_event_id": event["business_event_id"],
            "event_type": event["event_type"],
            "assigned_user_id": assignment["user_id"],
            "user_id_status": assignment["user_id_status"],
            "workspace_key": assignment["workspace_key"],
            "workspace": assignment["workspace"],
            "role": assignment["role"],
            "name": assignment["name"],
            "priority": event["priority"],
            "next_action": event["next_action"] or self._default_next_action(event["event_type"]),
            "distribution_status": "pending_user_binding" if assignment["user_id_status"] != "mapped" else "assigned",
            "ui_visibility": "current_user_only",
            "created_at": now_iso(),
        }

    def _hr_execution_item(self, event: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
        hr_assignment = self._hr_assignment(event, task)
        return {
            "schema_version": "oms.v1.hr_execution_item",
            "hr_execution_id": self._stable_id("hrx", event["business_event_id"] + hr_assignment["workspace_key"]),
            "business_event_id": event["business_event_id"],
            "workflow_task_id": task["workflow_task_id"],
            "source_event_type": event["event_type"],
            "source_type": event["source_type"],
            "executor_user_id": hr_assignment["user_id"],
            "user_id_status": hr_assignment["user_id_status"],
            "workspace_key": hr_assignment["workspace_key"],
            "workspace": hr_assignment["workspace"],
            "role": hr_assignment["role"],
            "name": hr_assignment["name"],
            "execution_status": "needs_user_binding" if hr_assignment["user_id_status"] != "mapped" else "assigned",
            "priority": task["priority"],
            "next_action": task["next_action"],
            "workload_points": self._workload_points(event),
            "source_evidence": event["source_evidence"],
            "title": event["title"],
            "daily_process": "business_event_execution",
            "event_chain": event["event_chain"],
            "hr_source": "business_event_flow",
            "created_at": now_iso(),
        }

    def _source_record(self, item: dict[str, Any]) -> dict[str, Any]:
        for key in ("excel_record", "finance_record", "record"):
            value = item.get(key)
            if isinstance(value, dict):
                return value
        return {}

    def _source_evidence(self, item: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
        for value in (item.get("source_evidence"), source_record.get("source_evidence")):
            if isinstance(value, dict):
                return value
        return {}

    def _assignment_from_item(self, item: dict[str, Any], source_record: dict[str, Any]) -> dict[str, str]:
        assignment = source_record.get("assignment") if isinstance(source_record.get("assignment"), dict) else {}
        if not assignment:
            assignment = {
                "workspace": item.get("workspace", ""),
                "role": item.get("role", ""),
            }
        return self._canonical_assignment(assignment)

    def _canonical_assignment(self, assignment: dict[str, Any]) -> dict[str, str]:
        workspace_key = str(assignment.get("workspace_key") or "")
        if workspace_key not in OPERATING_CENTER_PEOPLE:
            workspace_key = self._workspace_key_from_assignment(assignment)
        person = OPERATING_CENTER_PEOPLE.get(workspace_key, OPERATING_CENTER_PEOPLE["boss"])
        user_id = str(assignment.get("user_id") or os.getenv(person["feishu_env"], "").strip())
        return {
            "user_id": user_id,
            "user_id_status": "mapped" if user_id else "unresolved_user_id",
            "workspace_key": workspace_key if workspace_key in OPERATING_CENTER_PEOPLE else "boss",
            "workspace": str(assignment.get("workspace") or person["title"]),
            "role": str(assignment.get("role") or person["role"]),
            "name": str(assignment.get("name") or person["name"]),
        }

    def _workspace_key_from_assignment(self, assignment: dict[str, Any]) -> str:
        workspace = str(assignment.get("workspace") or "")
        role = str(assignment.get("role") or "")
        for key, person in OPERATING_CENTER_PEOPLE.items():
            if workspace == person["title"] or role == person["role"] or role == person["name"]:
                return key
        text = f"{workspace} {role}"
        if "sales" in text.lower() or "閿" in text:
            return "huanhuan"
        if "finance" in text.lower() or "璐" in text:
            return "liujie"
        if "room" in text.lower() or "鎴" in text:
            return "june"
        if "service" in text.lower() or "绠" in text or "鏈" in text:
            return "nana"
        return "boss"

    def _hr_assignment(self, event: dict[str, Any], task: dict[str, Any]) -> dict[str, str]:
        source_type = str(event.get("source_type") or "")
        if source_type in {"care_wage", "sales_commission"} or "wage" in source_type or "commission" in source_type:
            return self._canonical_assignment({"workspace_key": "songxue"})
        return self._canonical_assignment(
            {
                "workspace_key": task["workspace_key"],
                "workspace": task["workspace"],
                "role": task["role"],
                "name": task["name"],
                "user_id": task["assigned_user_id"],
            }
        )

    def _event_type(self, source_type: str, item: dict[str, Any], source_record: dict[str, Any]) -> str:
        text = " ".join(str(value or "") for value in [source_type, item.get("action_type"), item.get("role"), item.get("workspace")])
        if source_type in {"contracts", "sales_detail", "sales_commission"} or "sales" in text or "contract" in text:
            return "sales_event"
        if source_type == "room_status" or "room" in text:
            return "room_event"
        if source_type == "resident" or "service" in text:
            return "service_event"
        if source_type == "care_wage" or "wage" in text or "commission" in text:
            return "hr_event"
        if source_type.startswith("finance_") or "finance" in text or source_record.get("finance_mapping"):
            return "finance_event"
        return "service_event"

    def _event_chain(self, evidence: dict[str, Any], event_id: str, assignment: dict[str, str]) -> dict[str, str]:
        return {
            "source_file": str(evidence.get("source_file") or ""),
            "source_sheet": str(evidence.get("source_sheet") or ""),
            "source_row": str(evidence.get("row_number") or ""),
            "business_event_id": event_id,
            "executor": assignment["name"],
            "executor_user_id": assignment["user_id"],
            "workspace": assignment["workspace"],
        }

    def _priority(self, item: dict[str, Any], event_type: str) -> str:
        status = str(item.get("status") or "")
        if status in {"blocked", "attention_required", "waiting_confirmation"}:
            return "high"
        if event_type in {"finance_event", "room_event"}:
            return "high"
        return "normal"

    def _risk_level(self, item: dict[str, Any]) -> str:
        if item.get("confirmation_required") or item.get("status") in {"blocked", "attention_required"}:
            return "medium"
        return "low"

    def _default_next_action(self, event_type: str) -> str:
        return {
            "sales_event": "follow_up_customer_or_contract",
            "finance_event": "confirm_collection_or_reconciliation",
            "room_event": "confirm_room_status_or_assignment",
            "service_event": "confirm_service_execution",
            "hr_event": "confirm_staff_execution_or_performance",
        }.get(event_type, "confirm_business_event")

    def _workload_points(self, event: dict[str, Any]) -> int:
        if event.get("priority") == "high":
            return 3
        if event.get("event_type") in {"finance_event", "room_event"}:
            return 2
        return 1

    def _read_saved_work_items(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for file_name in BUSINESS_EVENT_SOURCE_FILES:
            rows.extend(self._read_jsonl(self.operating_root / file_name))
        return rows

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

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _count_by(self, rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = str(row.get(key) or "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _stable_id(self, prefix: str, value: Any) -> str:
        digest = hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"
