import tempfile
import unittest
from pathlib import Path

from oms_v1.business_state_writeback import BusinessStateWritebackLayer


class BusinessStateWritebackTests(unittest.TestCase):
    def test_room_execution_writes_truth_source_current_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp) / "live_runtime"
            layer = BusinessStateWritebackLayer(live_root=live_root)
            result = layer.apply(
                {
                    "business_command": {
                        "business_command_id": "cmd_test",
                        "entity": "room",
                        "target": "room_201",
                        "payload": {"route": "room", "action": "change_status"},
                    },
                    "workflow_task": {"workflow_task_id": "wft_test"},
                    "hr_execution": {"hr_execution_id": "hrx_test"},
                    "execution_result": {"execution_result_id": "exec_test"},
                    "state_update": {
                        "state_update_id": "state_test",
                        "route": "room",
                        "target": "room_201",
                        "user_id": "a2c82cb4",
                        "workspace_key": "boss",
                        "state_delta": {"status": "in_progress"},
                    },
                }
            )

            self.assertEqual(result["status"], "applied")
            self.assertEqual(result["domain"], "room")
            self.assertTrue(result["truth_source_updated"])
            room_state = layer.truth_store.read_domain("room")
            self.assertIn("room:room_201", room_state["current_state"])
            self.assertEqual(room_state["current_state"]["room:room_201"]["status"], "in_progress")
            self.assertTrue((live_root / "business_state" / "room_state_writebacks.jsonl").exists())

    def test_finance_and_sales_write_to_separate_domains(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_root = Path(tmp) / "live_runtime"
            layer = BusinessStateWritebackLayer(live_root=live_root)
            for route, target in [("finance", "fevt_1"), ("sales", "contract_1")]:
                result = layer.apply(
                    {
                        "business_command": {
                            "business_command_id": f"cmd_{route}",
                            "entity": route,
                            "target": target,
                            "payload": {"route": route, "action": "complete"},
                        },
                        "workflow_task": {"workflow_task_id": f"wft_{route}"},
                        "hr_execution": {"hr_execution_id": f"hrx_{route}"},
                        "execution_result": {"execution_result_id": f"exec_{route}"},
                        "state_update": {
                            "state_update_id": f"state_{route}",
                            "route": route,
                            "target": target,
                            "user_id": "a2c82cb4",
                            "workspace_key": "boss",
                            "state_delta": {"status": "done"},
                        },
                    }
                )
                self.assertEqual(result["domain"], route)

            finance = layer.truth_store.read_domain("finance")
            sales = layer.truth_store.read_domain("sales")
            self.assertEqual(finance["current_state"]["finance:fevt_1"]["status"], "completed")
            self.assertEqual(sales["current_state"]["sales:contract_1"]["status"], "completed")
            summary = layer.read_state_summary()
            self.assertEqual(summary["counts"]["finance"], 1)
            self.assertEqual(summary["counts"]["sales"], 1)


if __name__ == "__main__":
    unittest.main()
