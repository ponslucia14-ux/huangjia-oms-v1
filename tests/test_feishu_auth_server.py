import unittest
import json
import os
import tempfile
import threading
from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from oms_v1.feishu_auth_server import FeishuAuthHandler, load_runtime_env


class FakeHomeUI:
    def build_home_from_saved_state(self, *, user_id=None):
        return {
            "home_type": "user_centric_operating_interface",
            "entry": "personal_workspace",
            "current_user": {"user_id": user_id, "workspace_key": "boss", "name": "主理办（你）"},
            "sections": {
                "my_todos": {
                    "title": "我的待办",
                    "count": 60,
                    "items": [{"id": str(index)} for index in range(60)],
                }
            },
        }


class FeishuAuthServerTests(unittest.TestCase):
    def test_cors_allows_github_pages_with_credentials(self):
        self.assertIn("https://ponslucia14-ux.github.io", FeishuAuthHandler.allowed_origins)

    def test_runtime_env_loads_user_mapping_for_home_ui(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feishu.env"
            path.write_text("FEISHU_USER_ID_BOSS=a2c82cb4\n", encoding="utf-8")
            os.environ.pop("FEISHU_USER_ID_BOSS", None)
            try:
                load_runtime_env(path)
                self.assertEqual(os.environ["FEISHU_USER_ID_BOSS"], "a2c82cb4")
            finally:
                os.environ.pop("FEISHU_USER_ID_BOSS", None)

    def test_runtime_home_endpoint_returns_personal_workspace(self):
        original_home_ui = FeishuAuthHandler.home_ui
        FeishuAuthHandler.home_ui = FakeHomeUI()
        server = ThreadingHTTPServer(("127.0.0.1", 0), FeishuAuthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request(
                "POST",
                "/api/oms/home",
                body=json.dumps({"user_id": "a2c82cb4"}),
                headers={"Content-Type": "application/json", "Origin": "https://ponslucia14-ux.github.io"},
            )
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["data"]["entry"], "personal_workspace")
            self.assertEqual(payload["data"]["current_user"]["user_id"], "a2c82cb4")
            todos = payload["data"]["sections"]["my_todos"]
            self.assertEqual(todos["total_count"], 60)
            self.assertEqual(todos["visible_count"], 50)
            self.assertEqual(len(todos["items"]), 50)
        finally:
            server.shutdown()
            server.server_close()
            FeishuAuthHandler.home_ui = original_home_ui


if __name__ == "__main__":
    unittest.main()
