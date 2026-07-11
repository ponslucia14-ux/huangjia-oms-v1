from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any


SESSION_SCHEMA_VERSION = "oms.v1.auth_session"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


@dataclass(frozen=True)
class AuthSession:
    user_id: str
    workspace_key: str
    source: str
    issued_at: int
    expires_at: int
    session_id: str
    schema_version: str = SESSION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "user_id": self.user_id,
            "workspace_key": self.workspace_key,
            "source": self.source,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "session_id": self.session_id,
        }


class AuthSessionSigner:
    """Issue and verify short-lived OMS sessions after trusted identity exchange."""

    def __init__(self, secret: str, *, ttl_seconds: int = 8 * 60 * 60, clock: Any = None):
        normalized = str(secret or "").strip()
        if len(normalized) < 24:
            raise ValueError("OMS session secret must contain at least 24 characters.")
        self.secret = normalized.encode("utf-8")
        self.ttl_seconds = int(ttl_seconds)
        self.clock = clock or time.time

    @classmethod
    def from_environment(cls) -> "AuthSessionSigner | None":
        secret = os.getenv("OMS_SESSION_SECRET") or os.getenv("FEISHU_APP_SECRET") or ""
        if len(secret.strip()) < 24:
            return None
        return cls(secret, ttl_seconds=int(os.getenv("OMS_SESSION_TTL_SECONDS") or 8 * 60 * 60))

    def issue(self, *, user_id: str, workspace_key: str, source: str) -> dict[str, Any]:
        normalized_user_id = str(user_id or "").strip()
        normalized_workspace = str(workspace_key or "").strip()
        if not normalized_user_id or not normalized_workspace:
            raise ValueError("user_id and workspace_key are required.")
        issued_at = int(self.clock())
        session = AuthSession(
            user_id=normalized_user_id,
            workspace_key=normalized_workspace,
            source=str(source or "").strip(),
            issued_at=issued_at,
            expires_at=issued_at + self.ttl_seconds,
            session_id=secrets.token_urlsafe(18),
        )
        payload = _b64encode(json.dumps(session.to_dict(), ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        signature = _b64encode(hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest())
        return {"token": f"{payload}.{signature}", "session": session.to_dict()}

    def verify(self, token: str) -> dict[str, Any]:
        try:
            payload, signature = str(token or "").split(".", 1)
            expected = _b64encode(hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise PermissionError("invalid_session_signature")
            claims = json.loads(_b64decode(payload).decode("utf-8"))
        except PermissionError:
            raise
        except Exception as exc:
            raise PermissionError("invalid_session_token") from exc
        if claims.get("schema_version") != SESSION_SCHEMA_VERSION:
            raise PermissionError("invalid_session_schema")
        if int(claims.get("expires_at") or 0) <= int(self.clock()):
            raise PermissionError("session_expired")
        if not claims.get("user_id") or not claims.get("workspace_key"):
            raise PermissionError("invalid_session_identity")
        return claims

