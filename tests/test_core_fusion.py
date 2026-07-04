import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oms_v1.cli import main
from oms_v1.core_fusion import CORE_FUSION_FLOW, CoreFusionLayer
from oms_v1.excel_importer import ExcelOMSImporter
from oms_v1.finance_importer import FinanceDataImporter
from oms_v1.home_ui import OMSHomeUI
from oms_v1.operating_center_source import OPERATING_CENTER_PEOPLE


class CoreFusionLayerTests(unittest.TestCase):
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

    def _read_jsonl(self, path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _realworld_mapping(self, *, complete=True):
        rows = []
        keys = OPERATING_CENTER_PEOPLE if complete else {"boss": OPERATING_CENTER_PEOPLE["boss"]}
        for key, person in keys.items():
            rows.append({"name": person["name"], "role": person["role"], "user_id": f"user_{key}", "open_id": f"open_{key}"})
        path = self.live_root / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
        return path

    def _import_sample_business_data(self):
        resident = self._csv("resident.csv", [{"customer": "A", "room": "201", "checkin_date": "2026.7.5"}])
        room = self._csv("room.csv", [{"room": "201", "status": "occupied"}])
        contracts = self._csv("contracts.csv", [{"customer": "B", "contract_no": "HJ-1", "amount": "30000"}])
        finance = self._csv("finance.csv", [{"date": "2026.7.5", "income_item": "deposit", "income_amount": "10000"}])
        ExcelOMSImporter(self.live_root, self.operating_root).import_sources(
            resident=resident,
            room_status=room,
            contracts=contracts,
        )
        FinanceDataImporter(self.live_root, self.operating_root).import_sources(finance_daily=finance)

    def test_core_fusion_rebuilds_single_runtime_chain(self):
        self._realworld_mapping()
        self._import_sample_business_data()

        state = CoreFusionLayer(self.live_root, self.operating_root).rebuild_from_saved_state(user_id="user_huanhuan")
        tasks = self._read_jsonl(self.live_root / "core_fusion" / "unified_task_stream.jsonl")
        events = self._read_jsonl(self.live_root / "core_fusion" / "single_business_event_stream.jsonl")

        self.assertEqual(state["flow"], CORE_FUSION_FLOW)
        self.assertEqual(state["mode"], "single_runtime_system")
        self.assertGreater(state["counts"]["business_events"], 0)
        self.assertEqual(len(tasks), len(events))
        self.assertTrue(all(task["schema_version"] == "oms.v1.unified_task" for task in tasks))
        self.assertTrue(all(task["flow"] == CORE_FUSION_FLOW for task in tasks))
        self.assertTrue(all(task["assigned_user_id"] for task in tasks))
        self.assertEqual(state["identity_fusion"]["workspaces"]["huanhuan"]["user_id"], "user_huanhuan")
        self.assertEqual(state["work_entry"]["entry_type"], "personal_workspace")
        self.assertTrue(state["work_entry"]["tasks"])
        self.assertEqual({task["workspace_key"] for task in state["work_entry"]["tasks"]}, {"huanhuan"})
        self.assertTrue(state["validation"]["identity_traceable"])
        self.assertTrue(state["validation"]["data_traceable"])
        self.assertTrue(state["validation"]["task_traceable"])

    def test_missing_feishu_user_ids_block_execution_without_fallback_identity(self):
        self._realworld_mapping(complete=False)
        self._import_sample_business_data()

        state = CoreFusionLayer(self.live_root, self.operating_root).rebuild_from_saved_state(user_id="missing_user")
        tasks = self._read_jsonl(self.live_root / "core_fusion" / "unified_task_stream.jsonl")

        self.assertFalse(state["validation"]["identity_traceable"])
        self.assertEqual(state["validation"]["anonymous_execution_paths"], 0)
        self.assertEqual(state["validation"]["fallback_identity_paths"], 0)
        self.assertEqual(state["work_entry"]["entry_status"], "blocked")
        self.assertTrue(any(task["status"] == "pending_identity_binding" for task in tasks))
        self.assertTrue(any(task["execution_status"] == "needs_user_binding" for task in tasks))
        self.assertTrue(any(not task["assigned_user_id"] for task in tasks))

    def test_home_ui_reads_core_fusion_as_its_entry_source(self):
        self._realworld_mapping()
        self._import_sample_business_data()

        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="user_huanhuan")

        self.assertEqual(home["entry"], "personal_workspace")
        self.assertEqual(home["core_fusion"]["flow"], CORE_FUSION_FLOW)
        self.assertGreater(home["sections"]["event_execution_flow"]["count"], 0)
        source_data = home["business_dashboard"]["source_evidence_available_data"]
        self.assertTrue(source_data["business_event_flow"])
        self.assertTrue(source_data["workflow_distribution"])
        self.assertTrue(source_data["hr_execution_flow"])
        self.assertEqual(
            {item["business_domain"] for item in source_data["workflow_distribution"]},
            {"workflow_distribution"},
        )

    def test_cli_core_fusion_command_outputs_state(self):
        self._realworld_mapping()
        self._import_sample_business_data()
        out = self.root / "core_fusion.json"

        with redirect_stdout(io.StringIO()):
            code = main(
                [
                    "core-fusion",
                    "--live-root",
                    str(self.live_root),
                    "--operating-root",
                    str(self.operating_root),
                    "--user-id",
                    "user_boss",
                    "--out",
                    str(out),
                    "--pretty",
                ]
            )
        payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["flow"], CORE_FUSION_FLOW)
        self.assertEqual(payload["work_entry"]["workspace_key"], "boss")
        self.assertEqual(payload["work_entry"]["entry_type"], "master_control_dashboard")
        self.assertTrue(payload["work_entry"]["permissions"]["view_all_user_workspaces"])
        self.assertTrue(payload["work_entry"]["permissions"]["control_task_assignment"])
        self.assertEqual(payload["work_entry"]["hierarchy"]["layer_1"], "BOSS Master Control")
        self.assertIn("business_flows", payload["work_entry"])
        self.assertIn("workspace_matrix", payload["work_entry"])
        self.assertIn("risk_register", payload["work_entry"])
        self.assertIn("execution_status", payload["work_entry"])


if __name__ == "__main__":
    unittest.main()
