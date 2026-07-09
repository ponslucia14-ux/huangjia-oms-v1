import json
import tempfile
import unittest
from pathlib import Path

from oms_v1.home_ui import OMSHomeUI
from oms_v1.production_data_adapter import FINANCE_ADAPTER_ID, SALES_ADAPTER_ID, ProductionDataAdapter
from oms_v1.truth_source import TruthSourceStore


class ProductionDataAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.live_root = self.root / "live"
        self.operating_root = self.root / "operational"
        self.truth_root = self.root / "OMS_TRUTH_SOURCE"
        self.truth_root.mkdir(parents=True)
        mapping_path = self.live_root / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        mapping_path.write_text(
            json.dumps({"rows": [{"name": "石磊", "role": "boss", "user_id": "user_boss"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.sales_evidence = {
            "truth_source": "Sales Excel",
            "source_type": "sales_detail",
            "source_file": str(self.root / "sales.xlsx"),
            "source_sheet": "sales",
            "row_number": 2,
            "record_id": "sales_row_2",
            "trace_id": "sales:sales.xlsx:sales:2:sales_row_2",
        }
        self.finance_evidence = {
            "truth_source": "Finance Excel",
            "source_type": "finance_daily",
            "source_file": str(self.root / "finance.xlsx"),
            "source_sheet": "daily",
            "row_number": 3,
            "record_id": "finance_row_3",
            "trace_id": "finance:finance.xlsx:daily:3:finance_row_3",
        }
        (self.truth_root / "sales.json").write_text(
            json.dumps(
                {
                    "schema_version": "oms.v1.truth_source.sales",
                    "mode": "single_source_of_truth",
                    "domain": "sales",
                    "updated_at": "2026-07-09T23:59:00+08:00",
                    "work_items": [
                        {"work_item_id": "legacy_sales", "excel_record": {"source_type": "contracts"}},
                    ],
                    "entities": [
                        {
                            "entity_id": "sales_entity_1",
                            "contract_id": "HJ-001",
                            "guest_name": "王女士",
                            "stage": "转化",
                            "amount": 30000,
                            "salesperson_name": "欢欢",
                            "source_record_id": "sales_row_2",
                            "source_evidence": self.sales_evidence,
                        },
                        {"entity_id": "sales_entity_unverified", "contract_id": "HJ-LEGACY", "amount": 1},
                    ],
                    "migration_source": "legacy_runtime",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.truth_root / "finance.json").write_text(
            json.dumps(
                {
                    "schema_version": "oms.v1.truth_source.finance",
                    "mode": "single_source_of_truth",
                    "domain": "finance",
                    "updated_at": "2026-07-09T23:59:00+08:00",
                    "work_items": [{"work_item_id": "legacy_finance"}],
                    "entities": [],
                    "financial_events": [
                        {
                            "financial_event_id": "fevt_1",
                            "record_id": "finance_row_3",
                            "event_type": "finance_income",
                            "customer_name": "王女士",
                            "income_amount": "30000",
                            "expense_amount": "2000",
                            "occurred_at": "2026.7.9",
                            "settlement_subject": "尾款",
                            "truth_status": "source_verified",
                            "source_evidence": self.finance_evidence,
                        },
                        {"financial_event_id": "fevt_legacy", "income_amount": "999999"},
                    ],
                    "settlement_records": [
                        {
                            "settlement_id": "set_1",
                            "financial_event_id": "fevt_1",
                            "record_id": "finance_row_3",
                            "settlement_type": "收款确认",
                            "status": "pending_confirmation",
                            "amount": "30000",
                            "income_amount": "30000",
                            "expense_amount": "2000",
                            "workspace": "财务工作台",
                            "role": "财务",
                            "source_evidence": self.finance_evidence,
                        },
                        {"settlement_id": "set_legacy", "income_amount": "999999"},
                    ],
                    "migration_source": "legacy_runtime",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.truth_root / "room.json").write_text(
            json.dumps(
                {
                    "schema_version": "oms.v1.truth_source.room",
                    "mode": "single_source_of_truth",
                    "domain": "room",
                    "updated_at": "2026-07-09T23:59:00+08:00",
                    "work_items": [],
                    "entities": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.truth_root / "events.jsonl").write_text("", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _store(self):
        return TruthSourceStore(self.live_root, self.operating_root, truth_root=self.truth_root)

    def test_sales_and_finance_adapters_expose_only_verified_truth_records(self):
        adapter = ProductionDataAdapter(self._store())

        sales = adapter.sales_records()
        finance = adapter.finance_records()
        events = adapter.financial_event_records()

        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0]["adapter_id"], SALES_ADAPTER_ID)
        self.assertEqual(sales[0]["contract_id"], "HJ-001")
        self.assertEqual(sales[0]["row_id"], 2)
        self.assertEqual(adapter.sales_metrics()["sales_amount"], 30000)
        self.assertEqual(len(finance), 1)
        self.assertEqual(finance[0]["adapter_id"], FINANCE_ADAPTER_ID)
        self.assertEqual(finance[0]["payment_status"], "pending_confirmation")
        self.assertEqual(len(events), 1)
        self.assertEqual(adapter.finance_metrics()["income"], 30000)
        self.assertEqual(adapter.finance_metrics()["expenses"], 2000)

    def test_home_sales_and_finance_centers_use_production_adapter_records(self):
        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="user_boss")

        dashboard = home["business_dashboard"]
        source_data = dashboard["source_evidence_available_data"]
        sales_schema = dashboard["business_schema"]["sales_schema"]
        finance_schema = dashboard["business_schema"]["finance_schema"]

        self.assertEqual(source_data["counts"]["sales_contract_data"], 1)
        self.assertEqual(source_data["counts"]["finance_data"], 1)
        self.assertEqual(source_data["counts"]["financial_events"], 1)
        self.assertEqual(source_data["sales_contract_data"][0]["adapter_id"], SALES_ADAPTER_ID)
        self.assertEqual(source_data["finance_data"][0]["adapter_id"], FINANCE_ADAPTER_ID)
        self.assertEqual(source_data["financial_events"][0]["adapter_id"], FINANCE_ADAPTER_ID)
        self.assertEqual(sales_schema["sales_amount"], 30000)
        self.assertEqual(finance_schema["income"], 30000)
        self.assertEqual(finance_schema["receivable"], 30000)
        self.assertEqual(dashboard["production_adapters"]["sales_adapter"]["excluded_unverified"], 1)
        self.assertEqual(dashboard["production_adapters"]["finance_adapter"]["excluded_unverified_events"], 1)


if __name__ == "__main__":
    unittest.main()
