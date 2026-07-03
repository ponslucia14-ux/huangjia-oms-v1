from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .excel_importer import ExcelOMSImporter
from .finance_importer import FinanceDataImporter
from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import now_iso


AUTONOMOUS_RUN_SCHEMA_VERSION = "oms.v1.autonomous_execution"
BUSINESS_SOURCE_KEYS = {"resident", "room_status", "contracts"}
FINANCE_SOURCE_KEYS = {
    "checkin_registration",
    "finance_daily",
    "bank_cash_journal",
    "real_income",
    "service_refund",
    "sales_commission",
    "care_wage",
    "sales_detail",
}


class OMSAutonomousRunner:
    """Monitor Excel sources and trigger OMS imports when source files change."""

    def __init__(
        self,
        *,
        live_root: str | Path | None = None,
        operating_root: str | Path | None = None,
        state_path: str | Path | None = None,
        interval_seconds: int = 30,
    ):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")
        self.state_path = Path(state_path or self.live_root / "autonomous" / "runner_state.json")
        self.log_path = self.live_root / "autonomous" / "runner_log.jsonl"
        self.interval_seconds = max(1, int(interval_seconds))

    def run_once(
        self,
        *,
        sources: dict[str, str | Path | None],
        baseline_existing: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        state = self._read_state()
        signatures = {key: self._signature(path) for key, path in sources.items() if path}
        changed = self._changed_sources(signatures, state, force=force)
        business_changed = {key: sources[key] for key in changed if key in BUSINESS_SOURCE_KEYS}
        finance_changed = {key: sources[key] for key in changed if key in FINANCE_SOURCE_KEYS}
        result: dict[str, Any] = {
            "schema_version": AUTONOMOUS_RUN_SCHEMA_VERSION,
            "run_mode": "Continuous Execution",
            "trigger_mode": "Data-driven + Event-driven",
            "created_at": now_iso(),
            "baseline_existing": baseline_existing,
            "force": force,
            "changed_sources": sorted(changed),
            "business_import": None,
            "finance_import": None,
            "status": "baseline_recorded" if baseline_existing else "idle",
            "blocking": False,
            "pending_outbox_enabled": True,
        }
        if baseline_existing:
            self._write_state(signatures, result)
            self._append_log(result)
            return result
        if business_changed:
            result["business_import"] = ExcelOMSImporter(self.live_root, self.operating_root).import_sources(
                **{key: value for key, value in business_changed.items() if key in BUSINESS_SOURCE_KEYS}
            )
        if finance_changed:
            result["finance_import"] = FinanceDataImporter(self.live_root, self.operating_root).import_sources(
                **{key: value for key, value in finance_changed.items() if key in FINANCE_SOURCE_KEYS}
            )
        if business_changed or finance_changed:
            result["status"] = "executed"
        result["business_closure"] = self._business_closure(result, business_changed, finance_changed)
        result["workspace_update_status"] = result["business_closure"]["workspace_update_status"]
        self._write_state(signatures, result)
        self._append_log(result)
        return result

    def run_forever(
        self,
        *,
        sources: dict[str, str | Path | None],
        baseline_existing: bool = False,
        force_first_run: bool = False,
    ) -> None:
        first_run = True
        while True:
            try:
                self.run_once(
                    sources=sources,
                    baseline_existing=baseline_existing and first_run,
                    force=force_first_run and first_run,
                )
            except Exception as exc:
                failure = {
                    "schema_version": AUTONOMOUS_RUN_SCHEMA_VERSION,
                    "run_mode": "Continuous Execution",
                    "trigger_mode": "Data-driven + Event-driven",
                    "created_at": now_iso(),
                    "status": "error_pending",
                    "blocking": False,
                    "pending_outbox_enabled": True,
                    "error": str(exc),
                }
                self._append_log(failure)
            first_run = False
            time.sleep(self.interval_seconds)

    def _changed_sources(self, signatures: dict[str, dict[str, Any]], state: dict[str, Any], *, force: bool) -> set[str]:
        if force:
            return set(signatures)
        previous = state.get("signatures", {})
        return {
            key
            for key, signature in signatures.items()
            if signature.get("exists") and previous.get(key) != signature
        }

    def _signature(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        if not source.exists():
            return {"path": str(source), "exists": False}
        stat = source.stat()
        return {
            "path": str(source),
            "exists": True,
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, signatures: dict[str, dict[str, Any]], result: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "schema_version": AUTONOMOUS_RUN_SCHEMA_VERSION,
            "updated_at": now_iso(),
            "run_mode": "Continuous Execution",
            "trigger_mode": "Data-driven + Event-driven",
            "signatures": signatures,
            "last_result": self._compact_result(result),
        }
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_log(self, result: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._compact_result(result), ensure_ascii=False) + "\n")

    def _business_closure(
        self,
        result: dict[str, Any],
        business_changed: dict[str, str | Path | None],
        finance_changed: dict[str, str | Path | None],
    ) -> dict[str, Any]:
        imported_items = self._imported_work_items(result)
        trigger_events = [self._trigger_event(source_key) for source_key in sorted({*business_changed, *finance_changed})]
        workspace_updates = self._workspace_updates(imported_items)
        return {
            "schema_version": "oms.v1.business_closure",
            "mode": "Live Business Closure",
            "flow": "business_change -> import -> business_schema -> work_items -> workspace_update -> human_confirmation",
            "trigger_events": trigger_events,
            "workspace_updates": workspace_updates,
            "workspace_update_status": "updated" if workspace_updates else "idle",
            "business_flow_status": "executed" if trigger_events else "idle",
            "pending_outbox_enabled": True,
            "blocking": False,
        }

    def _trigger_event(self, source_key: str) -> dict[str, str]:
        mapping = {
            "resident": ("房态变化", "入住/护理流", "nana"),
            "room_status": ("房态变化", "排房/入住流", "june"),
            "contracts": ("销售变化", "转化/跟进流", "huanhuan"),
            "checkin_registration": ("财务变化", "收款/对账流", "liujie"),
            "finance_daily": ("财务变化", "收款/对账流", "liujie"),
            "bank_cash_journal": ("财务变化", "收款/对账流", "liujie"),
            "real_income": ("财务变化", "收款/对账流", "liujie"),
            "service_refund": ("财务变化", "收款/对账流", "liujie"),
            "sales_commission": ("销售变化", "转化/跟进流", "huanhuan"),
            "care_wage": ("服务变化", "入住/护理流", "boss"),
            "sales_detail": ("销售变化", "转化/跟进流", "huanhuan"),
        }
        event_type, flow, workspace_key = mapping.get(source_key, ("业务变化", "自动流转", "boss"))
        return {
            "source_key": source_key,
            "event_type": event_type,
            "flow": flow,
            "workspace_key": workspace_key,
            "trigger_mode": "data_change_detected",
        }

    def _imported_work_items(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for key in ["business_import", "finance_import"]:
            stream = result.get(key)
            if isinstance(stream, dict):
                items.extend(item for item in stream.get("work_items", []) if isinstance(item, dict))
        return items

    def _workspace_updates(self, work_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for item in work_items:
            workspace = str(item.get("workspace") or "")
            if not workspace:
                continue
            update = grouped.setdefault(
                workspace,
                {
                    "workspace": workspace,
                    "work_item_count": 0,
                    "todo_count": 0,
                    "risk_count": 0,
                    "today_key_task_count": 0,
                    "pending_outbox_count": 0,
                },
            )
            update["work_item_count"] += 1
            if item.get("status") != "ready":
                update["todo_count"] += 1
            if item.get("confirmation_required") or item.get("status") in {"attention_required", "blocked", "waiting_confirmation"}:
                update["risk_count"] += 1
            if item.get("daily_process"):
                update["today_key_task_count"] += 1
            if item.get("status") in {"ready_with_pending_sync", "waiting_live_sync"}:
                update["pending_outbox_count"] += 1
        return list(grouped.values())

    def _compact_result(self, result: dict[str, Any]) -> dict[str, Any]:
        compact = dict(result)
        for key in ["business_import", "finance_import"]:
            stream = compact.get(key)
            if isinstance(stream, dict):
                compact[key] = {
                    "schema_version": stream.get("schema_version"),
                    "record_count": stream.get("record_count"),
                    "work_item_count": stream.get("work_item_count"),
                    "pending_outbox_count": stream.get("pending_outbox_count"),
                    "financial_event_count": stream.get("financial_event_count"),
                    "settlement_record_count": stream.get("settlement_record_count"),
                    "errors": stream.get("errors", []),
                }
        return compact
