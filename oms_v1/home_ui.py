from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .operational_core import OPERATING_CENTER_PEOPLE, PERSONAL_WORKSPACES, ROLE_USER_ALIASES
from .schemas import now_iso


ROLE_HOME_PANELS = {
    "june": {"title": "我的房态", "empty": "暂无房态待处理事项"},
    "liujie": {"title": "我的财务", "empty": "暂无财务待处理事项"},
    "sales": {"title": "我的客户", "empty": "暂无客户待处理事项"},
    "huanhuan": {"title": "我的客户", "empty": "暂无客户待处理事项"},
    "nana": {"title": "我的服务", "empty": "暂无服务待处理事项"},
    "boss": {"title": "经营总览", "empty": "暂无全局待处理事项"},
    "admin": {"title": "我的行政", "empty": "暂无行政待处理事项"},
    "procurement": {"title": "我的采购", "empty": "暂无采购待处理事项"},
    "maternity_care": {"title": "我的产护", "empty": "暂无产护待处理事项"},
    "kitchen": {"title": "我的厨房", "empty": "暂无厨房待处理事项"},
    "logistics": {"title": "我的后勤", "empty": "暂无后勤待处理事项"},
}

STATUS_LABELS = {
    "ready": "已就绪",
    "ready_with_pending_sync": "待外部同步",
    "waiting_confirmation": "待确认",
    "waiting_live_sync": "待同步",
    "blocked": "需处理",
    "attention_required": "需关注",
}


class OMSHomeUI:
    """Build the user-facing OMS home payload from operating data."""

    def __init__(self, live_root: str | Path | None = None, operating_root: str | Path | None = None):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")

    def build_home(self, operating_stream: dict[str, Any], *, user_id: str | None = None) -> dict[str, Any]:
        identity = self._resolve_identity(user_id, operating_stream)
        workspace = self._workspace_for_identity(identity, operating_stream)
        role_panel = ROLE_HOME_PANELS.get(identity["workspace_key"], ROLE_HOME_PANELS["boss"])
        sections = {
            "my_todos": self._section("我的待办", workspace.get("my_todos", []), empty_text="暂无待办"),
            "my_tasks": self._section("我的任务", workspace.get("my_tasks", []), empty_text="暂无任务"),
            "my_approvals": self._section("我的审批", workspace.get("my_approvals", []), empty_text="暂无审批"),
            "role_home": self._section(role_panel["title"], workspace.get("all_visible_items", []), empty_text=role_panel["empty"]),
        }
        sync_status = self._sync_status_from_operating_stream(operating_stream)
        decision_assist = self._decision_assist(operating_stream, identity["workspace_key"])
        return {
            "schema_version": "oms.v1.home",
            "home_type": "user_centric_operating_interface",
            "entry": "personal_workspace",
            "opened_at": now_iso(),
            "current_user": {
                "user_id": identity["user_id"],
                "name": identity["name"],
                "role": identity["role"],
                "home_title": identity["title"],
            },
            "home_title": identity["title"],
            "sections": sections,
            "sync_status": sync_status,
            "decision_assist": decision_assist,
            "bottom_tabs": self._bottom_tabs(identity["workspace_key"]),
            "empty_state": self._empty_state(sections),
        }

    def build_home_from_saved_state(self, *, user_id: str | None = None) -> dict[str, Any]:
        identity = self._resolve_identity(user_id, None)
        workspace = self._workspace_from_saved_items(identity)
        role_panel = ROLE_HOME_PANELS.get(identity["workspace_key"], ROLE_HOME_PANELS["boss"])
        sections = {
            "my_todos": self._section("我的待办", workspace["my_todos"], empty_text="暂无待办"),
            "my_tasks": self._section("我的任务", workspace["my_tasks"], empty_text="暂无任务"),
            "my_approvals": self._section("我的审批", workspace["my_approvals"], empty_text="暂无审批"),
            "role_home": self._section(role_panel["title"], workspace["all_visible_items"], empty_text=role_panel["empty"]),
        }
        return {
            "schema_version": "oms.v1.home",
            "home_type": "user_centric_operating_interface",
            "entry": "personal_workspace",
            "opened_at": now_iso(),
            "current_user": {
                "user_id": identity["user_id"],
                "name": identity["name"],
                "role": identity["role"],
                "home_title": identity["title"],
            },
            "home_title": identity["title"],
            "sections": sections,
            "sync_status": self._sync_status_from_pending_outbox(),
            "decision_assist": self._decision_assist_from_saved_items(workspace["all_visible_items"]),
            "bottom_tabs": self._bottom_tabs(identity["workspace_key"]),
            "empty_state": self._empty_state(sections),
        }

    def _resolve_identity(self, user_id: str | None, operating_stream: dict[str, Any] | None) -> dict[str, str]:
        if operating_stream:
            current_user = (operating_stream.get("personal_workspace_system") or {}).get("current_user") or {}
            if user_id is None and current_user:
                return {
                    "user_id": str(current_user.get("user_id") or current_user.get("workspace_key") or "boss"),
                    "workspace_key": str(current_user.get("workspace_key") or "boss"),
                    "role": str(current_user.get("role") or "BOSS"),
                    "name": str(current_user.get("name") or "BOSS"),
                    "title": str(current_user.get("title") or "BOSS工作台"),
                    "identity_source": str(current_user.get("identity_source") or "operating_stream"),
                }
        raw_user_id = (user_id or os.getenv("OMS_CURRENT_USER_ID") or os.getenv("OMS_USER_ID") or "boss").strip()
        normalized = raw_user_id.lower()
        key, identity_source = self._workspace_key_from_user_id(raw_user_id, normalized)
        workspace = PERSONAL_WORKSPACES[key]
        return {
            "user_id": raw_user_id,
            "workspace_key": key,
            "role": workspace["role"],
            "name": workspace["name"],
            "title": workspace["title"],
            "identity_source": identity_source,
        }

    def _workspace_key_from_user_id(self, raw_user_id: str, normalized: str) -> tuple[str, str]:
        for key, person in OPERATING_CENTER_PEOPLE.items():
            feishu_user_id = os.getenv(person["feishu_env"], "").strip()
            if feishu_user_id and raw_user_id == feishu_user_id:
                return key, "feishu_user_id"
        if normalized in PERSONAL_WORKSPACES:
            return normalized, "workspace_key"
        alias_key = ROLE_USER_ALIASES.get(raw_user_id) or ROLE_USER_ALIASES.get(normalized)
        if alias_key:
            return alias_key, "role_alias"
        return "boss", "unresolved_fallback_to_boss_workspace"

    def _workspace_for_identity(self, identity: dict[str, str], operating_stream: dict[str, Any]) -> dict[str, Any]:
        workspaces = (operating_stream.get("personal_workspace_system") or {}).get("workspaces") or {}
        return workspaces.get(identity["workspace_key"]) or operating_stream.get("default_workspace") or {
            "my_todos": [],
            "my_tasks": [],
            "my_approvals": [],
            "all_visible_items": [],
        }

    def _workspace_from_saved_items(self, identity: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
        items = self._read_saved_work_items()
        role = identity["role"]
        visible = items if role == "BOSS" else [item for item in items if item.get("role") == role]
        approvals = [item for item in visible if item.get("confirmation_required") or item.get("status") == "waiting_confirmation"]
        todos = [item for item in visible if item.get("status") != "ready"]
        tasks = [item for item in visible if item.get("status") == "ready"]
        return {
            "my_todos": todos,
            "my_tasks": tasks,
            "my_approvals": approvals,
            "all_visible_items": visible,
        }

    def _read_saved_work_items(self) -> list[dict[str, Any]]:
        path = self.operating_root / "daily_work_items.jsonl"
        if not path.exists():
            return []
        items: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                items.append(data)
        return items

    def _section(self, title: str, items: list[dict[str, Any]], *, empty_text: str) -> dict[str, Any]:
        return {
            "title": title,
            "count": len(items),
            "items": [self._home_item(item) for item in items],
            "empty_text": empty_text if not items else "",
        }

    def _home_item(self, item: dict[str, Any]) -> dict[str, Any]:
        status = item.get("status", "")
        return {
            "id": item.get("work_item_id") or item.get("action_id") or "",
            "title": item.get("daily_process") or item.get("workspace") or "待处理事项",
            "action": item.get("next_operator_action") or "请在 OMS 中确认处理结果。",
            "status": STATUS_LABELS.get(status, status or "待处理"),
            "needs_confirmation": bool(item.get("confirmation_required")),
            "fallback": status in {"ready_with_pending_sync", "waiting_live_sync"},
        }

    def _sync_status_from_operating_stream(self, operating_stream: dict[str, Any]) -> dict[str, Any]:
        readiness = operating_stream.get("operational_readiness") or {}
        pending = int(readiness.get("pending_external_sync_count") or 0)
        failed = int(readiness.get("failed_sync_count") or 0)
        return {
            "title": "外部同步",
            "state": "待同步" if pending else "正常",
            "pending_count": pending,
            "failed_count": failed,
            "message": "外部系统暂未完全同步，事项已进入待同步队列。" if pending else "外部同步暂无待处理事项。",
        }

    def _sync_status_from_pending_outbox(self) -> dict[str, Any]:
        outbox = self.live_root / "pending_outbox"
        pending_count = 0
        queues: list[dict[str, Any]] = []
        if outbox.exists():
            for path in sorted(outbox.glob("*.jsonl")):
                line_count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
                pending_count += line_count
                queues.append({"name": path.stem, "count": line_count})
        return {
            "title": "外部同步",
            "state": "待同步" if pending_count else "正常",
            "pending_count": pending_count,
            "failed_count": 0,
            "queues": queues,
            "message": "外部系统暂未完全同步，事项已进入待同步队列。" if pending_count else "外部同步暂无待处理事项。",
        }

    def _decision_assist(self, operating_stream: dict[str, Any], workspace_key: str) -> dict[str, Any]:
        support_status = operating_stream.get("support_layer_status") or {}
        readiness = operating_stream.get("operational_readiness") or {}
        messages: list[str] = []
        if support_status.get("active"):
            messages.append("协同事项已自动分发，请优先处理自己的待办。")
        if readiness.get("pending_external_sync_count"):
            messages.append("有事项正在等待外部同步，不影响继续处理。")
        if workspace_key == "boss":
            messages.append("请关注需确认事项、待同步事项和跨岗位协同。")
        return {"title": "系统提醒", "messages": messages or ["当前首页暂无系统提醒。"]}

    def _decision_assist_from_saved_items(self, visible_items: list[dict[str, Any]]) -> dict[str, Any]:
        waiting = sum(1 for item in visible_items if item.get("confirmation_required"))
        pending = sum(1 for item in visible_items if item.get("status") in {"ready_with_pending_sync", "waiting_live_sync"})
        messages: list[str] = []
        if waiting:
            messages.append(f"有 {waiting} 个事项需要确认。")
        if pending:
            messages.append(f"有 {pending} 个事项等待外部同步，不影响继续处理。")
        return {"title": "系统提醒", "messages": messages or ["当前首页暂无系统提醒。"]}

    def _bottom_tabs(self, workspace_key: str) -> list[dict[str, Any]]:
        role_panel = ROLE_HOME_PANELS.get(workspace_key, ROLE_HOME_PANELS["boss"])
        return [
            {"key": "home", "label": "首页", "active": True},
            {"key": "todos", "label": "待办", "active": False},
            {"key": "approvals", "label": "审批", "active": False},
            {"key": "role_home", "label": role_panel["title"].replace("我的", ""), "active": False},
        ]

    def _empty_state(self, sections: dict[str, dict[str, Any]]) -> str:
        if any(section["count"] for section in sections.values()):
            return ""
        return "当前没有新的待办、任务或审批。"
