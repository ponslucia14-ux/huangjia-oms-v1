import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oms_v1.feishu_auth import FeishuIdentityAuthenticator
from oms_v1.feishu_mapping import FeishuApiResult


class FeishuIdentityAuthenticatorTests(unittest.TestCase):
    def test_missing_code_is_rejected(self):
        client = FeishuIdentityAuthenticator(env_path="missing.env")

        result = client.authenticate_code("")

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "missing Feishu authorization code")

    def test_missing_credentials_are_rejected_before_user_lookup(self):
        client = FeishuIdentityAuthenticator(env_path="missing.env")

        with patch.dict("os.environ", {"FEISHU_APP_ID": "", "FEISHU_APP_SECRET": ""}, clear=False):
            result = client.authenticate_code("auth_code")

        self.assertFalse(result.ok)
        self.assertIn("FEISHU_APP_ID", result.error)

    def test_auth_code_exchanges_to_user_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "feishu.env"
            env_path.write_text("FEISHU_APP_ID=cli_test\nFEISHU_APP_SECRET=secret\n", encoding="utf-8")
            client = FeishuIdentityAuthenticator(env_path=env_path)
            calls = []

            def fake_request(method, url, body=None, *, token=None):
                calls.append({"method": method, "url": url, "body": body, "token": token})
                if url.endswith("/auth/v3/app_access_token/internal"):
                    return FeishuApiResult(True, data={"app_access_token": "app_token", "expire": 7200})
                if url.endswith("/authen/v1/access_token"):
                    return FeishuApiResult(True, data={"data": {"access_token": "user_token"}})
                if url.endswith("/authen/v1/user_info"):
                    return FeishuApiResult(
                        True,
                        data={
                            "data": {
                                "user_id": "user_june",
                                "open_id": "ou_june",
                                "union_id": "on_june",
                                "name": "六月",
                            }
                        },
                    )
                return FeishuApiResult(False, error="unexpected")

            client._request = fake_request

            result = client.authenticate_code("auth_code")

            self.assertTrue(result.ok)
            self.assertEqual(result.data["user_id"], "user_june")
            self.assertEqual(result.data["open_id"], "ou_june")
            self.assertEqual(result.data["union_id"], "on_june")
            self.assertEqual(calls[1]["token"], "app_token")
            self.assertEqual(calls[1]["body"]["code"], "auth_code")
            self.assertEqual(calls[2]["token"], "user_token")


if __name__ == "__main__":
    unittest.main()
