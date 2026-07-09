import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.ai_memory import (
    AIMemoryEngine,
    AIExperienceRecord,
    AILearningFeedback,
    AIOutcomeRecord,
    OUTCOME_FAILURE,
    OUTCOME_HISTORICAL_CASE,
    OUTCOME_SUCCESS,
)
from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class AIMemoryTests(unittest.TestCase):
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
        self.engine = AIMemoryEngine(audit=self.audit, event_bus=self.bus, master_data=self.master_data)

    def tearDown(self):
        self.tmp.cleanup()

    def _experience(self, **overrides):
        payload = {
            "memory_id": "aimem_001",
            "recommendation_id": "rec_001",
            "context": {"context_id": "recctx_001", "objective": "Review finance risk."},
            "reasoning_source": {"result_id": "rres_001", "conclusion_ids": ["rconc_001"]},
            "decision_result": {"review_status": "APPROVED", "execution_flow_allowed": True},
            "related_domain": "Finance",
            "metadata": {"correlation_id": "aimem_corr_001"},
        }
        payload.update(overrides)
        return AIExperienceRecord(**payload)

    def _feedback(self, **overrides):
        payload = {
            "feedback_id": "aifb_001",
            "recommendation_id": "rec_001",
            "actor_emp_id": "EMP001",
            "adopted": True,
            "rejected": False,
            "outcome": "Receivable review was completed.",
            "impact": "Reduced pending receivable uncertainty.",
            "evidence_sources": ("alert_fin_001",),
        }
        payload.update(overrides)
        return AILearningFeedback(**payload)

    def _outcome_record(self, **overrides):
        payload = {
            "outcome_id": "aiout_001",
            "recommendation_id": "rec_001",
            "feedback_id": "aifb_001",
            "outcome_type": OUTCOME_SUCCESS,
            "outcome": "Receivable review closed without new issue.",
            "impact": "Improved finance follow-up reliability.",
            "lessons": ("Use alert severity as review priority.",),
            "evidence_sources": ("alert_fin_001", "aifb_001"),
        }
        payload.update(overrides)
        return AIOutcomeRecord(**payload)

    def test_experience_record_requires_traceable_context_and_freezes_inputs(self):
        context = {"context_id": "recctx_001"}
        record = AIExperienceRecord(
            recommendation_id="rec_model_001",
            context=context,
            reasoning_source={"result_id": "rres_001"},
            decision_result={"review_status": "APPROVED"},
        )
        context["context_id"] = "changed"

        self.assertEqual(record.context["context_id"], "recctx_001")
        with self.assertRaises(ValueError):
            AIExperienceRecord(
                recommendation_id="",
                context={"context_id": "recctx_001"},
                reasoning_source={"result_id": "rres_001"},
                decision_result={"review_status": "APPROVED"},
            )
        with self.assertRaises(ValueError):
            AIExperienceRecord(
                recommendation_id="rec_bad",
                context={},
                reasoning_source={"result_id": "rres_001"},
                decision_result={"review_status": "APPROVED"},
            )

    def test_learning_feedback_requires_adopted_or_rejected(self):
        feedback = self._feedback()

        self.assertTrue(feedback.adopted)
        self.assertFalse(feedback.rejected)
        with self.assertRaises(ValueError):
            self._feedback(adopted=True, rejected=True)
        with self.assertRaises(ValueError):
            self._feedback(adopted=False, rejected=False)

    def test_outcome_record_requires_supported_type_and_lessons(self):
        outcome = self._outcome_record()

        self.assertEqual(outcome.outcome_type, OUTCOME_SUCCESS)
        self.assertEqual(outcome.lessons, ("Use alert severity as review priority.",))
        with self.assertRaises(ValueError):
            self._outcome_record(outcome_type="AUTO_TRAINED")
        with self.assertRaises(ValueError):
            self._outcome_record(lessons=())

    def test_create_experience_writes_audit_and_event(self):
        case = self.engine.create_experience(
            self._experience(),
            actor_emp_id="EMP001",
            reason="Create AI memory from reviewed recommendation.",
            correlation_id="aimem_corr_001",
        )

        self.assertEqual(case["experience"]["memory_id"], "aimem_001")
        self.assertFalse(case["trains_model"])
        self.assertFalse(case["mutates_business_state"])
        self.assertFalse(case["auto_executes"])
        self.assertEqual([item["action"] for item in self.audit.events(sort_by_time=False)], ["ai.memory.created"])
        self.assertEqual([item["event_type"] for item in self.bus.events()], ["ai.memory.available"])
        self.assertEqual(self.bus.events()[0]["payload"]["action"], "created")

    def test_record_feedback_updates_memory_without_training_or_execution(self):
        self.engine.create_experience(
            self._experience(),
            actor_emp_id="EMP001",
            reason="Create AI memory.",
        )

        case = self.engine.record_feedback(
            self._feedback(),
            actor_emp_id="EMP001",
            reason="Record adoption feedback.",
        )

        self.assertEqual(len(case["feedback_records"]), 1)
        self.assertEqual(case["feedback_records"][0]["feedback_id"], "aifb_001")
        self.assertFalse(case["trains_model"])
        self.assertFalse(case["auto_optimizes_rules"])
        self.assertFalse(case["auto_executes"])
        self.assertEqual(
            [item["action"] for item in self.audit.events(sort_by_time=False)],
            ["ai.memory.created", "ai.memory.updated"],
        )

    def test_record_outcome_publishes_memory_available(self):
        self.engine.create_experience(
            self._experience(),
            actor_emp_id="EMP001",
            reason="Create AI memory.",
        )
        self.engine.record_feedback(
            self._feedback(),
            actor_emp_id="EMP001",
            reason="Record adoption feedback.",
        )

        case = self.engine.record_outcome(
            self._outcome_record(),
            actor_emp_id="EMP001",
            reason="Record final outcome.",
        )

        self.assertEqual(len(case["outcome_records"]), 1)
        self.assertEqual(case["outcome_records"][0]["outcome_type"], OUTCOME_SUCCESS)
        self.assertEqual([item["event_type"] for item in self.bus.events()], ["ai.memory.available", "ai.memory.available"])
        self.assertEqual(self.bus.events()[-1]["payload"]["outcome_count"], 1)

    def test_build_context_exposes_success_failure_and_historical_cases(self):
        self.engine.create_experience(self._experience(), actor_emp_id="EMP001", reason="Create memory.")
        self.engine.record_outcome(self._outcome_record(), actor_emp_id="EMP001", reason="Record success.")
        self.engine.create_experience(
            self._experience(
                memory_id="aimem_002",
                recommendation_id="rec_002",
                related_domain="Room",
                decision_result={"review_status": "REJECTED"},
            ),
            actor_emp_id="EMP001",
            reason="Create second memory.",
        )
        self.engine.record_outcome(
            self._outcome_record(
                outcome_id="aiout_002",
                recommendation_id="rec_002",
                feedback_id="",
                outcome_type=OUTCOME_FAILURE,
                outcome="Recommendation was not useful.",
                impact="No operational change.",
                lessons=("Require more room evidence before future recommendation.",),
            ),
            actor_emp_id="EMP001",
            reason="Record failure.",
        )
        self.engine.record_outcome(
            self._outcome_record(
                outcome_id="aiout_003",
                recommendation_id="rec_002",
                outcome_type=OUTCOME_HISTORICAL_CASE,
                outcome="Historical case retained.",
                impact="Useful as reference.",
                lessons=("Keep as context only.",),
            ),
            actor_emp_id="EMP001",
            reason="Record historical case.",
        )

        context = self.engine.build_context()
        room_context = self.engine.build_context(related_domain="Room")

        self.assertEqual(context["context_type"], "ai_memory")
        self.assertEqual(len(context["experience_records"]), 2)
        self.assertEqual(len(context["success_cases"]), 1)
        self.assertEqual(len(context["failure_cases"]), 1)
        self.assertEqual(len(context["historical_cases"]), 1)
        self.assertEqual([item["recommendation_id"] for item in room_context["experience_records"]], ["rec_002"])
        self.assertFalse(context["trains_model"])
        self.assertFalse(context["auto_optimizes_rules"])
        self.assertFalse(context["external_ai_called"])

    def test_memory_does_not_mutate_original_experience(self):
        experience = self._experience()
        before = copy.deepcopy(experience.to_dict())

        self.engine.create_experience(experience, actor_emp_id="EMP001", reason="Create memory.")
        self.engine.record_feedback(self._feedback(), actor_emp_id="EMP001", reason="Record feedback.")

        self.assertEqual(experience.to_dict(), before)

    def test_duplicate_and_unknown_memory_are_rejected(self):
        self.engine.create_experience(self._experience(), actor_emp_id="EMP001", reason="Create memory.")

        with self.assertRaises(ValueError):
            self.engine.create_experience(self._experience(), actor_emp_id="EMP001", reason="Duplicate memory.")
        with self.assertRaises(KeyError):
            self.engine.record_feedback(
                self._feedback(recommendation_id="missing_rec"),
                actor_emp_id="EMP001",
                reason="Unknown memory.",
            )

    def test_feedback_actor_must_match_call_actor_and_exist(self):
        self.engine.create_experience(self._experience(), actor_emp_id="EMP001", reason="Create memory.")

        with self.assertRaises(PermissionError):
            self.engine.record_feedback(
                self._feedback(actor_emp_id="EMP001"),
                actor_emp_id="EMP008",
                reason="Actor mismatch.",
            )
        with self.assertRaises(KeyError):
            self.engine.record_feedback(
                self._feedback(feedback_id="aifb_999", actor_emp_id="EMP999"),
                actor_emp_id="EMP999",
                reason="Unknown actor.",
            )


if __name__ == "__main__":
    unittest.main()
