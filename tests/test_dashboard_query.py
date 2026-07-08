import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.dashboard_query import (
    DASHBOARD_FUNDS,
    DASHBOARD_OPERATIONS,
    DASHBOARD_SALES,
    DATA_STATUS_EMPTY,
    DATA_STATUS_READY,
    TIME_MONTH,
    TIME_TODAY,
    TIME_WEEK,
    DashboardFilter,
    DashboardQuery,
    DashboardQueryEngine,
)
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.metrics import MetricsEngine
from tests.test_health_check import write_identity, write_organization


class DashboardQueryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_organization_master_data.md"
        identity_path = root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.engine = DashboardQueryEngine(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )
        self.dataset = MetricsEngine(audit=AuditEngine(root / "metrics_audit")).snapshot(
            self._source_data(),
            actor_emp_id="EMP001",
            actor_name="Owner",
            reason="Create metric dataset for dashboard query tests.",
            correlation_id="metrics_corr_001",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _source_data(self):
        return {
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

    def _query(self, **overrides):
        payload = {
            "actor_emp_id": "EMP001",
            "reason": "Query dashboard metrics.",
            "dataset": self.dataset,
            "filter": DashboardFilter(time_scope=TIME_TODAY, dashboard_category=DASHBOARD_SALES),
            "correlation_id": "dashboard_corr_001",
        }
        payload.update(overrides)
        return DashboardQuery(**payload)

    def test_filter_supports_time_and_dashboard_categories(self):
        today = DashboardFilter(time_scope="今日", dashboard_category="销售驾驶舱")
        week = DashboardFilter(time_scope="本周", dashboard_category="资金驾驶舱")
        month = DashboardFilter(time_scope="本月", dashboard_category="经营驾驶舱")

        self.assertEqual(today.time_scope, TIME_TODAY)
        self.assertEqual(today.dashboard_category, DASHBOARD_SALES)
        self.assertEqual(week.time_scope, TIME_WEEK)
        self.assertEqual(week.dashboard_category, DASHBOARD_FUNDS)
        self.assertEqual(month.time_scope, TIME_MONTH)
        self.assertEqual(month.dashboard_category, DASHBOARD_OPERATIONS)

    def test_sales_dashboard_query_returns_sales_metrics(self):
        view = self.engine.execute(self._query())

        self.assertEqual(view["dashboard_category"], DASHBOARD_SALES)
        self.assertEqual(view["time_scope"], TIME_TODAY)
        self.assertEqual(view["data_status"], DATA_STATUS_READY)
        self.assertEqual(view["metric_count"], 4)
        self.assertEqual({metric["category"] for metric in view["metrics"]}, {"sales"})
        self.assertEqual({metric["source_domain"] for metric in view["metrics"]}, {"Customer", "Contract"})
        self.assertTrue(all(metric["generated_time"] for metric in view["metrics"]))
        self.assertTrue(all(metric["data_status"] == DATA_STATUS_READY for metric in view["metrics"]))

    def test_funds_dashboard_query_returns_fund_metrics(self):
        view = self.engine.execute(
            self._query(
                actor_emp_id="EMP003",
                filter=DashboardFilter(time_scope=TIME_WEEK, dashboard_category=DASHBOARD_FUNDS),
            )
        )

        self.assertEqual(view["dashboard_category"], DASHBOARD_FUNDS)
        self.assertEqual(view["time_scope"], TIME_WEEK)
        self.assertEqual(view["metric_count"], 3)
        self.assertEqual({metric["category"] for metric in view["metrics"]}, {"funds"})
        self.assertEqual({metric["source_domain"] for metric in view["metrics"]}, {"Payment", "Expense"})

    def test_operations_dashboard_query_returns_operation_metrics(self):
        view = self.engine.execute(
            self._query(
                actor_emp_id="EMP008",
                filter=DashboardFilter(time_scope=TIME_MONTH, dashboard_category=DASHBOARD_OPERATIONS),
            )
        )

        self.assertEqual(view["dashboard_category"], DASHBOARD_OPERATIONS)
        self.assertEqual(view["time_scope"], TIME_MONTH)
        self.assertEqual(view["metric_count"], 3)
        self.assertEqual({metric["category"] for metric in view["metrics"]}, {"operations"})
        self.assertEqual({metric["source_domain"] for metric in view["metrics"]}, {"Stay", "Room", "Caregiver"})

    def test_query_can_filter_metric_ids_and_source_domains(self):
        view = self.engine.execute(
            self._query(
                filter=DashboardFilter(
                    dashboard_category=DASHBOARD_SALES,
                    metric_ids=("sales.deal_amount",),
                    source_domains=("Contract",),
                )
            )
        )

        self.assertEqual(view["metric_count"], 1)
        self.assertEqual(view["metrics"][0]["metric_id"], "sales.deal_amount")
        self.assertEqual(view["metrics"][0]["source_domain"], "Contract")

    def test_empty_query_returns_empty_status_without_mutation(self):
        view = self.engine.execute(
            self._query(
                filter=DashboardFilter(
                    dashboard_category=DASHBOARD_SALES,
                    metric_ids=("sales.not_exists",),
                )
            )
        )

        self.assertEqual(view["data_status"], DATA_STATUS_EMPTY)
        self.assertEqual(view["metric_count"], 0)
        self.assertEqual(view["metrics"], [])
        self.assertFalse(view["mutates_business_state"])

    def test_query_writes_audit_and_event(self):
        view = self.engine.execute(self._query())

        audit_events = self.audit.events(sort_by_time=False)
        self.assertEqual(len(audit_events), 1)
        self.assertEqual(audit_events[0]["action"], "dashboard.query")
        self.assertEqual(audit_events[0]["metadata"]["time_scope"], TIME_TODAY)
        self.assertEqual(audit_events[0]["metadata"]["dashboard_category"], DASHBOARD_SALES)
        self.assertEqual(audit_events[0]["metadata"]["metric_count"], 4)
        self.assertFalse(audit_events[0]["metadata"]["mutates_business_state"])

        published_events = self.bus.events()
        self.assertEqual(len(published_events), 1)
        self.assertEqual(published_events[0]["event_type"], "dashboard.query.executed")
        self.assertEqual(published_events[0]["payload"]["data_status"], DATA_STATUS_READY)
        self.assertFalse(published_events[0]["payload"]["mutates_business_state"])
        self.assertEqual(view["event"]["event"]["event_type"], "dashboard.query.executed")

    def test_permission_control_blocks_unauthorized_dashboard(self):
        allowed = self.engine.execute(
            self._query(
                actor_emp_id="EMP006",
                filter=DashboardFilter(dashboard_category=DASHBOARD_SALES),
            )
        )

        self.assertEqual(allowed["dashboard_category"], DASHBOARD_SALES)
        with self.assertRaises(PermissionError):
            self.engine.execute(
                self._query(
                    actor_emp_id="EMP006",
                    filter=DashboardFilter(dashboard_category=DASHBOARD_FUNDS),
                )
            )

    def test_invalid_filter_values_are_rejected(self):
        with self.assertRaises(ValueError):
            DashboardFilter(time_scope="year", dashboard_category=DASHBOARD_SALES)
        with self.assertRaises(ValueError):
            DashboardFilter(time_scope=TIME_TODAY, dashboard_category="unknown_dashboard")

    def test_query_is_read_only_and_does_not_mutate_dataset(self):
        original_dataset = copy.deepcopy(self.dataset)

        view = self.engine.execute(self._query())

        self.assertEqual(self.dataset, original_dataset)
        self.assertFalse(view["mutates_business_state"])
        self.assertFalse(view["audit_record"]["metadata"]["mutates_business_state"])
        self.assertFalse(view["event"]["event"]["payload"]["mutates_business_state"])


if __name__ == "__main__":
    unittest.main()
