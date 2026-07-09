from __future__ import annotations

from pathlib import Path
from typing import Any

from .truth_source import TruthSourceStore


PRODUCTION_ADAPTER_SCHEMA_VERSION = "oms.v1.production_data_adapter"
SALES_ADAPTER_ID = "sales_adapter_v1"
FINANCE_ADAPTER_ID = "finance_adapter_v1"
PRODUCTION_MAPPING_VERSION = "p0.9.production_truth.v1"


class ProductionDataAdapter:
    """Read-only adapter from OMS_TRUTH_SOURCE into page contract records.

    This adapter is intentionally strict for V1.0 production pages: only records
    with source_file + row_id evidence are exposed to the UI.
    """

    def __init__(self, truth_store: TruthSourceStore):
        self.truth_store = truth_store

    def sales_records(self) -> list[dict[str, Any]]:
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
        finance_domain = self.truth_store.read_domain("finance")
        events = [item for item in finance_domain.get("financial_events") or [] if isinstance(item, dict)]
        records = [self._financial_event_record(item) for item in events if self._valid_evidence(item.get("source_evidence"))]
        return [record for record in records if record]

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
        income = sum(self._number(event.get("income_amount") or event.get("amount")) for event in events)
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

    def summary(self) -> dict[str, Any]:
        sales_domain = self.truth_store.read_domain("sales")
        finance_domain = self.truth_store.read_domain("finance")
        sales_entities = [item for item in sales_domain.get("entities") or [] if isinstance(item, dict)]
        finance_events = [item for item in finance_domain.get("financial_events") or [] if isinstance(item, dict)]
        finance_settlements = [item for item in finance_domain.get("settlement_records") or [] if isinstance(item, dict)]
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
        }

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
            "stage": stage,
            "amount": amount,
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
        income = self._number(item.get("income_amount") or item.get("amount"))
        expense = self._number(item.get("expense_amount"))
        source_file = str(evidence.get("source_file") or item.get("source_file") or "")
        row_id = evidence.get("row_number") or item.get("row_number")
        payment_status = str(item.get("status") or "pending_confirmation")
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
        income = self._number(item.get("income_amount") or item.get("amount"))
        expense = self._number(item.get("expense_amount"))
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
            "record_id": item.get("record_id") or evidence.get("record_id") or "",
            "event_type": item.get("event_type") or "",
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
