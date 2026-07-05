import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oms_v1.business_event_engine import BusinessEventEngine
from oms_v1.cli import main
from oms_v1.core_data_model import CORE_DATA_MODEL_FLOW, CoreDataModelLayer
from oms_v1.excel_importer import ExcelOMSImporter
from oms_v1.finance_importer import FinanceDataImporter
from oms_v1.room_allocation_engine import ROOM_ALLOCATION_FLOW, RoomAllocationEngine


class CoreDataModelRoomEngineTests(unittest.TestCase):
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

    def _realworld_mapping(self):
        rows = [
            {"name": "六月", "role": "店总 + 销售", "user_id": "ou_june"},
            {"name": "欢欢", "role": "销售", "user_id": "ou_huanhuan"},
            {"name": "娜娜", "role": "管家", "user_id": "ou_nana"},
            {"name": "刘姐", "role": "出纳", "user_id": "ou_liujie"},
        ]
        path = self.live_root / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")

    def _import_sample_data(self):
        self._realworld_mapping()
        room_status = self._csv("room_status.csv", [{"房号": "201南双卫", "房态": "空房", "备注": "已清理"}])
        resident = self._csv(
            "resident.csv",
            [{"姓名": "刘一", "入住日期": "2026.7.10", "出馆时间": "2026.8.1", "护理需求": "南双卫 产康", "管家": "娜娜"}],
        )
        contracts = self._csv("contracts.csv", [{"签约客户": "刘一", "合同编号": "HJ-001", "合同金额": "30000", "销售": "欢欢"}])
        finance = self._csv("finance.csv", [{"日期": "2026.7.6", "收入项目": "刘一尾款", "收入金额": "12000", "客户": "刘一"}])
        ExcelOMSImporter(self.live_root, self.operating_root).import_sources(
            resident=resident,
            room_status=room_status,
            contracts=contracts,
        )
        FinanceDataImporter(self.live_root, self.operating_root).import_sources(finance_daily=finance)

    def test_core_data_model_builds_room_finance_and_sales_entities(self):
        self._import_sample_data()

        state = CoreDataModelLayer(self.live_root, self.operating_root).rebuild_from_saved_state()
        rooms = self._read_jsonl(self.live_root / "core_data_model" / "rooms.jsonl")
        finances = self._read_jsonl(self.live_root / "core_data_model" / "finances.jsonl")
        sales = self._read_jsonl(self.live_root / "core_data_model" / "sales.jsonl")

        self.assertEqual(state["flow"], CORE_DATA_MODEL_FLOW)
        self.assertGreaterEqual(state["counts"]["rooms"], 2)
        self.assertEqual(state["counts"]["finances"], 1)
        self.assertEqual(state["counts"]["sales"], 1)
        self.assertTrue(any(room["room_id"] == "201南双卫" and room["status"] == "空房" for room in rooms))
        self.assertTrue(any(room["guest_name"] == "刘一" and room["checkin_date"] == "2026.7.10" for room in rooms))
        self.assertEqual(finances[0]["type"], "收入")
        self.assertEqual(finances[0]["amount"], 12000.0)
        self.assertEqual(sales[0]["guest_name"], "刘一")
        self.assertEqual(sales[0]["amount"], 30000.0)
        self.assertFalse(state["validation"]["excel_direct_to_ui_allowed"])
        self.assertTrue(state["validation"]["entity_model_required_before_business_event"])

    def test_june_method_room_engine_outputs_structured_allocation(self):
        self._import_sample_data()
        entity_state = CoreDataModelLayer(self.live_root, self.operating_root).rebuild_from_saved_state()

        state = RoomAllocationEngine(self.live_root, self.operating_root).rebuild_from_entity_model(entity_state)
        allocation = state["allocations"][0]

        self.assertEqual(state["flow"], ROOM_ALLOCATION_FLOW)
        self.assertEqual(state["engine"], "RoomAllocationEngine")
        self.assertEqual(state["method"], "June Method Engine")
        self.assertEqual(allocation["guest_name"], "刘一")
        self.assertEqual(allocation["room_id"], "201南双卫")
        self.assertGreater(allocation["priority_score"], 0)
        self.assertIn("customer_priority", allocation["decision_factors"])
        self.assertIn("resource_load", allocation["decision_factors"])
        self.assertEqual(allocation["workflow_target"]["workspace_key"], "june")
        self.assertFalse(state["validation"]["excel_direct_allocation_allowed"])

    def test_business_events_are_entity_driven_and_include_room_allocation(self):
        self._import_sample_data()

        summary = BusinessEventEngine(self.live_root, self.operating_root).rebuild_from_saved_state()
        events = self._read_jsonl(self.live_root / "business_events" / "business_event_flow.jsonl")
        room_events = [event for event in events if event["event_type"] == "room_event"]

        self.assertEqual(summary["core_data_model"]["flow"], CORE_DATA_MODEL_FLOW)
        self.assertEqual(summary["room_allocation_engine"]["engine"], "RoomAllocationEngine")
        self.assertTrue(all(event["entity_model_layer"] == "core_data_model" for event in events))
        self.assertTrue(any(event["entity_model_refs"]["rooms"] or event["entity_model_refs"]["sales"] for event in events))
        self.assertTrue(any(event.get("room_allocation", {}).get("room_id") == "201南双卫" for event in room_events))
        self.assertTrue(any(event["next_action"] == "confirm_room_allocation_result" for event in room_events))

    def test_cli_core_data_model_and_room_engine_commands_output_state(self):
        self._import_sample_data()
        core_out = self.root / "core_data_model.json"
        room_out = self.root / "room_engine.json"

        with redirect_stdout(io.StringIO()):
            core_code = main(
                [
                    "core-data-model",
                    "--live-root",
                    str(self.live_root),
                    "--operating-root",
                    str(self.operating_root),
                    "--out",
                    str(core_out),
                    "--pretty",
                ]
            )
            room_code = main(
                [
                    "room-engine",
                    "--live-root",
                    str(self.live_root),
                    "--operating-root",
                    str(self.operating_root),
                    "--out",
                    str(room_out),
                    "--pretty",
                ]
            )

        core_payload = json.loads(core_out.read_text(encoding="utf-8"))
        room_payload = json.loads(room_out.read_text(encoding="utf-8"))
        self.assertEqual(core_code, 0)
        self.assertEqual(room_code, 0)
        self.assertEqual(core_payload["schema_version"], "oms.v1.core_data_model")
        self.assertEqual(room_payload["schema_version"], "oms.v1.room_allocation_engine")
        self.assertTrue(room_payload["allocations"])


if __name__ == "__main__":
    unittest.main()
