import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.business_correction import (
    APPLIED,
    ELIGIBLE,
    INELIGIBLE,
    BusinessCorrectionEngine,
)
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class BusinessCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        organization = root / "organization.md"
        identity = root / "identity.md"
        write_organization(organization)
        write_identity(identity)
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.engine = BusinessCorrectionEngine(
            master_data=OMSMasterData(organization_path=organization, feishu_identity_path=identity),
            audit=self.audit,
            event_bus=self.bus,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_duplicate_identifier_is_eligible_without_fact_dispute(self):
        result = self.engine.assess(
            correction_type="DUPLICATE_IDENTIFIER",
            domain="Sales",
            original_value="NSEKI94131081",
            corrected_value="NSEKI94131081-A",
        )
        self.assertEqual(result["result"], ELIGIBLE)

    def test_amount_customer_and_payment_disputes_are_ineligible(self):
        for flag in ("AMOUNT_DISPUTE", "CUSTOMER_OWNERSHIP_DISPUTE", "PAYMENT_FACT_DISPUTE"):
            result = self.engine.assess(
                correction_type="DUPLICATE_IDENTIFIER",
                domain="Sales",
                original_value="NSEKI94131081",
                corrected_value="NSEKI94131081-A",
                dispute_flags=[flag],
            )
            self.assertEqual(result["result"], INELIGIBLE)
            self.assertIn(f"forbidden_dispute:{flag}", result["reasons"])

    def test_correction_preserves_source_and_records_audit_event(self):
        source = {"contract_id": "NSEKI94131081", "customer_name": "郝梓涵", "amount": 21990}
        proposed = self.engine.propose(
            actor_emp_id="EMP006",
            domain="Sales",
            entity_id="sales:row:140",
            field_name="contract_id",
            original_value="NSEKI94131081",
            corrected_value="NSEKI94131081-A",
            correction_type="DUPLICATE_IDENTIFIER",
            correction_reason="Resolve duplicate manual identifier without changing contract facts.",
            source_file="sales.xlsx",
            source_sheet="Current",
            source_row=140,
            correlation_id="sales-correction-001",
        )
        applied = self.engine.apply(
            proposed["correction"]["correction_id"],
            confirming_emp_id="EMP003",
            reason="Identifier-only correction confirmed against business record.",
        )
        derived = self.engine.corrected_record(source, applied["correction"]["correction_id"])

        self.assertEqual(source["contract_id"], "NSEKI94131081")
        self.assertEqual(derived["contract_id"], "NSEKI94131081-A")
        self.assertEqual(derived["source_original_values"]["contract_id"], "NSEKI94131081")
        self.assertEqual(applied["correction"]["status"], APPLIED)
        events = self.bus.events()
        self.assertEqual([item["event_type"] for item in events], [
            "business.correction.proposed",
            "business.correction.applied",
        ])
        audit = self.audit.events(sort_by_time=False)
        self.assertEqual(len(audit), 2)
        self.assertEqual(audit[1]["metadata"]["original_value"], "NSEKI94131081")
        self.assertEqual(audit[1]["metadata"]["corrected_value"], "NSEKI94131081-A")

    def test_unauthorized_role_cannot_propose_sales_correction(self):
        with self.assertRaises(PermissionError):
            self.engine.propose(
                actor_emp_id="EMP011",
                domain="Sales",
                entity_id="sales:row:140",
                field_name="contract_id",
                original_value="NSEKI94131081",
                corrected_value="NSEKI94131081-A",
                correction_type="DUPLICATE_IDENTIFIER",
                correction_reason="Attempt unauthorized correction.",
                source_file="sales.xlsx",
                source_sheet="Current",
                source_row=140,
                correlation_id="sales-correction-002",
            )


if __name__ == "__main__":
    unittest.main()
