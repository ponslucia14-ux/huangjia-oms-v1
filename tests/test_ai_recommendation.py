import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.ai_assistant import CONFIDENCE_HIGH, CONFIDENCE_INSUFFICIENT, CONFIDENCE_MEDIUM
from oms_v1.ai_recommendation import (
    AIRecommendationEngine,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    RecommendationContext,
    RecommendationItem,
    RecommendationResult,
    collect_recommendation_evidence,
)
from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class AIRecommendationTests(unittest.TestCase):
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
        self.engine = AIRecommendationEngine(audit=self.audit, event_bus=self.bus, master_data=self.master_data)

    def tearDown(self):
        self.tmp.cleanup()

    def _reasoning_result(self):
        return {
            "result": {
                "result_id": "rres_001",
                "confidence": CONFIDENCE_HIGH,
                "evidence_sources": [
                    {
                        "source_id": "alert_fin_001",
                        "source_type": "alert",
                        "domain": "finance",
                        "title": "Receivable exception",
                        "severity": "high",
                        "status": "OPEN",
                    },
                    {
                        "source_id": "funds.receivable_amount",
                        "source_type": "metric",
                        "domain": "funds",
                        "title": "Receivable amount",
                    },
                    {
                        "source_id": "know_fin_rule_001",
                        "source_type": "knowledge",
                        "domain": "Finance",
                        "version": "2.0",
                        "title": "Receivable evidence rule",
                    },
                ],
                "conclusions": [
                    {
                        "conclusion_id": "rconc_001",
                        "statement": "Active finance alert needs review.",
                        "source_ids": ["alert_fin_001", "funds.receivable_amount"],
                        "reasoning_step_ids": ["rstep_001"],
                        "confidence": CONFIDENCE_HIGH,
                    }
                ],
            }
        }

    def _context(self, **overrides):
        payload = {
            "context_id": "recctx_001",
            "actor_emp_id": "EMP001",
            "objective": "Generate operating suggestions for today.",
            "reasoning_result": self._reasoning_result(),
            "metrics": (
                {"metric_id": "operations.room_utilization", "category": "operations", "value": "0.82"},
            ),
            "alerts": (
                {"alert_id": "alert_room_001", "domain": "operations", "severity": "medium", "status": "OPEN"},
            ),
            "knowledge_context": {
                "knowledge_entries": [
                    {
                        "knowledge_id": "know_room_sop_001",
                        "title": "Room readiness SOP",
                        "category": "sop",
                        "version": "1.0",
                        "related_domains": ["Room"],
                    }
                ]
            },
            "correlation_id": "rec_corr_001",
        }
        payload.update(overrides)
        return RecommendationContext(**payload)

    def test_recommendation_context_requires_actor_and_freezes_inputs(self):
        source = {"result": {"confidence": CONFIDENCE_MEDIUM}}
        context = RecommendationContext(actor_emp_id="EMP001", reasoning_result=source)
        source["result"]["confidence"] = CONFIDENCE_HIGH

        self.assertEqual(context.reasoning_result["result"]["confidence"], CONFIDENCE_MEDIUM)
        with self.assertRaises(ValueError):
            RecommendationContext(actor_emp_id="")
        with self.assertRaises(ValueError):
            RecommendationContext(actor_emp_id="EMP001", objective="")

    def test_recommendation_item_requires_basis_source_confidence_and_risk(self):
        item = RecommendationItem(
            recommendation="Review finance alert.",
            priority=PRIORITY_HIGH,
            expected_impact="Reduce receivable risk.",
            evidence_sources=("alert_fin_001",),
            confidence=CONFIDENCE_HIGH,
            risks=("Requires human review before action.",),
            basis="Alert evidence is open and high severity.",
            related_domain="finance",
        )
        result = RecommendationResult(
            context_id="recctx_model_001",
            recommendations=(item,),
            evidence_sources=({"source_id": "alert_fin_001", "source_type": "alert"},),
            confidence=CONFIDENCE_HIGH,
        )

        self.assertEqual(result.to_dict()["recommendations"][0]["priority"], PRIORITY_HIGH)
        with self.assertRaises(ValueError):
            RecommendationItem(
                recommendation="Bad item.",
                priority=PRIORITY_HIGH,
                expected_impact="x",
                evidence_sources=(),
                confidence=CONFIDENCE_HIGH,
                risks=("risk",),
                basis="basis",
            )
        with self.assertRaises(ValueError):
            RecommendationItem(
                recommendation="Bad item.",
                priority=PRIORITY_HIGH,
                expected_impact="x",
                evidence_sources=("source",),
                confidence=CONFIDENCE_HIGH,
                risks=(),
                basis="basis",
            )

    def test_engine_generates_explainable_recommendations(self):
        result = self.engine.recommend(self._context())
        recommendations = result["recommendations"]

        self.assertEqual(result["result"]["confidence"], CONFIDENCE_HIGH)
        self.assertGreaterEqual(len(recommendations), 3)
        for item in recommendations:
            self.assertTrue(item["basis"])
            self.assertTrue(item["evidence_sources"])
            self.assertTrue(item["risks"])
            self.assertIn(item["confidence"], {CONFIDENCE_HIGH, CONFIDENCE_MEDIUM})
        priorities = {item["priority"] for item in recommendations}
        self.assertIn(PRIORITY_HIGH, priorities)
        self.assertIn("alert_fin_001", result["result"]["evidence_sources"][0]["source_id"])

    def test_audit_and_event_are_written(self):
        result = self.engine.recommend(self._context())

        audit_events = self.audit.events(sort_by_time=False)
        events = self.bus.events()

        self.assertEqual([item["action"] for item in audit_events], ["ai.recommendation.request", "ai.recommendation.generated"])
        self.assertEqual(audit_events[1]["metadata"]["result_id"], result["result"]["result_id"])
        self.assertEqual(audit_events[1]["metadata"]["recommendation_count"], len(result["recommendations"]))
        self.assertFalse(audit_events[1]["metadata"]["external_ai_called"])
        self.assertFalse(audit_events[1]["metadata"]["mutates_business_state"])
        self.assertEqual([item["event_type"] for item in events], ["ai.recommendation.generated"])
        self.assertEqual(events[0]["payload"]["result_id"], result["result"]["result_id"])
        self.assertFalse(events[0]["payload"]["auto_executes"])
        self.assertFalse(events[0]["payload"]["auto_approves"])

    def test_recommendation_is_read_only_and_non_executing(self):
        context = self._context()
        before = context.to_dict()

        result = self.engine.recommend(context)

        self.assertEqual(context.to_dict(), before)
        self.assertFalse(result["mutates_business_state"])
        self.assertFalse(result["auto_executes"])
        self.assertFalse(result["auto_approves"])
        self.assertFalse(result["external_ai_called"])

    def test_no_evidence_returns_low_priority_evidence_collection_recommendation(self):
        result = self.engine.recommend(
            RecommendationContext(actor_emp_id="EMP001", context_id="recctx_empty", objective="Suggest next step.")
        )
        recommendation = result["recommendations"][0]

        self.assertEqual(result["result"]["confidence"], CONFIDENCE_INSUFFICIENT)
        self.assertEqual(recommendation["priority"], PRIORITY_LOW)
        self.assertEqual(recommendation["evidence_sources"], ["recctx_empty"])
        self.assertTrue(recommendation["risks"])

    def test_collect_recommendation_evidence_deduplicates_sources(self):
        context = self._context(
            metrics=({"metric_id": "funds.receivable_amount", "category": "funds", "value": 48000},),
            alerts=({"alert_id": "alert_fin_001", "domain": "finance", "severity": "high", "status": "OPEN"},),
        )

        source_ids = [item["source_id"] for item in collect_recommendation_evidence(context)]

        self.assertEqual(source_ids.count("funds.receivable_amount"), 1)
        self.assertEqual(source_ids.count("alert_fin_001"), 1)
        self.assertIn("rconc_001", source_ids)

    def test_unknown_actor_is_rejected(self):
        with self.assertRaises(KeyError):
            self.engine.recommend(self._context(actor_emp_id="EMP999"))


if __name__ == "__main__":
    unittest.main()
