import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.ai_assistant import CONFIDENCE_HIGH, CONFIDENCE_INSUFFICIENT, CONFIDENCE_MEDIUM
from oms_v1.ai_reasoning import (
    AIReasoningEngine,
    ReasoningChain,
    ReasoningContext,
    ReasoningResult,
    ReasoningStep,
    collect_evidence_sources,
)
from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class AIReasoningTests(unittest.TestCase):
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
        self.engine = AIReasoningEngine(audit=self.audit, event_bus=self.bus, master_data=self.master_data)

    def tearDown(self):
        self.tmp.cleanup()

    def _context(self, **overrides):
        payload = {
            "context_id": "rctx_001",
            "actor_emp_id": "EMP001",
            "question": "What needs attention today?",
            "ai_context": {
                "source_domains": ["Finance", "Room"],
                "metrics": [
                    {"metric_id": "funds.receivable_amount", "category": "funds", "value": 48000},
                ],
                "alerts": [
                    {"alert_id": "alert_fin_001", "domain": "finance", "severity": "high", "status": "OPEN"},
                ],
            },
            "knowledge_retrieval_result": {
                "matched_knowledge": [
                    {
                        "knowledge_id": "know_fin_rule_001",
                        "title": "Receivable evidence rule",
                        "category": "business_rule",
                        "source": "business_rule",
                        "version": "2.0",
                        "related_domains": ["Finance"],
                    }
                ]
            },
            "metrics": (
                {"metric_id": "operations.room_utilization", "category": "operations", "value": "0.82"},
            ),
            "alerts": (
                {"alert_id": "alert_room_001", "domain": "operations", "severity": "medium", "status": "OPEN"},
            ),
            "domain_data": (
                {"entity_id": "room_201", "domain": "Room", "status": "OCCUPIED"},
            ),
            "correlation_id": "reason_corr_001",
        }
        payload.update(overrides)
        return ReasoningContext(**payload)

    def test_reasoning_context_requires_actor_question_and_freezes_inputs(self):
        source = {"metrics": [{"metric_id": "m1"}]}
        context = ReasoningContext(actor_emp_id="EMP001", question="Explain.", ai_context=source)
        source["metrics"][0]["metric_id"] = "mutated"

        self.assertEqual(context.ai_context["metrics"][0]["metric_id"], "m1")
        with self.assertRaises(ValueError):
            ReasoningContext(actor_emp_id="", question="Explain.")
        with self.assertRaises(ValueError):
            ReasoningContext(actor_emp_id="EMP001", question="")

    def test_reasoning_models_require_traceable_sources_and_steps(self):
        step = ReasoningStep(
            order=1,
            description="Collect evidence.",
            input_sources=("source_1",),
            output="Collected evidence.",
            confidence=CONFIDENCE_MEDIUM,
        )
        chain = ReasoningChain(
            context_id="rctx_model_001",
            steps=(step,),
            evidence_sources=({"source_id": "source_1", "source_type": "metric", "domain": "funds"},),
        )
        result = ReasoningResult(
            reasoning_chain=chain,
            conclusions=(
                {
                    "conclusion_id": "rconc_001",
                    "statement": "Evidence supports the conclusion.",
                    "source_ids": ["source_1"],
                    "reasoning_step_ids": [step.step_id],
                    "confidence": CONFIDENCE_MEDIUM,
                },
            ),
            evidence_sources=chain.evidence_sources,
            confidence=CONFIDENCE_MEDIUM,
            uncertainty=(),
        )

        self.assertEqual(result.to_dict()["reasoning_chain"]["steps"][0]["step_id"], step.step_id)
        with self.assertRaises(ValueError):
            ReasoningResult(
                reasoning_chain=chain,
                conclusions=(
                    {
                        "conclusion_id": "rconc_bad",
                        "statement": "Missing sources.",
                        "source_ids": [],
                        "reasoning_step_ids": [step.step_id],
                    },
                ),
                evidence_sources=chain.evidence_sources,
                confidence=CONFIDENCE_MEDIUM,
                uncertainty=(),
            )

    def test_engine_builds_traceable_reasoning_chain_and_conclusions(self):
        result = self.engine.reason(self._context())
        reasoning_result = result["result"]

        self.assertEqual(reasoning_result["confidence"], CONFIDENCE_HIGH)
        self.assertGreaterEqual(len(reasoning_result["reasoning_chain"]["steps"]), 3)
        self.assertGreaterEqual(len(reasoning_result["evidence_sources"]), 5)
        for conclusion in reasoning_result["conclusions"]:
            self.assertTrue(conclusion["source_ids"])
            self.assertTrue(conclusion["reasoning_step_ids"])
        source_ids = {item["source_id"] for item in reasoning_result["evidence_sources"]}
        self.assertIn("know_fin_rule_001", source_ids)
        self.assertIn("funds.receivable_amount", source_ids)
        self.assertIn("alert_fin_001", source_ids)
        self.assertIn("room_201", source_ids)

    def test_audit_and_event_are_written_for_reasoning(self):
        result = self.engine.reason(self._context())

        audit_events = self.audit.events(sort_by_time=False)
        events = self.bus.events()

        self.assertEqual([item["action"] for item in audit_events], ["ai.reasoning.request", "ai.reasoning.completed"])
        self.assertEqual(audit_events[1]["metadata"]["result_id"], result["result"]["result_id"])
        self.assertEqual(audit_events[1]["metadata"]["confidence"], result["result"]["confidence"])
        self.assertFalse(audit_events[1]["metadata"]["external_ai_called"])
        self.assertFalse(audit_events[1]["metadata"]["mutates_business_state"])
        self.assertEqual([item["event_type"] for item in events], ["ai.reasoning.completed"])
        self.assertEqual(events[0]["payload"]["result_id"], result["result"]["result_id"])
        self.assertFalse(events[0]["payload"]["auto_executes"])
        self.assertFalse(events[0]["payload"]["auto_approves"])

    def test_no_evidence_returns_insufficient_confidence_with_uncertainty(self):
        result = self.engine.reason(
            ReasoningContext(actor_emp_id="EMP001", question="What should I know?", context_id="rctx_empty")
        )
        reasoning_result = result["result"]

        self.assertEqual(reasoning_result["confidence"], CONFIDENCE_INSUFFICIENT)
        self.assertEqual(reasoning_result["uncertainty"], ["No evidence sources were provided."])
        self.assertEqual(reasoning_result["evidence_sources"][0]["source_id"], "rctx_empty")
        self.assertEqual(reasoning_result["conclusions"][0]["source_ids"], ["rctx_empty"])

    def test_reasoning_is_read_only_and_does_not_call_external_ai(self):
        context = self._context()
        before = context.to_dict()

        result = self.engine.reason(context)

        self.assertEqual(context.to_dict(), before)
        self.assertFalse(result["mutates_business_state"])
        self.assertFalse(result["auto_executes"])
        self.assertFalse(result["auto_approves"])
        self.assertFalse(result["external_ai_called"])

    def test_collect_evidence_sources_deduplicates_ai_context_and_direct_inputs(self):
        context = self._context(
            metrics=({"metric_id": "funds.receivable_amount", "category": "funds", "value": 48000},),
            alerts=({"alert_id": "alert_fin_001", "domain": "finance", "severity": "high", "status": "OPEN"},),
        )

        source_ids = [item["source_id"] for item in collect_evidence_sources(context)]

        self.assertEqual(source_ids.count("funds.receivable_amount"), 1)
        self.assertEqual(source_ids.count("alert_fin_001"), 1)

    def test_unknown_actor_is_rejected(self):
        with self.assertRaises(KeyError):
            self.engine.reason(self._context(actor_emp_id="EMP999"))


if __name__ == "__main__":
    unittest.main()
