from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .core_data_model import CoreDataModelLayer
from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import now_iso


ROOM_ALLOCATION_SCHEMA_VERSION = "oms.v1.room_allocation_engine"
ROOM_ALLOCATION_FLOW = "Entity Model -> RoomAllocationEngine -> Workflow"


class RoomAllocationEngine:
    """Systemize June's room allocation method as a deterministic decision engine."""

    def __init__(self, live_root: str | Path | None = None, operating_root: str | Path | None = None):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.operating_root = Path(operating_root or self.live_root / "operational_core")
        self.engine_root = self.live_root / "room_engine"

    def rebuild_from_entity_model(self, entity_state: dict[str, Any] | None = None) -> dict[str, Any]:
        if entity_state is None:
            entity_state = CoreDataModelLayer(self.live_root, self.operating_root).rebuild_from_saved_state()
        entities = entity_state.get("entities") if isinstance(entity_state.get("entities"), dict) else {}
        rooms = list(entities.get("rooms") or [])
        sales = list(entities.get("sales") or [])
        customers = self._customers(rooms, sales)
        resource_load = self._resource_load(rooms)
        allocations = self._allocate(customers, rooms, resource_load)
        state = {
            "schema_version": ROOM_ALLOCATION_SCHEMA_VERSION,
            "created_at": now_iso(),
            "engine": "RoomAllocationEngine",
            "method": "June Method Engine",
            "flow": ROOM_ALLOCATION_FLOW,
            "input_contract": {
                "room_status": "core_data_model.entities.rooms",
                "customer_priority": "sales/resident/customer entities",
                "checkin_time": "Room.checkin_date",
                "nursing_need": "Room.nursing_need",
                "resource_load": "assigned_staff workload from Room.assigned_staff",
            },
            "rule_model": {
                "customer_priority": "checkin date + nursing need + sales amount + missing room",
                "room_priority": "available room + requested room/type match - staff load",
                "conflict_resolution": "occupied rooms are excluded unless already assigned to the same guest",
                "dynamic_adjustment": "risk flags and adjustment_suggestions are emitted for June workspace execution",
            },
            "input_counts": {
                "rooms": len(rooms),
                "customers": len(customers),
                "resource_load_staff": len(resource_load),
            },
            "allocation_count": len(allocations),
            "allocations": allocations,
            "validation": {
                "manual_room_method_allowed": False,
                "excel_direct_allocation_allowed": False,
                "ui_direct_allocation_allowed": False,
                "status": "active",
            },
            "paths": {
                "allocations": str(self.engine_root / "room_allocation_results.jsonl"),
                "state": str(self.engine_root / "room_allocation_state.json"),
            },
        }
        self._write_state(state)
        return state

    def _customers(self, rooms: list[dict[str, Any]], sales: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_guest: dict[str, dict[str, Any]] = {}
        for room in rooms:
            guest_id = str(room.get("guest_id") or "")
            if not guest_id:
                continue
            customer = by_guest.setdefault(guest_id, self._empty_customer(guest_id, str(room.get("guest_name") or "")))
            customer["guest_name"] = customer["guest_name"] or str(room.get("guest_name") or "")
            customer["requested_room_id"] = customer["requested_room_id"] or str(room.get("room_id") or "")
            customer["checkin_date"] = customer["checkin_date"] or str(room.get("checkin_date") or "")
            customer["checkout_date"] = customer["checkout_date"] or str(room.get("checkout_date") or "")
            customer["nursing_need"] = customer["nursing_need"] or str(room.get("nursing_need") or "")
            customer["source_entity_ids"].append(str(room.get("entity_id") or ""))
            customer["source_record_ids"].append(str(room.get("source_record_id") or ""))
        for sale in sales:
            guest_id = str(sale.get("guest_id") or "")
            if not guest_id:
                continue
            customer = by_guest.setdefault(guest_id, self._empty_customer(guest_id, str(sale.get("guest_name") or "")))
            customer["guest_name"] = customer["guest_name"] or str(sale.get("guest_name") or "")
            customer["requested_room_id"] = customer["requested_room_id"] or str(sale.get("room_id") or "")
            customer["sales_stage"] = str(sale.get("stage") or customer["sales_stage"] or "")
            customer["sales_amount"] = max(float(customer.get("sales_amount") or 0), float(sale.get("amount") or 0))
            customer["source_entity_ids"].append(str(sale.get("entity_id") or ""))
            customer["source_record_ids"].append(str(sale.get("source_record_id") or ""))
        customers = list(by_guest.values())
        for customer in customers:
            customer["source_entity_ids"] = self._unique(customer["source_entity_ids"])
            customer["source_record_ids"] = self._unique(customer["source_record_ids"])
            customer["priority_score"] = self._customer_priority(customer)
        return sorted(customers, key=lambda item: item["priority_score"], reverse=True)

    def _empty_customer(self, guest_id: str, name: str) -> dict[str, Any]:
        return {
            "guest_id": guest_id,
            "guest_name": name,
            "requested_room_id": "",
            "checkin_date": "",
            "checkout_date": "",
            "nursing_need": "",
            "sales_stage": "",
            "sales_amount": 0.0,
            "source_entity_ids": [],
            "source_record_ids": [],
        }

    def _allocate(
        self,
        customers: list[dict[str, Any]],
        rooms: list[dict[str, Any]],
        resource_load: dict[str, int],
    ) -> list[dict[str, Any]]:
        allocations: list[dict[str, Any]] = []
        reserved_room_ids: set[str] = set()
        for rank, customer in enumerate(customers, start=1):
            candidate_rooms = self._candidate_rooms(customer, rooms, reserved_room_ids)
            best = candidate_rooms[0] if candidate_rooms else None
            if best:
                reserved_room_ids.add(str(best["room"].get("room_id") or ""))
            allocation = self._allocation_result(customer, best, rank, resource_load)
            allocations.append(allocation)
        return allocations

    def _candidate_rooms(self, customer: dict[str, Any], rooms: list[dict[str, Any]], reserved_room_ids: set[str]) -> list[dict[str, Any]]:
        requested_room_id = str(customer.get("requested_room_id") or "")
        candidates: list[dict[str, Any]] = []
        for room in rooms:
            room_id = str(room.get("room_id") or "")
            if not room_id or room_id in reserved_room_ids:
                continue
            status = str(room.get("status") or "")
            same_guest = room.get("guest_id") == customer.get("guest_id")
            if status == "在住" and not same_guest:
                continue
            if status not in {"空房", "预订"} and not same_guest:
                continue
            score = self._room_score(customer, room, requested_room_id)
            candidates.append({"room": room, "score": score, "risk_flags": self._room_risks(customer, room)})
        return sorted(candidates, key=lambda item: item["score"], reverse=True)

    def _allocation_result(
        self,
        customer: dict[str, Any],
        best: dict[str, Any] | None,
        rank: int,
        resource_load: dict[str, int],
    ) -> dict[str, Any]:
        room = best["room"] if best else {}
        room_id = str(room.get("room_id") or "")
        risk_flags = list(best.get("risk_flags") or []) if best else ["no_available_room"]
        if not customer.get("checkin_date"):
            risk_flags.append("missing_checkin_date")
        if not room_id:
            suggestions = ["由六月人工确认可用房并处理冲突"]
        elif risk_flags:
            suggestions = ["六月复核风险后确认排房"]
        else:
            suggestions = ["可直接进入排房确认"]
        allocation_id = self._stable_id("alloc", f"{customer.get('guest_id')}:{room_id}:{rank}")
        return {
            "schema_version": "oms.v1.room_allocation_result",
            "allocation_id": allocation_id,
            "engine": "RoomAllocationEngine",
            "method": "June Method Engine",
            "guest_id": customer.get("guest_id") or "",
            "guest_name": customer.get("guest_name") or "",
            "room_id": room_id,
            "room_type": str(room.get("room_type") or ""),
            "priority_rank": rank,
            "priority_score": customer.get("priority_score") or 0,
            "room_score": best.get("score") if best else 0,
            "risk_flags": self._unique(risk_flags),
            "adjustment_suggestions": suggestions,
            "decision_factors": {
                "customer_priority": customer.get("priority_score") or 0,
                "requested_room_id": customer.get("requested_room_id") or "",
                "checkin_date": customer.get("checkin_date") or "",
                "nursing_need": customer.get("nursing_need") or "",
                "sales_amount": customer.get("sales_amount") or 0,
                "resource_load": resource_load,
                "selected_staff_load": resource_load.get(str(room.get("assigned_staff") or ""), 0) if room else 0,
            },
            "source_entity_ids": customer.get("source_entity_ids") or [],
            "source_record_ids": customer.get("source_record_ids") or [],
            "workflow_target": {
                "workspace_key": "june",
                "workspace": "店总工作台",
                "next_action": "确认排房结果并处理风险",
            },
            "created_at": now_iso(),
        }

    def _customer_priority(self, customer: dict[str, Any]) -> int:
        score = 10
        if customer.get("checkin_date"):
            score += 35
        if customer.get("nursing_need"):
            score += 25
        if not customer.get("requested_room_id"):
            score += 20
        if customer.get("sales_stage") in {"签约", "转化"}:
            score += 15
        amount = float(customer.get("sales_amount") or 0)
        if amount:
            score += min(20, int(amount // 5000))
        return score

    def _room_score(self, customer: dict[str, Any], room: dict[str, Any], requested_room_id: str) -> int:
        score = 0
        if room.get("status") == "空房":
            score += 60
        if room.get("status") == "预订":
            score += 30
        if requested_room_id and requested_room_id == room.get("room_id"):
            score += 40
        need = str(customer.get("nursing_need") or "")
        room_text = f"{room.get('room_id') or ''} {room.get('room_type') or ''}"
        if need and any(token in room_text for token in ["南", "北", "双卫", "单卫", "套"] if token in need):
            score += 15
        if room.get("assigned_staff"):
            score -= 5
        return score

    def _room_risks(self, customer: dict[str, Any], room: dict[str, Any]) -> list[str]:
        risks: list[str] = []
        if room.get("status") == "预订" and room.get("guest_id") != customer.get("guest_id"):
            risks.append("reserved_room_conflict")
        if customer.get("requested_room_id") and customer.get("requested_room_id") != room.get("room_id"):
            risks.append("requested_room_adjusted")
        if not room.get("room_id"):
            risks.append("missing_room_id")
        return risks

    def _resource_load(self, rooms: list[dict[str, Any]]) -> dict[str, int]:
        load: dict[str, int] = {}
        for room in rooms:
            staff = str(room.get("assigned_staff") or "").strip()
            if not staff:
                continue
            load[staff] = load.get(staff, 0) + 1
        return load

    def _write_state(self, state: dict[str, Any]) -> None:
        self.engine_root.mkdir(parents=True, exist_ok=True)
        self._write_jsonl(self.engine_root / "room_allocation_results.jsonl", state["allocations"])
        (self.engine_root / "room_allocation_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result

    def _stable_id(self, prefix: str, value: Any) -> str:
        digest = hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"
