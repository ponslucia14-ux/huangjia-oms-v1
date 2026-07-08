import tempfile
import unittest
from pathlib import Path

from oms_v1.business_rules import (
    BusinessRulesEngine,
    RuleContext,
    RULE_PASS,
    RULE_REJECT,
    RULE_WARNING,
    default_business_rules,
)
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class BusinessRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_organization_master_data.md"
        identity_path = root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.engine = BusinessRulesEngine(master_data=self.master_data)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rule_definitions_are_sorted_by_priority(self):
        definitions = self.engine.definitions()

        self.assertEqual([rule["rule_id"] for rule in definitions], [
            "BR_REQUIRED_FIELDS",
            "BR_ROLE_PERMISSION",
            "BR_CONTRACT_PAYMENT_CONFIRMED",
            "BR_ROOM_MAINTENANCE_NOT_CHECKIN",
            "BR_ROOM_DISABLED_NOT_CHECKIN",
        ])
        self.assertEqual([rule["priority"] for rule in definitions], [10, 20, 30, 40, 50])

    def test_required_fields_rule_rejects_missing_values(self):
        result = self.engine.evaluate(
            RuleContext(
                action="create_stay",
                actor_emp_id="EMP008",
                domain="Stay",
                required_fields=("customer_id", "contract_id"),
                data={"customer_id": "customer_001", "contract_id": ""},
            )
        )

        self.assertEqual(result["overall_status"], RULE_REJECT)
        self.assertIn("Missing required fields: contract_id.", result["reject_reasons"])

    def test_contract_requires_confirmed_payment_to_be_effective(self):
        no_payment = self.engine.evaluate(
            RuleContext(
                action="activate_contract",
                actor_emp_id="EMP006",
                domain="Contract",
                data={"payments": []},
            )
        )
        pending_payment = self.engine.evaluate(
            RuleContext(
                action="activate_contract",
                actor_emp_id="EMP006",
                domain="Contract",
                data={"payments": [{"status": "pending", "amount": "10000"}]},
            )
        )
        confirmed_payment = self.engine.evaluate(
            RuleContext(
                action="activate_contract",
                actor_emp_id="EMP006",
                domain="Contract",
                data={"payments": [{"status": "confirmed", "amount": "10000"}]},
            )
        )

        self.assertEqual(no_payment["overall_status"], RULE_REJECT)
        self.assertEqual(pending_payment["overall_status"], RULE_REJECT)
        self.assertEqual(confirmed_payment["overall_status"], RULE_PASS)

    def test_room_maintenance_and_disabled_reject_checkin(self):
        maintenance = self.engine.evaluate(
            RuleContext(
                action="check_in_room",
                actor_emp_id="EMP008",
                domain="Room",
                data={"room": {"status": "MAINTENANCE"}},
            )
        )
        disabled = self.engine.evaluate(
            RuleContext(
                action="check_in_room",
                actor_emp_id="EMP008",
                domain="Room",
                data={"room": {"status": "DISABLED"}},
            )
        )
        available = self.engine.evaluate(
            RuleContext(
                action="check_in_room",
                actor_emp_id="EMP008",
                domain="Room",
                data={"room": {"status": "RESERVED"}},
            )
        )

        self.assertEqual(maintenance["overall_status"], RULE_REJECT)
        self.assertIn("Room is under maintenance and cannot be checked in.", maintenance["reject_reasons"])
        self.assertEqual(disabled["overall_status"], RULE_REJECT)
        self.assertIn("Room is disabled and cannot be checked in.", disabled["reject_reasons"])
        self.assertEqual(available["overall_status"], RULE_PASS)

    def test_role_permission_rule_checks_emp_and_domain_roles(self):
        allowed = self.engine.evaluate(RuleContext(action="reserve_room", actor_emp_id="EMP008", domain="Room"))
        forbidden = self.engine.evaluate(RuleContext(action="reserve_room", actor_emp_id="EMP006", domain="Room"))
        unknown_emp = self.engine.evaluate(RuleContext(action="reserve_room", actor_emp_id="Official Name Is Not EMP", domain="Room"))

        self.assertEqual(allowed["overall_status"], RULE_PASS)
        self.assertEqual(forbidden["overall_status"], RULE_REJECT)
        self.assertEqual(unknown_emp["overall_status"], RULE_REJECT)

    def test_missing_actor_or_domain_is_warning_not_business_mutation(self):
        result = self.engine.evaluate(RuleContext(action="view_summary"))

        self.assertEqual(result["overall_status"], RULE_WARNING)
        self.assertFalse(result["mutates_business_state"])
        self.assertIn("Actor EMP or domain was not provided; role permission was not evaluated.", result["warning_reasons"])

    def test_custom_rules_can_be_injected(self):
        rules = default_business_rules(self.master_data)[:1]
        engine = BusinessRulesEngine(rules=rules, master_data=self.master_data)

        result = engine.evaluate({"action": "create_room", "required_fields": ("room_number",), "data": {"room_number": "A-101"}})

        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["overall_status"], RULE_PASS)


if __name__ == "__main__":
    unittest.main()
