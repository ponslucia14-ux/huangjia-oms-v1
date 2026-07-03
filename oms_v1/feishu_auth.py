from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .feishu_mapping import DEFAULT_ENV_PATH, FeishuApiResult


class FeishuIdentityAuthenticator:
    """Exchange a Feishu WebView auth code for the current user's real identity."""

    def __init__(self, env_path: str | Path | None = None):
        self.env_path = Path(env_path or os.getenv("OMS_FEISHU_ENV") or DEFAULT_ENV_PATH)
        self.env = self._read_env(self.env_path)
        self.app_access_token: str | None = None

    def authenticate_code(self, code: str) -> FeishuApiResult:
        auth_code = str(code or "").strip()
        if not auth_code:
            return FeishuApiResult(False, error="missing Feishu authorization code")

        app_token = self._app_access_token()
        if not app_token.ok:
            return app_token

        user_token = self._user_access_token(auth_code)
        if not user_token.ok:
            return user_token

        access_token = (
            (user_token.data or {}).get("data", {}).get("access_token")
            or (user_token.data or {}).get("data", {}).get("user_access_token")
            or (user_token.data or {}).get("access_token")
            or (user_token.data or {}).get("user_access_token")
        )
        if not access_token:
            return FeishuApiResult(False, data=user_token.data, error="missing user_access_token from Feishu")

        user_info = self._user_info(str(access_token))
        if not user_info.ok:
            return user_info

        data = (user_info.data or {}).get("data") or user_info.data or {}
        identity = {
            "user_id": str(data.get("user_id") or ""),
            "open_id": str(data.get("open_id") or ""),
            "union_id": str(data.get("union_id") or ""),
            "name": str(data.get("name") or data.get("en_name") or ""),
            "avatar_url": str(data.get("avatar_url") or ""),
            "source": "feishu_webapp_sso",
        }
        if not (identity["user_id"] or identity["open_id"] or identity["union_id"]):
            return FeishuApiResult(False, data=user_info.data, error="Feishu user_info returned no identity id")
        return FeishuApiResult(True, data=identity, endpoint=user_info.endpoint)

    def _app_access_token(self) -> FeishuApiResult:
        app_id = self.env.get("FEISHU_APP_ID") or os.getenv("FEISHU_APP_ID")
        app_secret = self.env.get("FEISHU_APP_SECRET") or os.getenv("FEISHU_APP_SECRET")
        if not app_id or not app_secret:
            return FeishuApiResult(False, error="missing FEISHU_APP_ID or FEISHU_APP_SECRET")
        result = self._request(
            "POST",
            "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
            body={"app_id": app_id, "app_secret": app_secret},
            token=None,
        )
        if not result.ok:
            return result
        token = (result.data or {}).get("app_access_token")
        if not token:
            return FeishuApiResult(False, data=result.data, error="missing app_access_token from Feishu")
        self.app_access_token = str(token)
        return FeishuApiResult(True, data={"expire": (result.data or {}).get("expire")}, endpoint=result.endpoint)

    def _user_access_token(self, code: str) -> FeishuApiResult:
        return self._request(
            "POST",
            "https://open.feishu.cn/open-apis/authen/v1/access_token",
            body={"grant_type": "authorization_code", "code": code},
            token=self.app_access_token,
        )

    def _user_info(self, user_access_token: str) -> FeishuApiResult:
        return self._request(
            "GET",
            "https://open.feishu.cn/open-apis/authen/v1/user_info",
            token=user_access_token,
        )

    def _request(self, method: str, url: str, body: dict[str, Any] | None = None, *, token: str | None) -> FeishuApiResult:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
                parsed = json.loads(payload) if payload else {}
                return FeishuApiResult(True, data=parsed, status_code=response.status, endpoint=url)
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                parsed = payload
            return FeishuApiResult(False, data=parsed, error=str(exc), status_code=exc.code, endpoint=url)
        except Exception as exc:
            return FeishuApiResult(False, error=str(exc), endpoint=url)

    def _read_env(self, path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        return values
