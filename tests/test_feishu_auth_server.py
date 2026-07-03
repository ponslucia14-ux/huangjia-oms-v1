import unittest

from oms_v1.feishu_auth_server import FeishuAuthHandler


class FeishuAuthServerTests(unittest.TestCase):
    def test_cors_allows_github_pages_with_credentials(self):
        self.assertIn("https://ponslucia14-ux.github.io", FeishuAuthHandler.allowed_origins)


if __name__ == "__main__":
    unittest.main()
