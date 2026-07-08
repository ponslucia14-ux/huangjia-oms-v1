import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.metrics import MetricsEngine, default_metric_definitions


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.audit = AuditEngine(Path(self.tmp.name) / "audit")
        self.engine = MetricsEngine(audit=self.audit)
        self.source_data = {
            "sales_records": [
                {"event_type": "reception", "customer_id": "c_001"},
                {"event_type": "reception", "customer_id": "c_002"},
                {"event_type": "contract_signed", "customer_id": "c_001", "amount": "58000"},
            ],
            "finance_records": [
                {"type": "received", "amount": "10000"},
                {"type": "received", "amount": "25000"},
                {"type": "receivable", "amount": "48000"},
                {"type": "payable", "amount": "6800"},
            ],
            "stay_records": [
                {"stay_id": "stay_001", "status": "in_house"},
                {"stay_id": "stay_002", "status": "planned"},
                {"stay_id": "stay_003", "status": "in_house"},
            ],
            "room_records": [
                {"room_id": "room_001", "status": "OCCUPIED"},
                {"room_id": "room_002", "status": "AVAILABLE"},
                {"room_id": "room_003", "status": "OCCUPIED"},
                {"room_id": "room_004", "status": "DISABLED"},
            ],
            "caregiver_records": [
                {"caregiver_id": "cg_001", "status": "AVAILABLE"},
                {"caregiver_id": "cg_002", "status": "AVAILABLE"},
                {"caregiver_id": "cg_003", "status": "ON_LEAVE"},
            ],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _snapshot_map(self, dataset):
        return {snapshot["metric_id"]: snapshot for snapshot in dataset["snapshots"]}

    def test_default_definitions_cover_first_metric_batch(self):
        definitions = default_metric_definitions()

        self.assertEqual(len(definitions), 10)
        self.assertEqual(
            {definition.metric_id for definition in definitions},
            {
                "sales.today_receptions",
                "sales.today_contracts",
                "sales.deal_amount",
                "sales.conversion_rate",
                "funds.today_received",
                "funds.receivable_amount",
                "funds.payable_amount",
                "operations.current_stays",
                "operations.room_utilization_rate",
                "operations.caregiver_status_counts",
            },
        )
        self.assertTrue(all(definition.source_domain for definition in definitions))
        self.assertTrue(all(definition.calculation_method for definition in definitions))

    def test_metrics_engine_generates_dashboard_dataset(self):
        dataset = self.engine.snapshot(
            self.source_data,
            actor_emp_id="EMP001",
            actor_name="Owner",
            reason="Generate P18 dashboard foundation dataset.",
            correlation_id="metrics_corr_001",
        )

        self.assertFalse(dataset["mutates_business_state"])
        self.assertEqual(len(dataset["snapshots"]), 10)
        self.assertEqual(dataset["source_summary"]["sales_records"], 3)
        self.assertEqual(dataset["source_summary"]["finance_records"], 4)
        self.assertEqual(dataset["audit_record"]["action"], "metrics.snapshot")

    def test_sales_metrics_are_calculated(self):
        dataset = self.engine.snapshot(
            self.source_data,
            actor_emp_id="EMP001",
            actor_name="Owner",
            reason="Calculate sales metrics.",
        )
        snapshots = self._snapshot_map(dataset)

        self.assertEqual(snapshots["sales.today_receptions"]["value"], 2)
        self.assertEqual(snapshots["sales.today_contracts"]["value"], 1)
        self.assertEqual(snapshots["sales.deal_amount"]["value"], "58000")
        self.assertEqual(snapshots["sales.conversion_rate"]["value"], "0.5000")
        self.assertEqual(snapshots["sales.deal_amount"]["source_domain"], "Contract")

    def test_fund_metrics_are_calculated(self):
        dataset = self.engine.snapshot(
            self.source_data,
            actor_emp_id="EMP001",
            actor_name="Owner",
            reason="Calculate fund metrics.",
        )
        snapshots = self._snapshot_map(dataset)

        self.assertEqual(snapshots["funds.today_received"]["value"], "35000")
        self.assertEqual(snapshots["funds.receivable_amount"]["value"], "48000")
        self.assertEqual(snapshots["funds.payable_amount"]["value"], "6800")
        self.assertEqual(snapshots["funds.today_received"]["source_domain"], "Payment")

    def test_operation_metrics_are_calculated(self):
        dataset = self.engine.snapshot(
            self.source_data,
            actor_emp_id="EMP001",
            actor_name="Owner",
            reason="Calculate operations metrics.",
        )
        snapshots = self._snapshot_map(dataset)

        self.assertEqual(snapshots["operations.current_stays"]["value"], 2)
        self.assertEqual(snapshots["operations.room_utilization_rate"]["value"], "0.6667")
        self.assertEqual(
            snapshots["operations.caregiver_status_counts"]["value"],
            {"AVAILABLE": 2, "ON_LEAVE": 1},
        )
        self.assertEqual(snapshots["operations.room_utilization_rate"]["source_domain"], "Room")

    def test_snapshot_is_audited(self):
        self.engine.snapshot(
            self.source_data,
            actor_emp_id="EMP001",
            actor_name="Owner",
            reason="Audit metrics snapshot.",
            correlation_id="metrics_corr_001",
        )

        audit_events = self.audit.events(sort_by_time=False)
        self.assertEqual(len(audit_events), 1)
        self.assertEqual(audit_events[0]["action"], "metrics.snapshot")
        self.assertEqual(audit_events[0]["metadata"]["metric_count"], 10)
        self.assertFalse(audit_events[0]["metadata"]["mutates_business_state"])
        self.assertEqual(audit_events[0]["correlation_id"], "metrics_corr_001")

    def test_missing_sources_return_zero_metrics(self):
        dataset = self.engine.snapshot(
            {},
            actor_emp_id="EMP001",
            actor_name="Owner",
            reason="Calculate metrics from empty source data.",
        )
        snapshots = self._snapshot_map(dataset)

        self.assertEqual(snapshots["sales.today_receptions"]["value"], 0)
        self.assertEqual(snapshots["sales.conversion_rate"]["value"], "0")
        self.assertEqual(snapshots["operations.room_utilization_rate"]["value"], "0")
        self.assertEqual(snapshots["operations.caregiver_status_counts"]["value"], {})

    def test_source_records_must_be_lists(self):
        with self.assertRaises(TypeError):
            self.engine.snapshot(
                {"sales_records": {"event_type": "reception"}},
                actor_emp_id="EMP001",
                actor_name="Owner",
                reason="Reject malformed metric source.",
            )


if __name__ == "__main__":
    unittest.main()
