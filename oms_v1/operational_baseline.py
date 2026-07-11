from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .schemas import now_iso


OPERATIONAL_BASELINE_SCHEMA_VERSION = "oms.v1.operational_baseline"
ACTIVE_STAY_STATUS = "IN_STAY"
ROOM_COUNT = 42


class OperationalBaselineBuilder:
    """Build an immutable reality-checked Stay/Room baseline candidate.

    Calendar markers and contract plans are not evidence that a guest is still
    in-house. A Current stay therefore requires an explicit operational
    confirmation before it can make a room OCCUPIED.
    """

    def __init__(self, output_root: str | Path):
        self.output_root = Path(output_root)

    def build(
        self,
        *,
        room_master: list[dict[str, Any]],
        stay_candidates: list[dict[str, Any]],
        snapshot_id: str,
        source_version: str,
        activate: bool = False,
    ) -> dict[str, Any]:
        rooms = self._room_master(room_master)
        current_stays, excluded = self._actual_stays(stay_candidates)
        room_by_id = {item["room_id"]: item for item in rooms}
        anomalies: list[dict[str, Any]] = []

        for stay in current_stays:
            room = room_by_id.get(stay["room_id"])
            if room is None:
                anomalies.append({"code": "stay_room_missing", "stay_id": stay["stay_id"], "room_id": stay["room_id"]})
                continue
            if room["status"] == "OCCUPIED":
                anomalies.append({"code": "room_has_multiple_current_stays", "room_id": stay["room_id"]})
                continue
            room.update(
                {
                    "status": "OCCUPIED",
                    "current_stay_id": stay["stay_id"],
                    "current_customer": stay["customer_name"],
                }
            )

        if len(rooms) != ROOM_COUNT:
            anomalies.append({"code": "room_master_count_invalid", "expected": ROOM_COUNT, "actual": len(rooms)})
        if not current_stays:
            anomalies.append(
                {
                    "code": "actual_stay_current_not_confirmed",
                    "reason": "No stay has explicit in-house confirmation from the operating owner.",
                }
            )
        linked = {item["current_stay_id"] for item in rooms if item["status"] == "OCCUPIED"}
        expected = {item["stay_id"] for item in current_stays}
        if linked != expected:
            anomalies.append({"code": "room_stay_link_mismatch", "room_links": sorted(linked), "stay_ids": sorted(expected)})

        acceptance = "PASS" if not anomalies else "FAIL"
        payload = {
            "schema_version": OPERATIONAL_BASELINE_SCHEMA_VERSION,
            "snapshot_id": snapshot_id,
            "generated_at": now_iso(),
            "effective_date": date.today().isoformat(),
            "source_version": source_version,
            "status": acceptance,
            "active": bool(activate and acceptance == "PASS"),
            "activation_policy": "PASS_AND_EMP001_MOBILE_ACCEPTANCE_REQUIRED",
            "actual_stay_current": current_stays,
            "room_current": rooms if acceptance == "PASS" else [],
            "room_master": rooms,
            "excluded_stay_records": excluded,
            "counts": {
                "actual_stay_current": len(current_stays),
                "occupied_rooms": len(linked),
                "room_master": len(rooms),
                "excluded_stays": len(excluded),
            },
            "unresolved_anomalies": anomalies,
            "previous_snapshot_unchanged": "TS-20260711-V1",
        }
        payload["content_sha256"] = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        self._write_immutable(snapshot_id, payload)
        self._write_state(payload)
        return payload

    @staticmethod
    def _room_master(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rooms: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in records:
            room_id = str(item.get("room_id") or item.get("room_number") or "").strip()
            if not room_id or room_id in seen:
                continue
            seen.add(room_id)
            rooms.append(
                {
                    "room_id": room_id,
                    "room_name": str(item.get("room_name") or room_id).strip(),
                    "status": "AVAILABLE",
                    "current_stay_id": "",
                    "current_customer": "",
                    "active": True,
                    "source_evidence": item.get("source_evidence") or {},
                }
            )
        return rooms

    @staticmethod
    def _actual_stays(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        current: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        seen_stays: set[str] = set()
        seen_rooms: set[str] = set()
        for item in records:
            stay_id = str(item.get("stay_id") or item.get("record_id") or "").strip()
            room_id = str(item.get("room_id") or item.get("room_number") or "").strip()
            status = str(item.get("stay_status") or item.get("status") or "").strip().upper()
            checkout = str(item.get("checkout_date") or item.get("checkout_time") or "").strip()
            active = item.get("active") is True or item.get("is_active") is True
            verified = item.get("reality_verified") is True
            verifier = str(item.get("verified_by_emp_id") or "").strip()
            verified_at = str(item.get("verified_at") or "").strip()
            reasons: list[str] = []
            if not active:
                reasons.append("ACTIVE_NOT_TRUE")
            if status != ACTIVE_STAY_STATUS:
                reasons.append("STATUS_NOT_IN_STAY")
            if checkout:
                reasons.append("CHECKOUT_PRESENT")
            if not verified or not verifier or not verified_at:
                reasons.append("REALITY_CONFIRMATION_MISSING")
            if not stay_id or not room_id:
                reasons.append("IDENTITY_OR_ROOM_MISSING")
            if stay_id in seen_stays:
                reasons.append("DUPLICATE_STAY_ID")
            if room_id in seen_rooms:
                reasons.append("ROOM_ALREADY_OCCUPIED")
            if reasons:
                excluded.append({"stay_id": stay_id, "room_id": room_id, "reasons": reasons, "source_evidence": item.get("source_evidence") or {}})
                continue
            seen_stays.add(stay_id)
            seen_rooms.add(room_id)
            current.append(
                {
                    "stay_id": stay_id,
                    "customer_id": str(item.get("customer_id") or "").strip(),
                    "customer_name": str(item.get("customer_name") or item.get("guest_name") or "").strip(),
                    "room_id": room_id,
                    "checkin_date": str(item.get("checkin_date") or item.get("checkin_time") or "").strip(),
                    "checkout_date": "",
                    "status": ACTIVE_STAY_STATUS,
                    "stay_status": ACTIVE_STAY_STATUS,
                    "active": True,
                    "reality_verified": True,
                    "verified_by_emp_id": verifier,
                    "verified_at": verified_at,
                    "source_evidence": item.get("source_evidence") or {},
                }
            )
        return current, excluded

    def _write_immutable(self, snapshot_id: str, payload: dict[str, Any]) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        target = self.output_root / f"{snapshot_id}.json"
        if target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
            if existing != payload:
                raise FileExistsError(f"Operational baseline snapshot already exists: {snapshot_id}")
            return
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)

    def _write_state(self, payload: dict[str, Any]) -> None:
        state = {
            "schema_version": OPERATIONAL_BASELINE_SCHEMA_VERSION,
            "status": "ACTIVE" if payload["active"] else "BLOCKED",
            "snapshot_id": payload["snapshot_id"],
            "snapshot_file": f"{payload['snapshot_id']}.json",
            "reason": "" if payload["active"] else "REALITY_BASELINE_NOT_CONFIRMED",
            "updated_at": payload["generated_at"],
        }
        target = self.output_root / "operational_baseline_state.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
