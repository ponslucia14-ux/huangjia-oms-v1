import csv
import json
import tempfile
import unittest
from pathlib import Path

from oms_v1.excel_importer import ExcelOMSImporter
from oms_v1.finance_importer import FinanceDataImporter
from oms_v1.human_execution_closure import HumanExecutionClosure


class HumanExecutionClosureTests(unittest.TestCase):
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

    def _env(self, values):
        path = self.root / "feishu.env"
        path.write_text("\n".join(f"{key}={value}" for key, value in values.items()), encoding="utf-8")
        return path

    def test_missing_user_ids_block_human_execution_closure(self):
        env_path = self._env({"FEISHU_USER_ID_BOSS": "user_boss"})

        result = HumanExecutionClosure(self.live_root, self.operating_root, env_path).close()

        self.assertEqual(result["closure_status"], "blocked")
        self.assertEqual(result["mapping_status"], "missing_required_user_id")
        self.assertIn("FEISHU_USER_ID_HUANHUAN", result["missing_env_keys"])
        self.assertFalse(result["policy"]["unresolved_user_id_allowed"])
        self.assertTrue((self.live_root / "audit" / "human_execution_closure.json").exists())

    def test_complete_user_ids_assign_all_workflow_and_hr_items(self):
        resident = self._csv("resident.csv", [{"客户姓名": "客户A", "房间": "201", "入住日期": "2026.7.5"}])
        room = self._csv("room.csv", [{"房号": "201", "房态": "待排房"}])
        contracts = self._csv("contracts.csv", [{"签约客户": "客户B", "合同编号": "HJ-1", "合同金额": "30000"}])
        finance = self._csv("finance.csv", [{"日期": "2026.7.5", "收入项目": "定金", "收入金额": "10000"}])
        wage = self._csv("wage.csv", [{"姓名": "照护师A", "工资": "6000"}])
        ExcelOMSImporter(self.live_root, self.operating_root).import_sources(
            resident=resident,
            room_status=room,
            contracts=contracts,
        )
        FinanceDataImporter(self.live_root, self.operating_root).import_sources(
            finance_daily=finance,
            care_wage=wage,
        )
        env_path = self._env(
            {
                "FEISHU_USER_ID_BOSS": "user_boss",
                "FEISHU_USER_ID_HUANHUAN": "user_huanhuan",
                "FEISHU_USER_ID_JUNE": "user_june",
                "FEISHU_USER_ID_LIUJIE": "user_liujie",
                "FEISHU_USER_ID_NANA": "user_nana",
            }
        )

        result = HumanExecutionClosure(self.live_root, self.operating_root, env_path).close()

        self.assertEqual(result["closure_status"], "complete")
        self.assertEqual(result["mapping_status"], "complete")
        self.assertEqual(result["unassigned_workflow_task_count"], 0)
        self.assertEqual(result["unassigned_hr_execution_count"], 0)
        self.assertEqual(result["human_execution_rate"], 1.0)

        hr_items = [
            json.loads(line)
            for line in (self.live_root / "hr_flow" / "hr_execution_items.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(all(item["executor_user_id"] for item in hr_items))
        self.assertEqual({item["execution_status"] for item in hr_items}, {"assigned"})


if __name__ == "__main__":
    unittest.main()
