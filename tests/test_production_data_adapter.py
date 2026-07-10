import json
import tempfile
import unittest
from pathlib import Path

from oms_v1.home_ui import OMSHomeUI
from oms_v1.production_data_adapter import (
    CAREGIVER_ADAPTER_ID,
    FINANCE_ADAPTER_ID,
    ROOM_ADAPTER_ID,
    SALES_ADAPTER_ID,
    STAY_ADAPTER_ID,
    ProductionDataAdapter,
)
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
            json.dumps({"rows": [{"name": "石磊", "role": "boss", "user_id": "legacy_boss"}]}, ensure_ascii=False),
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
        self.stay_evidence = {
            "truth_source": "Operations Truth Source",
            "source_type": "stay",
            "source_file": str(self.root / "operations.xlsx"),
            "source_sheet": "stay",
            "row_number": 4,
            "record_id": "stay_row_4",
            "trace_id": "operations:operations.xlsx:stay:4:stay_row_4",
        }
        self.room_evidence = {
            "truth_source": "Operations Truth Source",
            "source_type": "room_status",
            "source_file": str(self.root / "operations.xlsx"),
            "source_sheet": "room",
            "row_number": 5,
            "record_id": "room_row_5",
            "trace_id": "operations:operations.xlsx:room:5:room_row_5",
        }
        self.caregiver_evidence = {
            "truth_source": "Operations Truth Source",
            "source_type": "caregiver",
            "source_file": str(self.root / "operations.xlsx"),
            "source_sheet": "caregiver",
            "row_number": 6,
            "record_id": "caregiver_row_6",
            "trace_id": "operations:operations.xlsx:caregiver:6:caregiver_row_6",
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
                    "stay_records": [
                        {
                            "stay_id": "stay_1",
                            "customer_name": "Customer A",
                            "room_id": "201",
                            "caregiver_id": "cg_1",
                            "status": "IN_STAY",
                            "checkin_date": "2026-07-10",
                            "checkout_date": "2026-08-10",
                            "source_evidence": self.stay_evidence,
                        },
                        {"stay_id": "stay_legacy"},
                    ],
                    "room_records": [
                        {
                            "room_id": "201",
                            "room_name": "201",
                            "floor": "2",
                            "status": "OCCUPIED",
                            "current_stay_id": "stay_1",
                            "source_evidence": self.room_evidence,
                        },
                        {"room_id": "999"},
                    ],
                    "caregiver_records": [
                        {
                            "caregiver_id": "cg_1",
                            "caregiver_name": "Caregiver A",
                            "status": "ASSIGNED",
                            "current_stay_id": "stay_1",
                            "source_evidence": self.caregiver_evidence,
                        },
                        {"caregiver_id": "cg_legacy"},
                    ],
                    "validation": {
                        "warnings": [
                            {"row_number": 42, "reason": "missing_room_label", "markers": [{"day": 1, "value": "Customer Missing Room"}]}
                        ]
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.truth_root / "stay.json").write_text(
            json.dumps(
                {
                    "schema_version": "oms.v1.truth_source.stay",
                    "mode": "single_source_of_truth",
                    "domain": "stay",
                    "updated_at": "2026-07-09T23:59:00+08:00",
                    "stay_records": [
                        {
                            "stay_id": "stay_1",
                            "customer_name": "Customer A",
                            "room_id": "201",
                            "status": "IN_STAY",
                            "checkin_date": "2026-07-10",
                            "checkout_date": "2026-08-10",
                            "source_evidence": self.stay_evidence,
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.truth_root / "customer.json").write_text(
            json.dumps(
                {
                    "schema_version": "oms.v1.truth_source.customer",
                    "mode": "single_source_of_truth",
                    "domain": "customer",
                    "updated_at": "2026-07-09T23:59:00+08:00",
                    "customer_records": [
                        {
                            "record_id": "customer_1",
                            "customer_id": "customer_1",
                            "customer_name": "Customer A",
                            "phone": "13800000000",
                            "expected_delivery_date": "2026-08-01",
                            "source_evidence": self.sales_evidence,
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.truth_root / "contract.json").write_text(
            json.dumps(
                {
                    "schema_version": "oms.v1.truth_source.contract",
                    "mode": "single_source_of_truth",
                    "domain": "contract",
                    "updated_at": "2026-07-09T23:59:00+08:00",
                    "contract_records": [
                        {
                            "record_id": "contract_1",
                            "contract_id": "contract_1",
                            "customer_id": "customer_1",
                            "customer_name": "Customer A",
                            "phone": "13800000000",
                            "sign_date": "2026-07-01",
                            "expected_delivery_date": "2026-08-01",
                            "package_name": "Package A",
                            "salesperson_name": "Sales A",
                            "contract_amount": 30000,
                            "inner_store_nights": 24,
                            "outer_store_nights": 3,
                            "source_month": "2026-07",
                            "source_evidence": self.sales_evidence,
                        }
                    ],
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

    def test_operations_adapters_expose_only_verified_truth_records(self):
        adapter = ProductionDataAdapter(self._store())

        stays = adapter.stay_records()
        rooms = adapter.room_records()
        caregivers = adapter.caregiver_records()
        metrics = adapter.operations_metrics()

        self.assertEqual(len(stays), 1)
        self.assertEqual(stays[0]["adapter_id"], STAY_ADAPTER_ID)
        self.assertEqual(stays[0]["domain"], "Stay")
        self.assertEqual(stays[0]["source_evidence"]["record_id"], "stay_row_4")
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]["adapter_id"], ROOM_ADAPTER_ID)
        self.assertEqual(rooms[0]["domain"], "Room")
        self.assertEqual(len(caregivers), 1)
        self.assertEqual(caregivers[0]["adapter_id"], CAREGIVER_ADAPTER_ID)
        self.assertEqual(caregivers[0]["domain"], "Caregiver")
        self.assertEqual(metrics["active_stays"], 1)
        self.assertEqual(metrics["occupied_rooms"], 1)
        self.assertEqual(metrics["assigned_caregivers"], 1)

    def test_home_sales_and_finance_centers_use_production_adapter_records(self):
        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="a2c82cb4")

        dashboard = home["business_dashboard"]
        source_data = dashboard["source_evidence_available_data"]
        sales_schema = dashboard["business_schema"]["sales_schema"]
        finance_schema = dashboard["business_schema"]["finance_schema"]

        self.assertEqual(source_data["counts"]["sales_contract_data"], 1)
        self.assertEqual(source_data["counts"]["finance_data"], 1)
        self.assertEqual(source_data["counts"]["financial_events"], 1)
        self.assertEqual(source_data["counts"]["stay_data"], 1)
        self.assertEqual(source_data["counts"]["room_status_data"], 1)
        self.assertEqual(source_data["counts"]["caregiver_data"], 1)
        self.assertEqual(source_data["sales_contract_data"][0]["adapter_id"], SALES_ADAPTER_ID)
        self.assertEqual(source_data["finance_data"][0]["adapter_id"], FINANCE_ADAPTER_ID)
        self.assertEqual(source_data["financial_events"][0]["adapter_id"], FINANCE_ADAPTER_ID)
        self.assertEqual(source_data["stay_data"][0]["adapter_id"], STAY_ADAPTER_ID)
        self.assertEqual(source_data["room_status_data"][0]["adapter_id"], ROOM_ADAPTER_ID)
        self.assertEqual(source_data["caregiver_data"][0]["adapter_id"], CAREGIVER_ADAPTER_ID)
        self.assertEqual(sales_schema["sales_amount"], 30000)
        self.assertEqual(finance_schema["income"], 30000)
        self.assertEqual(finance_schema["receivable"], 30000)
        self.assertEqual(dashboard["business_schema"]["resident_flow_schema"]["active_stays"], 1)
        self.assertEqual(dashboard["business_schema"]["service_schema"]["in_service"], 1)
        self.assertEqual(dashboard["production_adapters"]["sales_adapter"]["excluded_unverified"], 1)
        self.assertEqual(dashboard["production_adapters"]["finance_adapter"]["excluded_unverified_events"], 1)
        self.assertEqual(dashboard["production_adapters"]["stay_adapter"]["excluded_unverified"], 0)
        self.assertEqual(dashboard["production_adapters"]["room_adapter"]["excluded_unverified"], 1)
        self.assertEqual(dashboard["production_adapters"]["caregiver_adapter"]["excluded_unverified"], 1)

    def test_production_page_datasets_expose_full_feishu_page_records(self):
        adapter = ProductionDataAdapter(self._store())

        sales = adapter.production_page_dataset("sales")
        finance = adapter.production_page_dataset("finance")
        rooms = adapter.production_page_dataset("rooms")
        contracts = adapter.production_page_dataset("contracts")

        self.assertEqual(sales["record_count"], 1)
        self.assertEqual(sales["records"][0]["contract_id"], "HJ-001")
        self.assertEqual(sales["metrics"]["contract_amount_total"], 30000)
        self.assertIn("source_line", sales["records"][0])
        self.assertEqual(finance["record_count"], 2)
        self.assertEqual(finance["metrics"]["income_total"], 30000)
        self.assertEqual(finance["metrics"]["expense_total"], 2000)
        self.assertEqual(rooms["record_count"], 2)
        self.assertEqual(rooms["metrics"]["missing_room_number_count"], 1)
        self.assertEqual(contracts["record_count"], 1)
        self.assertEqual(contracts["records"][0]["phone"], "13800000000")
        self.assertEqual(contracts["metrics"]["contract_amount_total"], 30000)


if __name__ == "__main__":
    unittest.main()
