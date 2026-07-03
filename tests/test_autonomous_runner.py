import csv
import io
import json
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oms_v1.autonomous_runner import OMSAutonomousRunner
from oms_v1.cli import main


class AutonomousRunnerTests(unittest.TestCase):
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

    def test_baseline_existing_records_state_without_importing(self):
        resident = self._csv("resident.csv", [{"客户姓名": "张三", "房间号": "301"}])
        runner = OMSAutonomousRunner(live_root=self.live_root, operating_root=self.operating_root, interval_seconds=1)

        result = runner.run_once(sources={"resident": resident}, baseline_existing=True)

        self.assertEqual(result["status"], "baseline_recorded")
        self.assertFalse((self.operating_root / "excel_work_items.jsonl").exists())
        self.assertTrue((self.live_root / "autonomous" / "runner_state.json").exists())

    def test_changed_excel_source_triggers_business_import(self):
        resident = self._csv("resident.csv", [{"客户姓名": "张三", "房间号": "301"}])
        runner = OMSAutonomousRunner(live_root=self.live_root, operating_root=self.operating_root, interval_seconds=1)
        runner.run_once(sources={"resident": resident}, baseline_existing=True)
        time.sleep(0.01)
        resident.write_text("客户姓名,房间号\n李四,302\n", encoding="utf-8-sig")

        result = runner.run_once(sources={"resident": resident})

        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["business_import"]["record_count"], 1)
        self.assertEqual(result["business_import"]["work_item_count"], 1)
        self.assertTrue((self.operating_root / "excel_work_items.jsonl").exists())

    def test_cli_auto_run_once_outputs_continuous_execution_status(self):
        finance_daily = self._csv("daily.csv", [{"日期": "2026.7.1", "收入项目": "入住尾款", "收入金额": "10000"}])
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "auto-run",
                    "--finance-daily",
                    str(finance_daily),
                    "--live-root",
                    str(self.live_root),
                    "--operating-root",
                    str(self.operating_root),
                    "--once",
                    "--force",
                    "--pretty",
                ]
            )
        payload = json.loads(output.getvalue())

        self.assertEqual(code, 0)
        self.assertEqual(payload["run_mode"], "Continuous Execution")
        self.assertEqual(payload["trigger_mode"], "Data-driven + Event-driven")
        self.assertEqual(payload["finance_import"]["work_item_count"], 1)


if __name__ == "__main__":
    unittest.main()
