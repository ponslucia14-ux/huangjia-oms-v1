from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import now_iso
from .truth_source import TruthSourceStore


HISTORICAL_VIEW_SCHEMA_VERSION = "oms.v1.historical_data_view"
HISTORICAL_VIEW_FLOW = (
    "Excel/data_import -> business_event -> workflow_distribution -> "
    "hr_execution -> completion_log"
)
HISTORICAL_DOMAINS = {
    "room": {"room_event", "resident_event", "stay_event"},
    "finance": {"finance_event", "payment_event", "settlement_event"},
    "sales": {"sales_event", "contract_event", "customer_event"},
    "service": {"service_event", "care_event"},
    "hr": {"hr_event", "human_execution_event"},
}


class HistoricalDataViewLayer:
    """Read-only historical view over the live OMS execution chain."""

    def __init__(self, live_root: str | Path | None = None, operating_root: str | Path | None = None):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")
        self.history_root = self.live_root / "history"
        self.truth_store = TruthSourceStore(self.live_root, self.operating_root)

    def build_history_view(
        self,
        *,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        workspace_key: str | None = None,
        event_type: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        events = self.truth_store.read_events()
        workflow_tasks = self._read_jsonl(self.live_root / "business_events" / "workflow_distribution.jsonl")
        hr_items = self._read_jsonl(self.live_root / "hr_flow" / "hr_execution_items.jsonl")
        finance_events = self.truth_store.read_financial_events()
        unified_tasks = self._read_jsonl(self.live_root / "core_fusion" / "unified_task_stream.jsonl")

        task_by_event = self._first_by(workflow_tasks, "business_event_id")
        hr_by_event = self._first_by(hr_items, "business_event_id")
        unified_by_event = self._first_by(unified_tasks, "business_event_id")

        timeline = [
            self._timeline_item(event, task_by_event.get(str(event.get("business_event_id") or ""), {}), hr_by_event.get(str(event.get("business_event_id") or ""), {}), unified_by_event.get(str(event.get("business_event_id") or ""), {}))
            for event in events
        ]
        timeline = self._apply_filters(
            timeline,
            date=date,
            start_date=start_date,
            end_date=end_date,
            workspace_key=workspace_key,
            event_type=event_type,
        )
        timeline.sort(key=lambda item: (item.get("occurred_at") or "", item.get("business_event_id") or ""))
        visible_timeline = timeline[: max(0, int(limit or 0))]
        state = {
            "schema_version": HISTORICAL_VIEW_SCHEMA_VERSION,
            "mode": "historical_data_view",
            "source_of_truth": "OMS_TRUTH_SOURCE",
            "source_root": str(self.truth_store.root),
            "truth_source": self.truth_store.summary(),
            "created_at": now_iso(),
            "flow": HISTORICAL_VIEW_FLOW,
            "filters": {
                "date": date or "",
                "start_date": start_date or "",
                "end_date": end_date or "",
                "workspace_key": workspace_key or "",
                "event_type": event_type or "",
                "limit": limit,
            },
            "counts": {
                "business_events": len(events),
                "workflow_tasks": len(workflow_tasks),
                "hr_execution_items": len(hr_items),
                "financial_events": len(finance_events),
                "unified_tasks": len(unified_tasks),
                "matched_timeline_items": len(timeline),
                "returned_timeline_items": len(visible_timeline),
            },
            "timeline": visible_timeline,
            "date_index": self._date_index(timeline),
            "multidimensional_history": self._multidimensional_history(timeline),
            "boss_history_analysis": self._boss_history_analysis(timeline),
            "traceability": self._traceability_summary(timeline),
            "paths": {
                "business_event_flow": str(self.truth_store.events_path),
                "workflow_distribution": str(self.live_root / "business_events" / "workflow_distribution.jsonl"),
                "hr_execution_items": str(self.live_root / "hr_flow" / "hr_execution_items.jsonl"),
                "history_state": str(self.history_root / "historical_view_state.json"),
            },
        }
        self._write_state(state)
        self._append_audit(state)
        return state

    def load_cached_history_view(self, *, limit: int = 80) -> dict[str, Any]:
        path = self.history_root / "historical_view_state.json"
        if not path.exists():
            return self.build_history_view(limit=limit)
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return self.build_history_view(limit=limit)
        timeline = state.get("timeline") if isinstance(state.get("timeline"), list) else []
        cached = dict(state)
        cached["timeline"] = timeline[:limit]
        cached.setdefault("counts", {})["returned_timeline_items"] = len(cached["timeline"])
        return cached

    def _timeline_item(
        self,
        event: dict[str, Any],
        task: dict[str, Any],
        hr_item: dict[str, Any],
        unified_task: dict[str, Any],
    ) -> dict[str, Any]:
        event_id = str(event.get("business_event_id") or "")
        trace_chain = self._trace_chain(event, task, hr_item, unified_task)
        evidence = self._source_evidence(event, task, hr_item, unified_task)
        occurred_at = self._occurred_at(event, task, hr_item, unified_task)
        completion_log = self._completion_log(event, task, hr_item, unified_task)
        domain = self._domain(event.get("event_type") or unified_task.get("event_type") or "")
        workspace_key = str(
            event.get("workspace_key")
            or task.get("workspace_key")
            or hr_item.get("workspace_key")
            or unified_task.get("workspace_key")
            or (event.get("assignment") if isinstance(event.get("assignment"), dict) else {}).get("workspace_key")
            or ""
        )
        return {
            "timeline_id": self._stable_id("hist", event_id or trace_chain.get("source_record_id") or occurred_at),
            "occurred_at": occurred_at,
            "date": self._date_part(occurred_at),
            "domain": domain,
            "event_type": str(event.get("event_type") or unified_task.get("event_type") or ""),
            "event_action": str(event.get("event_action") or task.get("event_action") or hr_item.get("event_action") or ""),
            "event_name": str(event.get("event_name") or task.get("event_name") or hr_item.get("event_name") or ""),
            "title": str(event.get("title") or task.get("event_name") or hr_item.get("title") or event.get("event_type") or ""),
            "priority": str(event.get("priority") or task.get("priority") or hr_item.get("priority") or "normal"),
            "status": str(hr_item.get("execution_status") or unified_task.get("execution_status") or task.get("distribution_status") or event.get("status") or ""),
            "workspace_key": workspace_key,
            "workspace": str(task.get("workspace") or hr_item.get("workspace") or unified_task.get("workspace") or ""),
            "role": str(task.get("role") or hr_item.get("role") or unified_task.get("role") or ""),
            "name": str(task.get("name") or hr_item.get("name") or unified_task.get("name") or ""),
            "source_file": trace_chain.get("source_file") or evidence.get("source_file") or "",
            "row_id": trace_chain.get("row_id") or trace_chain.get("source_row") or evidence.get("row_id") or evidence.get("row_number") or "",
            "ingestion_event_id": trace_chain.get("ingestion_event_id") or evidence.get("ingestion_event_id") or "",
            "business_event_id": event_id,
            "workflow_task_id": trace_chain.get("workflow_task_id") or task.get("workflow_task_id") or "",
            "hr_execution_id": trace_chain.get("hr_execution_id") or hr_item.get("hr_execution_id") or "",
            "source_evidence": evidence,
            "trace_chain": trace_chain,
            "stage_sequence": self._stage_sequence(occurred_at, event, task, hr_item, completion_log, trace_chain),
            "completion_log": completion_log,
            "trace_status": trace_chain.get("trace_status") or self._trace_status(trace_chain),
        }

    def _trace_chain(
        self,
        event: dict[str, Any],
        task: dict[str, Any],
        hr_item: dict[str, Any],
        unified_task: dict[str, Any],
    ) -> dict[str, Any]:
        chain = event.get("trace_chain") if isinstance(event.get("trace_chain"), dict) else event.get("event_chain")
        chain = dict(chain) if isinstance(chain, dict) else {}
        evidence = self._source_evidence(event, task, hr_item, unified_task)
        self._fill_trace_value(chain, "source_file", evidence.get("source_file") or "")
        self._fill_trace_value(chain, "source_row", evidence.get("row_number") or evidence.get("row_id") or "")
        self._fill_trace_value(chain, "row_id", evidence.get("row_id") or evidence.get("row_number") or "")
        self._fill_trace_value(chain, "source_record_id", evidence.get("record_id") or event.get("source_record_id") or "")
        self._fill_trace_value(chain, "ingestion_event_id", event.get("ingestion_event_id") or evidence.get("ingestion_event_id") or "")
        self._fill_trace_value(chain, "business_event_id", event.get("business_event_id") or task.get("business_event_id") or hr_item.get("business_event_id") or "")
        self._fill_trace_value(chain, "workflow_task_id", task.get("workflow_task_id") or unified_task.get("workflow_task_id") or "")
        self._fill_trace_value(chain, "hr_execution_id", hr_item.get("hr_execution_id") or unified_task.get("hr_execution_id") or "")
        chain["trace_status"] = self._trace_status(chain)
        return chain

    def _fill_trace_value(self, chain: dict[str, Any], key: str, value: Any) -> None:
        if not chain.get(key) and value not in {"", None}:
            chain[key] = str(value)

    def _source_evidence(self, *items: dict[str, Any]) -> dict[str, Any]:
        for item in items:
            evidence = item.get("source_evidence") if isinstance(item.get("source_evidence"), dict) else {}
            if evidence:
                normalized = dict(evidence)
                normalized.setdefault("row_id", normalized.get("row_number") or "")
                normalized.setdefault("ingestion_event_id", item.get("ingestion_event_id") or "")
                return normalized
        return {}

    def _stage_sequence(
        self,
        occurred_at: str,
        event: dict[str, Any],
        task: dict[str, Any],
        hr_item: dict[str, Any],
        completion_log: dict[str, Any],
        trace_chain: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            {
                "stage": "data_import",
                "at": occurred_at,
                "id": trace_chain.get("ingestion_event_id") or "",
                "status": "source_recorded" if trace_chain.get("source_file") else "source_partial",
            },
            {
                "stage": "business_event",
                "at": event.get("created_at") or occurred_at,
                "id": trace_chain.get("business_event_id") or "",
                "status": event.get("status") or "event_generated",
            },
            {
                "stage": "workflow_distribution",
                "at": task.get("created_at") or occurred_at,
                "id": trace_chain.get("workflow_task_id") or "",
                "status": task.get("distribution_status") or task.get("status") or "not_distributed",
            },
            {
                "stage": "hr_execution",
                "at": hr_item.get("created_at") or occurred_at,
                "id": trace_chain.get("hr_execution_id") or "",
                "status": hr_item.get("execution_status") or "not_assigned",
            },
            {
                "stage": "completion",
                "at": completion_log.get("completed_at") or "",
                "id": completion_log.get("completion_id") or "",
                "status": completion_log.get("completion_status") or "not_completed",
            },
        ]

    def _completion_log(
        self,
        event: dict[str, Any],
        task: dict[str, Any],
        hr_item: dict[str, Any],
        unified_task: dict[str, Any],
    ) -> dict[str, Any]:
        status = str(
            hr_item.get("execution_status")
            or unified_task.get("execution_status")
            or task.get("distribution_status")
            or event.get("status")
            or "not_completed"
        )
        completed = status == "completed"
        return {
            "completion_id": str(hr_item.get("completion_id") or unified_task.get("completion_id") or ""),
            "completion_status": status,
            "completed": completed,
            "completed_at": str(hr_item.get("completed_at") or unified_task.get("completed_at") or ""),
            "result": str(hr_item.get("result") or unified_task.get("result") or ""),
            "source": "hr_execution_items",
        }

    def _occurred_at(self, *items: dict[str, Any]) -> str:
        for item in items:
            for key in ("occurred_at", "created_at", "timestamp", "updated_at"):
                value = item.get(key)
                if value:
                    return str(value)
        return now_iso()

    def _apply_filters(
        self,
        rows: list[dict[str, Any]],
        *,
        date: str | None,
        start_date: str | None,
        end_date: str | None,
        workspace_key: str | None,
        event_type: str | None,
    ) -> list[dict[str, Any]]:
        start = date or start_date or ""
        end = date or end_date or ""
        filtered: list[dict[str, Any]] = []
        for row in rows:
            row_date = str(row.get("date") or "")
            if start and row_date and row_date < start:
                continue
            if end and row_date and row_date > end:
                continue
            if workspace_key and row.get("workspace_key") != workspace_key:
                continue
            if event_type and row.get("event_type") != event_type:
                continue
            filtered.append(row)
        return filtered

    def _multidimensional_history(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "room_history": self._history_bucket(rows, "room"),
            "finance_history": self._history_bucket(rows, "finance"),
            "sales_history": self._history_bucket(rows, "sales"),
            "service_history": self._history_bucket(rows, "service"),
            "hr_history": self._history_bucket(rows, "hr"),
        }

    def _history_bucket(self, rows: list[dict[str, Any]], domain: str) -> dict[str, Any]:
        items = [row for row in rows if row.get("domain") == domain]
        return {
            "domain": domain,
            "count": len(items),
            "by_status": self._count_by(items, "status"),
            "by_workspace": self._count_by(items, "workspace_key"),
            "items": items[:50],
        }

    def _boss_history_analysis(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        today = datetime.now().astimezone().date()
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        yesterday_rows = [row for row in rows if row.get("date") == yesterday.isoformat()]
        week_rows = [row for row in rows if str(row.get("date") or "") >= week_start.isoformat()]
        return {
            "yesterday_summary": self._period_summary(yesterday_rows),
            "this_week_summary": self._period_summary(week_rows),
            "risk_history": self._risk_rows(rows)[:50],
            "completion_rate_trend": self._completion_rate_trend(rows),
        }

    def _period_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "event_count": len(rows),
            "by_domain": self._count_by(rows, "domain"),
            "by_status": self._count_by(rows, "status"),
            "completed_count": sum(1 for row in rows if (row.get("completion_log") or {}).get("completed")),
            "unfinished_count": sum(1 for row in rows if not (row.get("completion_log") or {}).get("completed")),
        }

    def _risk_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        risk_status = {"blocked", "needs_user_binding", "pending_identity_binding", "attention_required", "not_assigned"}
        return [
            row
            for row in rows
            if row.get("priority") in {"high", "urgent"}
            or row.get("status") in risk_status
            or row.get("trace_status") != "complete"
        ]

    def _completion_rate_trend(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_date[str(row.get("date") or "unknown")].append(row)
        trend = []
        for date, items in sorted(by_date.items()):
            completed = sum(1 for item in items if (item.get("completion_log") or {}).get("completed"))
            trend.append(
                {
                    "date": date,
                    "total": len(items),
                    "completed": completed,
                    "completion_rate": round(completed / len(items), 4) if items else 0,
                }
            )
        return trend[-30:]

    def _traceability_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        complete = [row for row in rows if row.get("trace_status") in {"complete", "traceable"}]
        partial = [row for row in rows if row.get("trace_status") not in {"complete", "traceable"}]
        missing_completion = [row for row in rows if not (row.get("completion_log") or {}).get("completed")]
        return {
            "complete_chain_count": len(complete),
            "partial_chain_count": len(partial),
            "missing_completion_log_count": len(missing_completion),
            "traceable_count": len(rows) - len(partial),
            "total": len(rows),
            "traceability_rate": round(len(complete) / len(rows), 4) if rows else 1,
        }

    def _date_index(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_date[str(row.get("date") or "unknown")].append(row)
        return [
            {
                "date": date,
                "event_count": len(items),
                "by_domain": self._count_by(items, "domain"),
            }
            for date, items in sorted(by_date.items())
        ]

    def _domain(self, event_type: str) -> str:
        text = str(event_type or "")
        for domain, values in HISTORICAL_DOMAINS.items():
            if text in values or any(token in text for token in values):
                return domain
        if "finance" in text:
            return "finance"
        if "sales" in text or "contract" in text:
            return "sales"
        if "room" in text or "resident" in text or "stay" in text:
            return "room"
        if "service" in text or "care" in text:
            return "service"
        return "hr"

    def _trace_status(self, trace_chain: dict[str, Any]) -> str:
        required = ["source_file", "source_record_id", "ingestion_event_id", "business_event_id", "workflow_task_id", "hr_execution_id"]
        return "traceable" if all(trace_chain.get(key) for key in required) else "partial_trace"

    def _date_part(self, value: str) -> str:
        text = str(value or "")
        if "T" in text:
            return text.split("T", 1)[0]
        if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
            return text[:10]
        return ""

    def _first_by(self, rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            value = str(row.get(key) or "")
            if value and value not in result:
                result[value] = row
        return result

    def _count_by(self, rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = str(row.get(key) or "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def _write_state(self, state: dict[str, Any]) -> None:
        self.history_root.mkdir(parents=True, exist_ok=True)
        (self.history_root / "historical_view_state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _append_audit(self, state: dict[str, Any]) -> None:
        audit_dir = self.live_root / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "schema_version": state["schema_version"],
            "created_at": state["created_at"],
            "mode": state["mode"],
            "counts": state["counts"],
            "traceability": state["traceability"],
            "history_state": state["paths"]["history_state"],
        }
        with (audit_dir / "historical_data_view.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False) + "\n")

    def _stable_id(self, prefix: str, seed: Any) -> str:
        digest = hashlib.sha1(str(seed or prefix).encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"
