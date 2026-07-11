from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .data_quality import DataHealthInput, DataHealthScorer, TruthSourceSnapshotManager
from .truth_source import TruthSourceStore


PRODUCTION_ADAPTER_SCHEMA_VERSION = "oms.v1.production_data_adapter"
SALES_ADAPTER_ID = "sales_adapter_v1"
FINANCE_ADAPTER_ID = "finance_adapter_v1"
STAY_ADAPTER_ID = "stay_adapter_v1"
ROOM_ADAPTER_ID = "room_adapter_v1"
CAREGIVER_ADAPTER_ID = "caregiver_adapter_v1"
PRODUCTION_MAPPING_VERSION = "p0.9.production_truth.v1"
PRODUCTION_PAGE_SCHEMA_VERSION = "oms.v1.production_page_dataset"


class ProductionDataAdapter:
    """Read-only adapter from OMS_TRUTH_SOURCE into page contract records.

    This adapter is intentionally strict for V1.0 production pages: only records
    with source_file + row_id evidence are exposed to the UI.
    """

    def __init__(self, truth_store: TruthSourceStore, operational_baseline_root: str | Path | None = None):
        self.truth_store = truth_store
        self.operational_baseline_root = Path(operational_baseline_root) if operational_baseline_root else None

    def sales_records(self) -> list[dict[str, Any]]:
        if not self._current_records_allowed():
            return []
        sales_domain = self.truth_store.read_domain("sales")
        entities = [item for item in sales_domain.get("entities") or [] if isinstance(item, dict)]
        verified_entities = [item for item in entities if self._valid_evidence(item.get("source_evidence"))]
        if verified_entities:
            records = [self._sales_record(item) for item in verified_entities]
        else:
            work_items = [item for item in sales_domain.get("work_items") or [] if isinstance(item, dict)]
            records = [self._sales_work_item_record(item) for item in work_items if self._valid_evidence(self._item_evidence(item))]
        return [record for record in records if record]

    def finance_records(self) -> list[dict[str, Any]]:
        if not self._current_records_allowed():
            return []
        finance_domain = self.truth_store.read_domain("finance")
        settlements = [item for item in finance_domain.get("settlement_records") or [] if isinstance(item, dict)]
        verified_settlements = [item for item in settlements if self._valid_evidence(item.get("source_evidence"))]
        if verified_settlements:
            records = [self._finance_record(item) for item in verified_settlements]
        else:
            work_items = [item for item in finance_domain.get("work_items") or [] if isinstance(item, dict)]
            records = [self._finance_work_item_record(item) for item in work_items if self._valid_evidence(self._item_evidence(item))]
        return [record for record in records if record]

    def financial_event_records(self) -> list[dict[str, Any]]:
        if not self._current_records_allowed():
            return []
        finance_domain = self.truth_store.read_domain("finance")
        events = [item for item in finance_domain.get("financial_events") or [] if isinstance(item, dict)]
        records = [self._financial_event_record(item) for item in events if self._valid_evidence(item.get("source_evidence"))]
        return [record for record in records if record]

    def stay_records(self) -> list[dict[str, Any]]:
        if not self._current_records_allowed():
            return []
        baseline_rows = self._operational_baseline_records("actual_stay_current")
        if baseline_rows is not None:
            rows = baseline_rows
        elif self.operational_baseline_root is not None:
            room_domain = self.truth_store.read_domain("room")
            rows = [item for item in room_domain.get("stay_records") or [] if isinstance(item, dict)]
        else:
            stay_domain = self.truth_store.read_domain("stay")
            rows = [item for item in stay_domain.get("stay_records") or [] if isinstance(item, dict)]
            if not rows:
                room_domain = self.truth_store.read_domain("room")
                rows = [item for item in room_domain.get("stay_records") or [] if isinstance(item, dict)]
        return [self._stay_record(item) for item in rows if self._valid_evidence(item.get("source_evidence"))]

    def room_records(self) -> list[dict[str, Any]]:
        if not self._current_records_allowed():
            return []
        room_domain = self.truth_store.read_domain("room")
        rows = [item for item in room_domain.get("room_records") or [] if isinstance(item, dict)]
        return [self._room_record(item) for item in rows if self._valid_evidence(item.get("source_evidence"))]

    def caregiver_records(self) -> list[dict[str, Any]]:
        if not self._current_records_allowed():
            return []
        caregiver_domain = self.truth_store.read_domain("caregiver")
        rows = [item for item in caregiver_domain.get("caregiver_records") or caregiver_domain.get("entities") or [] if isinstance(item, dict)]
        if not rows and self.operational_baseline_root is None:
            room_domain = self.truth_store.read_domain("room")
            rows = [item for item in room_domain.get("caregiver_records") or [] if isinstance(item, dict)]
        return [self._caregiver_record(item) for item in rows if self._valid_evidence(item.get("source_evidence"))]

    def customer_records(self) -> list[dict[str, Any]]:
        if not self._current_records_allowed():
            return []
        customer_domain = self.truth_store.read_domain("customer")
        rows = [item for item in customer_domain.get("customer_records") or [] if isinstance(item, dict)]
        return [self._customer_record(item) for item in rows if self._valid_evidence(item.get("source_evidence"))]

    def contract_records(self) -> list[dict[str, Any]]:
        if not self._current_records_allowed():
            return []
        contract_domain = self.truth_store.read_domain("contract")
        rows = [item for item in contract_domain.get("contract_records") or [] if isinstance(item, dict)]
        return [self._contract_record(item) for item in rows if self._valid_evidence(item.get("source_evidence"))]

    def production_page_dataset(self, dataset: str) -> dict[str, Any]:
        normalized = str(dataset or "").strip().lower()
        if normalized in {"sales", "sales-data"}:
            return self._sales_page_dataset()
        if normalized in {"finance", "financial-events"}:
            return self._finance_page_dataset()
        if normalized in {"rooms", "room", "room-status"}:
            return self._room_page_dataset()
        if normalized in {"contracts", "contract", "customers", "signed-customers"}:
            return self._contract_customer_page_dataset()
        raise ValueError(f"unknown production dataset: {dataset}")

    def sales_metrics(self) -> dict[str, Any]:
        records = self.sales_records()
        contracts = sum(1 for record in records if record.get("stage") in {"签约", "转化", "成交"})
        lost = sum(1 for record in records if record.get("stage") == "流失")
        sales_amount = sum(self._number(record.get("amount")) for record in records)
        return {
            "records": len(records),
            "leads": len(records),
            "contracts": contracts,
            "lost": lost,
            "conversion": round(contracts / len(records), 4) if records else 0,
            "sales_amount": round(sales_amount, 2),
            "adapter_id": SALES_ADAPTER_ID,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
        }

    def finance_metrics(self) -> dict[str, Any]:
        events = self.financial_event_records()
        settlements = self.finance_records()
        income = sum(self._number(event.get("income_amount")) for event in events)
        expenses = sum(self._number(event.get("expense_amount")) for event in events)
        receivable = sum(
            self._number(record.get("receivable_amount") or record.get("income_amount") or record.get("amount"))
            for record in settlements
            if record.get("payment_status") in {"待确认", "待收", "pending_confirmation"}
        )
        pending_payment = sum(
            self._number(record.get("pending_payment_amount") or record.get("expense_amount"))
            for record in settlements
            if record.get("payment_status") in {"待付", "pending_payment"}
        )
        return {
            "records": len(settlements),
            "event_records": len(events),
            "income": round(income, 2),
            "collected": round(income, 2),
            "receivable": round(receivable, 2),
            "pending_payment_amount": round(pending_payment, 2),
            "expenses": round(expenses, 2),
            "profit": round(income - expenses, 2),
            "adapter_id": FINANCE_ADAPTER_ID,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
        }

    def operations_metrics(self) -> dict[str, Any]:
        stays = self.stay_records()
        rooms = self.room_records()
        caregivers = self.caregiver_records()
        active_stay_statuses = {"CHECKED_IN", "IN_STAY", "EXTENDED", "checked_in", "in_stay", "extended"}
        waiting_stay_statuses = {"CONTRACTED", "WAITING_CHECKIN", "contracted", "waiting_checkin"}
        occupied_room_statuses = {"OCCUPIED", "occupied"}
        unavailable_room_statuses = {"CLEANING", "MAINTENANCE", "DISABLED", "cleaning", "maintenance", "disabled"}
        on_duty_caregiver_statuses = {"AVAILABLE", "RESERVED", "ASSIGNED", "available", "reserved", "assigned"}
        assigned_caregiver_statuses = {"ASSIGNED", "assigned"}
        return {
            "stay_records": len(stays),
            "active_stays": sum(1 for record in stays if record.get("status") in active_stay_statuses),
            "waiting_checkins": sum(1 for record in stays if record.get("status") in waiting_stay_statuses),
            "checked_out": sum(1 for record in stays if record.get("status") in {"CHECKED_OUT", "checked_out"}),
            "room_records": len(rooms),
            "occupied_rooms": sum(1 for record in rooms if record.get("status") in occupied_room_statuses),
            "available_rooms": sum(1 for record in rooms if record.get("status") in {"AVAILABLE", "available"}),
            "unavailable_rooms": sum(1 for record in rooms if record.get("status") in unavailable_room_statuses),
            "caregiver_records": len(caregivers),
            "on_duty_caregivers": sum(1 for record in caregivers if record.get("status") in on_duty_caregiver_statuses),
            "assigned_caregivers": sum(1 for record in caregivers if record.get("status") in assigned_caregiver_statuses),
            "adapter_ids": [STAY_ADAPTER_ID, ROOM_ADAPTER_ID, CAREGIVER_ADAPTER_ID],
            "mapping_version": PRODUCTION_MAPPING_VERSION,
        }

    def summary(self) -> dict[str, Any]:
        sales_domain = self.truth_store.read_domain("sales")
        finance_domain = self.truth_store.read_domain("finance")
        room_domain = self.truth_store.read_domain("room")
        stay_domain = self.truth_store.read_domain("stay")
        sales_entities = [item for item in sales_domain.get("entities") or [] if isinstance(item, dict)]
        finance_events = [item for item in finance_domain.get("financial_events") or [] if isinstance(item, dict)]
        finance_settlements = [item for item in finance_domain.get("settlement_records") or [] if isinstance(item, dict)]
        stay_rows = [item for item in stay_domain.get("stay_records") or [] if isinstance(item, dict)]
        if not stay_rows:
            stay_rows = [item for item in room_domain.get("stay_records") or [] if isinstance(item, dict)]
        room_rows = [item for item in room_domain.get("room_records") or [] if isinstance(item, dict)]
        caregiver_rows = [item for item in room_domain.get("caregiver_records") or [] if isinstance(item, dict)]
        return {
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "policy": "truth_source_contract_records_only",
            "sales_adapter": {
                "adapter_id": SALES_ADAPTER_ID,
                "source_system": "OMS_TRUTH_SOURCE/sales.json",
                "source_version": sales_domain.get("updated_at") or "",
                "target_domain": "Sales",
                "mapping_version": PRODUCTION_MAPPING_VERSION,
                "total_entities": len(sales_entities),
                "contract_records": len(self.sales_records()),
                "fallback_to_verified_work_items": not any(self._valid_evidence(item.get("source_evidence")) for item in sales_entities),
                "excluded_unverified": sum(1 for item in sales_entities if not self._valid_evidence(item.get("source_evidence"))),
            },
            "finance_adapter": {
                "adapter_id": FINANCE_ADAPTER_ID,
                "source_system": "OMS_TRUTH_SOURCE/finance.json",
                "source_version": finance_domain.get("updated_at") or "",
                "target_domain": "Payment",
                "mapping_version": PRODUCTION_MAPPING_VERSION,
                "total_financial_events": len(finance_events),
                "total_settlement_records": len(finance_settlements),
                "payment_records": len(self.finance_records()),
                "financial_event_records": len(self.financial_event_records()),
                "fallback_to_verified_work_items": not any(self._valid_evidence(item.get("source_evidence")) for item in finance_settlements),
                "excluded_unverified_events": sum(1 for item in finance_events if not self._valid_evidence(item.get("source_evidence"))),
                "excluded_unverified_settlements": sum(1 for item in finance_settlements if not self._valid_evidence(item.get("source_evidence"))),
            },
            "stay_adapter": {
                "adapter_id": STAY_ADAPTER_ID,
                "source_system": "OMS_TRUTH_SOURCE/stay.json.stay_records",
                "source_version": stay_domain.get("updated_at") or room_domain.get("updated_at") or "",
                "target_domain": "Stay",
                "mapping_version": PRODUCTION_MAPPING_VERSION,
                "total_records": len(stay_rows),
                "verified_records": len(self.stay_records()),
                "excluded_unverified": sum(1 for item in stay_rows if not self._valid_evidence(item.get("source_evidence"))),
            },
            "room_adapter": {
                "adapter_id": ROOM_ADAPTER_ID,
                "source_system": "OMS_TRUTH_SOURCE/room.json.room_records",
                "source_version": room_domain.get("updated_at") or "",
                "target_domain": "Room",
                "mapping_version": PRODUCTION_MAPPING_VERSION,
                "total_records": len(room_rows),
                "verified_records": len(self.room_records()),
                "excluded_unverified": sum(1 for item in room_rows if not self._valid_evidence(item.get("source_evidence"))),
            },
            "caregiver_adapter": {
                "adapter_id": CAREGIVER_ADAPTER_ID,
                "source_system": "OMS_TRUTH_SOURCE/room.json.caregiver_records",
                "source_version": room_domain.get("updated_at") or "",
                "target_domain": "Caregiver",
                "mapping_version": PRODUCTION_MAPPING_VERSION,
                "total_records": len(caregiver_rows),
                "verified_records": len(self.caregiver_records()),
                "excluded_unverified": sum(1 for item in caregiver_rows if not self._valid_evidence(item.get("source_evidence"))),
                "data_status": "verified" if (self.truth_store.read_domain("caregiver").get("entities") or []) else "missing_structured_production_data",
            },
        }

    def _sales_page_dataset(self) -> dict[str, Any]:
        records = self.sales_records()
        total = sum(self._number(record.get("contract_amount") or record.get("amount")) for record in records)
        collected = sum(self._number(record.get("actual_received_amount") or record.get("collected_amount")) for record in records)
        unpaid = sum(self._number(record.get("unpaid_balance_amount") or record.get("unpaid_amount")) for record in records)
        return self._page_dataset(
            dataset="sales",
            title="销售数据",
            source_domain="sales",
            source_file="2026年销售明细表（经验为王7.10）.xlsx",
            rows=[self._sales_page_row(record) for record in records],
            metrics={
                "record_count": len(records),
                "contract_amount_total": round(total, 2),
                "collected_amount_total": round(collected, 2),
                "unpaid_amount_total": round(unpaid, 2),
            },
            columns=[
                {"key": "customer_name", "label": "客户姓名"},
                {"key": "salesperson_name", "label": "销售人员"},
                {"key": "sign_date", "label": "签约日期"},
                {"key": "package_name", "label": "套餐"},
                {"key": "contract_amount", "label": "合同金额"},
                {"key": "collected_amount", "label": "已收金额"},
                {"key": "unpaid_amount", "label": "未收尾款"},
                {"key": "payment_status", "label": "付款状态"},
                {"key": "contract_status", "label": "合同状态"},
                {"key": "source_line", "label": "Excel来源"},
            ],
            filters=["search", "salesperson_name", "month"],
        )

    def _finance_page_dataset(self) -> dict[str, Any]:
        events = [self._finance_event_page_row(record) for record in self.financial_event_records()]
        settlements = [self._finance_settlement_page_row(record) for record in self.finance_records()]
        rows = [*events, *settlements]
        income = sum(self._number(row.get("income_amount")) for row in events)
        expense = sum(self._number(row.get("expense_amount")) for row in events)
        receivable = sum(self._number(row.get("receivable_amount")) for row in settlements)
        payable = sum(self._number(row.get("pending_payment_amount")) for row in settlements)
        return self._page_dataset(
            dataset="finance",
            title="财务数据",
            source_domain="finance",
            source_file="2026年财务报表（7月）.xlsx",
            rows=rows,
            metrics={
                "record_count": len(rows),
                "financial_event_count": len(events),
                "settlement_record_count": len(settlements),
                "income_total": round(income, 2),
                "expense_total": round(expense, 2),
                "profit": round(income - expense, 2),
                "receivable_total": round(receivable, 2),
                "pending_payment_total": round(payable, 2),
            },
            columns=[
                {"key": "date", "label": "日期"},
                {"key": "type", "label": "收支类型"},
                {"key": "amount", "label": "金额"},
                {"key": "subject", "label": "对应客户或事项"},
                {"key": "payment_method", "label": "收款方式"},
                {"key": "account", "label": "到账账户"},
                {"key": "operator", "label": "经办人"},
                {"key": "remark", "label": "备注"},
                {"key": "receivable_amount", "label": "待收"},
                {"key": "pending_payment_amount", "label": "待付"},
                {"key": "source_line", "label": "Excel来源"},
            ],
            filters=["search", "month", "type"],
        )

    def _room_page_dataset(self) -> dict[str, Any]:
        stays = self.stay_records()
        stays_by_room: dict[str, list[dict[str, Any]]] = {}
        for stay in stays:
            room_id = str(stay.get("room_id") or "").strip()
            if room_id:
                stays_by_room.setdefault(room_id, []).append(stay)
        rows = [self._room_page_row(record, stays_by_room.get(str(record.get("room_id") or "").strip(), [])) for record in self.room_records()]
        room_domain = self.truth_store.read_domain("room")
        warnings = (room_domain.get("validation") or {}).get("warnings") or []
        missing_room_rows = [
            self._room_warning_page_row(item)
            for item in warnings
            if isinstance(item, dict) and item.get("reason") == "missing_room_label"
        ]
        rows.extend(missing_room_rows)
        return self._page_dataset(
            dataset="rooms",
            title="房态明细",
            source_domain="room",
            source_file="①凰家母婴 2021房态表June(1).xlsx",
            rows=rows,
            metrics={
                "record_count": len(rows),
                "room_count": len(self.room_records()),
                "occupied_count": sum(1 for row in rows if row.get("status") == "OCCUPIED"),
                "reserved_count": sum(1 for row in rows if row.get("status") == "RESERVED"),
                "available_count": sum(1 for row in rows if row.get("status") == "AVAILABLE"),
                "maintenance_or_disabled_count": sum(1 for row in rows if row.get("status") in {"MAINTENANCE", "DISABLED"}),
                "missing_room_number_count": len(missing_room_rows),
            },
            columns=[
                {"key": "room_number", "label": "房号"},
                {"key": "status", "label": "当前状态"},
                {"key": "current_customer", "label": "当前客户"},
                {"key": "checkin_date", "label": "入住日期"},
                {"key": "checkout_date", "label": "预计出馆日期"},
                {"key": "stayed_days", "label": "已住天数"},
                {"key": "room_flag", "label": "房态"},
                {"key": "source_line", "label": "Excel来源"},
            ],
            filters=["search", "status", "room_flag"],
        )

    def _contract_customer_page_dataset(self) -> dict[str, Any]:
        customers_by_id = {str(item.get("customer_id") or item.get("record_id") or ""): item for item in self.customer_records()}
        rows = [self._contract_customer_page_row(record, customers_by_id) for record in self.contract_records()]
        return self._page_dataset(
            dataset="contracts",
            title="签约客户",
            source_domain="contract",
            source_file="A  凰家母婴签约客户一览表（挤牙膏）(1).xlsx",
            rows=rows,
            metrics={
                "record_count": len(rows),
                "contract_amount_total": round(sum(self._number(row.get("contract_amount")) for row in rows), 2),
                "checked_in_count": sum(1 for row in rows if row.get("is_checked_in") == "是"),
                "reconciliation_required_count": sum(1 for row in rows if row.get("needs_room_reconciliation") == "是"),
            },
            columns=[
                {"key": "customer_name", "label": "客户姓名"},
                {"key": "phone", "label": "联系方式"},
                {"key": "salesperson_name", "label": "销售"},
                {"key": "sign_date", "label": "签约日期"},
                {"key": "expected_delivery_date", "label": "预产期"},
                {"key": "package_name", "label": "套餐"},
                {"key": "contract_amount", "label": "合同金额"},
                {"key": "stay_plan", "label": "入住计划"},
                {"key": "status", "label": "当前状态"},
                {"key": "is_checked_in", "label": "是否已入住"},
                {"key": "needs_room_reconciliation", "label": "是否需房态核对"},
                {"key": "source_line", "label": "Excel来源"},
            ],
            filters=["search", "salesperson_name", "month", "status"],
        )

    def _page_dataset(
        self,
        *,
        dataset: str,
        title: str,
        source_domain: str,
        source_file: str,
        rows: list[dict[str, Any]],
        metrics: dict[str, Any],
        columns: list[dict[str, str]],
        filters: list[str],
    ) -> dict[str, Any]:
        domain = self.truth_store.read_domain(source_domain)
        return {
            "schema_version": PRODUCTION_PAGE_SCHEMA_VERSION,
            "dataset": dataset,
            "title": title,
            "source": {
                "source_file": domain.get("source_file") or source_file,
                "source_file_name": domain.get("source_file_name") or source_file,
                "source_version": domain.get("source_version") or "",
                "updated_at": domain.get("updated_at") or "",
                "truth_source_path": str(self.truth_store._domain_path(source_domain)),
                "adapter": domain.get("adapter") or "",
                "domain": source_domain,
            },
            "columns": columns,
            "filters": filters,
            "metrics": metrics,
            "records": rows,
            "record_count": len(rows),
            "data_policy": {
                "mock_allowed": False,
                "legacy_runtime_allowed": False,
                "manual_page_data_allowed": False,
                "source_trace_required": True,
            },
        }

    def _sales_page_row(self, record: dict[str, Any]) -> dict[str, Any]:
        amount = self._number(record.get("amount"))
        collected = self._number(record.get("actual_received_amount"))
        if not collected:
            collected = self._number(record.get("paid_room_amount")) + self._number(record.get("deposit_amount")) + self._number(record.get("paid_balance_amount"))
        unpaid = self._number(record.get("unpaid_balance_amount"))
        if not unpaid and amount > collected:
            unpaid = amount - collected
        return {
            "id": record.get("record_id") or record.get("contract_id") or "",
            "customer_name": record.get("customer_name") or record.get("guest_name") or "",
            "salesperson_name": record.get("salesperson_name") or "",
            "sign_date": record.get("sign_date") or "",
            "month": self._month(record.get("sign_date")),
            "package_name": record.get("package_name") or "",
            "contract_amount": round(amount, 2),
            "collected_amount": round(collected, 2),
            "unpaid_amount": round(unpaid, 2),
            "payment_status": "已结清" if unpaid <= 0 else "有尾款",
            "contract_status": record.get("stage") or record.get("status") or "",
            "contract_id": record.get("contract_id") or "",
            **self._source_columns(record),
        }

    def _finance_event_page_row(self, record: dict[str, Any]) -> dict[str, Any]:
        income = self._number(record.get("income_amount"))
        expense = self._number(record.get("expense_amount"))
        amount = income or expense or self._number(record.get("amount"))
        return {
            "id": record.get("financial_event_id") or record.get("record_id") or "",
            "date": record.get("occurred_at") or record.get("tx_date") or "",
            "month": self._month(record.get("occurred_at") or record.get("tx_date")),
            "type": "收入" if income else "支出" if expense else str(record.get("event_type") or ""),
            "amount": round(amount, 2),
            "income_amount": round(income, 2),
            "expense_amount": round(expense, 2),
            "subject": record.get("settlement_subject") or record.get("related_customer") or record.get("counterparty") or "",
            "payment_method": record.get("payment_method") or "",
            "account": record.get("account") or "",
            "operator": record.get("operator") or "",
            "remark": record.get("remark") or "",
            "receivable_amount": 0,
            "pending_payment_amount": 0,
            "status": record.get("status") or record.get("payment_status") or "",
            **self._source_columns(record),
        }

    def _finance_settlement_page_row(self, record: dict[str, Any]) -> dict[str, Any]:
        income = self._number(record.get("income_amount"))
        expense = self._number(record.get("expense_amount"))
        amount = self._number(record.get("amount")) or income or expense
        return {
            "id": record.get("tx_id") or record.get("record_id") or "",
            "date": "",
            "month": "",
            "type": "待收" if self._number(record.get("receivable_amount")) else "待付" if self._number(record.get("pending_payment_amount")) else record.get("type") or "",
            "amount": round(amount, 2),
            "income_amount": round(income, 2),
            "expense_amount": round(expense, 2),
            "subject": record.get("settlement_subject") or record.get("title") or "",
            "payment_method": "",
            "account": "",
            "operator": record.get("role") or "",
            "remark": record.get("payment_status") or "",
            "receivable_amount": round(self._number(record.get("receivable_amount")), 2),
            "pending_payment_amount": round(self._number(record.get("pending_payment_amount")), 2),
            "status": record.get("payment_status") or "",
            **self._source_columns(record),
        }

    def _room_page_row(self, record: dict[str, Any], stays: list[dict[str, Any]]) -> dict[str, Any]:
        current = self._current_stay(stays)
        status = record.get("status") or ""
        return {
            "id": record.get("record_id") or record.get("room_id") or "",
            "room_number": record.get("room_id") or record.get("room_name") or "",
            "room_name": record.get("room_name") or "",
            "status": status,
            "current_customer": current.get("customer_name") or "",
            "checkin_date": current.get("checkin_date") or current.get("planned_checkin_date") or "",
            "checkout_date": current.get("checkout_date") or "",
            "stayed_days": self._stayed_days(current.get("checkin_date") or current.get("planned_checkin_date")),
            "room_flag": self._room_flag(status),
            "missing_room_number": "否",
            **self._source_columns(record),
        }

    def _room_warning_page_row(self, warning: dict[str, Any]) -> dict[str, Any]:
        markers = warning.get("markers") if isinstance(warning.get("markers"), list) else []
        marker_text = "；".join(
            f"{marker.get('day')}日 {marker.get('value')}"
            for marker in markers
            if isinstance(marker, dict)
        )
        return {
            "id": f"ROOM-WARNING-R{warning.get('row_number') or ''}",
            "room_number": "",
            "room_name": "",
            "status": "MISSING_ROOM",
            "current_customer": marker_text,
            "checkin_date": "",
            "checkout_date": "",
            "stayed_days": "",
            "room_flag": "缺房号异常",
            "missing_room_number": "是",
            "source_file_name": "①凰家母婴 2021房态表June(1).xlsx",
            "source_sheet": "Sheet1",
            "row_number": warning.get("row_number") or "",
            "source_line": f"①凰家母婴 2021房态表June(1).xlsx / Sheet1 / 第{warning.get('row_number') or ''}行",
            "trace_id": "",
            "source_evidence": {
                "source_file_name": "①凰家母婴 2021房态表June(1).xlsx",
                "source_sheet": "Sheet1",
                "row_number": warning.get("row_number") or "",
                "reason": warning.get("reason") or "",
            },
        }

    def _contract_customer_page_row(self, record: dict[str, Any], customers_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
        customer = customers_by_id.get(str(record.get("customer_id") or "")) or {}
        inner_nights = self._number(record.get("inner_store_nights"))
        outer_nights = self._number(record.get("outer_store_nights"))
        status = "已入住" if str(record.get("status") or "").upper() in {"CHECKED_IN", "IN_STAY"} else "待核对"
        return {
            "id": record.get("record_id") or record.get("contract_id") or "",
            "customer_name": record.get("customer_name") or customer.get("customer_name") or "",
            "phone": record.get("phone") or customer.get("phone") or "",
            "salesperson_name": record.get("salesperson_name") or "",
            "sign_date": record.get("sign_date") or "",
            "month": record.get("source_month") or self._month(record.get("sign_date")),
            "expected_delivery_date": record.get("expected_delivery_date") or customer.get("expected_delivery_date") or "",
            "package_name": record.get("package_name") or "",
            "contract_amount": round(self._number(record.get("contract_amount")), 2),
            "stay_plan": f"馆内{inner_nights:g}晚 / 馆外{outer_nights:g}晚",
            "status": status,
            "is_checked_in": "是" if status == "已入住" else "否",
            "needs_room_reconciliation": "是",
            "contract_id": record.get("contract_id") or "",
            **self._source_columns(record),
        }

    def _customer_record(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") or {}
        source_file = str(evidence.get("source_file") or "")
        return {
            **item,
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "business_domain": "customer_data",
            "data_status": "verified",
            "data_confidence": "source_verified",
            "adapter_id": "customer_adapter_v1",
            "source_file": source_file,
            "source_file_name": Path(source_file).name,
            "row_id": evidence.get("row_number"),
            "row_number": evidence.get("row_number"),
        }

    def _contract_record(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") or {}
        source_file = str(evidence.get("source_file") or "")
        return {
            **item,
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "business_domain": "contract_data",
            "data_status": "verified",
            "data_confidence": "source_verified",
            "adapter_id": "contract_adapter_v1",
            "domain": "Contract",
            "domain_id": item.get("contract_id") or item.get("record_id") or "",
            "source_file": source_file,
            "source_file_name": Path(source_file).name,
            "row_id": evidence.get("row_number"),
            "row_number": evidence.get("row_number"),
        }

    def _source_columns(self, record: dict[str, Any]) -> dict[str, Any]:
        evidence = record.get("source_evidence") if isinstance(record.get("source_evidence"), dict) else {}
        source_file = str(evidence.get("source_file_name") or record.get("source_file_name") or Path(str(evidence.get("source_file") or "")).name)
        sheet = str(evidence.get("source_sheet") or record.get("source_version") or "")
        row = evidence.get("row_number") or record.get("row_number") or record.get("row_id") or ""
        return {
            "source_file_name": source_file,
            "source_sheet": sheet,
            "row_number": row,
            "source_line": " / ".join([part for part in [source_file, sheet, f"第{row}行" if row else ""] if part]),
            "trace_id": evidence.get("trace_id") or "",
            "source_evidence": evidence,
        }

    def _current_stay(self, stays: list[dict[str, Any]]) -> dict[str, Any]:
        if not stays:
            return {}
        active = [stay for stay in stays if str(stay.get("status") or "").upper() in {"IN_STAY", "CHECKED_IN", "EXTENDED"}]
        if active:
            return active[0]
        return stays[0]

    def _room_flag(self, status: Any) -> str:
        normalized = str(status or "").upper()
        if normalized == "AVAILABLE":
            return "空房"
        if normalized == "OCCUPIED":
            return "占用"
        if normalized == "RESERVED":
            return "预留"
        if normalized in {"MAINTENANCE", "DISABLED"}:
            return "维修或停用"
        return normalized or "-"

    def _month(self, value: Any) -> str:
        text = str(value or "").strip().replace(".", "-").replace("/", "-")
        parts = text.split("-")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}"
        return ""

    def _stayed_days(self, checkin_date: Any) -> int | str:
        text = str(checkin_date or "").strip()
        if not text:
            return ""
        from datetime import date, datetime

        normalized = text.replace(".", "-").replace("/", "-")
        try:
            started = datetime.strptime(normalized, "%Y-%m-%d").date()
        except ValueError:
            return ""
        return max((date(2026, 7, 10) - started).days + 1, 0)

    def _stay_record(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") or {}
        stay_id = str(item.get("stay_id") or item.get("record_id") or evidence.get("record_id") or "")
        customer_name = str(item.get("customer_name") or item.get("guest_name") or "")
        status = str(item.get("status") or "WAITING_CHECKIN")
        source_file = str(evidence.get("source_file") or "")
        row_id = evidence.get("row_number")
        return {
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "business_domain": "resident_data",
            "data_status": "verified",
            "data_confidence": "source_verified",
            "adapter_id": STAY_ADAPTER_ID,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
            "domain": "Stay",
            "domain_id": stay_id,
            "work_item_id": stay_id,
            "record_id": item.get("record_id") or evidence.get("record_id") or stay_id,
            "stay_id": stay_id,
            "customer_name": customer_name,
            "guest_name": customer_name,
            "room_id": item.get("room_id") or "",
            "caregiver_id": item.get("caregiver_id") or "",
            "checkin_date": item.get("checkin_date") or item.get("planned_checkin_date") or "",
            "checkout_date": item.get("checkout_date") or item.get("planned_checkout_date") or "",
            "status": status,
            "source_file": source_file,
            "source_file_name": Path(source_file).name,
            "row_id": row_id,
            "row_number": row_id,
            "source_version": evidence.get("source_sheet") or evidence.get("trace_id") or "",
            "title": str(item.get("title") or f"{customer_name or stay_id} / {status}"),
            "source_evidence": evidence,
            "trace_chain": self._trace_chain(evidence, adapter_id=STAY_ADAPTER_ID, domain_id=stay_id),
            "display_fields": [
                {"label": "客户", "value": customer_name or "-"},
                {"label": "房间", "value": str(item.get("room_id") or "-")},
                {"label": "入住", "value": str(item.get("checkin_date") or item.get("planned_checkin_date") or "-")},
                {"label": "出馆", "value": str(item.get("checkout_date") or item.get("planned_checkout_date") or "-")},
                {"label": "状态", "value": status},
            ],
        }

    def _room_record(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") or {}
        room_id = str(item.get("room_id") or item.get("record_id") or evidence.get("record_id") or "")
        status = str(item.get("status") or "AVAILABLE")
        source_file = str(evidence.get("source_file") or "")
        row_id = evidence.get("row_number")
        return {
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "business_domain": "room_status_data",
            "data_status": "verified",
            "data_confidence": "source_verified",
            "adapter_id": ROOM_ADAPTER_ID,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
            "domain": "Room",
            "domain_id": room_id,
            "work_item_id": room_id,
            "record_id": item.get("record_id") or evidence.get("record_id") or room_id,
            "room_id": room_id,
            "room_name": item.get("room_name") or room_id,
            "floor": item.get("floor") or "",
            "status": status,
            "current_stay_id": item.get("current_stay_id") or "",
            "source_file": source_file,
            "source_file_name": Path(source_file).name,
            "row_id": row_id,
            "row_number": row_id,
            "source_version": evidence.get("source_sheet") or evidence.get("trace_id") or "",
            "title": str(item.get("title") or f"{item.get('room_name') or room_id} / {status}"),
            "source_evidence": evidence,
            "trace_chain": self._trace_chain(evidence, adapter_id=ROOM_ADAPTER_ID, domain_id=room_id),
            "display_fields": [
                {"label": "房间", "value": str(item.get("room_name") or room_id or "-")},
                {"label": "楼层", "value": str(item.get("floor") or "-")},
                {"label": "状态", "value": status},
                {"label": "入住", "value": str(item.get("current_stay_id") or "-")},
            ],
        }

    def _caregiver_record(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") or {}
        caregiver_id = str(item.get("caregiver_id") or item.get("employee_id") or item.get("record_id") or evidence.get("record_id") or "")
        name = str(item.get("caregiver_name") or item.get("employee_name") or item.get("name") or "")
        status = str(item.get("status") or "AVAILABLE")
        source_file = str(evidence.get("source_file") or "")
        row_id = evidence.get("row_number")
        return {
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "business_domain": "caregiver_data",
            "data_status": "verified",
            "data_confidence": "source_verified",
            "adapter_id": CAREGIVER_ADAPTER_ID,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
            "domain": "Caregiver",
            "domain_id": caregiver_id,
            "work_item_id": caregiver_id,
            "record_id": item.get("record_id") or evidence.get("record_id") or caregiver_id,
            "caregiver_id": caregiver_id,
            "caregiver_name": name,
            "employee_id": item.get("employee_id") or caregiver_id,
            "status": status,
            "current_stay_id": item.get("current_stay_id") or "",
            "source_file": source_file,
            "source_file_name": Path(source_file).name,
            "row_id": row_id,
            "row_number": row_id,
            "source_version": evidence.get("source_sheet") or evidence.get("trace_id") or "",
            "title": str(item.get("title") or f"{name or caregiver_id} / {status}"),
            "source_evidence": evidence,
            "trace_chain": self._trace_chain(evidence, adapter_id=CAREGIVER_ADAPTER_ID, domain_id=caregiver_id),
            "display_fields": [
                {"label": "照护师", "value": name or "-"},
                {"label": "状态", "value": status},
                {"label": "入住", "value": str(item.get("current_stay_id") or "-")},
            ],
        }

    def resident_records(self) -> list[dict[str, Any]]:
        active_statuses = {"CHECKED_IN", "IN_STAY", "EXTENDED", "in_house", "checked_in", "in_stay", "extended", "入住中", "在住"}
        return [record for record in self.stay_records() if str(record.get("status") or "") in active_statuses]

    def _operational_baseline_records(self, field: str) -> list[dict[str, Any]] | None:
        if self.operational_baseline_root is None:
            return None
        state_path = self.operational_baseline_root / "operational_baseline_state.json"
        if not state_path.is_file():
            return None
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("status") != "ACTIVE":
            return []
        snapshot_path = self.operational_baseline_root / str(state.get("snapshot_file") or "")
        if not snapshot_path.is_file():
            return []
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if snapshot.get("active") is not True or snapshot.get("status") != "PASS":
            return []
        return [item for item in snapshot.get(field) or [] if isinstance(item, dict)]

    def operating_mode(self) -> dict[str, Any]:
        state_path = self._operating_mode_path()
        if state_path is None or not state_path.is_file():
            return {"current_status": "LEGACY_COMPATIBILITY", "current_initialized": True}
        state = json.loads(state_path.read_text(encoding="utf-8"))
        initialized = bool(state.get("current_operating_snapshot"))
        return {
            **state,
            "current_status": "INITIALIZED" if initialized else "NOT_INITIALIZED",
            "current_initialized": initialized,
        }

    def data_quality_summary(self) -> dict[str, Any]:
        operating_mode = self.operating_mode()
        if operating_mode.get("current_status") == "NOT_INITIALIZED":
            return {
                "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
                "status": "NOT_INITIALIZED",
                "score": None,
                "snapshot_version": "NOT_INITIALIZED",
                "snapshot_status": "NOT_INITIALIZED",
                "activated_for_production": False,
                "current_only": True,
                "historical_included": False,
                "quarantine_included": False,
                "legacy_snapshot": operating_mode.get("legacy_snapshot"),
                "legacy_snapshot_status": operating_mode.get("legacy_snapshot_status"),
            }
        domains = {
            "sales": self.sales_records(),
            "finance": self.financial_event_records(),
            "room": self.room_records(),
            "stay": self.stay_records(),
            "caregiver": self.caregiver_records(),
        }
        scores = {domain: self._score_records(domain, records) for domain, records in domains.items()}
        overall = DataHealthScorer().overall(scores)
        snapshot = self._active_quality_snapshot()
        source_integrity = self._snapshot_source_integrity(snapshot)
        overall.update({
            "snapshot_version": snapshot.get("snapshot_version") or "PENDING_DQ_SNAPSHOT",
            "snapshot_status": (snapshot.get("acceptance_result") if source_integrity["valid"] else "FAIL") or "WARNING",
            "activated_for_production": bool(snapshot.get("activated_for_production")) and source_integrity["valid"],
            "snapshot_source_integrity": source_integrity,
            "current_only": True,
            "historical_included": False,
            "quarantine_included": False,
        })
        return overall

    def _current_records_allowed(self) -> bool:
        if self.operating_mode().get("current_status") == "NOT_INITIALIZED":
            return False
        if self.operational_baseline_root is not None:
            state_path = self.operational_baseline_root / "operational_baseline_state.json"
            if state_path.is_file():
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if state.get("status") != "ACTIVE":
                    return False
        snapshot = self._active_quality_snapshot()
        if snapshot and not self._snapshot_source_integrity(snapshot)["valid"]:
            return False
        return True

    def _operating_mode_path(self) -> Path | None:
        if self.operational_baseline_root is None:
            return None
        return self.operational_baseline_root.parent / "operating_mode.json"

    def _score_records(self, domain: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        if not records:
            return DataHealthScorer().score(DataHealthInput(1, 1, 1, 1))
        required = {
            "sales": ("record_id", "contract_id", "customer_name", "amount"),
            "finance": ("record_id", "tx_id", "amount", "tx_date"),
            "room": ("record_id", "room_id", "status"),
            "stay": ("record_id", "stay_id", "status"),
            "caregiver": ("record_id", "caregiver_id", "caregiver_name"),
        }.get(domain, ("record_id",))
        complete = sum(sum(1 for field in required if record.get(field) not in {None, ""}) / len(required) for record in records) / len(records)
        ids = [str(record.get("record_id") or record.get("domain_id") or "") for record in records]
        consistency = len({item for item in ids if item}) / len(records)
        traceable = sum(1 for record in records if self._trace_complete(record.get("source_evidence"))) / len(records)
        warnings = sum(1 for record in records if record.get("quality_status") != "PASS")
        return DataHealthScorer().score(DataHealthInput(complete, consistency, 1.0, traceable, {"medium": warnings}))

    def _trace_complete(self, evidence: Any) -> bool:
        return bool(isinstance(evidence, dict) and evidence.get("source_file") and evidence.get("source_sheet") and evidence.get("row_number") not in {None, ""} and evidence.get("source_version"))

    def _active_quality_snapshot(self) -> dict[str, Any]:
        try:
            return TruthSourceSnapshotManager(self.truth_store.root / "snapshots").active() or {}
        except (KeyError, OSError, ValueError, TypeError):
            return {}

    def _snapshot_source_integrity(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        if not snapshot:
            return {"valid": True, "checked": False, "mismatches": []}
        metadata = snapshot.get("snapshot_metadata") or {}
        lock = metadata.get("production_lock") if isinstance(metadata, dict) else {}
        source_locks = lock.get("source_files") if isinstance(lock, dict) else {}
        if not source_locks:
            return {"valid": False, "checked": True, "mismatches": ["missing_source_file_locks"]}
        mismatches: list[str] = []
        for domain, source in source_locks.items():
            if not isinstance(source, dict):
                mismatches.append(f"{domain}:invalid_lock")
                continue
            path = self.truth_store.root / str(source.get("relative_path") or f"{domain}.json")
            if not path.is_file():
                mismatches.append(f"{domain}:missing_file")
                continue
            expected = str(source.get("sha256") or "")
            if not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                mismatches.append(f"{domain}:sha256_mismatch")
        return {"valid": not mismatches, "checked": True, "mismatches": mismatches}

    def _sales_record(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") or {}
        amount = self._number(item.get("amount"))
        source_file = str(evidence.get("source_file") or "")
        row_id = evidence.get("row_number")
        contract_id = str(item.get("contract_id") or item.get("source_record_id") or item.get("entity_id") or "")
        customer_name = str(item.get("guest_name") or item.get("customer_name") or "")
        stage = str(item.get("stage") or "签约")
        return {
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "business_domain": "sales_contract_data",
            "data_status": "verified",
            "data_confidence": "source_verified",
            "adapter_id": SALES_ADAPTER_ID,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
            "domain": "Sales",
            "domain_id": item.get("entity_id") or contract_id,
            "work_item_id": item.get("entity_id") or contract_id,
            "record_id": item.get("source_record_id") or evidence.get("record_id") or contract_id,
            "contract_id": contract_id,
            "customer_name": customer_name,
            "guest_name": customer_name,
            "sign_date": item.get("sign_date") or "",
            "expected_delivery_date": item.get("expected_delivery_date") or "",
            "package_name": item.get("package_name") or "",
            "stage": stage,
            "amount": amount,
            "paid_room_amount": self._number(item.get("paid_room_amount")),
            "deposit_amount": self._number(item.get("deposit_amount")),
            "paid_balance_amount": self._number(item.get("paid_balance_amount")),
            "unpaid_balance_amount": self._number(item.get("unpaid_balance_amount")),
            "actual_received_amount": self._number(item.get("actual_received_amount")),
            "salesperson_id": item.get("salesperson_id") or "",
            "salesperson_name": item.get("salesperson_name") or "",
            "source_file": source_file,
            "source_file_name": Path(source_file).name,
            "row_id": row_id,
            "row_number": row_id,
            "source_version": evidence.get("source_sheet") or evidence.get("trace_id") or "",
            "title": f"{customer_name or '客户'} / {contract_id}",
            "status": stage,
            "source_evidence": evidence,
            "trace_chain": self._trace_chain(evidence, adapter_id=SALES_ADAPTER_ID, domain_id=item.get("entity_id") or contract_id),
            "display_fields": [
                {"label": "客户", "value": customer_name or "-"},
                {"label": "合同", "value": contract_id or "-"},
                {"label": "金额", "value": f"{amount:.2f}"},
                {"label": "阶段", "value": stage or "-"},
                {"label": "来源行", "value": str(row_id)},
            ],
        }

    def _sales_work_item_record(self, item: dict[str, Any]) -> dict[str, Any]:
        source_record = item.get("excel_record") if isinstance(item.get("excel_record"), dict) else {}
        normalized = source_record.get("normalized") if isinstance(source_record.get("normalized"), dict) else {}
        raw_row = source_record.get("raw_row") if isinstance(source_record.get("raw_row"), dict) else {}
        evidence = self._item_evidence(item)
        amount = self._number(normalized.get("amount") or raw_row.get("全款费用") or raw_row.get("成交金额"))
        contract_id = str(normalized.get("contract_no") or raw_row.get("合同编号") or item.get("action_id") or item.get("work_item_id") or "")
        customer_name = str(normalized.get("customer_name") or raw_row.get("宝妈姓名") or raw_row.get("姓名") or "")
        entity = {
            "entity_id": item.get("work_item_id") or item.get("action_id") or contract_id,
            "contract_id": contract_id,
            "guest_name": customer_name,
            "stage": "签约",
            "amount": amount,
            "salesperson_name": normalized.get("sales_owner") or raw_row.get("销售") or "",
            "source_record_id": evidence.get("record_id") or item.get("action_id") or "",
            "source_evidence": evidence,
        }
        return self._sales_record(entity)

    def _finance_record(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") or {}
        amount = self._number(item.get("amount"))
        payment_status = str(item.get("status") or "pending_confirmation")
        settlement_type = str(item.get("settlement_type") or "")
        income = self._number(item.get("income_amount"))
        if not income and payment_status not in {"pending_payment", "寰呬粯"} and settlement_type != "payable":
            income = amount
        expense = self._number(item.get("expense_amount"))
        if not expense and (payment_status in {"pending_payment", "寰呬粯"} or settlement_type == "payable"):
            expense = amount
        source_file = str(evidence.get("source_file") or item.get("source_file") or "")
        row_id = evidence.get("row_number") or item.get("row_number")
        return {
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "business_domain": "finance_data",
            "data_status": "verified",
            "data_confidence": "source_verified",
            "adapter_id": FINANCE_ADAPTER_ID,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
            "domain": "Payment",
            "domain_id": item.get("settlement_id") or item.get("financial_event_id") or item.get("record_id"),
            "work_item_id": item.get("settlement_id") or item.get("financial_event_id") or item.get("record_id"),
            "tx_id": item.get("settlement_id") or item.get("financial_event_id") or item.get("record_id"),
            "financial_event_id": item.get("financial_event_id") or "",
            "settlement_subject": item.get("settlement_subject") or "",
            "record_id": item.get("record_id") or evidence.get("record_id") or "",
            "type": item.get("settlement_type") or "收款",
            "amount": amount,
            "income_amount": income,
            "expense_amount": expense,
            "receivable_amount": income if payment_status in {"pending_confirmation", "待确认", "待收"} else 0,
            "pending_payment_amount": expense if payment_status in {"pending_payment", "待付"} else 0,
            "payment_status": payment_status,
            "workspace": item.get("workspace") or "财务工作台",
            "role": item.get("role") or "财务",
            "source_file": source_file,
            "source_file_name": Path(source_file).name,
            "row_id": row_id,
            "row_number": row_id,
            "source_version": evidence.get("source_sheet") or "",
            "title": f"{item.get('settlement_type') or '财务记录'} / {income or amount:.2f}",
            "status": payment_status,
            "source_evidence": evidence,
            "trace_chain": self._trace_chain(evidence, adapter_id=FINANCE_ADAPTER_ID, domain_id=item.get("settlement_id") or ""),
            "display_fields": [
                {"label": "金额", "value": f"{income or amount:.2f}"},
                {"label": "状态", "value": payment_status},
                {"label": "来源行", "value": str(row_id)},
                {"label": "财务事件", "value": str(item.get("financial_event_id") or "-")},
            ],
        }

    def _finance_work_item_record(self, item: dict[str, Any]) -> dict[str, Any]:
        source_record = item.get("finance_record") if isinstance(item.get("finance_record"), dict) else {}
        normalized = source_record.get("normalized") if isinstance(source_record.get("normalized"), dict) else {}
        evidence = self._item_evidence(item)
        settlement = {
            "settlement_id": item.get("settlement_id") or item.get("work_item_id") or item.get("action_id") or "",
            "financial_event_id": item.get("financial_event_id") or "",
            "record_id": evidence.get("record_id") or item.get("action_id") or "",
            "settlement_type": item.get("daily_process") or normalized.get("business_type") or "财务记录",
            "status": item.get("status") or "pending_confirmation",
            "amount": normalized.get("amount") or normalized.get("income_amount") or "",
            "income_amount": normalized.get("income_amount") or normalized.get("amount") or "",
            "expense_amount": normalized.get("expense_amount") or "",
            "workspace": item.get("workspace") or "财务工作台",
            "role": item.get("role") or "财务",
            "source_evidence": evidence,
        }
        return self._finance_record(settlement)

    def _financial_event_record(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence") or {}
        amount = self._number(item.get("amount"))
        event_type = str(item.get("event_type") or "")
        income = self._number(item.get("income_amount"))
        if not income and event_type == "income":
            income = amount
        expense = self._number(item.get("expense_amount"))
        if not expense and event_type == "expense":
            expense = amount
        source_file = str(evidence.get("source_file") or "")
        row_id = evidence.get("row_number") or item.get("row_number")
        return {
            "schema_version": PRODUCTION_ADAPTER_SCHEMA_VERSION,
            "business_domain": "financial_events",
            "data_status": "verified",
            "data_confidence": "source_verified",
            "adapter_id": FINANCE_ADAPTER_ID,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
            "domain": "Finance",
            "domain_id": item.get("financial_event_id") or item.get("record_id"),
            "work_item_id": item.get("financial_event_id") or item.get("record_id"),
            "tx_id": item.get("financial_event_id") or item.get("record_id"),
            "financial_event_id": item.get("financial_event_id") or item.get("record_id"),
            "record_id": item.get("record_id") or evidence.get("record_id") or "",
            "event_type": event_type,
            "type": item.get("event_type") or "收款",
            "amount": amount,
            "income_amount": income,
            "expense_amount": expense,
            "counterparty": item.get("customer_name") or "",
            "related_customer": item.get("customer_name") or "",
            "settlement_subject": item.get("settlement_subject") or "",
            "tx_date": item.get("occurred_at") or "",
            "occurred_at": item.get("occurred_at") or "",
            "payment_status": item.get("truth_status") or "source_verified",
            "source_file": source_file,
            "source_file_name": Path(source_file).name,
            "row_id": row_id,
            "row_number": row_id,
            "source_version": evidence.get("source_sheet") or item.get("source_sheet") or "",
            "title": f"{item.get('customer_name') or '收款'} / {income or amount:.2f}",
            "status": item.get("truth_status") or "source_verified",
            "source_evidence": evidence,
            "trace_chain": self._trace_chain(evidence, adapter_id=FINANCE_ADAPTER_ID, domain_id=item.get("financial_event_id") or ""),
            "display_fields": [
                {"label": "客户", "value": str(item.get("customer_name") or "-")},
                {"label": "金额", "value": f"{income or amount:.2f}"},
                {"label": "日期", "value": str(item.get("occurred_at") or "-")},
                {"label": "来源行", "value": str(row_id)},
            ],
        }

    def _trace_chain(self, evidence: dict[str, Any], *, adapter_id: str, domain_id: str) -> dict[str, Any]:
        return {
            "source_file": evidence.get("source_file") or "",
            "source_file_name": Path(str(evidence.get("source_file") or "")).name,
            "row_id": evidence.get("row_number"),
            "source_record_id": evidence.get("record_id") or "",
            "adapter_id": adapter_id,
            "mapping_version": PRODUCTION_MAPPING_VERSION,
            "domain_id": domain_id,
            "trace_id": evidence.get("trace_id") or "",
        }

    def _valid_evidence(self, evidence: Any) -> bool:
        if not isinstance(evidence, dict):
            return False
        return bool(evidence.get("source_file") and evidence.get("row_number") not in {"", None} and evidence.get("record_id"))

    def _item_evidence(self, item: dict[str, Any]) -> dict[str, Any]:
        evidence = item.get("source_evidence")
        if not evidence and isinstance(item.get("excel_record"), dict):
            evidence = item["excel_record"].get("source_evidence")
        if not evidence and isinstance(item.get("finance_record"), dict):
            evidence = item["finance_record"].get("source_evidence")
        return evidence if isinstance(evidence, dict) else {}

    def _number(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if value is None:
            return 0.0
        text = str(value).replace(",", "").replace("￥", "").replace("¥", "").strip()
        try:
            return float(text)
        except ValueError:
            return 0.0
