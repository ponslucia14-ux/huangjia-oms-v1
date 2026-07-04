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

    def _realworld_mapping(self, rows):
        path = self.live_root / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_env_user_ids_are_ignored_for_human_execution_closure(self):
        env_path = self._env({"FEISHU_USER_ID_BOSS": "user_boss"})

        result = HumanExecutionClosure(self.live_root, self.operating_root, env_path).close()

        self.assertEqual(result["closure_status"], "blocked")
        self.assertEqual(result["mapping_status"], "missing_required_user_id")
        self.assertIn("FEISHU_USER_ID_BOSS", result["missing_env_keys"])
        self.assertIn("FEISHU_USER_ID_HUANHUAN", result["missing_env_keys"])
        self.assertFalse(result["policy"]["missing_required_user_id_allowed"])
        self.assertTrue((self.live_root / "audit" / "human_execution_closure.json").exists())

    def test_realworld_mapping_supplies_feishu_user_id_bindings(self):
        env_path = self._env({})
        self._realworld_mapping(
            [
                {"name": "BOSS", "role": "boss", "user_id": "user_boss"},
                {"name": "刘姐", "role": "财务", "user_id": "user_liujie"},
            ]
        )

        result = HumanExecutionClosure(self.live_root, self.operating_root, env_path).close()

        self.assertEqual(result["closure_status"], "blocked")
        self.assertEqual(result["mapping_status"], "missing_required_user_id")
        self.assertNotIn("FEISHU_USER_ID_BOSS", result["missing_env_keys"])
        self.assertNotIn("FEISHU_USER_ID_LIUJIE", result["missing_env_keys"])
        self.assertIn("FEISHU_USER_ID_HUANHUAN", result["missing_env_keys"])

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
        env_path = self._env({})
        self._realworld_mapping(
            [
                {"name": "BOSS", "role": "boss", "user_id": "user_boss"},
                {"name": "欢欢", "role": "销售", "user_id": "user_huanhuan"},
                {"name": "六月", "role": "店总 + 销售", "user_id": "user_june"},
                {"name": "刘姐", "role": "财务", "user_id": "user_liujie"},
                {"name": "张姐", "role": "财务总监/会计", "user_id": "user_zhangjie"},
                {"name": "娜娜", "role": "管家", "user_id": "user_nana"},
                {"name": "陈晶辉", "role": "产护部总监", "user_id": "user_chenchangyi"},
                {"name": "周厨", "role": "厨师长", "user_id": "user_zhouchen"},
                {"name": "维维", "role": "行政采购 + 照护师工资决算", "user_id": "user_yaowei"},
                {"name": "宗惠", "role": "人事行政", "user_id": "user_songxue"},
                {"name": "子渝", "role": "食材采购 + 销售", "user_id": "user_yuchun"},
            ]
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
