import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.ai_assistant import CONFIDENCE_HIGH, CONFIDENCE_LOW
from oms_v1.ai_governance import (
    AIGovernanceEngine,
    AIGovernancePolicy,
    AIRecommendationRecord,
    AIReview,
    GOVERNANCE_APPROVED,
    GOVERNANCE_EXPIRED,
    GOVERNANCE_PENDING_REVIEW,
    GOVERNANCE_REJECTED,
)
from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class AIGovernanceTests(unittest.TestCase):
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
        self.engine = AIGovernanceEngine(audit=self.audit, event_bus=self.bus, master_data=self.master_data)

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, **overrides):
        payload = {
            "record_id": "aigovrec_001",
            "recommendation_id": "rec_001",
            "proposer_emp_id": "EMP001",
            "source_reasoning": {"result_id": "rres_001", "conclusion_ids": ["rconc_001"]},
            "evidence_sources": ("alert_fin_001", "metric_receivable_001"),
            "confidence": CONFIDENCE_HIGH,
            "generated_at": "2026-07-09T09:00:00",
            "recommendation_text": "Review pending receivables.",
            "metadata": {"correlation_id": "ai_gov_corr_001"},
        }
        payload.update(overrides)
        return AIRecommendationRecord(**payload)

    def _policy(self, **overrides):
        payload = {
            "policy_id": "aigovpol_001",
            "name": "Owner AI recommendation review policy",
            "requires_human_review": True,
            "allowed_reviewer_emp_ids": ("EMP001",),
            "allow_execution_flow": True,
            "expires_after_hours": 24,
        }
        payload.update(overrides)
        return AIGovernancePolicy(**payload)

    def test_recommendation_record_requires_source_and_freezes_inputs(self):
        source = {"result_id": "rres_001"}
        record = AIRecommendationRecord(
            recommendation_id="rec_model_001",
            proposer_emp_id="EMP001",
            source_reasoning=source,
            evidence_sources=("source_001", "source_001"),
            confidence=CONFIDENCE_LOW,
            generated_at="2026-07-09T09:00:00",
        )
        source["result_id"] = "changed"

        self.assertEqual(record.source_reasoning["result_id"], "rres_001")
        self.assertEqual(record.evidence_sources, ("source_001",))
        self.assertEqual(record.status, GOVERNANCE_PENDING_REVIEW)
        with self.assertRaises(ValueError):
            AIRecommendationRecord(
                recommendation_id="",
                proposer_emp_id="EMP001",
                source_reasoning={"result_id": "rres_001"},
                evidence_sources=("source_001",),
                confidence=CONFIDENCE_HIGH,
                generated_at="2026-07-09T09:00:00",
            )
        with self.assertRaises(ValueError):
            AIRecommendationRecord(
                recommendation_id="rec_bad",
                proposer_emp_id="EMP001",
                source_reasoning={},
                evidence_sources=("source_001",),
                confidence=CONFIDENCE_HIGH,
                generated_at="2026-07-09T09:00:00",
            )

    def test_governance_policy_requires_reviewers(self):
        policy = self._policy()

        self.assertTrue(policy.requires_human_review)
        self.assertTrue(policy.can_review("EMP001"))
        self.assertFalse(policy.can_review("EMP008"))
        with self.assertRaises(ValueError):
            self._policy(allowed_reviewer_emp_ids=())

    def test_request_review_creates_pending_case_and_audit_without_event(self):
        case = self.engine.request_review(
            self._record(),
            self._policy(),
            requester_emp_id="EMP001",
            reason="Review AI recommendation before any execution flow.",
            correlation_id="ai_gov_corr_001",
        )

        self.assertEqual(case["current_status"], GOVERNANCE_PENDING_REVIEW)
        self.assertFalse(case["execution_flow_allowed"])
        self.assertFalse(case["mutates_business_state"])
        self.assertFalse(case["auto_executes"])
        self.assertFalse(case["auto_approves"])
        self.assertEqual(case["record"]["recommendation_id"], "rec_001")
        self.assertEqual([item["action"] for item in self.audit.events(sort_by_time=False)], ["ai.governance.review.request"])
        self.assertEqual(self.bus.events(), [])
        self.assertEqual(case["audit_records"][0]["metadata"]["policy_id"], "aigovpol_001")

    def test_approve_completes_review_and_allows_execution_flow_flag_only(self):
        self.engine.request_review(
            self._record(),
            self._policy(),
            requester_emp_id="EMP001",
            reason="Request owner review.",
        )

        case = self.engine.approve(
            recommendation_id="rec_001",
            reviewer_emp_id="EMP001",
            reason="Approved for possible downstream execution review.",
        )

        self.assertEqual(case["current_status"], GOVERNANCE_APPROVED)
        self.assertTrue(case["execution_flow_allowed"])
        self.assertFalse(case["auto_executes"])
        self.assertFalse(case["auto_approves"])
        self.assertFalse(case["mutates_business_state"])
        self.assertEqual(case["reviews"][0]["review_status"], GOVERNANCE_APPROVED)
        self.assertTrue(case["reviews"][0]["execution_flow_allowed"])
        self.assertEqual(
            [item["action"] for item in self.audit.events(sort_by_time=False)],
            ["ai.governance.review.request", "ai.governance.review.completed"],
        )
        self.assertEqual([item["event_type"] for item in self.bus.events()], ["ai.governance.review.completed"])
        self.assertEqual(self.bus.events()[0]["payload"]["review_status"], GOVERNANCE_APPROVED)

    def test_reject_keeps_execution_flow_blocked(self):
        self.engine.request_review(
            self._record(),
            self._policy(),
            requester_emp_id="EMP001",
            reason="Request review.",
        )

        case = self.engine.reject(
            recommendation_id="rec_001",
            reviewer_emp_id="EMP001",
            reason="Rejected because evidence is not sufficient for operations.",
        )

        self.assertEqual(case["current_status"], GOVERNANCE_REJECTED)
        self.assertFalse(case["execution_flow_allowed"])
        self.assertFalse(case["reviews"][0]["execution_flow_allowed"])
        self.assertEqual(self.bus.events()[0]["payload"]["review_status"], GOVERNANCE_REJECTED)

    def test_expire_supported_without_execution_flow(self):
        self.engine.request_review(
            self._record(),
            self._policy(),
            requester_emp_id="EMP001",
            reason="Request review.",
        )

        case = self.engine.expire(
            recommendation_id="rec_001",
            reviewer_emp_id="EMP001",
            reason="Review window expired.",
        )

        self.assertEqual(case["current_status"], GOVERNANCE_EXPIRED)
        self.assertFalse(case["execution_flow_allowed"])

    def test_only_policy_reviewer_can_complete_review(self):
        self.engine.request_review(
            self._record(),
            self._policy(),
            requester_emp_id="EMP001",
            reason="Request review.",
        )

        with self.assertRaises(PermissionError):
            self.engine.approve(
                recommendation_id="rec_001",
                reviewer_emp_id="EMP008",
                reason="Wrong reviewer.",
            )

    def test_review_cannot_complete_twice(self):
        self.engine.request_review(
            self._record(),
            self._policy(),
            requester_emp_id="EMP001",
            reason="Request review.",
        )
        self.engine.approve(
            recommendation_id="rec_001",
            reviewer_emp_id="EMP001",
            reason="Approved once.",
        )

        with self.assertRaises(ValueError):
            self.engine.reject(
                recommendation_id="rec_001",
                reviewer_emp_id="EMP001",
                reason="Reject after approval.",
            )

    def test_review_model_rejects_invalid_execution_authorization(self):
        with self.assertRaises(ValueError):
            AIReview(
                recommendation_id="rec_001",
                reviewer_emp_id="EMP001",
                review_status=GOVERNANCE_REJECTED,
                reason="Invalid execution authorization.",
                execution_flow_allowed=True,
            )

    def test_governance_is_read_only_and_does_not_mutate_record(self):
        record = self._record()
        before = copy.deepcopy(record.to_dict())

        requested = self.engine.request_review(
            record,
            self._policy(allow_execution_flow=False),
            requester_emp_id="EMP001",
            reason="Request read-only governance review.",
        )
        approved = self.engine.approve(
            recommendation_id="rec_001",
            reviewer_emp_id="EMP001",
            reason="Approved but policy blocks execution flow.",
        )

        self.assertEqual(record.to_dict(), before)
        self.assertFalse(requested["auto_approves"])
        self.assertFalse(approved["execution_flow_allowed"])
        self.assertFalse(approved["auto_executes"])
        self.assertFalse(approved["external_ai_called"])

    def test_unknown_recommendation_is_rejected(self):
        with self.assertRaises(KeyError):
            self.engine.approve(
                recommendation_id="missing_rec",
                reviewer_emp_id="EMP001",
                reason="Cannot review missing recommendation.",
            )

    def test_unknown_requester_is_rejected(self):
        with self.assertRaises(KeyError):
            self.engine.request_review(
                self._record(),
                self._policy(),
                requester_emp_id="EMP999",
                reason="Unknown requester.",
            )


if __name__ == "__main__":
    unittest.main()
