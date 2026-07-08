import unittest

from oms_v1.domain import DOMAIN_DEFINITIONS, DOMAIN_SCHEMA_VERSION, DomainRegistry, default_domain_registry


EXPECTED_DOMAINS = {
    "Customer",
    "Contract",
    "Payment",
    "Room",
    "Stay",
    "Employee",
    "Caregiver",
    "Expense",
    "Approval",
    "Task",
    "Notification",
}

KNOWN_ROLES = {
    "ROLE_OWNER",
    "ROLE_HR",
    "ROLE_ACCOUNTANT",
    "ROLE_CASHIER",
    "ROLE_ADMIN",
    "ROLE_SALES",
    "ROLE_STORE_MANAGER",
    "ROLE_BUTLER",
    "ROLE_NURSING_DIRECTOR",
    "ROLE_KITCHEN_DIRECTOR",
}


class DomainModelTests(unittest.TestCase):
    def test_required_domains_are_defined(self):
        registry = default_domain_registry()

        self.assertEqual(set(registry.names()), EXPECTED_DOMAINS)
        self.assertEqual(len(registry.all()), 11)

    def test_each_domain_has_required_contract_fields(self):
        for domain in DOMAIN_DEFINITIONS:
            self.assertEqual(domain.schema_version, DOMAIN_SCHEMA_VERSION)
            self.assertTrue(domain.identifier.endswith("_id") or domain.identifier == "emp_id")
            self.assertTrue(domain.responsibility)
            self.assertGreaterEqual(len(domain.lifecycle), 3)
            self.assertGreaterEqual(len(domain.statuses), 2)
            self.assertTrue(domain.allowed_actions)
            self.assertTrue(domain.events)
            self.assertTrue(domain.audit_events)
            self.assertTrue(domain.mutable_by_roles)

    def test_identifiers_are_unique_and_domains_are_readable_by_name(self):
        registry = DomainRegistry()
        identifiers = [domain.identifier for domain in registry.all()]

        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(registry.get("Customer").identifier, "customer_id")
        self.assertEqual(registry.get("Employee").identifier, "emp_id")
        with self.assertRaises(KeyError):
            registry.get("Unknown")

    def test_events_and_audit_names_are_domain_scoped(self):
        for domain in DOMAIN_DEFINITIONS:
            prefix = domain.name.lower()
            self.assertTrue(all(event.startswith(f"{prefix}.") for event in domain.events))
            self.assertTrue(all(audit.startswith(f"{prefix}.") for audit in domain.audit_events))

    def test_mutable_roles_are_known_master_data_roles(self):
        for domain in DOMAIN_DEFINITIONS:
            self.assertTrue(set(domain.mutable_by_roles).issubset(KNOWN_ROLES))

    def test_registry_policy_blocks_local_object_definitions(self):
        model = default_domain_registry().to_dict()

        self.assertEqual(model["schema_version"], DOMAIN_SCHEMA_VERSION)
        self.assertEqual(model["domain_count"], 11)
        self.assertTrue(model["policy"]["business_modules_must_reference_domain"])
        self.assertFalse(model["policy"]["module_local_object_definitions_allowed"])
        self.assertFalse(model["policy"]["database_binding_in_this_phase"])


if __name__ == "__main__":
    unittest.main()
