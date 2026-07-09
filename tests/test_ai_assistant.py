import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.ai_assistant import (
    CONFIDENCE_HIGH,
    CONFIDENCE_INSUFFICIENT,
    CONTEXT_ALERT,
    CONTEXT_AUDIT,
    CONTEXT_DASHBOARD_QUERY,
    CONTEXT_EVENT,
    CONTEXT_METRICS,
    AIAssistantEngine,
    AIQuery,
)
from oms_v1.audit_log import AuditEngine
from oms_v1.dashboard_query import DASHBOARD_FUNDS, DASHBOARD_OPERATIONS, DASHBOARD_SALES
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.metrics import MetricsEngine
from tests.test_health_check import write_identity, write_organization


class AIAssistantTests(unittest.TestCase):
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
        self.engine = AIAssistantEngine(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )
        self.metrics_dataset = MetricsEngine(audit=AuditEngine(root / "metrics_audit")).snapshot(
            self._source_data(),
            actor_emp_id="EMP001",
            actor_name="Owner",
            reason="Create metric dataset for AI assistant tests.",
            correlation_id="metrics_corr_001",
        )
        self.context_sources = self._context_sources()

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

    def _context_sources(self):
        snapshots = self.metrics_dataset["snapshots"]
        sales_metrics = [item for item in snapshots if item["category"] == "sales"]
        fund_metrics = [item for item in snapshots if item["category"] == "funds"]
        operation_metrics = [item for item in snapshots if item["category"] == "operations"]
        return {
            "metrics": snapshots,
            "dashboard_data": [
                {
                    "dashboard_category": DASHBOARD_SALES,
                    "metrics": sales_metrics,
                    "source_domains": ["Customer", "Contract"],
                },
                {
                    "dashboard_category": DASHBOARD_FUNDS,
                    "metrics": fund_metrics,
                    "source_domains": ["Payment", "Expense"],
                },
                {
                    "dashboard_category": DASHBOARD_OPERATIONS,
                    "metrics": operation_metrics,
                    "source_domains": ["Stay", "Room", "Caregiver"],
                },
            ],
            "alerts": [
                {"alert_id": "alert_finance_001", "domain": "finance", "severity": "high", "status": "OPEN"},
                {"alert_id": "alert_operations_001", "domain": "operations", "severity": "critical", "status": "OPEN"},
            ],
            "audit_records": [
                {"audit_id": "audit_finance_001", "emp_id": "EMP003", "module": "finance", "metadata": {"domain": "finance"}},
                {"audit_id": "audit_sales_001", "emp_id": "EMP006", "module": "sales", "metadata": {"domain": "sales"}},
                {"audit_id": "audit_ops_001", "emp_id": "EMP001", "module": "operations", "metadata": {"domain": "operations"}},
            ],
            "events": [
                {"event_id": "event_finance_001", "event_type": "finance.updated", "payload": {"domain": "finance"}},
                {"event_id": "event_sales_001", "event_type": "sales.updated", "payload": {"domain": "sales"}},
                {"event_id": "event_ops_001", "event_type": "room.updated", "payload": {"domain": "operations"}},
            ],
        }

    def _query(self, **overrides):
        payload = {
            "actor_emp_id": "EMP001",
            "question": "What should I pay attention to today?",
            "context_scope": (
                CONTEXT_METRICS,
                CONTEXT_DASHBOARD_QUERY,
                CONTEXT_ALERT,
                CONTEXT_AUDIT,
                CONTEXT_EVENT,
            ),
            "correlation_id": "ai_corr_001",
        }
        payload.update(overrides)
        return AIQuery(**payload)

    def test_ai_query_requires_actor_question_and_valid_scope(self):
        query = self._query()

        self.assertEqual(query.actor_emp_id, "EMP001")
        self.assertIn(CONTEXT_METRICS, query.to_dict()["context_scope"])
        with self.assertRaises(ValueError):
            AIQuery(actor_emp_id="", question="x", context_scope=(CONTEXT_METRICS,))
        with self.assertRaises(ValueError):
            AIQuery(actor_emp_id="EMP001", question="", context_scope=(CONTEXT_METRICS,))
        with self.assertRaises(ValueError):
            AIQuery(actor_emp_id="EMP001", question="x", context_scope=("unknown",))

    def test_owner_can_read_global_operating_context(self):
        result = self.engine.ask(self._query(), self.context_sources)
        context = result["context"]
        response = result["response"]

        self.assertEqual(len(context["metrics"]), 10)
        self.assertEqual(len(context["dashboard_data"]), 3)
        self.assertEqual(len(context["alerts"]), 2)
        self.assertEqual(len(context["audit_records"]), 3)
        self.assertEqual(len(context["events"]), 3)
        self.assertEqual(response["confidence"], CONFIDENCE_HIGH)
        self.assertIn("sales.deal_amount", response["related_metrics"])
        self.assertIn("alert_finance_001", response["related_alerts"])
        self.assertFalse(result["mutates_business_state"])
        self.assertFalse(result["external_ai_called"])

    def test_finance_role_only_reads_authorized_context(self):
        result = self.engine.ask(self._query(actor_emp_id="EMP003"), self.context_sources)
        context = result["context"]

        self.assertEqual({item["category"] for item in context["metrics"]}, {"funds"})
        self.assertEqual({item["dashboard_category"] for item in context["dashboard_data"]}, {DASHBOARD_FUNDS})
        self.assertEqual({item["domain"] for item in context["alerts"]}, {"finance"})
        self.assertTrue(all(item["metadata"]["domain"] == "finance" or item["emp_id"] == "EMP003" for item in context["audit_records"]))
        self.assertEqual({item["payload"]["domain"] for item in context["events"]}, {"finance"})
        self.assertNotIn("sales.deal_amount", result["response"]["related_metrics"])

    def test_sales_role_cannot_read_fund_or_operation_context(self):
        result = self.engine.ask(self._query(actor_emp_id="EMP006"), self.context_sources)
        context = result["context"]

        self.assertEqual({item["category"] for item in context["metrics"]}, {"sales"})
        self.assertEqual({item["dashboard_category"] for item in context["dashboard_data"]}, {DASHBOARD_SALES})
        self.assertEqual(context["alerts"], [])
        self.assertEqual({item["payload"]["domain"] for item in context["events"]}, {"sales"})
        self.assertFalse(any(metric["metric_id"].startswith("funds.") for metric in context["metrics"]))

    def test_context_scope_limits_context_building(self):
        result = self.engine.ask(
            self._query(context_scope=(CONTEXT_ALERT,), question="Any alerts?"),
            self.context_sources,
        )
        context = result["context"]

        self.assertEqual(context["metrics"], [])
        self.assertEqual(context["dashboard_data"], [])
        self.assertEqual(len(context["alerts"]), 2)
        self.assertEqual(context["audit_records"], [])
        self.assertEqual(context["events"], [])

    def test_no_authorized_context_returns_insufficient_confidence(self):
        sales_only_sources = copy.deepcopy(self.context_sources)
        sales_only_sources["metrics"] = [
            item for item in self.context_sources["metrics"] if item["category"] == "sales"
        ]
        sales_only_sources["dashboard_data"] = []
        sales_only_sources["alerts"] = []
        sales_only_sources["audit_records"] = []
        sales_only_sources["events"] = []

        result = self.engine.ask(
            self._query(actor_emp_id="EMP003", context_scope=(CONTEXT_METRICS,), question="Show me sales."),
            sales_only_sources,
        )

        self.assertEqual(result["context"]["metrics"], [])
        self.assertEqual(result["response"]["confidence"], CONFIDENCE_INSUFFICIENT)
        self.assertEqual(result["response"]["source_domains"], [])

    def test_ai_query_and_response_write_audit_and_events(self):
        result = self.engine.ask(self._query(), self.context_sources)

        audit_events = self.audit.events(sort_by_time=False)
        self.assertEqual([item["action"] for item in audit_events], ["ai.query", "ai.response"])
        self.assertTrue(all(not item["metadata"]["mutates_business_state"] for item in audit_events))
        self.assertTrue(all(not item["metadata"]["external_ai_called"] for item in audit_events))
        self.assertEqual(audit_events[0]["metadata"]["permission_result"], "trimmed")

        events = self.bus.events()
        self.assertEqual([item["event_type"] for item in events], ["ai.query.requested", "ai.response.generated"])
        self.assertTrue(all(not item["payload"]["mutates_business_state"] for item in events))
        self.assertTrue(all(not item["payload"]["external_ai_called"] for item in events))
        self.assertEqual(result["events"][1]["event"]["payload"]["confidence"], result["response"]["confidence"])

    def test_ai_assistant_is_read_only_and_does_not_mutate_sources(self):
        original_sources = copy.deepcopy(self.context_sources)

        result = self.engine.ask(self._query(), self.context_sources)

        self.assertEqual(self.context_sources, original_sources)
        self.assertFalse(result["mutates_business_state"])
        self.assertFalse(result["external_ai_called"])

    def test_unknown_actor_is_rejected_by_master_data(self):
        with self.assertRaises(KeyError):
            self.engine.ask(self._query(actor_emp_id="EMP999"), self.context_sources)


if __name__ == "__main__":
    unittest.main()
