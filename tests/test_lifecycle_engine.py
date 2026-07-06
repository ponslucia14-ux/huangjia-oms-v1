import json
import tempfile
import unittest
from pathlib import Path

from oms_v1.lifecycle_engine import LIFECYCLE_MODELS, LifecycleEngine


class LifecycleEngineTests(unittest.TestCase):
    def test_room_execution_enters_room_lifecycle_and_action_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp) / "live_runtime"
            engine = LifecycleEngine(live_root)

            result = engine.apply_execution(
                {
                    "business_command": {
                        "business_command_id": "cmd_room",
                        "entity": "room",
                        "target": "room_201",
                        "payload": {"route": "room", "action": "open-room"},
                    },
                    "execution_result": {"execution_result_id": "exec_room"},
                    "state_update": {
                        "state_update_id": "state_room",
                        "route": "room",
                        "target": "room_201",
                        "state_delta": {"status": "in_progress"},
                    },
                    "trace_chain": {"workflow_task_id": "wfc_room"},
                }
            )

            self.assertEqual(result["domain"], "room")
            self.assertEqual(result["current_stage"], "in_house")
            self.assertEqual(result["closure_detection"]["status"], "open")
            self.assertEqual(result["next_stage"], "cleaning")
            self.assertTrue((live_root / "lifecycle" / "lifecycle_events.jsonl").exists())
            self.assertTrue((live_root / "lifecycle" / "action_queue.jsonl").exists())
            current = json.loads((live_root / "lifecycle" / "current_lifecycles.json").read_text(encoding="utf-8"))
            self.assertIn("room:room_201", current["current_state"])

    def test_allocation_retrigger_enters_allocation_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp) / "live_runtime"
            engine = LifecycleEngine(live_root)

            result = engine.apply_execution(
                {
                    "business_command": {
                        "business_command_id": "cmd_allocation",
                        "entity": "room",
                        "target": "room_201",
                        "payload": {"route": "room", "action": "retrigger_room_allocation"},
                    },
                    "execution_result": {"execution_result_id": "exec_allocation"},
                    "state_update": {
                        "state_update_id": "state_allocation",
                        "route": "room",
                        "target": "room_201",
                        "state_delta": {"status": "in_progress"},
                    },
                }
            )

            self.assertEqual(result["domain"], "allocation")
            self.assertEqual(result["current_stage"], "room_matching")
            self.assertIn(result["current_stage"], [item["stage"] for item in LIFECYCLE_MODELS["allocation"]])
            self.assertEqual(result["feedback_loop"]["next_cycle_adjustment"], "use_current_stage_to_drive_next_action")

    def test_summary_counts_open_lifecycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp) / "live_runtime"
            engine = LifecycleEngine(live_root)
            engine.apply_execution(
                {
                    "business_command": {
                        "business_command_id": "cmd_finance",
                        "entity": "finance",
                        "target": "tx_1",
                        "payload": {"route": "finance", "action": "trace-finance"},
                    },
                    "execution_result": {"execution_result_id": "exec_finance"},
                    "state_update": {
                        "state_update_id": "state_finance",
                        "route": "finance",
                        "target": "tx_1",
                        "state_delta": {"status": "trace_requested"},
                    },
                }
            )

            summary = engine.build_summary()

            self.assertEqual(summary["source"], "OMS_LIFECYCLE_ENGINE")
            self.assertEqual(summary["open_count"], 1)
            self.assertEqual(summary["closed_count"], 0)
            self.assertEqual(summary["counts"]["finance"], 1)
            self.assertEqual(summary["risk_status"], "attention_required")


if __name__ == "__main__":
    unittest.main()
