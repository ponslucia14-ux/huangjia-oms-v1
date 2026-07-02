from __future__ import annotations

from typing import Any

from .schemas import EVENT_SCHEMA_VERSION, BusinessEvent, now_iso


MODULE_SUBSCRIPTIONS = {
    "sales_event": ["sales_module"],
    "room_status_event": ["room_status_module"],
    "financial_event": ["finance_module"],
    "service_event": ["service_module"],
}


class EventEngine:
    """Convert structured parser JSON into one or more business events."""

    def build_event_stream(self, parsed_json: dict[str, Any]) -> dict[str, Any]:
        events = self.to_events(parsed_json)
        return {
            "schema_version": "oms.v1.event_stream",
            "input_id": parsed_json.get("input", {}).get("input_id"),
            "flow": ["input", "parsed_json", "business_events", "dispatch"],
            "events": [event.to_dict() for event in events],
            "dispatch": self.dispatch(events),
            "audit": {
                "created_at": now_iso(),
                "event_count": len(events),
                "multi_event": len(events) > 1,
            },
        }

    def to_events(self, parsed_json: dict[str, Any]) -> list[BusinessEvent]:
        text = parsed_json.get("text_extraction", {}).get("text", "") or parsed_json.get("input", {}).get("text", "")
        structured = parsed_json.get("structured_data", {})
        entities = parsed_json.get("entities", {})
        source = self._source(parsed_json)
        timestamp = self._timestamp(parsed_json)
        events: list[BusinessEvent] = []

        if self._has_sales_signal(text, structured):
            events.append(
                self._event(
                    "sales_event",
                    source,
                    "contract",
                    "contract_signed",
                    {
                        "customer_name": structured.get("customer_name") or self._first(entities.get("people", [])),
                        "contract_number": structured.get("contract_number") or self._first(entities.get("contract_numbers", [])),
                        "contract_amount": structured.get("contract_amount"),
                        "package_or_room_hint": structured.get("package_or_room_hint"),
                        "raw_summary": structured.get("raw_summary"),
                    },
                    timestamp,
                )
            )

        if self._has_financial_signal(text, parsed_json):
            action = "payment_received" if self._has_any(text, ["收款", "到账", "转账", "定金", "尾款", "押金"]) else "reimbursement_submitted"
            entity = "reimbursement" if action == "reimbursement_submitted" else "payment"
            events.append(
                self._event(
                    "financial_event",
                    source,
                    entity,
                    action,
                    {
                        "amount": self._financial_amount(text, entities, structured, action),
                        "payment_type": structured.get("payment_type") or self._payment_type(text),
                        "payment_date": structured.get("payment_date") or structured.get("expense_date") or self._first(entities.get("dates", [])),
                        "payment_channel": structured.get("payment_channel") or structured.get("platform"),
                        "contract_number": structured.get("contract_number") or self._first(entities.get("contract_numbers", [])),
                        "department": structured.get("department") or self._first(entities.get("departments", [])),
                        "raw_summary": structured.get("raw_summary"),
                    },
                    timestamp,
                )
            )

        if self._has_room_signal(text):
            events.append(
                self._event(
                    "room_status_event",
                    source,
                    "room_or_stay",
                    "room_status_changed",
                    {
                        "customer_name": structured.get("customer_name") or self._first(entities.get("people", [])),
                        "dates": entities.get("dates", []),
                        "room_hint": self._hint(text, ["房间", "房态", "入住", "出馆", "待入住", "排房"]),
                        "raw_summary": structured.get("raw_summary"),
                    },
                    timestamp,
                )
            )

        if self._has_service_signal(text):
            events.append(
                self._event(
                    "service_event",
                    source,
                    "service",
                    "service_recorded",
                    {
                        "customer_name": structured.get("customer_name") or self._first(entities.get("people", [])),
                        "service_hint": self._hint(text, ["照护", "管家", "跟家", "院陪", "月嫂", "服务", "护理", "备注"]),
                        "dates": entities.get("dates", []),
                        "raw_summary": structured.get("raw_summary"),
                    },
                    timestamp,
                )
            )

        if not events:
            events.append(
                self._event(
                    "service_event",
                    source,
                    "note",
                    "note_recorded",
                    {"raw_summary": structured.get("raw_summary"), "needs_human_review": True},
                    timestamp,
                )
            )
        return events

    def dispatch(self, events: list[BusinessEvent]) -> dict[str, list[dict[str, str]]]:
        dispatched: dict[str, list[dict[str, str]]] = {}
        for event in events:
            for module in event.subscriptions:
                dispatched.setdefault(module, []).append({"event_id": event.event_id, "event_type": event.event_type, "action": event.action})
        return dispatched

    def _event(self, event_type: str, source: str, entity: str, action: str, payload: dict[str, Any], timestamp: str) -> BusinessEvent:
        return BusinessEvent(
            event_type=event_type,
            source=source,
            entity=entity,
            action=action,
            payload=payload,
            timestamp=timestamp,
            subscriptions=MODULE_SUBSCRIPTIONS.get(event_type, []),
        )

    def _source(self, parsed_json: dict[str, Any]) -> str:
        input_data = parsed_json.get("input", {})
        return input_data.get("source") or "unknown"

    def _timestamp(self, parsed_json: dict[str, Any]) -> str:
        return parsed_json.get("input", {}).get("received_at") or now_iso()

    def _has_sales_signal(self, text: str, structured: dict[str, Any]) -> bool:
        return bool(structured.get("contract_number") or self._has_any(text, ["合同", "签约", "预定", "套餐", "全款费用"]))

    def _has_financial_signal(self, text: str, parsed_json: dict[str, Any]) -> bool:
        entities = parsed_json.get("entities", {})
        return bool(entities.get("amounts")) and self._has_any(
            text,
            ["收款", "到账", "转账", "定金", "尾款", "全款", "押金", "报销", "采购", "费用", "付款", "发票", "单据"],
        )

    def _has_room_signal(self, text: str) -> bool:
        return self._has_any(text, ["房态", "房间", "入住", "出馆", "待入住", "排房", "上户", "下户"])

    def _has_service_signal(self, text: str) -> bool:
        return self._has_any(text, ["照护", "管家", "跟家", "院陪", "月嫂", "服务", "护理", "备注"])

    def _has_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _first(self, values: list[Any]) -> Any:
        return values[0] if values else None

    def _financial_amount(self, text: str, entities: dict[str, Any], structured: dict[str, Any], action: str) -> dict[str, Any] | None:
        if action == "reimbursement_submitted":
            return structured.get("expense_amount") or self._first(entities.get("amounts", []))
        if structured.get("amount"):
            return structured.get("amount")

        amounts = entities.get("amounts", [])
        if len(amounts) <= 1:
            return self._first(amounts) or structured.get("contract_amount")

        payment_anchor = self._first_existing_index(text, ["收款", "到账", "转账", "定金", "尾款", "押金"])
        if payment_anchor is None:
            return self._first(amounts)

        best = None
        best_distance = None
        for amount in amounts:
            raw = amount.get("raw", "")
            idx = text.find(raw)
            if idx < 0:
                continue
            distance = abs(idx - payment_anchor)
            if best_distance is None or distance < best_distance:
                best = amount
                best_distance = distance
        return best or self._first(amounts)

    def _first_existing_index(self, text: str, keywords: list[str]) -> int | None:
        indexes = [text.find(keyword) for keyword in keywords if text.find(keyword) >= 0]
        return min(indexes) if indexes else None

    def _payment_type(self, text: str) -> str | None:
        for keyword in ["定金", "尾款", "全款", "押金", "收款", "到账", "转账"]:
            if keyword in text:
                return keyword
        return None

    def _hint(self, text: str, keywords: list[str]) -> str | None:
        for keyword in keywords:
            idx = text.find(keyword)
            if idx >= 0:
                return text[max(0, idx - 16) : min(len(text), idx + 32)].replace("\n", " ")
        return None
