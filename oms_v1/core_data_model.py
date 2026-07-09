from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import now_iso
from .truth_source import TruthSourceStore


CORE_DATA_MODEL_SCHEMA_VERSION = "oms.v1.core_data_model"
CORE_DATA_MODEL_FLOW = "OMS_TRUTH_SOURCE -> Entity Model -> Business Event"


class CoreDataModelLayer:
    """Normalize source rows into OMS core entities before business events are built."""

    def __init__(self, live_root: str | Path | None = None, operating_root: str | Path | None = None):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")
        self.entity_root = self.live_root / "core_data_model"
        self.truth_store = TruthSourceStore(self.live_root, self.operating_root)

    def rebuild_from_saved_state(self) -> dict[str, Any]:
        work_items = self.truth_store.read_work_items()
        financial_events = self.truth_store.read_financial_events()
        rooms = self._room_entities(work_items)
        finances = self._finance_entities(work_items, financial_events)
        sales = self._sales_entities(work_items)
        entity_index = self._entity_index(rooms, finances, sales)
        state = {
            "schema_version": CORE_DATA_MODEL_SCHEMA_VERSION,
            "created_at": now_iso(),
            "mode": "entity_driven_runtime",
            "flow": CORE_DATA_MODEL_FLOW,
            "source_of_truth": "OMS_TRUTH_SOURCE",
            "truth_source": self.truth_store.summary(),
            "entities": {
                "rooms": rooms,
                "finances": finances,
                "sales": sales,
            },
            "entity_index": entity_index,
            "counts": {
                "rooms": len(rooms),
                "finances": len(finances),
                "sales": len(sales),
                "source_records": len(entity_index["source_records"]),
            },
            "validation": {
                "excel_direct_to_ui_allowed": False,
                "aggregate_as_truth_source_allowed": False,
                "ui_direct_excel_read_allowed": False,
                "entity_model_required_before_business_event": True,
                "status": "active",
                "runtime_source": "OMS_TRUTH_SOURCE",
            },
            "paths": {
                "rooms": str(self.truth_store.room_path),
                "finances": str(self.truth_store.finance_path),
                "sales": str(self.truth_store.sales_path),
                "entity_index": str(self.entity_root / "entity_index.json"),
                "state": str(self.entity_root / "core_data_model_state.json"),
            },
        }
        self._write_state(state)
        return state

    def _room_entities(self, work_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rooms: list[dict[str, Any]] = []
        for item in work_items:
            source_record = self._source_record(item)
            source_type = str(source_record.get("source_type") or "")
            if source_type not in {"resident", "room_status", "contracts", "sales_detail"}:
                continue
            normalized = self._normalized(source_record)
            raw_row = self._raw_row(source_record)
            room_id = self._first_value(
                normalized,
                raw_row,
                ["room", "room_id", "房间", "房间号", "房号", "房型", "房态"],
            )
            customer_name = self._first_value(normalized, raw_row, ["customer_name", "guest", "客户", "客户姓名", "姓名", "妈妈姓名", "签约客户"])
            if not room_id and not customer_name:
                continue
            evidence = self._source_evidence(item, source_record)
            status = self._room_status(source_type, normalized, raw_row)
            room_type = self._room_type(room_id, normalized, raw_row)
            guest_id = self._guest_id(customer_name)
            rooms.append(
                {
                    "schema_version": "oms.v1.entity.room",
                    "entity_type": "room",
                    "entity_id": self._stable_id("room_ent", f"{evidence.get('record_id')}:{room_id}:{guest_id}"),
                    "room_id": room_id,
                    "room_type": room_type,
                    "status": status,
                    "guest_id": guest_id,
                    "guest_name": customer_name,
                    "checkin_date": self._first_value(normalized, raw_row, ["checkin_date", "入住时间", "入住日期", "入住"]),
                    "checkout_date": self._first_value(normalized, raw_row, ["checkout_date", "出馆时间", "出馆日期", "退房日期"]),
                    "assigned_staff": self._first_value(normalized, raw_row, ["assigned_staff", "管家", "照护师", "护理师"]),
                    "nursing_need": self._first_value(normalized, raw_row, ["nursing_need", "service_note", "产康套餐", "需求", "服务", "备注"]),
                    "source_record_id": str(source_record.get("record_id") or evidence.get("record_id") or ""),
                    "source_type": source_type,
                    "source_evidence": evidence,
                    "created_at": now_iso(),
                }
            )
        return rooms

    def _finance_entities(self, work_items: list[dict[str, Any]], financial_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        finances: list[dict[str, Any]] = []
        seen_events: set[str] = set()
        for event in financial_events:
            entity = self._finance_entity_from_event(event)
            finances.append(entity)
            if event.get("financial_event_id"):
                seen_events.add(str(event["financial_event_id"]))
        for item in work_items:
            source_record = self._source_record(item)
            if not isinstance(source_record.get("finance_mapping"), dict):
                continue
            if item.get("financial_event_id") and str(item["financial_event_id"]) in seen_events:
                continue
            finances.append(self._finance_entity_from_record(item, source_record))
        return finances

    def _sales_entities(self, work_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sales: list[dict[str, Any]] = []
        for item in work_items:
            source_record = self._source_record(item)
            source_type = str(source_record.get("source_type") or "")
            if source_type not in {"contracts", "sales_detail", "sales_commission"}:
                continue
            normalized = self._normalized(source_record)
            raw_row = self._raw_row(source_record)
            customer_name = self._first_value(normalized, raw_row, ["customer_name", "guest", "客户", "客户姓名", "姓名", "妈妈姓名", "签约客户"])
            contract_id = self._first_value(normalized, raw_row, ["contract_no", "contract_id", "合同", "合同号", "合同编号", "订单号"])
            amount = self._number(self._first_value(normalized, raw_row, ["amount", "金额", "价格", "合同金额", "收款", "定金", "尾款"]))
            evidence = self._source_evidence(item, source_record)
            assignment = self._assignment(item, source_record)
            guest_id = self._guest_id(customer_name)
            sales.append(
                {
                    "schema_version": "oms.v1.entity.sales",
                    "entity_type": "sales",
                    "entity_id": self._stable_id("sales_ent", f"{evidence.get('record_id')}:{contract_id}:{guest_id}"),
                    "contract_id": contract_id or self._stable_id("contract", evidence.get("record_id")),
                    "guest_id": guest_id,
                    "guest_name": customer_name,
                    "room_id": self._first_value(normalized, raw_row, ["room", "room_id", "房间", "房号", "房型"]),
                    "stage": self._sales_stage(source_type, normalized, raw_row, amount),
                    "amount": amount,
                    "salesperson_id": str(assignment.get("user_id") or ""),
                    "salesperson_name": str(assignment.get("name") or ""),
                    "source_record_id": str(source_record.get("record_id") or evidence.get("record_id") or ""),
                    "source_type": source_type,
                    "source_evidence": evidence,
                    "created_at": now_iso(),
                }
            )
        return sales

    def _finance_entity_from_event(self, event: dict[str, Any]) -> dict[str, Any]:
        evidence = event.get("source_evidence") if isinstance(event.get("source_evidence"), dict) else {}
        amount = self._number(event.get("amount"))
        income = self._number(event.get("income_amount"))
        expense = self._number(event.get("expense_amount"))
        tx_type = self._finance_type(event.get("event_type"), income, expense)
        return {
            "schema_version": "oms.v1.entity.finance",
            "entity_type": "finance",
            "entity_id": self._stable_id("fin_ent", event.get("financial_event_id") or event.get("record_id") or evidence.get("record_id")),
            "tx_id": str(event.get("financial_event_id") or event.get("record_id") or ""),
            "type": tx_type,
            "amount": amount or income or expense,
            "related_guest": str(event.get("customer_name") or ""),
            "related_room": "",
            "timestamp": str(event.get("occurred_at") or event.get("created_at") or ""),
            "source_record_id": str(event.get("record_id") or evidence.get("record_id") or ""),
            "source_type": str(event.get("source_type") or evidence.get("source_type") or "financial_event"),
            "source_evidence": evidence,
            "created_at": now_iso(),
        }

    def _finance_entity_from_record(self, item: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalized(source_record)
        raw_row = self._raw_row(source_record)
        evidence = self._source_evidence(item, source_record)
        amount = self._number(self._first_value(normalized, raw_row, ["amount", "金额", "价格"]))
        income = self._number(self._first_value(normalized, raw_row, ["income_amount", "收入", "收入金额", "实际到账金额"]))
        expense = self._number(self._first_value(normalized, raw_row, ["expense_amount", "支出", "支出金额", "退款", "退费"]))
        return {
            "schema_version": "oms.v1.entity.finance",
            "entity_type": "finance",
            "entity_id": self._stable_id("fin_ent", f"{evidence.get('record_id')}:{amount}:{income}:{expense}"),
            "tx_id": str(item.get("financial_event_id") or source_record.get("record_id") or evidence.get("record_id") or ""),
            "type": self._finance_type(source_record.get("source_type"), income, expense),
            "amount": amount or income or expense,
            "related_guest": self._first_value(normalized, raw_row, ["customer_name", "客户", "宝妈", "姓名"]),
            "related_room": self._first_value(normalized, raw_row, ["room", "房间", "房号"]),
            "timestamp": self._first_value(normalized, raw_row, ["date", "日期", "签约日期"]),
            "source_record_id": str(source_record.get("record_id") or evidence.get("record_id") or ""),
            "source_type": str(source_record.get("source_type") or evidence.get("source_type") or ""),
            "source_evidence": evidence,
            "created_at": now_iso(),
        }

    def _entity_index(self, rooms: list[dict[str, Any]], finances: list[dict[str, Any]], sales: list[dict[str, Any]]) -> dict[str, Any]:
        source_records: dict[str, dict[str, list[str]]] = {}
        guest_index: dict[str, dict[str, list[str]]] = {}
        room_index: dict[str, list[str]] = {}

        def add_record(record_id: str, entity_type: str, entity_id: str) -> None:
            if not record_id:
                return
            source_records.setdefault(record_id, {"rooms": [], "finances": [], "sales": [], "guest_ids": [], "room_ids": []})
            source_records[record_id][self._plural(entity_type)].append(entity_id)

        for room in rooms:
            add_record(str(room.get("source_record_id") or ""), "room", room["entity_id"])
            if room.get("guest_id"):
                guest_index.setdefault(str(room["guest_id"]), {"rooms": [], "finances": [], "sales": []})["rooms"].append(room["entity_id"])
                source_records[str(room.get("source_record_id") or "")]["guest_ids"].append(str(room["guest_id"]))
            if room.get("room_id"):
                room_index.setdefault(str(room["room_id"]), []).append(room["entity_id"])
                source_records[str(room.get("source_record_id") or "")]["room_ids"].append(str(room["room_id"]))
        for finance in finances:
            add_record(str(finance.get("source_record_id") or ""), "finance", finance["entity_id"])
            guest_id = self._guest_id(str(finance.get("related_guest") or ""))
            if guest_id:
                guest_index.setdefault(guest_id, {"rooms": [], "finances": [], "sales": []})["finances"].append(finance["entity_id"])
                source_records[str(finance.get("source_record_id") or "")]["guest_ids"].append(guest_id)
        for sale in sales:
            add_record(str(sale.get("source_record_id") or ""), "sales", sale["entity_id"])
            if sale.get("guest_id"):
                guest_index.setdefault(str(sale["guest_id"]), {"rooms": [], "finances": [], "sales": []})["sales"].append(sale["entity_id"])
                source_records[str(sale.get("source_record_id") or "")]["guest_ids"].append(str(sale["guest_id"]))
            if sale.get("room_id"):
                source_records[str(sale.get("source_record_id") or "")]["room_ids"].append(str(sale["room_id"]))

        for value in source_records.values():
            for key, items in value.items():
                value[key] = self._unique(items)
        for value in guest_index.values():
            for key, items in value.items():
                value[key] = self._unique(items)
        for key, items in list(room_index.items()):
            room_index[key] = self._unique(items)
        return {
            "schema_version": "oms.v1.entity_index",
            "source_records": source_records,
            "guest_index": guest_index,
            "room_index": room_index,
        }

    def _source_record(self, item: dict[str, Any]) -> dict[str, Any]:
        for key in ("excel_record", "finance_record", "record"):
            value = item.get(key)
            if isinstance(value, dict):
                return value
        return {}

    def _source_evidence(self, item: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence")
        if not isinstance(evidence, dict):
            evidence = source_record.get("source_evidence")
        if isinstance(evidence, dict):
            return dict(evidence)
        return {}

    def _normalized(self, source_record: dict[str, Any]) -> dict[str, Any]:
        value = source_record.get("normalized")
        return value if isinstance(value, dict) else {}

    def _raw_row(self, source_record: dict[str, Any]) -> dict[str, Any]:
        value = source_record.get("raw_row")
        return value if isinstance(value, dict) else {}

    def _assignment(self, item: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
        value = source_record.get("assignment")
        if isinstance(value, dict):
            return value
        return {"user_id": item.get("user_id") or "", "name": item.get("name") or ""}

    def _first_value(self, normalized: dict[str, Any], raw_row: dict[str, Any], names: list[str]) -> str:
        for name in names:
            value = normalized.get(name)
            if value not in {"", None}:
                return str(value)
        for name in names:
            value = raw_row.get(name)
            if value not in {"", None}:
                return str(value)
        return ""

    def _room_status(self, source_type: str, normalized: dict[str, Any], raw_row: dict[str, Any]) -> str:
        text = " ".join(str(value or "") for value in [source_type, *normalized.values(), *raw_row.values()])
        if any(word in text for word in ["在住", "入住", "occupied"]):
            return "在住"
        if any(word in text for word in ["空房", "空", "available", "vacant"]):
            return "空房"
        if any(word in text for word in ["预订", "待排", "预约", "booked", "reserved"]):
            return "预订"
        if source_type == "resident":
            return "在住"
        if source_type in {"contracts", "sales_detail"}:
            return "预订"
        return "空房"

    def _room_type(self, room_id: str, normalized: dict[str, Any], raw_row: dict[str, Any]) -> str:
        explicit = self._first_value(normalized, raw_row, ["room_type", "房型", "套餐", "产康套餐"])
        if explicit:
            return explicit
        text = str(room_id or "")
        if "南" in text:
            return "南向"
        if "北" in text:
            return "北向"
        if "双卫" in text:
            return "双卫"
        if "单卫" in text:
            return "单卫"
        return ""

    def _sales_stage(self, source_type: str, normalized: dict[str, Any], raw_row: dict[str, Any], amount: float) -> str:
        text = " ".join(str(value or "") for value in [source_type, *normalized.values(), *raw_row.values()])
        if "流失" in text:
            return "流失"
        if amount or any(word in text for word in ["转化", "成交"]):
            return "转化"
        if source_type == "contracts" or any(word in text for word in ["签约", "合同"]):
            return "签约"
        return "线索"

    def _finance_type(self, marker: Any, income: float, expense: float) -> str:
        text = str(marker or "")
        if "应付" in text or "payable" in text:
            return "应付"
        if "应收" in text or "receivable" in text:
            return "应收"
        if expense:
            return "支出"
        if income:
            return "收入"
        if any(word in text for word in ["expense", "refund", "wage", "commission"]):
            return "支出"
        return "收入"

    def _guest_id(self, name: str) -> str:
        text = str(name or "").strip()
        return self._stable_id("guest", text) if text else ""

    def _number(self, value: Any) -> float:
        if value in {"", None}:
            return 0.0
        try:
            return float(str(value).replace(",", "").replace("￥", "").replace("¥", "").strip())
        except ValueError:
            return 0.0

    def _plural(self, entity_type: str) -> str:
        return {"room": "rooms", "finance": "finances", "sales": "sales"}[entity_type]

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result

    def _read_saved_work_items(self) -> list[dict[str, Any]]:
        return self.truth_store.read_work_items()

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

    def _write_state(self, state: dict[str, Any]) -> None:
        self.entity_root.mkdir(parents=True, exist_ok=True)
        room_domain = self.truth_store.read_domain("room")
        room_domain["entities"] = self._merge_truth_entities(room_domain.get("entities") or [], state["entities"]["rooms"])
        self.truth_store.write_domain("room", room_domain)
        finance_domain = self.truth_store.read_domain("finance")
        finance_domain["entities"] = self._merge_truth_entities(finance_domain.get("entities") or [], state["entities"]["finances"])
        self.truth_store.write_domain("finance", finance_domain)
        sales_domain = self.truth_store.read_domain("sales")
        sales_domain["entities"] = self._merge_truth_entities(sales_domain.get("entities") or [], state["entities"]["sales"])
        self.truth_store.write_domain("sales", sales_domain)
        self._write_jsonl(self.entity_root / "rooms.jsonl", state["entities"]["rooms"])
        self._write_jsonl(self.entity_root / "finances.jsonl", state["entities"]["finances"])
        self._write_jsonl(self.entity_root / "sales.jsonl", state["entities"]["sales"])
        (self.entity_root / "entity_index.json").write_text(json.dumps(state["entity_index"], ensure_ascii=False, indent=2), encoding="utf-8")
        (self.entity_root / "core_data_model_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _merge_truth_entities(self, existing: list[dict[str, Any]], generated: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for item in generated:
            if isinstance(item, dict):
                merged[self._entity_merge_key(item)] = item
        for item in existing:
            if isinstance(item, dict) and self._has_source_evidence(item):
                merged[self._entity_merge_key(item)] = item
        return list(merged.values())

    def _entity_merge_key(self, item: dict[str, Any]) -> str:
        evidence = item.get("source_evidence") if isinstance(item.get("source_evidence"), dict) else {}
        return str(
            item.get("entity_id")
            or item.get("room_id")
            or item.get("contract_id")
            or item.get("tx_id")
            or item.get("source_record_id")
            or evidence.get("record_id")
            or self._stable_id("entity", json.dumps(item, ensure_ascii=False, sort_keys=True))
        )

    def _has_source_evidence(self, item: dict[str, Any]) -> bool:
        evidence = item.get("source_evidence")
        return isinstance(evidence, dict) and bool(
            evidence.get("source_file") and evidence.get("row_number") not in {"", None} and evidence.get("record_id")
        )

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _stable_id(self, prefix: str, value: Any) -> str:
        digest = hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"
