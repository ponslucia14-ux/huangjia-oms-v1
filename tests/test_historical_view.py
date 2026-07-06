import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oms_v1.business_event_engine import BusinessEventEngine
from oms_v1.cli import main
from oms_v1.excel_importer import ExcelOMSImporter
from oms_v1.finance_importer import FinanceDataImporter
from oms_v1.historical_view import HISTORICAL_VIEW_FLOW, HistoricalDataViewLayer
from oms_v1.operating_center_source import OPERATING_CENTER_PEOPLE


class HistoricalDataViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.live_root = self.root / "live"
        self.operating_root = self.root / "operating"

    def tearDown(self):
        self.tmp.cleanup()

    def _csv(self, name, rows):
        path = self.root / name
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _realworld_mapping(self):
        rows = [
            {"name": person["name"], "role": person["role"], "user_id": f"user_{key}", "open_id": f"open_{key}"}
            for key, person in OPERATING_CENTER_PEOPLE.items()
        ]
        path = self.live_root / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")

    def _build_runtime(self):
        self._realworld_mapping()
        resident = self._csv("resident.csv", [{"customer": "A", "room": "201", "checkin_date": "2026.7.5", "checkout_date": "2026.7.8"}])
        contracts = self._csv("contracts.csv", [{"customer": "B", "contract_no": "HJ-1", "amount": "30000"}])
        finance = self._csv("finance.csv", [{"date": "2026.7.5", "income_item": "deposit", "income_amount": "10000"}])
        ExcelOMSImporter(self.live_root, self.operating_root).import_sources(resident=resident, contracts=contracts)
        FinanceDataImporter(self.live_root, self.operating_root).import_sources(finance_daily=finance)
        return BusinessEventEngine(self.live_root, self.operating_root).rebuild_from_saved_state()

    def test_history_layer_builds_timeline_trace_chain_and_completion_log(self):
        summary = self._build_runtime()

        view = HistoricalDataViewLayer(self.live_root, self.operating_root).build_history_view(limit=20)
        first = view["timeline"][0]

        self.assertEqual(view["flow"], HISTORICAL_VIEW_FLOW)
        self.assertEqual(view["counts"]["business_events"], summary["business_event_count"])
        self.assertEqual(view["counts"]["returned_timeline_items"], len(view["timeline"]))
        self.assertTrue(view["timeline"])
        self.assertTrue(first["source_file"])
        self.assertTrue(first["row_id"])
        self.assertTrue(first["ingestion_event_id"])
        self.assertTrue(first["business_event_id"])
        self.assertTrue(first["workflow_task_id"])
        self.assertTrue(first["hr_execution_id"])
        self.assertEqual([stage["stage"] for stage in first["stage_sequence"]], ["data_import", "business_event", "workflow_distribution", "hr_execution", "completion"])
        self.assertIn(first["completion_log"]["completion_status"], {"assigned", "needs_user_binding", "not_completed"})
        self.assertIn("room_history", view["multidimensional_history"])
        self.assertIn("finance_history", view["multidimensional_history"])
        self.assertIn("sales_history", view["multidimensional_history"])
        self.assertTrue((self.live_root / "history" / "historical_view_state.json").exists())

    def test_history_layer_filters_by_date_and_workspace(self):
        self._build_runtime()
        full_view = HistoricalDataViewLayer(self.live_root, self.operating_root).build_history_view(limit=20)
        first = full_view["timeline"][0]

        filtered = HistoricalDataViewLayer(self.live_root, self.operating_root).build_history_view(
            date=first["date"],
            workspace_key=first["workspace_key"],
            limit=20,
        )

        self.assertTrue(filtered["timeline"])
        self.assertTrue(all(item["date"] == first["date"] for item in filtered["timeline"]))
        self.assertTrue(all(item["workspace_key"] == first["workspace_key"] for item in filtered["timeline"]))

    def test_cli_history_outputs_historical_view(self):
        self._build_runtime()
        out = self.root / "history.json"

        with redirect_stdout(io.StringIO()):
            code = main(
                [
                    "history",
                    "--live-root",
                    str(self.live_root),
                    "--operating-root",
                    str(self.operating_root),
                    "--limit",
                    "5",
                    "--out",
                    str(out),
                    "--pretty",
                ]
            )
        payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["schema_version"], "oms.v1.historical_data_view")
        self.assertLessEqual(len(payload["timeline"]), 5)
        self.assertEqual(payload["source_of_truth"], "OMS_TRUTH_SOURCE")


if __name__ == "__main__":
    unittest.main()
