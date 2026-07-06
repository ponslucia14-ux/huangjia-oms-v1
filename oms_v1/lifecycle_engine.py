from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import new_id, now_iso


LIFECYCLE_SCHEMA_VERSION = "oms.v1.lifecycle_engine"


LIFECYCLE_MODELS: dict[str, list[dict[str, str]]] = {
    "room": [
        {"stage": "reserved", "label": "\u9884\u8ba2"},
        {"stage": "checkin", "label": "\u5165\u4f4f"},
        {"stage": "in_house", "label": "\u5728\u4f4f"},
        {"stage": "cleaning", "label": "\u6e05\u6d01"},
        {"stage": "vacant", "label": "\u7a7a\u7f6e"},
        {"stage": "reallocation", "label": "\u518d\u5206\u914d"},
    ],
    "finance": [
        {"stage": "receivable_created", "label": "\u751f\u6210\u5e94\u6536"},
        {"stage": "confirmed", "label": "\u786e\u8ba4"},
        {"stage": "paid", "label": "\u6536\u6b3e"},
        {"stage": "reconciled", "label": "\u5bf9\u8d26"},
        {"stage": "settled", "label": "\u7ed3\u7b97"},
        {"stage": "archived", "label": "\u5f52\u6863"},
    ],
    "sales": [
        {"stage": "lead", "label": "\u7ebf\u7d22"},
        {"stage": "follow_up", "label": "\u8ddf\u8fdb"},
        {"stage": "intent", "label": "\u610f\u5411"},
        {"stage": "contracted", "label": "\u7b7e\u7ea6"},
        {"stage": "converted", "label": "\u5165\u4f4f/\u6210\u4ea4"},
        {"stage": "repurchase", "label": "\u590d\u8d2d"},
    ],
    "allocation": [
        {"stage": "demand_input", "label": "\u9700\u6c42\u8f93\u5165"},
        {"stage": "rule_calculation", "label": "\u89c4\u5219\u8ba1\u7b97"},
        {"stage": "room_matching", "label": "\u623f\u95f4\u5339\u914d"},
        {"stage": "assignment_execution", "label": "\u6267\u884c\u5206\u914d"},
        {"stage": "actual_checkin", "label": "\u5b9e\u9645\u5165\u4f4f"},
        {"stage": "result_feedback", "label": "\u7ed3\u679c\u53cd\u9988"},
        {"stage": "model_optimization", "label": "\u6a21\u578b\u4f18\u5316"},
    ],
}


class LifecycleEngine:
    """Aggregate execution events into business lifecycle state."""

    def __init__(self, live_root: Path | str, operating_root: Path | str | None = None) -> None:
        self.live_root = Path(live_root)
        self.operating_root = Path(operating_root) if operating_root else self.live_root / "operational_core"
        self.lifecycle_root = self.live_root / "lifecycle"

    def apply_execution(self, execution_payload: dict[str, Any]) -> dict[str, Any]:
        timestamp = now_iso()
        command = execution_payload.get("business_command") if isinstance(execution_payload.get("business_command"), dict) else {}
        command_payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        state_update = execution_payload.get("state_update") if isinstance(execution_payload.get("state_update"), dict) else {}
        route = str(command_payload.get("route") or state_update.get("route") or command.get("entity") or "task")
        action = str(command_payload.get("action") or "")
        target = str(command.get("target") or state_update.get("target") or "").strip()
        status = str((state_update.get("state_delta") or {}).get("status") if isinstance(state_update.get("state_delta"), dict) else "")
        domain = self._domain_for_execution(route=route, action=action, command=command, execution_payload=execution_payload)
        stage = self._stage_for_action(domain=domain, action=action, status=status, target=target, execution_payload=execution_payload)
        entity_id = self._entity_id(domain, target, command, state_update)
        current_state = self._read_current_state()
        previous = current_state.get(entity_id) if isinstance(current_state.get(entity_id), dict) else {}
        transition = self._transition(previous, domain, stage, timestamp)
        stages = self._stage_names(domain)
        stage_index = stages.index(stage) if stage in stages else 0
        next_stage = "" if stage_index >= len(stages) - 1 else stages[stage_index + 1]
        completed = not next_stage
        closure_detection = {
            "completed": completed,
            "status": "closed" if completed else "open",
            "risk": "" if completed else "unclosed_lifecycle",
            "risk_level": "none" if completed else "attention_required",
            "should_push_to_action_queue": not completed,
        }
        lifecycle = {
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
            "lifecycle_id": str(previous.get("lifecycle_id") or new_id("life")),
            "lifecycle_event_id": new_id("life_evt"),
            "domain": domain,
            "entity_id": entity_id,
            "route": route,
            "action": action,
            "target": target,
            "previous_stage": str(previous.get("current_stage") or ""),
            "current_stage": stage,
            "current_stage_label": self._stage_label(domain, stage),
            "next_stage": next_stage,
            "next_stage_label": self._stage_label(domain, next_stage),
            "next_action": self._next_action(domain, next_stage),
            "stage_index": stage_index,
            "stage_count": len(stages),
            "completed": completed,
            "closure_detection": closure_detection,
            "duration_stats": transition,
            "feedback_loop": self._feedback_loop(execution_payload, domain, stage, completed),
            "trace_chain": execution_payload.get("trace_chain") if isinstance(execution_payload.get("trace_chain"), dict) else {},
            "updated_at": timestamp,
            "source": "business_execution_closure",
        }
        current_state[entity_id] = lifecycle
        state_payload = {
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
            "updated_at": timestamp,
            "models": LIFECYCLE_MODELS,
            "current_state": current_state,
            "counts": self._counts(current_state),
        }
        self._append_jsonl(self.lifecycle_root / "lifecycle_events.jsonl", lifecycle)
        self._write_json(self.lifecycle_root / "current_lifecycles.json", state_payload)
        self._write_json(self.lifecycle_root / "latest_lifecycle.json", lifecycle)
        if not completed:
            queue_item = self._action_queue_item(lifecycle)
            self._append_jsonl(self.lifecycle_root / "open_lifecycle_risks.jsonl", lifecycle)
            self._append_jsonl(self.lifecycle_root / "action_queue.jsonl", queue_item)
        return lifecycle

    def build_summary(self) -> dict[str, Any]:
        state = self._read_json(self.lifecycle_root / "current_lifecycles.json")
        current_state = state.get("current_state") if isinstance(state.get("current_state"), dict) else {}
        lifecycles = [value for value in current_state.values() if isinstance(value, dict)]
        open_lifecycles = [item for item in lifecycles if not item.get("completed")]
        closed_lifecycles = [item for item in lifecycles if item.get("completed")]
        return {
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
            "source": "OMS_LIFECYCLE_ENGINE",
            "state_root": str(self.lifecycle_root),
            "models": LIFECYCLE_MODELS,
            "counts": self._counts(current_state),
            "open_count": len(open_lifecycles),
            "closed_count": len(closed_lifecycles),
            "latest_lifecycle": self._read_json(self.lifecycle_root / "latest_lifecycle.json"),
            "open_lifecycles": open_lifecycles[-25:],
            "action_queue": self._read_jsonl(self.lifecycle_root / "action_queue.jsonl")[-25:],
            "risk_status": "attention_required" if open_lifecycles else "clear",
        }

    def _domain_for_execution(
        self,
        *,
        route: str,
        action: str,
        command: dict[str, Any],
        execution_payload: dict[str, Any],
    ) -> str:
        marker = f"{route} {action} {command.get('command_type') or ''} {command.get('target') or ''}".lower()
        state_writeback = execution_payload.get("business_state_writeback")
        if isinstance(state_writeback, dict) and state_writeback.get("allocation_writeback"):
            return "allocation"
        if any(token in marker for token in ["allocation", "allocate", "reassign", "\u6392\u623f", "\u5206\u914d", "\u91cd\u65b0\u8ba1\u7b97"]):
            return "allocation"
        if route == "finance" or command.get("entity") == "finance":
            return "finance"
        if route == "sales" or command.get("entity") == "sales":
            return "sales"
        return "room"

    def _stage_for_action(
        self,
        *,
        domain: str,
        action: str,
        status: str,
        target: str,
        execution_payload: dict[str, Any],
    ) -> str:
        marker = f"{action} {status} {target}".lower()
        if domain == "room":
            return self._room_stage(marker)
        if domain == "finance":
            return self._finance_stage(marker)
        if domain == "sales":
            return self._sales_stage(marker)
        if domain == "allocation":
            return self._allocation_stage(marker, execution_payload)
        return LIFECYCLE_MODELS[domain][0]["stage"]

    def _room_stage(self, marker: str) -> str:
        if any(token in marker for token in ["reallocation", "reassign", "allocate", "\u518d\u5206\u914d", "\u6392\u623f", "\u5206\u914d"]):
            return "reallocation"
        if any(token in marker for token in ["clean", "\u6e05\u6d01"]):
            return "cleaning"
        if any(token in marker for token in ["vacant", "\u7a7a\u623f", "\u7a7a\u7f6e"]):
            return "vacant"
        if any(token in marker for token in ["checkout", "\u51fa\u9986", "\u9000\u623f"]):
            return "cleaning"
        if any(token in marker for token in ["checkin", "\u5165\u4f4f"]):
            return "checkin"
        if any(token in marker for token in ["complete", "done", "\u5b8c\u6210"]):
            return "in_house"
        return "in_house"

    def _finance_stage(self, marker: str) -> str:
        if any(token in marker for token in ["archive", "\u5f52\u6863"]):
            return "archived"
        if any(token in marker for token in ["settle", "\u7ed3\u7b97"]):
            return "settled"
        if any(token in marker for token in ["reconcile", "\u5bf9\u8d26"]):
            return "reconciled"
        if any(token in marker for token in ["paid", "pay", "\u6536\u6b3e", "\u4ed8\u6b3e"]):
            return "paid"
        if any(token in marker for token in ["confirm", "\u786e\u8ba4", "complete", "done"]):
            return "confirmed"
        return "receivable_created"

    def _sales_stage(self, marker: str) -> str:
        if any(token in marker for token in ["repurchase", "\u590d\u8d2d"]):
            return "repurchase"
        if any(token in marker for token in ["converted", "convert", "\u8f6c\u5316", "\u6210\u4ea4", "\u5165\u4f4f"]):
            return "converted"
        if any(token in marker for token in ["contract", "\u7b7e\u7ea6", "complete", "done"]):
            return "contracted"
        if any(token in marker for token in ["intent", "\u610f\u5411"]):
            return "intent"
        if any(token in marker for token in ["follow", "\u8ddf\u8fdb"]):
            return "follow_up"
        return "lead"

    def _allocation_stage(self, marker: str, execution_payload: dict[str, Any]) -> str:
        if any(token in marker for token in ["optimize", "\u4f18\u5316"]):
            return "model_optimization"
        if any(token in marker for token in ["feedback", "result", "complete", "done", "\u53cd\u9988", "\u5b8c\u6210"]):
            return "result_feedback"
        if any(token in marker for token in ["actual", "checkin", "\u5b9e\u9645\u5165\u4f4f", "\u5165\u4f4f"]):
            return "actual_checkin"
        state_writeback = execution_payload.get("business_state_writeback")
        if isinstance(state_writeback, dict) and state_writeback.get("allocation_writeback"):
            return "assignment_execution"
        if any(token in marker for token in ["match", "room", "\u5339\u914d"]):
            return "room_matching"
        if any(token in marker for token in ["rule", "calc", "retrigger", "recalculate", "\u89c4\u5219", "\u8ba1\u7b97", "\u91cd\u65b0"]):
            return "rule_calculation"
        return "demand_input"

    def _transition(self, previous: dict[str, Any], domain: str, stage: str, timestamp: str) -> dict[str, Any]:
        previous_stage = str(previous.get("current_stage") or "")
        first_seen_at = str((previous.get("duration_stats") or {}).get("first_seen_at") or previous.get("updated_at") or timestamp)
        transition_count = int((previous.get("duration_stats") or {}).get("transition_count") or 0)
        stage_dwell_count = int((previous.get("duration_stats") or {}).get("stage_dwell_count") or 0)
        if previous_stage and previous_stage != stage:
            transition_count += 1
            stage_dwell_count = 1
        else:
            stage_dwell_count += 1
        return {
            "first_seen_at": first_seen_at,
            "last_transition_at": timestamp if previous_stage != stage else str((previous.get("duration_stats") or {}).get("last_transition_at") or timestamp),
            "last_seen_at": timestamp,
            "transition_count": transition_count,
            "stage_dwell_count": stage_dwell_count,
            "stage_path": self._stage_names(domain),
        }

    def _feedback_loop(self, execution_payload: dict[str, Any], domain: str, stage: str, completed: bool) -> dict[str, Any]:
        execution_result = execution_payload.get("execution_result") if isinstance(execution_payload.get("execution_result"), dict) else {}
        state_update = execution_payload.get("state_update") if isinstance(execution_payload.get("state_update"), dict) else {}
        return {
            "execution_result_id": str(execution_result.get("execution_result_id") or ""),
            "state_update_id": str(state_update.get("state_update_id") or ""),
            "model_update_required": domain == "allocation" and stage in {"result_feedback", "model_optimization"},
            "next_cycle_adjustment": "closed_cycle_ready_for_next_run" if completed else "use_current_stage_to_drive_next_action",
        }

    def _action_queue_item(self, lifecycle: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
            "queue_item_id": new_id("life_queue"),
            "lifecycle_id": lifecycle["lifecycle_id"],
            "lifecycle_event_id": lifecycle["lifecycle_event_id"],
            "domain": lifecycle["domain"],
            "entity_id": lifecycle["entity_id"],
            "current_stage": lifecycle["current_stage"],
            "next_stage": lifecycle["next_stage"],
            "next_action": lifecycle["next_action"],
            "priority": "attention_required",
            "status": "queued",
            "created_at": now_iso(),
        }

    def _entity_id(self, domain: str, target: str, command: dict[str, Any], state_update: dict[str, Any]) -> str:
        if target:
            return f"{domain}:{target}"
        candidate = command.get("business_command_id") or state_update.get("state_update_id") or new_id(domain)
        return f"{domain}:{candidate}"

    def _stage_names(self, domain: str) -> list[str]:
        return [item["stage"] for item in LIFECYCLE_MODELS[domain]]

    def _stage_label(self, domain: str, stage: str) -> str:
        if not stage:
            return ""
        for item in LIFECYCLE_MODELS[domain]:
            if item["stage"] == stage:
                return item["label"]
        return stage

    def _next_action(self, domain: str, next_stage: str) -> str:
        if not next_stage:
            return "lifecycle_closed"
        return f"advance_{domain}_to_{next_stage}"

    def _counts(self, current_state: dict[str, Any]) -> dict[str, int]:
        counts = {domain: 0 for domain in LIFECYCLE_MODELS}
        for lifecycle in current_state.values():
            if isinstance(lifecycle, dict) and lifecycle.get("domain") in counts:
                counts[str(lifecycle["domain"])] += 1
        return counts

    def _read_current_state(self) -> dict[str, Any]:
        state = self._read_json(self.lifecycle_root / "current_lifecycles.json")
        current_state = state.get("current_state") if isinstance(state.get("current_state"), dict) else {}
        return dict(current_state)

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
