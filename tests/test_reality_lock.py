import tempfile
import unittest
from pathlib import Path

from oms_v1.reality_lock import FINAL_ARCHITECTURE, RealityLock


class RealityLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lock = RealityLock(Path(self.tmp.name) / "lock")

    def tearDown(self):
        self.tmp.cleanup()

    def _switch_stream(self, state="SOFT_SWITCH", ready=False, blockers=None):
        roles = ["六月", "刘姐", "销售", "娜娜"]
        return {
            "input_id": "in_test",
            "switch": {
                "switch_state": state,
                "blockers": blockers or [],
                "role_switches": [
                    {
                        "role": role,
                        "switch_ready": ready,
                        "blockers": [] if ready else ["not full adoption"],
                    }
                    for role in roles
                ],
            },
        }

    def test_full_operating_without_blockers_locks_reality(self):
        stream = self.lock.build_lock_stream(self._switch_stream("FULL_OPERATING", ready=True))

        self.assertEqual(stream["lock"]["lock_state"], "LOCKED")
        self.assertEqual(stream["lock"]["fixed_architecture"], FINAL_ARCHITECTURE)
        self.assertIn("event trace", stream["lock"]["trace_requirements"])

    def test_soft_switch_stays_migration(self):
        stream = self.lock.build_lock_stream(self._switch_stream("SOFT_SWITCH", ready=False))

        self.assertEqual(stream["lock"]["lock_state"], "MIGRATION")
        self.assertTrue(stream["lock"]["blockers"])

    def test_pre_switch_is_readonly(self):
        stream = self.lock.build_lock_stream(self._switch_stream("PRE_SWITCH", ready=False))

        self.assertEqual(stream["lock"]["lock_state"], "READONLY")

    def test_debug_unlock_is_explicit(self):
        stream = self.lock.build_lock_stream(self._switch_stream("FULL_OPERATING", ready=True), debug_unlock=True)

        self.assertEqual(stream["lock"]["lock_state"], "UNLOCKED")

    def test_reality_lock_status_is_persisted(self):
        stream = self.lock.build_lock_stream(self._switch_stream("FULL_OPERATING", ready=True))
        path = Path(stream["audit"]["lock_root"]) / "reality_lock_status.jsonl"

        self.assertTrue(path.exists())
        self.assertIn("lock_state", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
