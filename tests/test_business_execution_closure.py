import json
import tempfile
import unittest
from pathlib import Path

from oms_v1.business_execution_closure import BusinessExecutionClosureLayer


class BusinessExecutionClosureTests(unittest.TestCase):
    def test_execute_action_writes_closure_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp) / "live_runtime"
            operating_root = live_root / "operational_core"
            layer = BusinessExecutionClosureLayer(live_root=live_root, operating_root=operating_root)

            result = layer.execute_action(
                {
                    "user_id": "a2c82cb4",
                    "workspace_key": "boss",
                    "route": "room",
                    "action": "open-room",
                    "target": "201南双卫",
                    "current_room": "201南双卫",
                    "source": "oms_ui",
                }
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["closure_status"], "closed")
            self.assertEqual(result["business_command"]["entity"], "room")
            self.assertEqual(result["execution_result"]["explainability_status"], "explained")
            self.assertEqual(result["decision_chain"]["domain"], "room")
            self.assertTrue(result["decision_chain"]["decision_summary"])
            self.assertEqual(result["retrigger_closure"]["status"], "not_requested")
            self.assertEqual(result["business_state_writeback"]["status"], "applied")
            self.assertTrue(result["business_state_writeback"]["truth_source_updated"])
            self.assertEqual(result["state_update"]["state_delta"]["status"], "in_progress")
            for field in [
                "action_event_id",
                "business_command_id",
                "workflow_task_id",
                "hr_execution_id",
                "execution_result_id",
                "state_update_id",
            ]:
                self.assertTrue(result["trace_chain"][field])
            for path in [
                live_root / "business_execution" / "action_events.jsonl",
                live_root / "business_execution" / "execution_results.jsonl",
                live_root / "business_execution" / "state_updates.jsonl",
                live_root / "business_events" / "workflow_execution_closure.jsonl",
                live_root / "hr_flow" / "hr_execution_closure.jsonl",
            ]:
                self.assertTrue(path.exists(), str(path))
                self.assertTrue(path.read_text(encoding="utf-8").strip(), str(path))
            latest = json.loads((live_root / "business_execution" / "latest_state.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["trace_chain"]["state_update_id"], result["trace_chain"]["state_update_id"])

    def test_room_retrigger_reruns_room_engine_and_records_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp) / "live_runtime"
            operating_root = live_root / "operational_core"
            layer = BusinessExecutionClosureLayer(live_root=live_root, operating_root=operating_root)

            result = layer.execute_action(
                {
                    "user_id": "a2c82cb4",
                    "workspace_key": "boss",
                    "route": "room",
                    "action": "retrigger_room_allocation",
                    "target": "room_201",
                    "source": "oms_ui",
                }
            )

            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["decision_chain"]["retrigger_available"])
            self.assertEqual(result["retrigger_closure"]["status"], "completed")
            self.assertEqual(result["retrigger_closure"]["engine"], "RoomAllocationEngine")
            self.assertIn("allocation_count", result["retrigger_closure"]["result_summary"])
            self.assertTrue((live_root / "decision_explainability" / "decision_chains.jsonl").exists())
            self.assertTrue((live_root / "decision_retrigger" / "retrigger_results.jsonl").exists())

    def test_execute_action_blocks_missing_user_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            layer = BusinessExecutionClosureLayer(live_root=Path(tmp) / "live_runtime")

            result = layer.execute_action({"route": "finance", "action": "trace-finance", "target": "today"})

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["closure_status"], "blocked")
            self.assertEqual(result["blocking_reason"], "missing_user_id")
            self.assertTrue((Path(tmp) / "live_runtime" / "business_execution" / "blocked_actions.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
