import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FeishuWebAppDeployTests(unittest.TestCase):
    def test_github_pages_workflow_deploys_oms_app(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy-oms-app.yml").read_text(encoding="utf-8")

        self.assertIn("Deploy OMS App", workflow)
        self.assertIn("peaceiris/actions-gh-pages@v4", workflow)
        self.assertIn("publish_dir: ./oms_app", workflow)
        self.assertIn("publish_branch: gh-pages", workflow)

    def test_feishu_webapp_manifest_uses_https_web_url(self):
        manifest = json.loads((ROOT / "oms_app" / "feishu_webapp.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["integration_mode"], "feishu_web_app")
        self.assertEqual(manifest["feishu_app_id"], "cli_aaac7e6da2b95cfc")
        self.assertEqual(manifest["entry_type"], "web_url")
        self.assertTrue(manifest["web_url"].startswith("https://"))
        self.assertEqual(manifest["oauth_redirect_uris"], ["https://ponslucia14-ux.github.io/huangjia-oms-v1/"])
        self.assertEqual(manifest["home_page"], "personal_workspace")
        self.assertEqual(manifest["ui_contract"]["primary_entry"], "OMS Native Business App")
        self.assertEqual(manifest["ui_contract"]["feishu_role"], "entry_container_and_notification_channel")
        self.assertEqual(manifest["oauth"]["flow"], "feishu_h5_jssdk_requestAccess")
        self.assertEqual(manifest["oauth"]["client_id_field"], "appID")
        self.assertEqual(manifest["oauth"]["app_id"], manifest["feishu_app_id"])
        self.assertEqual(manifest["oauth"]["redirect_uri"], manifest["web_url"])
        self.assertEqual(manifest["oauth"]["allowed_redirect_uris"], [manifest["web_url"]])
        self.assertEqual(manifest["oauth"]["scope_list"], [])
        self.assertFalse(manifest["oauth"]["manual_oauth_url"])
        self.assertTrue(manifest["oauth"]["redirect_uri_exact_match_required"])
        self.assertEqual(manifest["h5_security"]["js_safe_domains"], ["ponslucia14-ux.github.io"])
        self.assertEqual(manifest["h5_security"]["oauth_redirect_domains"], ["ponslucia14-ux.github.io"])
        self.assertEqual(manifest["h5_security"]["h5_trusted_domains"], ["ponslucia14-ux.github.io"])
        self.assertTrue(manifest["h5_security"]["trailing_slash_required"])
        self.assertFalse(manifest["h5_security"]["dev_prod_url_mixing_allowed"])

    def test_feishu_webapp_manifest_does_not_change_backend_flow(self):
        manifest = json.loads((ROOT / "oms_app" / "feishu_webapp.json").read_text(encoding="utf-8"))

        self.assertTrue(manifest["runtime_policy"]["do_not_modify_backend_flow"])
        self.assertTrue(manifest["runtime_policy"]["do_not_use_feishu_as_primary_ui"])
        self.assertEqual(manifest["runtime_policy"]["external_sync_strategy"], "pending_outbox")


if __name__ == "__main__":
    unittest.main()
