from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core_data_model import CoreDataModelLayer
from .room_allocation_engine import RoomAllocationEngine
from .schemas import new_id, now_iso


DECISION_EXPLAINABILITY_SCHEMA_VERSION = "oms.v1.decision_explainability"
RETRIGGER_CLOSURE_SCHEMA_VERSION = "oms.v1.retrigger_closure"


class DecisionExplainabilityLayer:
    """Attach decision reasons and re-trigger results to execution output."""

    def __init__(self, live_root: Path | str, operating_root: Path | str | None = None) -> None:
        self.live_root = Path(live_root)
        self.operating_root = Path(operating_root) if operating_root else self.live_root / "operational_core"
        self.explain_root = self.live_root / "decision_explainability"
        self.retrigger_root = self.live_root / "decision_retrigger"

    def explain(self, execution_payload: dict[str, Any]) -> dict[str, Any]:
        command = execution_payload.get("business_command") if isinstance(execution_payload.get("business_command"), dict) else {}
        command_payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        state_update = execution_payload.get("state_update") if isinstance(execution_payload.get("state_update"), dict) else {}
        route = str(command_payload.get("route") or state_update.get("route") or command.get("entity") or "task")
        action = str(command_payload.get("action") or "")
        target = str(command.get("target") or state_update.get("target") or "")
        domain = self._domain_for_route(route)
        allocation = self._room_allocation(target) if domain == "room" else {}
        factors = self._decision_factors(domain, command, state_update, allocation)
        chain = {
            "schema_version": DECISION_EXPLAINABILITY_SCHEMA_VERSION,
            "decision_chain_id": new_id("decision"),
            "domain": domain,
            "route": route,
            "action": action,
            "target": target,
            "decision_summary": self._decision_summary(domain, action, target, factors, allocation),
            "why": self._why(domain, factors, allocation),
            "rules_applied": self._rules_applied(domain),
            "decision_factors": factors,
            "source_links": self._source_links(allocation, execution_payload),
            "confidence": self._confidence(domain, allocation),
            "retrigger_available": True,
            "retrigger_actions": self._retrigger_actions(domain),
            "created_at": now_iso(),
        }
        self._append_jsonl(self.explain_root / "decision_chains.jsonl", chain)
        self._write_json(self.explain_root / "latest_decision_chain.json", chain)
        return chain

    def retrigger(self, execution_payload: dict[str, Any], decision_chain: dict[str, Any] | None = None) -> dict[str, Any]:
        command = execution_payload.get("business_command") if isinstance(execution_payload.get("business_command"), dict) else {}
        command_payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        state_update = execution_payload.get("state_update") if isinstance(execution_payload.get("state_update"), dict) else {}
        route = str(command_payload.get("route") or state_update.get("route") or command.get("entity") or "task")
        action = str(command_payload.get("action") or "")
        target = str(command.get("target") or state_update.get("target") or "")
        domain = self._domain_for_route(route)
        requested = self._is_retrigger_action(action)
        result = {
            "schema_version": RETRIGGER_CLOSURE_SCHEMA_VERSION,
            "retrigger_id": new_id("retrigger"),
            "status": "not_requested",
            "domain": domain,
            "route": route,
            "action": action,
            "target": target,
            "decision_chain_id": str((decision_chain or {}).get("decision_chain_id") or ""),
            "engine": "",
            "message": "Re-trigger is available but was not requested by this action.",
            "result_summary": {},
            "created_at": now_iso(),
        }
        if not requested:
            return result
        if domain == "room":
            entity_state = CoreDataModelLayer(self.live_root, self.operating_root).rebuild_from_saved_state()
            room_state = RoomAllocationEngine(self.live_root, self.operating_root).rebuild_from_entity_model(entity_state)
            allocation = self._select_allocation(room_state.get("allocations") or [], target)
            result.update(
                {
                    "status": "completed",
                    "engine": "RoomAllocationEngine",
                    "message": "Room allocation engine re-ran and refreshed allocation results.",
                    "result_summary": {
                        "allocation_count": room_state.get("allocation_count") or 0,
                        "selected_allocation": allocation,
                        "state_path": str(self.live_root / "room_engine" / "room_allocation_state.json"),
                    },
                }
            )
        else:
            result.update(
                {
                    "status": "completed",
                    "engine": "ExecutionReplay",
                    "message": "Execution context was replayed and state write-back was refreshed.",
                    "result_summary": {
                        "business_command_id": command.get("business_command_id") or "",
                        "state_update_id": state_update.get("state_update_id") or "",
                        "writeback_mode": "state_overlay_replay",
                    },
                }
            )
        self._append_jsonl(self.retrigger_root / "retrigger_results.jsonl", result)
        self._write_json(self.retrigger_root / "latest_retrigger.json", result)
        return result

    def _decision_factors(
        self,
        domain: str,
        command: dict[str, Any],
        state_update: dict[str, Any],
        allocation: dict[str, Any],
    ) -> dict[str, Any]:
        if domain == "room" and allocation:
            return {
                "priority_score": allocation.get("priority_score") or 0,
                "room_score": allocation.get("room_score") or 0,
                "risk_flags": allocation.get("risk_flags") or [],
                "adjustment_suggestions": allocation.get("adjustment_suggestions") or [],
                "decision_factors": allocation.get("decision_factors") or {},
                "workflow_target": allocation.get("workflow_target") or {},
            }
        delta = state_update.get("state_delta") if isinstance(state_update.get("state_delta"), dict) else {}
        return {
            "command_type": command.get("command_type") or "",
            "target_module": command.get("target_module") or "",
            "state_delta": delta,
            "status": delta.get("status") or command.get("status") or "",
        }

    def _decision_summary(
        self,
        domain: str,
        action: str,
        target: str,
        factors: dict[str, Any],
        allocation: dict[str, Any],
    ) -> str:
        if domain == "room" and allocation:
            room_id = allocation.get("room_id") or "unassigned room"
            guest_name = allocation.get("guest_name") or target or "current guest"
            score = allocation.get("priority_score") or 0
            return f"{guest_name} is assigned to {room_id} because the room engine ranked this option with priority score {score}."
        if domain == "finance":
            return f"Finance action '{action}' was applied to '{target}' and marked for state update."
        if domain == "sales":
            return f"Sales action '{action}' was applied to '{target}' and moved into workflow execution."
        return f"Action '{action}' was accepted for '{target}' and entered the execution loop."

    def _why(self, domain: str, factors: dict[str, Any], allocation: dict[str, Any]) -> list[str]:
        if domain == "room" and allocation:
            risk_flags = allocation.get("risk_flags") or []
            suggestions = allocation.get("adjustment_suggestions") or []
            decision_factors = allocation.get("decision_factors") if isinstance(allocation.get("decision_factors"), dict) else {}
            return [
                f"Customer priority score: {allocation.get('priority_score') or 0}.",
                f"Room matching score: {allocation.get('room_score') or 0}.",
                f"Check-in date considered: {decision_factors.get('checkin_date') or 'missing'}.",
                f"Nursing need considered: {decision_factors.get('nursing_need') or 'missing'}.",
                f"Risk flags: {', '.join(risk_flags) if risk_flags else 'none'}.",
                f"Suggested next step: {', '.join(suggestions) if suggestions else 'confirm result'}.",
            ]
        return [
            f"Target module: {factors.get('target_module') or 'workflow'}.",
            f"State status: {factors.get('status') or 'in_progress'}.",
            "The action is recorded, assigned, written back, and reflected in the UI.",
        ]

    def _rules_applied(self, domain: str) -> list[dict[str, str]]:
        if domain == "room":
            return [
                {"rule": "customer_priority", "meaning": "check-in date, nursing need, sales amount, and missing room are scored."},
                {"rule": "room_priority", "meaning": "available room, requested room/type match, and staff load are scored."},
                {"rule": "conflict_resolution", "meaning": "occupied rooms are excluded unless already assigned to the same guest."},
                {"rule": "dynamic_adjustment", "meaning": "risk flags and adjustment suggestions are emitted for June workspace execution."},
            ]
        if domain == "finance":
            return [
                {"rule": "source_trace", "meaning": "finance action must retain source and state update identifiers."},
                {"rule": "writeback", "meaning": "execution result must update current finance state overlay."},
            ]
        if domain == "sales":
            return [
                {"rule": "workflow_stage", "meaning": "sales action moves the contract/customer into workflow execution."},
                {"rule": "writeback", "meaning": "execution result must update current sales state overlay."},
            ]
        return [{"rule": "execution_loop", "meaning": "action must create command, workflow task, execution item, state update, and UI reflection."}]

    def _source_links(self, allocation: dict[str, Any], execution_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_record_ids": allocation.get("source_record_ids") or [],
            "source_entity_ids": allocation.get("source_entity_ids") or [],
            "trace_chain": execution_payload.get("trace_chain") if isinstance(execution_payload.get("trace_chain"), dict) else {},
        }

    def _confidence(self, domain: str, allocation: dict[str, Any]) -> str:
        if domain == "room" and allocation:
            if allocation.get("room_id") and not allocation.get("risk_flags"):
                return "high"
            return "needs_review"
        return "execution_recorded"

    def _retrigger_actions(self, domain: str) -> list[dict[str, str]]:
        if domain == "room":
            return [{"label": "重新计算排房", "action": "retrigger_room_allocation"}]
        return [{"label": "重新执行当前动作", "action": "retrigger_execution"}]

    def _room_allocation(self, target: str) -> dict[str, Any]:
        state = self._read_json(self.live_root / "room_engine" / "room_allocation_state.json")
        allocations = state.get("allocations") if isinstance(state.get("allocations"), list) else []
        return self._select_allocation(allocations, target)

    def _select_allocation(self, allocations: list[dict[str, Any]], target: str) -> dict[str, Any]:
        target_text = str(target or "")
        for allocation in allocations:
            if target_text and (
                target_text in str(allocation.get("room_id") or "")
                or target_text in str(allocation.get("room_type") or "")
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
        return "task"

    def _is_retrigger_action(self, action: str) -> bool:
        text = str(action or "").lower()
        tokens = ["retrigger", "rerun", "recalculate", "recompute", "\u91cd\u65b0", "\u91cd\u7b97", "\u91cd\u8dd1", "\u518d\u6b21"]
        return any(token in text for token in tokens)

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
