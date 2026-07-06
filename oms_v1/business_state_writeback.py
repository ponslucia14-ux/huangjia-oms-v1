from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core_data_model import CoreDataModelLayer
from .room_allocation_engine import RoomAllocationEngine
from .schemas import new_id, now_iso
from .truth_source import TruthSourceStore


BUSINESS_STATE_WRITEBACK_SCHEMA_VERSION = "oms.v1.business_state_writeback"


class BusinessStateWritebackLayer:
    """Apply execution results to the current OMS business state overlay."""

    def __init__(self, live_root: Path | str, operating_root: Path | str | None = None) -> None:
        self.live_root = Path(live_root)
        self.operating_root = Path(operating_root) if operating_root else self.live_root / "operational_core"
        self.state_root = self.live_root / "business_state"
        self.truth_store = TruthSourceStore(self.live_root, self.operating_root)

    def apply(self, execution_payload: dict[str, Any]) -> dict[str, Any]:
        command = execution_payload.get("business_command") if isinstance(execution_payload.get("business_command"), dict) else {}
        command_payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        state_update = execution_payload.get("state_update") if isinstance(execution_payload.get("state_update"), dict) else {}
        route = str(command_payload.get("route") or state_update.get("route") or command.get("entity") or "task")
        domain = self._domain_for_route(route)
        target = str(command.get("target") or state_update.get("target") or "").strip()
        action = str(command_payload.get("action") or "")
        status = self._status_for_action(action, state_update)
        writeback = {
            "schema_version": BUSINESS_STATE_WRITEBACK_SCHEMA_VERSION,
            "business_state_id": new_id("bst"),
            "domain": domain,
            "route": route,
            "entity_id": self._entity_id(domain, target, command, state_update),
            "target": target,
            "status": status,
            "action": action,
            "execution_result_id": str((execution_payload.get("execution_result") or {}).get("execution_result_id") or ""),
            "state_update_id": str(state_update.get("state_update_id") or ""),
            "workflow_task_id": str((execution_payload.get("workflow_task") or {}).get("workflow_task_id") or ""),
            "hr_execution_id": str((execution_payload.get("hr_execution") or {}).get("hr_execution_id") or ""),
            "user_id": str(state_update.get("user_id") or ""),
            "workspace_key": str(state_update.get("workspace_key") or ""),
            "updated_at": now_iso(),
            "state_delta": state_update.get("state_delta") if isinstance(state_update.get("state_delta"), dict) else {},
            "source": "business_execution_closure",
        }
        allocation_writeback = self._allocation_writeback(writeback, action, target) if domain == "room" else None
        if allocation_writeback:
            writeback["room_allocation"] = allocation_writeback
        domain_state = self._write_domain_state(domain, writeback)
        self._append_jsonl(self.state_root / f"{domain}_state_writebacks.jsonl", writeback)
        self._write_json(self.state_root / f"{domain}_current_state.json", domain_state)
        self._write_json(self.state_root / "latest_writeback.json", writeback)
        return {
            "schema_version": BUSINESS_STATE_WRITEBACK_SCHEMA_VERSION,
            "status": "applied",
            "domain": domain,
            "entity_id": writeback["entity_id"],
            "business_state_id": writeback["business_state_id"],
            "state_status": status,
            "truth_source_updated": True,
            "current_state_path": str(self.state_root / f"{domain}_current_state.json"),
            "writeback_log_path": str(self.state_root / f"{domain}_state_writebacks.jsonl"),
            "truth_domain_path": str(self.truth_store._domain_path(domain)),
            "allocation_writeback": allocation_writeback or {},
        }

    def read_state_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "schema_version": BUSINESS_STATE_WRITEBACK_SCHEMA_VERSION,
            "source": "business_state_writeback",
            "state_root": str(self.state_root),
            "domains": {},
            "counts": {},
            "latest_writeback": self._read_json(self.state_root / "latest_writeback.json"),
        }
        for domain in ("room", "finance", "sales"):
            data = self._read_json(self.state_root / f"{domain}_current_state.json")
            items = data.get("current_state") if isinstance(data.get("current_state"), dict) else {}
            summary["domains"][domain] = data
            summary["counts"][domain] = len(items)
        return summary

    def _write_domain_state(self, domain: str, writeback: dict[str, Any]) -> dict[str, Any]:
        data = self.truth_store.read_domain(domain)
        current_state = data.get("current_state") if isinstance(data.get("current_state"), dict) else {}
        state_writebacks = data.get("state_writebacks") if isinstance(data.get("state_writebacks"), list) else []
        entity_id = str(writeback["entity_id"])
        previous = current_state.get(entity_id) if isinstance(current_state.get(entity_id), dict) else {}
        current_state[entity_id] = {
            **previous,
            **writeback,
            "previous_status": previous.get("status", ""),
        }
        state_writebacks.append(writeback)
        data["current_state"] = current_state
        data["state_writebacks"] = state_writebacks[-1000:]
        data["state_writeback_policy"] = {
            "mode": "current_state_overlay",
            "raw_source_records_mutated": False,
            "execution_must_modify_business_state": True,
            "domains": ["room", "finance", "sales"],
        }
        self.truth_store.write_domain(domain, data)
        return {
            "schema_version": f"{BUSINESS_STATE_WRITEBACK_SCHEMA_VERSION}.{domain}",
            "domain": domain,
            "updated_at": now_iso(),
            "current_state": current_state,
            "latest_writeback": writeback,
            "source_of_truth": str(self.truth_store._domain_path(domain)),
        }

    def _allocation_writeback(self, writeback: dict[str, Any], action: str, target: str) -> dict[str, Any] | None:
        marker = f"{action} {target}".lower()
        if not any(token in marker for token in ["allocation", "roomallocation", "\u6392\u623f", "\u5206\u914d", "assign", "allocate", "reassign"]):
            return None
        state_path = self.live_root / "room_engine" / "room_allocation_state.json"
        state = self._read_json(state_path)
        if not state.get("allocations"):
            entity_state = CoreDataModelLayer(self.live_root, self.operating_root).rebuild_from_saved_state()
            state = RoomAllocationEngine(self.live_root, self.operating_root).rebuild_from_entity_model(entity_state)
        allocation = self._select_allocation(state.get("allocations") or [], target)
        if not allocation:
            return {
                "status": "no_allocation_match",
                "engine": "RoomAllocationEngine",
                "allocation_count": len(state.get("allocations") or []),
            }
        allocation_state = {
            "schema_version": BUSINESS_STATE_WRITEBACK_SCHEMA_VERSION,
            "allocation_writeback_id": new_id("alloc_wb"),
            "allocation_id": allocation.get("allocation_id") or "",
            "room_id": allocation.get("room_id") or "",
            "guest_name": allocation.get("guest_name") or "",
            "priority_score": allocation.get("priority_score") or 0,
            "risk_flags": allocation.get("risk_flags") or [],
            "adjustment_suggestions": allocation.get("adjustment_suggestions") or [],
            "status": "confirmed" if writeback.get("status") in {"done", "completed"} else "in_progress",
            "source_engine": "RoomAllocationEngine",
            "updated_at": now_iso(),
        }
        self._append_jsonl(self.state_root / "room_allocation_writebacks.jsonl", allocation_state)
        self._write_json(self.state_root / "latest_room_allocation_writeback.json", allocation_state)
        return allocation_state

    def _select_allocation(self, allocations: list[dict[str, Any]], target: str) -> dict[str, Any]:
        target_text = str(target or "")
        for allocation in allocations:
            if target_text and (
                target_text in str(allocation.get("room_id") or "")
                or target_text in str(allocation.get("guest_name") or "")
                or target_text in str(allocation.get("allocation_id") or "")
            ):
                return allocation
        return allocations[0] if allocations else {}

    def _domain_for_route(self, route: str) -> str:
        if route == "finance":
            return "finance"
        if route == "sales":
            return "sales"
        if route == "room":
            return "room"
        return "room"

    def _entity_id(self, domain: str, target: str, command: dict[str, Any], state_update: dict[str, Any]) -> str:
        if target:
            return f"{domain}:{target}"
        candidate = command.get("business_command_id") or state_update.get("state_update_id") or new_id(domain)
        return f"{domain}:{candidate}"

    def _status_for_action(self, action: str, state_update: dict[str, Any]) -> str:
        text = str(action or "").lower()
        if "complete" in text or "done" in text or "\u5b8c\u6210" in action:
            return "completed"
        delta = state_update.get("state_delta") if isinstance(state_update.get("state_delta"), dict) else {}
        status = str(delta.get("status") or "")
        return status or "in_progress"

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
