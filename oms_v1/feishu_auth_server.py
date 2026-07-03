from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .feishu_auth import FeishuIdentityAuthenticator


class FeishuAuthHandler(BaseHTTPRequestHandler):
    authenticator = FeishuIdentityAuthenticator()
    allowed_origins = {
        "https://ponslucia14-ux.github.io",
        "https://fepatfrt2v.feishu.cn",
    }

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/api/feishu/identity":
            self._send_json({"ok": False, "error": "not_found"}, status=404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "invalid_json"}, status=400)
            return

        result = self.authenticator.authenticate_code(str(payload.get("code") or ""))
        self._write_audit(result)
        if not result.ok:
            self._send_json({"ok": False, "error": result.error, "data": result.data}, status=401)
            return
        self._send_json({"ok": True, "data": result.data})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        origin = self.headers.get("Origin", "")
        allowed_origin = origin if origin in self.allowed_origins else "https://ponslucia14-ux.github.io"
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_audit(self, result: Any) -> None:
        audit_dir = Path(__file__).resolve().parents[1] / "live_runtime" / "auth_audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        data = result.data if isinstance(result.data, dict) else {}
        identity = data.get("data") if isinstance(data.get("data"), dict) else data
        payload = {
            "ok": bool(result.ok),
            "error": result.error,
            "status_code": result.status_code,
            "endpoint": result.endpoint,
            "identity": {
                "user_id": str(identity.get("user_id") or ""),
                "open_id": str(identity.get("open_id") or ""),
                "union_id": str(identity.get("union_id") or ""),
                "workspace_key": str(identity.get("workspace_key") or ""),
                "source": str(identity.get("source") or ""),
            },
        }
        (audit_dir / "last_identity_exchange.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), FeishuAuthHandler)
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(prog="feishu-auth-server", description="OMS Feishu WebApp identity endpoint")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
