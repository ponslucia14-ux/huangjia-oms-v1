import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FeishuWebAppDeployTests(unittest.TestCase):
    def test_github_pages_workflow_deploys_oms_app(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy-oms-app.yml").read_text(encoding="utf-8")

        self.assertIn("Deploy OMS App", workflow)
        self.assertIn("actions/upload-pages-artifact@v3", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)
        self.assertIn("path: oms_app", workflow)

    def test_feishu_webapp_manifest_uses_https_web_url(self):
        manifest = json.loads((ROOT / "oms_app" / "feishu_webapp.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["integration_mode"], "feishu_web_app")
        self.assertEqual(manifest["entry_type"], "web_url")
        self.assertTrue(manifest["web_url"].startswith("https://"))
        self.assertEqual(manifest["home_page"], "personal_workspace")
        self.assertEqual(manifest["ui_contract"]["primary_entry"], "OMS Native Business App")
        self.assertEqual(manifest["ui_contract"]["feishu_role"], "entry_container_and_notification_channel")

    def test_feishu_webapp_manifest_does_not_change_backend_flow(self):
        manifest = json.loads((ROOT / "oms_app" / "feishu_webapp.json").read_text(encoding="utf-8"))

        self.assertTrue(manifest["runtime_policy"]["do_not_modify_backend_flow"])
        self.assertTrue(manifest["runtime_policy"]["do_not_use_feishu_as_primary_ui"])
        self.assertEqual(manifest["runtime_policy"]["external_sync_strategy"], "pending_outbox")


if __name__ == "__main__":
    unittest.main()
