from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .business_state_writeback import BusinessStateWritebackLayer
from .schemas import new_id, now_iso


EXECUTION_CLOSURE_SCHEMA_VERSION = "oms.v1.business_execution_closure"


class BusinessExecutionClosureLayer:
    """Close the UI action -> backend execution -> state update loop."""

    def __init__(self, live_root: Path | str, operating_root: Path | str | None = None) -> None:
        self.live_root = Path(live_root)
        self.operating_root = Path(operating_root) if operating_root else self.live_root / "operational_core"
        self.closure_root = self.live_root / "business_execution"
        self.business_event_root = self.live_root / "business_events"
        self.hr_root = self.live_root / "hr_flow"
        self.state_writeback = BusinessStateWritebackLayer(self.live_root, self.operating_root)

    def execute_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = str(payload.get("user_id") or "").strip()
        workspace_key = str(payload.get("workspace_key") or "").strip()
        route = self._normalize_route(payload.get("route"))
        action = str(payload.get("action") or "execute").strip()
        target = str(payload.get("target") or payload.get("selected_task") or payload.get("current_room") or "").strip()
        timestamp = now_iso()

        if not user_id:
            return self._blocked_result(
                reason="missing_user_id",
                route=route,
                action=action,
                target=target,
                timestamp=timestamp,
            )

        command = self._business_command(route=route, action=action, target=target, payload=payload, timestamp=timestamp)
        action_event = {
            "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
            "action_event_id": new_id("ui_action"),
            "event_type": "ui_action_triggered",
            "user_id": user_id,
            "workspace_key": workspace_key,
            "route": route,
            "action": action,
            "target": target,
            "selected_task": str(payload.get("selected_task") or ""),
            "current_room": str(payload.get("current_room") or ""),
            "active_workflow": str(payload.get("active_workflow") or ""),
            "source": str(payload.get("source") or "oms_ui"),
            "created_at": timestamp,
        }
        business_command = {
            "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
            "business_command_id": new_id("cmd"),
            "action_event_id": action_event["action_event_id"],
            "command_type": command["command_type"],
            "entity": command["entity"],
            "target_module": command["target_module"],
            "target": target,
            "requested_by": user_id,
            "workspace_key": workspace_key,
            "status": "accepted",
            "created_at": timestamp,
            "payload": {
                "route": route,
                "action": action,
                "next_action": command["next_action"],
                "state_delta": command["state_delta"],
            },
        }
        workflow_task = {
            "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
            "workflow_task_id": new_id("wfc"),
            "business_command_id": business_command["business_command_id"],
            "assigned_user_id": user_id,
            "workspace_key": workspace_key,
            "route": route,
            "target": target,
            "status": command["workflow_status"],
            "created_at": timestamp,
            "source": "ui_action_execution",
        }
        hr_execution = {
            "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
            "hr_execution_id": new_id("hrx_ui"),
            "workflow_task_id": workflow_task["workflow_task_id"],
            "assigned_user_id": user_id,
            "workspace_key": workspace_key,
            "execution_status": command["execution_status"],
            "created_at": timestamp,
            "source": "ui_action_execution",
        }
        execution_result = {
            "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
            "execution_result_id": new_id("exec_result"),
            "action_event_id": action_event["action_event_id"],
            "business_command_id": business_command["business_command_id"],
            "workflow_task_id": workflow_task["workflow_task_id"],
            "hr_execution_id": hr_execution["hr_execution_id"],
            "status": "completed",
            "closure_status": "closed",
            "message": command["message"],
            "created_at": timestamp,
        }
        state_update = {
            "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
            "state_update_id": new_id("state"),
            "execution_result_id": execution_result["execution_result_id"],
            "route": route,
            "target": target,
            "user_id": user_id,
            "workspace_key": workspace_key,
            "state_delta": command["state_delta"],
            "ui_should_refresh": True,
            "created_at": timestamp,
        }
        result = {
            "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
            "status": "completed",
            "closure_status": "closed",
            "action_event": action_event,
            "business_command": business_command,
            "workflow_task": workflow_task,
            "hr_execution": hr_execution,
            "execution_result": execution_result,
            "state_update": state_update,
            "ui_reflect": {
                "message": command["message"],
                "next_action": command["next_action"],
                "execution_badge": "已执行",
                "route": route,
                "target": target,
            },
            "trace_chain": {
                "action_event_id": action_event["action_event_id"],
                "business_command_id": business_command["business_command_id"],
                "workflow_task_id": workflow_task["workflow_task_id"],
                "hr_execution_id": hr_execution["hr_execution_id"],
                "execution_result_id": execution_result["execution_result_id"],
                "state_update_id": state_update["state_update_id"],
            },
            "runtime_paths": {
                "action_events": str(self.closure_root / "action_events.jsonl"),
                "execution_results": str(self.closure_root / "execution_results.jsonl"),
                "state_updates": str(self.closure_root / "state_updates.jsonl"),
                "workflow_closure": str(self.business_event_root / "workflow_execution_closure.jsonl"),
                "hr_execution_closure": str(self.hr_root / "hr_execution_closure.jsonl"),
                "business_state": str(self.live_root / "business_state"),
            },
        }
        result["business_state_writeback"] = self.state_writeback.apply(result)
        self._persist(result)
        return result

    def _blocked_result(self, *, reason: str, route: str, action: str, target: str, timestamp: str) -> dict[str, Any]:
        result = {
            "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
            "status": "blocked",
            "closure_status": "blocked",
            "blocking_reason": reason,
            "action_event": {
                "schema_version": EXECUTION_CLOSURE_SCHEMA_VERSION,
                "action_event_id": new_id("ui_action"),
                "event_type": "ui_action_blocked",
                "route": route,
                "action": action,
                "target": target,
                "created_at": timestamp,
            },
            "ui_reflect": {
                "message": "身份未就绪，动作未执行",
                "next_action": "重新进入飞书工作台",
                "execution_badge": "已阻断",
                "route": route,
                "target": target,
            },
            "trace_chain": {},
        }
        self._append_jsonl(self.closure_root / "blocked_actions.jsonl", result)
        return result

    def _business_command(self, *, route: str, action: str, target: str, payload: dict[str, Any], timestamp: str) -> dict[str, Any]:
        route_map = {
            "room": ("room", "room_status_module", "update_room_workflow", "房态动作已记录，房间处理状态已进入执行队列"),
            "finance": ("finance", "finance_module", "open_finance_flow", "财务动作已记录，收支/对账事项已进入执行队列"),
            "sales": ("sales", "sales_module", "open_sales_flow", "销售动作已记录，客户跟进事项已进入执行队列"),
            "service": ("task", "service_module", "open_service_flow", "服务动作已记录，服务事项已进入执行队列"),
            "hr": ("task", "hr_module", "open_hr_flow", "人效动作已记录，执行事项已进入执行队列"),
            "risk": ("task", "risk_module", "open_risk_flow", "风险动作已记录，异常事项已进入处理队列"),
            "data": ("task", "traceability_module", "open_trace_flow", "追溯动作已记录，来源链路已进入查询队列"),
            "action": ("task", "workflow_module", "start_task", "任务动作已记录，今日事项已进入执行队列"),
            "work": ("task", "workflow_module", "start_task", "任务动作已记录，今日事项已进入执行队列"),
        }
        entity, module, command_type, message = route_map.get(route, ("task", "workflow_module", "open_status_flow", "状态动作已记录，业务状态已进入执行队列"))
        if "完成" in action or "complete" in action.lower():
            workflow_status = "completed"
            execution_status = "completed"
            next_action = "刷新工作台确认完成状态"
            state_status = "done"
        elif "追踪" in action or "trace" in action.lower() or route == "data":
            workflow_status = "trace_requested"
            execution_status = "in_review"
            next_action = "查看来源链路"
            state_status = "trace_requested"
        else:
            workflow_status = "in_progress"
            execution_status = "in_progress"
            next_action = "继续处理并确认结果"
            state_status = "in_progress"
        return {
            "entity": entity,
            "target_module": module,
            "command_type": command_type,
            "message": message,
            "workflow_status": workflow_status,
            "execution_status": execution_status,
            "next_action": next_action,
            "state_delta": {
                "status": state_status,
                "route": route,
                "target": target,
                "last_action": action,
                "updated_at": timestamp,
                "selected_task": str(payload.get("selected_task") or ""),
                "current_room": str(payload.get("current_room") or ""),
                "active_workflow": str(payload.get("active_workflow") or ""),
            },
        }

    def _normalize_route(self, value: Any) -> str:
        route = str(value or "status").strip().lower()
        return route if route in {"home", "action", "status", "work", "business", "risk", "room", "finance", "sales", "service", "hr", "data"} else "status"

    def _persist(self, result: dict[str, Any]) -> None:
        self._append_jsonl(self.closure_root / "action_events.jsonl", result["action_event"])
        self._append_jsonl(self.closure_root / "business_commands.jsonl", result["business_command"])
        self._append_jsonl(self.closure_root / "execution_results.jsonl", result["execution_result"])
        self._append_jsonl(self.closure_root / "state_updates.jsonl", result["state_update"])
        self._append_jsonl(self.business_event_root / "workflow_execution_closure.jsonl", result["workflow_task"])
        self._append_jsonl(self.hr_root / "hr_execution_closure.jsonl", result["hr_execution"])
        self._write_json(self.closure_root / "latest_state.json", result)

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
