from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote, urlparse


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "oms_app"


def main() -> None:
    manifest = json.loads((APP_ROOT / "feishu_webapp.json").read_text(encoding="utf-8"))
    redirect_uri = manifest["oauth"]["redirect_uri"]
    parsed = urlparse(redirect_uri)
    expected = "https://ponslucia14-ux.github.io/huangjia-oms-v1/"
    checks = {
        "app_id": manifest["feishu_app_id"],
        "app_id_match": manifest["feishu_app_id"] == manifest["oauth"]["app_id"],
        "entry_type": manifest["entry_type"],
        "web_url": manifest["web_url"],
        "redirect_uri": redirect_uri,
        "encoded_redirect_uri": quote(redirect_uri, safe=""),
        "exact_match": redirect_uri == expected,
        "protocol": parsed.scheme,
        "domain": parsed.netloc,
        "path": parsed.path,
        "trailing_slash": redirect_uri.endswith("/"),
        "allowed_redirect_uris": manifest["oauth"]["allowed_redirect_uris"],
        "oauth_redirect_uris": manifest["oauth_redirect_uris"],
        "js_safe_domains": manifest["h5_security"]["js_safe_domains"],
        "oauth_redirect_domains": manifest["h5_security"]["oauth_redirect_domains"],
        "h5_trusted_domains": manifest["h5_security"]["h5_trusted_domains"],
        "client_api": manifest["identity_auth"]["client_api"],
        "single_auth_flow": manifest["identity_auth"]["single_auth_flow"],
        "flow_steps": manifest["identity_auth"]["flow_steps"],
        "legacy_sdk_api_allowed": manifest["oauth"]["legacy_sdk_api_allowed"],
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
