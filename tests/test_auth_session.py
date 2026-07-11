import unittest

from oms_v1.auth_session import AuthSessionSigner


class AuthSessionTests(unittest.TestCase):
    def signer(self, now=1000):
        return AuthSessionSigner("test-session-secret-with-32-characters", ttl_seconds=60, clock=lambda: now)

    def test_issue_and_verify_preserves_identity(self):
        issued = self.signer().issue(user_id="ou_emp004", workspace_key="liujie", source="feishu_webapp_sso")
        claims = self.signer().verify(issued["token"])

        self.assertEqual(claims["user_id"], "ou_emp004")
        self.assertEqual(claims["workspace_key"], "liujie")
        self.assertEqual(claims["source"], "feishu_webapp_sso")
        self.assertEqual(claims["expires_at"], 1060)

    def test_tampered_token_is_rejected(self):
        issued = self.signer().issue(user_id="ou_emp008", workspace_key="june", source="feishu_webapp_sso")
        token = issued["token"][:-1] + ("A" if issued["token"][-1] != "A" else "B")

        with self.assertRaisesRegex(PermissionError, "invalid_session_signature"):
            self.signer().verify(token)

    def test_expired_token_is_rejected(self):
        issued = self.signer(now=1000).issue(user_id="ou_emp009", workspace_key="nana", source="feishu_webapp_sso")

        with self.assertRaisesRegex(PermissionError, "session_expired"):
            self.signer(now=1061).verify(issued["token"])


if __name__ == "__main__":
    unittest.main()
