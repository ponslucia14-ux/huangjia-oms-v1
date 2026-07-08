import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oms_v1.bootstrap import OMSBootstrap, write_design_doc
from oms_v1.health_check import HealthItem
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class BootstrapTests(unittest.TestCase):
    def _master_data(self, tmp: str) -> OMSMasterData:
        root = Path(tmp)
        organization_path = root / "OMS_组织主数据.md"
        identity_path = root / "OMS_飞书身份映射.md"
        write_organization(organization_path)
        write_identity(identity_path)
        return OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)

    def test_bootstrap_initializes_infrastructure_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            master_data = self._master_data(tmp)

            with patch("oms_v1.bootstrap.OMSMasterData", return_value=master_data), patch(
                "oms_v1.health_check.FeishuObjectSyncer",
                side_effect=AssertionError("default bootstrap must not probe Feishu API"),
            ):
                result = OMSBootstrap().run()

            self.assertTrue(result["ready"])
            self.assertEqual(result["status"], "OMS Ready.")
            self.assertFalse(result["scope"]["business_logic_executed"])
            self.assertFalse(result["scope"]["sales_module_entered"])
            self.assertFalse(result["scope"]["finance_module_entered"])
            self.assertEqual([step["name"] for step in result["steps"]], [
                "Config",
                "Master Data",
                "Feishu Identity",
                "Permission Engine",
                "Governance Engine",
                "Execution Engine",
                "Health Check",
            ])
            self.assertEqual(result["health_check"]["counts"]["warning"], 1)

    def test_bootstrap_fails_when_health_check_blocks_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            master_data = self._master_data(tmp)

            with patch("oms_v1.bootstrap.OMSMasterData", return_value=master_data), patch(
                "oms_v1.health_check.OMSHealthChecker._feishu_api_permissions",
                return_value=HealthItem("feishu_api_permission_status", "飞书接口权限", "fail", "critical", "blocked", True),
            ):
                result = OMSBootstrap(require_feishu_api=True).run()

            self.assertFalse(result["ready"])
            self.assertEqual(result["status"], "OMS Not Ready.")
            self.assertEqual(result["steps"][-1]["status"], "FAIL")

    def test_write_design_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_design_doc(Path(tmp) / "OMS_启动流程设计.md")

            text = path.read_text(encoding="utf-8")
            self.assertIn("# OMS 启动流程设计", text)
            self.assertIn("python -m oms_v1.bootstrap", text)
            self.assertIn("不进入销售模块", text)


if __name__ == "__main__":
    unittest.main()
