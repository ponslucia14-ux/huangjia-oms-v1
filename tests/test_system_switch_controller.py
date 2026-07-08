import tempfile
import unittest
from pathlib import Path

from oms_v1.system_switch_controller import SystemSwitchController


class SystemSwitchControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.controller = SystemSwitchController(Path(self.tmp.name) / "switch")

    def tearDown(self):
        self.tmp.cleanup()

    def _adoption_stream(self, status="active", blockers=None):
        roles = ["刘芳羽", "刘晶", "销售", "尚丽娜"]
        return {
            "input_id": "in_test",
            "adoption": [
                {
                    "role": role,
                    "adoption_status": status,
                    "blockers": blockers or [],
                    "risk_level": "low" if status == "full" and not blockers else "medium",
                }
                for role in roles
            ],
        }

    def test_unauthed_hard_switch_downgrades_to_soft(self):
        stream = self.controller.build_switch_stream(
            self._adoption_stream("active", ["pending sync"]),
            requested_state="HARD_SWITCH",
            boss_authorized=False,
        )

        self.assertEqual(stream["switch"]["switch_state"], "SOFT_SWITCH")
        self.assertIn("石磊", stream["switch"]["required_authorization"])

    def test_full_operating_requires_full_adoption_and_boss(self):
        stream = self.controller.build_switch_stream(
            self._adoption_stream("full", []),
            requested_state="FULL_OPERATING",
            boss_authorized=True,
        )

        self.assertEqual(stream["switch"]["switch_state"], "FULL_OPERATING")
        self.assertEqual(stream["switch"]["oms_truth_role"], "OMS = 现在")
        self.assertEqual(stream["switch"]["legacy_system_role"]["Excel"], "历史")

    def test_full_operating_with_blockers_stays_hard_switch(self):
        stream = self.controller.build_switch_stream(
            self._adoption_stream("active", ["pending sync"]),
            requested_state="FULL_OPERATING",
            boss_authorized=True,
        )

        self.assertEqual(stream["switch"]["switch_state"], "HARD_SWITCH")
        self.assertTrue(stream["switch"]["blockers"])

    def test_bypass_blocks_full_operating(self):
        stream = self.controller.build_switch_stream(
            self._adoption_stream("full", []),
            requested_state="FULL_OPERATING",
            boss_authorized=True,
            bypass_events=[{"role": "销售", "source": "微信群"}],
        )

        self.assertEqual(stream["switch"]["switch_state"], "HARD_SWITCH")
        self.assertTrue(stream["switch"]["bypass_log"])

    def test_switch_status_is_persisted(self):
        stream = self.controller.build_switch_stream(self._adoption_stream("full", []), boss_authorized=True)
        path = Path(stream["audit"]["switch_root"]) / "system_switch_status.jsonl"

        self.assertTrue(path.exists())
        self.assertIn("switch_state", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
