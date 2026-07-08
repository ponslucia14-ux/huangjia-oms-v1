import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.scheduling_approval import (
    APPROVAL_APPROVED,
    APPROVAL_EXPIRED,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    ApprovalDecision,
    ApprovalRequest,
    SchedulingApprovalEngine,
)
from tests.test_health_check import write_identity, write_organization


class SchedulingApprovalTests(unittest.TestCase):
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
        self.engine = SchedulingApprovalEngine(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _request(self, **overrides):
        payload = {
            "approval_id": "sched_appr_001",
            "decision_id": "scheddec_res_001",
            "requester_emp_id": "EMP008",
            "approver_emp_id": "EMP001",
            "reason": "Request owner approval for scheduling recommendation.",
            "correlation_id": "sched_dec_req_001",
        }
        payload.update(overrides)
        return ApprovalRequest(**payload)

    def test_approval_request_contains_required_fields(self):
        request = self._request()

        payload = request.to_dict()
        self.assertEqual(payload["approval_id"], "sched_appr_001")
        self.assertEqual(payload["decision_id"], "scheddec_res_001")
        self.assertEqual(payload["requester_emp_id"], "EMP008")
        self.assertEqual(payload["approver_emp_id"], "EMP001")
        self.assertEqual(payload["decision_status"], APPROVAL_PENDING)
        self.assertEqual(payload["correlation_id"], "sched_dec_req_001")
        self.assertTrue(payload["timestamp"])

    def test_request_approval_writes_audit_and_event(self):
        workflow = self.engine.request_approval(self._request())

        self.assertEqual(workflow["current_status"], APPROVAL_PENDING)
        self.assertFalse(workflow["execution_authorized"])
        self.assertFalse(workflow["mutates_business_state"])
        self.assertEqual([event["event_type"] for event in self.bus.events()], ["scheduling.approval.requested"])
        self.assertEqual([event["action"] for event in self.audit.events(sort_by_time=False)], ["approval.request"])
        self.assertEqual(workflow["events"][0]["event"]["payload"]["decision_status"], APPROVAL_PENDING)
        self.assertEqual(workflow["audit_records"][0]["metadata"]["approval_id"], "sched_appr_001")

    def test_approve_authorizes_future_execution_but_does_not_execute(self):
        self.engine.request_approval(self._request())

        workflow = self.engine.approve(
            approval_id="sched_appr_001",
            approver_emp_id="EMP001",
            reason="Approved for execution by future scheduling executor.",
        )

        self.assertEqual(workflow["current_status"], APPROVAL_APPROVED)
        self.assertTrue(workflow["execution_authorized"])
        self.assertFalse(workflow["mutates_business_state"])
        self.assertEqual(workflow["decisions"][0]["decision_status"], APPROVAL_APPROVED)
        self.assertTrue(workflow["decisions"][0]["execution_authorized"])
        self.assertEqual(
            [event["event_type"] for event in self.bus.events()],
            ["scheduling.approval.requested", "scheduling.approval.approved"],
        )
        self.assertEqual(
            [event["action"] for event in self.audit.events(sort_by_time=False)],
            ["approval.request", "approval.approve"],
        )
        self.assertIn("execution_authorization", workflow["decision_chain"])

    def test_reject_keeps_execution_unauthorized(self):
        self.engine.request_approval(self._request())

        workflow = self.engine.reject(
            approval_id="sched_appr_001",
            approver_emp_id="EMP001",
            reason="Rejected because the recommended timing is not acceptable.",
        )

        self.assertEqual(workflow["current_status"], APPROVAL_REJECTED)
        self.assertFalse(workflow["execution_authorized"])
        self.assertEqual(workflow["decisions"][0]["decision_status"], APPROVAL_REJECTED)
        self.assertEqual(
            [event["event_type"] for event in self.bus.events()],
            ["scheduling.approval.requested", "scheduling.approval.rejected"],
        )
        self.assertEqual(self.audit.events(sort_by_time=False)[-1]["action"], "approval.reject")

    def test_expire_supported_without_execution_authorization(self):
        self.engine.request_approval(self._request())

        workflow = self.engine.expire(
            approval_id="sched_appr_001",
            approver_emp_id="EMP001",
            reason="Approval window expired before confirmation.",
        )

        self.assertEqual(workflow["current_status"], APPROVAL_EXPIRED)
        self.assertFalse(workflow["execution_authorized"])
        self.assertEqual(workflow["events"][-1]["event"]["event_type"], "scheduling.approval.expired")

    def test_decision_rejects_invalid_authorization_combination(self):
        with self.assertRaises(ValueError):
            ApprovalDecision(
                approval_id="sched_appr_001",
                decision_id="scheddec_res_001",
                requester_emp_id="EMP008",
                approver_emp_id="EMP001",
                reason="Invalid authorization.",
                decision_status=APPROVAL_REJECTED,
                execution_authorized=True,
            )

    def test_approval_cannot_be_decided_twice(self):
        self.engine.request_approval(self._request())
        self.engine.approve(
            approval_id="sched_appr_001",
            approver_emp_id="EMP001",
            reason="Approved once.",
        )

        with self.assertRaises(ValueError):
            self.engine.reject(
                approval_id="sched_appr_001",
                approver_emp_id="EMP001",
                reason="Try rejecting after approval.",
            )

    def test_only_designated_approver_can_decide(self):
        self.engine.request_approval(self._request())

        with self.assertRaises(PermissionError):
            self.engine.approve(
                approval_id="sched_appr_001",
                approver_emp_id="EMP008",
                reason="Wrong approver.",
            )

    def test_unknown_approval_id_is_rejected(self):
        with self.assertRaises(KeyError):
            self.engine.approve(
                approval_id="missing_approval",
                approver_emp_id="EMP001",
                reason="Cannot approve unknown request.",
            )

    def test_approval_does_not_mutate_original_request(self):
        request = self._request()
        request_before = copy.deepcopy(request.to_dict())

        workflow = self.engine.request_approval(request)
        approved = self.engine.approve(
            approval_id="sched_appr_001",
            approver_emp_id="EMP001",
            reason="Approved without mutating request object.",
        )

        self.assertEqual(request.to_dict(), request_before)
        self.assertFalse(workflow["mutates_business_state"])
        self.assertFalse(approved["mutates_business_state"])


if __name__ == "__main__":
    unittest.main()
