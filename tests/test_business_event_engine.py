import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from oms_v1.business_event_engine import BusinessEventEngine
from oms_v1.excel_importer import ExcelOMSImporter
from oms_v1.finance_importer import FinanceDataImporter
from oms_v1.home_ui import OMSHomeUI


class BusinessEventEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.live_root = self.root / "live"
        self.operating_root = self.root / "operating"

    def tearDown(self):
        self.tmp.cleanup()
        for key in ["FEISHU_USER_ID_HUANHUAN", "FEISHU_USER_ID_JUNE", "FEISHU_USER_ID_NANA", "FEISHU_USER_ID_SONGXUE"]:
            os.environ.pop(key, None)

    def _csv(self, name, rows):
        path = self.root / name
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _read_jsonl(self, path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_runtime_rows_become_business_events_workflow_tasks_and_hr_execution(self):
        os.environ["FEISHU_USER_ID_HUANHUAN"] = "ou_huanhuan"
        os.environ["FEISHU_USER_ID_JUNE"] = "ou_june"
        os.environ["FEISHU_USER_ID_NANA"] = "ou_nana"
        os.environ["FEISHU_USER_ID_SONGXUE"] = "ou_songxue"
        resident = self._csv("resident.csv", [{"濮撳悕": "瀹㈡埛A", "鍏ヤ綇鏃ユ湡": "2026.7.4", "绠″": "濞滃"}])
        room = self._csv("room.csv", [{"鎴垮彿": "201", "鎴挎€?": "寰呮帓", "濮撳悕": "瀹㈡埛B"}])
        contracts = self._csv("contracts.csv", [{"绛剧害鏃ユ湡": "2026.7.4", "瀹㈡埛": "瀹㈡埛C", "浠锋牸": "25000"}])
        finance_daily = self._csv("finance.csv", [{"鏃ユ湡": "2026.7.4", "鏀跺叆椤圭洰": "灏炬", "鏀跺叆閲戦": "10000"}])
        wage = self._csv("wage.csv", [{"濮撳悕": "鐓ф姢甯圓", "搴斿彂": "6000"}])

        ExcelOMSImporter(self.live_root, self.operating_root).import_sources(
            resident=resident,
            room_status=room,
            contracts=contracts,
        )
        FinanceDataImporter(self.live_root, self.operating_root).import_sources(
            finance_daily=finance_daily,
            care_wage=wage,
        )
        summary = BusinessEventEngine(self.live_root, self.operating_root).rebuild_from_saved_state()

        self.assertEqual(summary["business_event_count"], 5)
        self.assertEqual(summary["workflow_task_count"], 5)
        self.assertEqual(summary["hr_execution_item_count"], 5)
        self.assertEqual(summary["event_type_counts"]["sales_event"], 1)
        self.assertEqual(summary["event_type_counts"]["finance_event"], 1)
        self.assertEqual(summary["event_type_counts"]["room_event"], 1)
        self.assertEqual(summary["event_type_counts"]["service_event"], 1)
        self.assertEqual(summary["event_type_counts"]["hr_event"], 1)

        events = self._read_jsonl(self.live_root / "business_events" / "business_event_flow.jsonl")
        tasks = self._read_jsonl(self.live_root / "business_events" / "workflow_distribution.jsonl")
        hr_items = self._read_jsonl(self.live_root / "hr_flow" / "hr_execution_items.jsonl")
        self.assertTrue(all(event["event_chain"]["source_file"] for event in events))
        self.assertTrue(all(task["business_event_id"] for task in tasks))
        self.assertTrue(all(item["hr_source"] == "business_event_flow" for item in hr_items))
        self.assertTrue(all(item["next_action"] for item in hr_items))
        self.assertTrue(any(item["workspace_key"] == "songxue" for item in hr_items))

    def test_home_ui_exposes_event_chain_and_hr_execution_flow(self):
        contracts = self._csv("contracts.csv", [{"绛剧害鏃ユ湡": "2026.7.4", "瀹㈡埛": "瀹㈡埛C", "浠锋牸": "25000"}])
        ExcelOMSImporter(self.live_root, self.operating_root).import_sources(contracts=contracts)

        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="huanhuan")
        dashboard = home["business_dashboard"]

        self.assertGreaterEqual(home["sections"]["event_execution_flow"]["count"], 1)
        self.assertGreaterEqual(dashboard["data_truth_alignment"]["visible_business_events"], 1)
        self.assertGreaterEqual(dashboard["data_truth_alignment"]["visible_hr_execution_items"], 1)
        source_data = dashboard["source_evidence_available_data"]
        self.assertTrue(source_data["business_event_flow"])
        self.assertTrue(source_data["hr_execution_flow"])
        self.assertEqual(source_data["business_event_flow"][0]["event_chain"]["workspace"], "销售工作台")
        event_item = home["sections"]["event_execution_flow"]["items"][0]
        self.assertTrue(event_item["id"])
        self.assertEqual([field["label"] for field in event_item["display_fields"][:4]], ["Excel来源", "业务事件", "执行人", "工作台"])


if __name__ == "__main__":
    unittest.main()
