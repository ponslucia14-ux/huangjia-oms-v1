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

        self.assertEqual(manifest["integration_mode"], "feishu_h5_workbench_app")
        self.assertEqual(manifest["feishu_app_id"], "cli_aaac7e6da2b95cfc")
        self.assertEqual(manifest["entry_type"], "feishu_h5_workbench_container")
        self.assertTrue(manifest["web_url"].startswith("https://"))
        self.assertEqual(manifest["oauth_redirect_uris"], ["https://ponslucia14-ux.github.io/huangjia-oms-v1/"])
        self.assertEqual(manifest["home_page"], "personal_workspace")
        self.assertEqual(manifest["ui_contract"]["primary_entry"], "OMS Daily Operational Workbench")
        self.assertEqual(manifest["ui_contract"]["feishu_role"], "entry_container_and_notification_channel")
        self.assertEqual(manifest["oauth"]["flow"], "feishu_h5_jssdk_requestAccess")
        self.assertEqual(manifest["oauth"]["client_id_field"], "appID")
        self.assertEqual(manifest["oauth"]["sdk_api"], "tt.requestAccess")
        self.assertFalse(manifest["oauth"]["legacy_sdk_api_allowed"])
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
        self.assertEqual(manifest["identity_auth"]["client_api"], "tt.requestAccess")
        self.assertTrue(manifest["identity_auth"]["single_auth_flow"])
        self.assertTrue(manifest["identity_auth"]["block_non_feishu_container"])
        self.assertTrue(manifest["identity_auth"]["reset_state_on_failure"])
        self.assertEqual(manifest["identity_auth"]["success_route"], "personal_workspace")
        self.assertEqual(
            manifest["identity_auth"]["flow_steps"],
            [
                "feishu_container",
                "requestAccess",
                "auth_code",
                "server_exchange",
                "user_id",
                "workspace",
                "personal_workspace",
            ],
        )
        self.assertNotIn("legacy_client_api", manifest["identity_auth"])

    def test_feishu_workbench_entry_must_open_inside_h5_container(self):
        manifest = json.loads((ROOT / "oms_app" / "feishu_webapp.json").read_text(encoding="utf-8"))
        launch_policy = manifest["launch_policy"]

        self.assertTrue(launch_policy["only_open_in_feishu_client"])
        self.assertFalse(launch_policy["browser_tab_entry_allowed"])
        self.assertFalse(launch_policy["direct_github_pages_entry_allowed"])
        self.assertFalse(launch_policy["ordinary_web_url_launch_allowed"])
        self.assertEqual(launch_policy["expected_runtime_flag"], "is_feishu_workbench_container=true")
        self.assertEqual(launch_policy["failure_if_runtime_flag"], "is_feishu_workbench_container=false")
        self.assertIn("not as external browser URL", launch_policy["platform_action_required"])

    def test_feishu_webapp_manifest_does_not_change_backend_flow(self):
        manifest = json.loads((ROOT / "oms_app" / "feishu_webapp.json").read_text(encoding="utf-8"))

        self.assertTrue(manifest["runtime_policy"]["do_not_modify_backend_flow"])
        self.assertTrue(manifest["runtime_policy"]["do_not_use_feishu_as_primary_ui"])
        self.assertEqual(manifest["runtime_policy"]["external_sync_strategy"], "pending_outbox")
        self.assertEqual(manifest["runtime_policy"]["single_source_of_truth"], "D:\\OMS_V1\\OMS_TRUTH_SOURCE")
        self.assertEqual(manifest["runtime_policy"]["api_home_role"], "forward_to_oms_truth_source")
        self.assertEqual(manifest["runtime_policy"]["cloud_role"], "ui_host_and_request_forwarding_only")
        self.assertFalse(manifest["runtime_policy"]["remote_data_generation_allowed"])
        self.assertFalse(manifest["runtime_policy"]["remote_mock_allowed"])
        self.assertFalse(manifest["runtime_policy"]["merge_remote_sources_allowed"])


if __name__ == "__main__":
    unittest.main()
