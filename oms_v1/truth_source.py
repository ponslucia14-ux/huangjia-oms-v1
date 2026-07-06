from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import now_iso


TRUTH_SOURCE_SCHEMA_VERSION = "oms.v1.truth_source"
TRUTH_SOURCE_DIR_NAME = "OMS_TRUTH_SOURCE"
TRUTH_SOURCE_MODE = "single_source_of_truth"

ROOM_SOURCE_TYPES = {"resident", "room_status"}
FINANCE_SOURCE_TYPES = {
    "checkin_registration",
    "finance_daily",
    "bank_cash_journal",
    "real_income",
    "service_refund",
}
SALES_SOURCE_TYPES = {"contracts", "sales_detail", "sales_commission"}


def default_truth_root(live_root: str | Path | None = None) -> Path:
    configured = os.getenv("OMS_TRUTH_SOURCE_ROOT", "").strip()
    if configured:
        return Path(configured)
    if live_root:
        return Path(live_root).resolve().parent / TRUTH_SOURCE_DIR_NAME
    return Path(__file__).resolve().parents[1] / TRUTH_SOURCE_DIR_NAME


class TruthSourceStore:
    """Canonical runtime data store for OMS.

    Excel and legacy runtime files are input/audit material only. Runtime layers read
    room, finance, sales, and business events from this store.
    """

    def __init__(
        self,
        live_root: str | Path | None = None,
        operating_root: str | Path | None = None,
        truth_root: str | Path | None = None,
    ):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")
        self.root = Path(truth_root) if truth_root else default_truth_root(self.live_root)

    @property
    def room_path(self) -> Path:
        return self.root / "room.json"

    @property
    def finance_path(self) -> Path:
        return self.root / "finance.json"

    @property
    def sales_path(self) -> Path:
        return self.root / "sales.json"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    def read_work_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for domain in ("room", "finance", "sales"):
            items.extend(self.read_domain(domain).get("work_items") or [])
        return [item for item in items if isinstance(item, dict)]

    def read_financial_events(self) -> list[dict[str, Any]]:
        return [item for item in self.read_domain("finance").get("financial_events") or [] if isinstance(item, dict)]

    def read_settlement_records(self) -> list[dict[str, Any]]:
        return [item for item in self.read_domain("finance").get("settlement_records") or [] if isinstance(item, dict)]

    def read_entities(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "rooms": [item for item in self.read_domain("room").get("entities") or [] if isinstance(item, dict)],
            "finances": [item for item in self.read_domain("finance").get("entities") or [] if isinstance(item, dict)],
            "sales": [item for item in self.read_domain("sales").get("entities") or [] if isinstance(item, dict)],
        }

    def read_events(self) -> list[dict[str, Any]]:
        return self._read_jsonl(self.events_path)

    def read_domain(self, domain: str) -> dict[str, Any]:
        path = self._domain_path(domain)
        if not path.exists():
            return self._empty_domain(domain)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return self._empty_domain(domain)
        return data if isinstance(data, dict) else self._empty_domain(domain)

    def append_work_items(
        self,
        work_items: list[dict[str, Any]],
        *,
        financial_events: list[dict[str, Any]] | None = None,
        settlement_records: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        grouped = self._group_work_items(work_items)
        for domain, items in grouped.items():
            data = self.read_domain(domain)
            data["work_items"] = self._dedupe([*(data.get("work_items") or []), *items], self._item_key)
            if domain == "finance":
                data["financial_events"] = self._dedupe(
                    [*(data.get("financial_events") or []), *(financial_events or [])],
                    self._financial_event_key,
                )
                data["settlement_records"] = self._dedupe(
                    [*(data.get("settlement_records") or []), *(settlement_records or [])],
                    self._settlement_key,
                )
            self.write_domain(domain, data)
        self._write_manifest()
        return self.summary()

    def write_domain(self, domain: str, data: dict[str, Any]) -> None:
        payload = self._empty_domain(domain)
        payload.update(data)
        payload["schema_version"] = f"{TRUTH_SOURCE_SCHEMA_VERSION}.{domain}"
        payload["mode"] = TRUTH_SOURCE_MODE
        payload["domain"] = domain
        payload["updated_at"] = now_iso()
        payload["runtime_policy"] = self.runtime_policy()
        self._write_json(self._domain_path(domain), payload)

    def write_events(self, events: list[dict[str, Any]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._write_jsonl(self.events_path, events)
        self._write_manifest()

    def migrate_from_runtime(self) -> dict[str, Any]:
        work_items = self._read_legacy_work_items()
        financial_events = self._read_jsonl(self.live_root / "finance" / "financial_events.jsonl")
        settlement_records = self._read_jsonl(self.live_root / "finance" / "settlement_records.jsonl")
        core_state = self._read_json(self.live_root / "core_data_model" / "core_data_model_state.json")
        entities = core_state.get("entities") if isinstance(core_state.get("entities"), dict) else {}
        grouped = self._group_work_items(work_items)
        self.write_domain(
            "room",
            {
                "work_items": grouped["room"],
                "entities": [item for item in entities.get("rooms") or [] if isinstance(item, dict)],
                "migration_source": "legacy_runtime",
            },
        )
        self.write_domain(
            "finance",
            {
                "work_items": grouped["finance"],
                "financial_events": financial_events,
                "settlement_records": settlement_records,
                "entities": [item for item in entities.get("finances") or [] if isinstance(item, dict)],
                "migration_source": "legacy_runtime",
            },
        )
        self.write_domain(
            "sales",
            {
                "work_items": grouped["sales"],
                "entities": [item for item in entities.get("sales") or [] if isinstance(item, dict)],
                "migration_source": "legacy_runtime",
            },
        )
        events = self._read_jsonl(self.live_root / "business_events" / "business_event_flow.jsonl")
        self.write_events(events)
        return self.summary()

    def summary(self) -> dict[str, Any]:
        room = self.read_domain("room")
        finance = self.read_domain("finance")
        sales = self.read_domain("sales")
        events = self.read_events()
        return {
            "schema_version": TRUTH_SOURCE_SCHEMA_VERSION,
            "mode": TRUTH_SOURCE_MODE,
            "root": str(self.root),
            "runtime_policy": self.runtime_policy(),
            "counts": {
                "room_work_items": len(room.get("work_items") or []),
                "room_entities": len(room.get("entities") or []),
                "finance_work_items": len(finance.get("work_items") or []),
                "financial_events": len(finance.get("financial_events") or []),
                "settlement_records": len(finance.get("settlement_records") or []),
                "finance_entities": len(finance.get("entities") or []),
                "sales_work_items": len(sales.get("work_items") or []),
                "sales_entities": len(sales.get("entities") or []),
                "business_events": len(events),
            },
            "paths": {
                "room": str(self.room_path),
                "finance": str(self.finance_path),
                "sales": str(self.sales_path),
                "events": str(self.events_path),
                "manifest": str(self.manifest_path),
            },
        }

    def runtime_policy(self) -> dict[str, Any]:
        return {
            "runtime_source": "OMS_TRUTH_SOURCE",
            "excel_as_runtime_source_allowed": False,
            "ui_calculation_as_truth_allowed": False,
            "multiple_runtime_sources_allowed": False,
            "legacy_runtime_role": "migration_input_and_audit_only",
        }

    def _write_manifest(self) -> None:
        manifest = self.summary()
        manifest["updated_at"] = now_iso()
        self._write_json(self.manifest_path, manifest)

    def _empty_domain(self, domain: str) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema_version": f"{TRUTH_SOURCE_SCHEMA_VERSION}.{domain}",
            "mode": TRUTH_SOURCE_MODE,
            "domain": domain,
            "updated_at": "",
            "runtime_policy": self.runtime_policy(),
            "work_items": [],
            "entities": [],
        }
        if domain == "finance":
            data["financial_events"] = []
            data["settlement_records"] = []
        return data

    def _domain_path(self, domain: str) -> Path:
        return {"room": self.room_path, "finance": self.finance_path, "sales": self.sales_path}[domain]

    def _group_work_items(self, work_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped = {"room": [], "finance": [], "sales": []}
        for item in work_items:
            if not isinstance(item, dict):
                continue
            domain = self._domain_for_work_item(item)
            grouped[domain].append(item)
        return grouped

    def _domain_for_work_item(self, item: dict[str, Any]) -> str:
        record = self._source_record(item)
        source_type = str(record.get("source_type") or item.get("source_type") or item.get("action_type") or "")
        marker = " ".join(
            str(value or "")
            for value in [
                source_type,
                item.get("role"),
                item.get("workspace"),
                item.get("daily_process"),
                item.get("action_type"),
            ]
        ).lower()
        if source_type in FINANCE_SOURCE_TYPES or item.get("finance_record") or item.get("financial_event_id") or "finance" in marker:
            return "finance"
        if source_type in SALES_SOURCE_TYPES or "sales" in marker or "contract" in marker:
            return "sales"
        if source_type in ROOM_SOURCE_TYPES or "room" in marker or "resident" in marker:
            return "room"
        if item.get("excel_record"):
            return "room"
        return "finance" if "payment" in marker or "collection" in marker else "room"

    def _source_record(self, item: dict[str, Any]) -> dict[str, Any]:
        for key in ("excel_record", "finance_record", "record"):
            value = item.get(key)
            if isinstance(value, dict):
                return value
        return {}

    def _read_legacy_work_items(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in ("daily_work_items.jsonl", "excel_work_items.jsonl", "finance_work_items.jsonl"):
            rows.extend(self._read_jsonl_with_source(self.operating_root / name))
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

    def _read_jsonl_with_source(self, path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line_number, item in enumerate(self._read_jsonl(path), start=1):
            row = dict(item)
            row.setdefault("_runtime_source_file", str(path))
            row.setdefault("_runtime_source_line", line_number)
            rows.append(row)
        return rows

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _dedupe(self, items: list[dict[str, Any]], key_fn: Any) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(key_fn(item) or id(item))
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _item_key(self, item: dict[str, Any]) -> str:
        return str(item.get("work_item_id") or item.get("action_id") or item.get("financial_event_id") or "")

    def _financial_event_key(self, item: dict[str, Any]) -> str:
        return str(item.get("financial_event_id") or item.get("record_id") or "")

    def _settlement_key(self, item: dict[str, Any]) -> str:
        return str(item.get("settlement_id") or item.get("financial_event_id") or item.get("record_id") or "")
