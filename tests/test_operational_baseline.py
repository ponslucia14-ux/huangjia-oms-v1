from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from oms_v1.operational_baseline import OperationalBaselineBuilder
from oms_v1.production_data_adapter import ProductionDataAdapter
from oms_v1.truth_source import TruthSourceStore


class OperationalBaselineTests(unittest.TestCase):
    def room_master(self):
        return [{"room_id": str(index), "room_name": f"{index}房"} for index in range(1, 43)]

    def test_unverified_calendar_marker_cannot_enter_current(self):
        with TemporaryDirectory() as directory:
            result = OperationalBaselineBuilder(Path(directory)).build(
                room_master=self.room_master(),
                stay_candidates=[
                    {"stay_id": "S1", "room_id": "1", "customer_name": "客户甲", "status": "IN_STAY", "checkout_date": ""}
                ],
                snapshot_id="OB-TEST-V1",
                source_version="source-v1",
            )
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["active"])
        self.assertEqual(result["counts"]["actual_stay_current"], 0)
        self.assertIn("REALITY_CONFIRMATION_MISSING", result["excluded_stay_records"][0]["reasons"])

    def test_verified_stay_drives_occupied_room(self):
        with TemporaryDirectory() as directory:
            result = OperationalBaselineBuilder(Path(directory)).build(
                room_master=self.room_master(),
                stay_candidates=[
                    {
                        "stay_id": "S1",
                        "room_id": "1",
                        "customer_name": "客户甲",
                        "status": "IN_STAY",
                        "active": True,
                        "checkout_date": "",
                        "reality_verified": True,
                        "verified_by_emp_id": "EMP008",
                        "verified_at": "2026-07-11T18:00:00+08:00",
                    }
                ],
                snapshot_id="OB-TEST-V2",
                source_version="source-v1",
                activate=True,
            )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["active"])
        self.assertEqual(result["counts"]["occupied_rooms"], 1)
        occupied = next(item for item in result["room_current"] if item["room_id"] == "1")
        self.assertEqual(occupied["current_stay_id"], "S1")

    def test_checked_out_record_is_historical(self):
        with TemporaryDirectory() as directory:
            result = OperationalBaselineBuilder(Path(directory)).build(
                room_master=self.room_master(),
                stay_candidates=[
                    {
                        "stay_id": "S1", "room_id": "1", "status": "IN_STAY", "active": True,
                        "checkout_date": "2026-07-11", "reality_verified": True,
                        "verified_by_emp_id": "EMP008", "verified_at": "2026-07-11T18:00:00+08:00",
                    }
                ],
                snapshot_id="OB-TEST-V3",
                source_version="source-v1",
            )
        self.assertEqual(result["counts"]["actual_stay_current"], 0)
        self.assertIn("CHECKOUT_PRESENT", result["excluded_stay_records"][0]["reasons"])

    def test_blocked_baseline_hides_legacy_room_and_stay_current(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "room.json").write_text('{"room_records":[{"room_id":"1","status":"OCCUPIED","is_current":true}]}', encoding="utf-8")
            (root / "stay.json").write_text('{"stay_records":[{"stay_id":"S1","status":"IN_STAY","is_current":true}]}', encoding="utf-8")
            baseline_root = root / "operational_baseline"
            OperationalBaselineBuilder(baseline_root).build(
                room_master=self.room_master(), stay_candidates=[], snapshot_id="OB-BLOCKED", source_version="source-v1"
            )
            adapter = ProductionDataAdapter(
                TruthSourceStore(root, root, truth_root=root), operational_baseline_root=baseline_root
            )
            self.assertEqual(adapter.room_records(), [])
            self.assertEqual(adapter.stay_records(), [])

    def test_not_initialized_operating_mode_hides_all_legacy_current(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_root = root / "operational_baseline"
            baseline_root.mkdir()
            (root / "operating_mode.json").write_text(
                '{"current_operating_snapshot":null,"legacy_snapshot":"TS-20260711-V1","legacy_snapshot_status":"ARCHIVED_LEGACY"}',
                encoding="utf-8",
            )
            (root / "sales.json").write_text('{"entities":[{"entity_id":"C1","is_current":true}]}', encoding="utf-8")
            (root / "finance.json").write_text('{"financial_events":[{"record_id":"F1","is_current":true}]}', encoding="utf-8")
            (root / "room.json").write_text('{"room_records":[{"room_id":"1","is_current":true}]}', encoding="utf-8")
            (root / "stay.json").write_text('{"stay_records":[{"stay_id":"S1","is_current":true}]}', encoding="utf-8")
            adapter = ProductionDataAdapter(
                TruthSourceStore(root, root, truth_root=root), operational_baseline_root=baseline_root
            )
            self.assertEqual(adapter.sales_records(), [])
            self.assertEqual(adapter.financial_event_records(), [])
            self.assertEqual(adapter.room_records(), [])
            self.assertEqual(adapter.stay_records(), [])
            self.assertEqual(adapter.data_quality_summary()["status"], "NOT_INITIALIZED")


if __name__ == "__main__":
    unittest.main()
