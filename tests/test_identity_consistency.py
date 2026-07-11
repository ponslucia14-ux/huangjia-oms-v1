import tempfile
import unittest

from oms_v1.audit_log import AuditEngine
from oms_v1.identity_consistency import IdentityConsistencyChecker


class IdentityConsistencyTests(unittest.TestCase):
    def test_eleven_production_identities_are_consistent_and_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = IdentityConsistencyChecker(audit=AuditEngine(audit_root=tmp)).check(write_audit=True)

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["required_count"], 11)
            self.assertEqual(result["pass_count"], 11)
            self.assertEqual(result["conflict_count"], 0)
            self.assertTrue(all(row["audit_name"] == row["feishu_name"] for row in result["rows"]))


if __name__ == "__main__":
    unittest.main()
