import json
import tempfile
import unittest
from pathlib import Path

from oms_v1.production_data_adapter import ProductionDataAdapter
from oms_v1.production_snapshot import ProductionSnapshotBuilder
from oms_v1.truth_source import TruthSourceStore


class ProductionSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        evidence = lambda domain: {
            "source_file": f"{domain}.xlsx",
            "source_sheet": "Current",
            "row_number": 2,
            "source_version": "sha256:source",
            "record_id": f"{domain}-1",
        }
        payloads = {
            "sales": {
                "updated_at": "2026-07-11T00:00:00+08:00",
                "source_version": "sha256:sales",
                "entities": [{
                    "entity_id": "sales-1", "source_record_id": "sales-1", "contract_id": "C-1",
                    "guest_name": "客户甲", "stage": "签约", "amount": 1000,
                    "source_evidence": evidence("sales"),
                }],
            },
            "finance": {
                "updated_at": "2026-07-11T00:00:00+08:00",
                "source_version": "sha256:finance",
                "financial_events": [{
                    "financial_event_id": "finance-1", "record_id": "finance-1",
                    "income_amount": 1000, "occurred_at": "2026-07-11",
                    "source_evidence": evidence("finance"),
                }],
                "settlement_records": [],
            },
            "room": {
                "updated_at": "2026-07-11T00:00:00+08:00",
                "source_version": "sha256:room",
                "entities": [{
                    "record_id": "room-1", "room_id": "201", "status": "OCCUPIED",
                    "source_evidence": evidence("room"),
                }],
                "room_records": [{
                    "record_id": "room-1", "room_id": "201", "status": "OCCUPIED",
                    "source_evidence": evidence("room"),
                }],
            },
            "stay": {
                "updated_at": "2026-07-11T00:00:00+08:00",
                "source_version": "sha256:stay",
                "entities": [{
                    "record_id": "stay-1", "stay_id": "S-1", "status": "IN_STAY",
                    "source_evidence": evidence("stay"),
                }],
                "stay_records": [{
                    "record_id": "stay-1", "stay_id": "S-1", "status": "IN_STAY",
                    "source_evidence": evidence("stay"),
                }],
            },
        }
        for domain, payload in payloads.items():
            payload.update({"schema_version": "test", "domain": domain, "work_items": []})
            (self.root / f"{domain}.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )

    def tearDown(self):
        self.tmp.cleanup()

    def test_pass_snapshot_activates_and_locks_current_records(self):
        snapshot = ProductionSnapshotBuilder(self.root).build(
            expected_counts={"sales": 1, "finance": 1, "room": 1, "stay": 1}
        )
        self.assertEqual(snapshot["acceptance_result"], "PASS")
        self.assertTrue(snapshot["activated_for_production"])
        self.assertTrue((self.root / "snapshots" / "ACTIVE_SNAPSHOT.json").is_file())

        adapter = ProductionDataAdapter(TruthSourceStore(self.root, self.root, truth_root=self.root))
        quality = adapter.data_quality_summary()
        self.assertEqual(quality["snapshot_version"], snapshot["snapshot_version"])
        self.assertEqual(quality["snapshot_status"], "PASS")
        self.assertTrue(quality["snapshot_source_integrity"]["valid"])
        self.assertEqual(len(adapter.sales_records()), 1)

    def test_changed_truth_file_does_not_overwrite_or_pass_active_snapshot(self):
        snapshot = ProductionSnapshotBuilder(self.root).build(
            expected_counts={"sales": 1, "finance": 1, "room": 1, "stay": 1}
        )
        sales_path = self.root / "sales.json"
        payload = json.loads(sales_path.read_text(encoding="utf-8"))
        payload["entities"].append(dict(payload["entities"][0], entity_id="sales-2", source_record_id="sales-2"))
        sales_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        adapter = ProductionDataAdapter(TruthSourceStore(self.root, self.root, truth_root=self.root))
        quality = adapter.data_quality_summary()
        self.assertEqual(quality["snapshot_version"], snapshot["snapshot_version"])
        self.assertEqual(quality["snapshot_status"], "FAIL")
        self.assertFalse(quality["activated_for_production"])
        self.assertEqual(adapter.sales_records(), [])


if __name__ == "__main__":
    unittest.main()
