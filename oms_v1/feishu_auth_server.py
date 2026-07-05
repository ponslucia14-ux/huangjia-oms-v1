from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .feishu_auth import FeishuIdentityAuthenticator
from .feishu_mapping import DEFAULT_ENV_PATH
from .home_ui import OMSHomeUI


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_LIVE_RUNTIME_ROOT = Path(os.getenv("OMS_LIVE_ROOT") or REPO_ROOT / "live_runtime")
LOCAL_OPERATING_ROOT = Path(os.getenv("OMS_OPERATING_ROOT") or LOCAL_LIVE_RUNTIME_ROOT / "operational_core")


def load_runtime_env(path: Path = DEFAULT_ENV_PATH) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        normalized_key = key.strip()
        if normalized_key.startswith("FEISHU_USER_ID_"):
            continue
        os.environ.setdefault(normalized_key, value.strip().strip('"').strip("'"))


load_runtime_env()


class FeishuAuthHandler(BaseHTTPRequestHandler):
    authenticator = FeishuIdentityAuthenticator()
    home_ui = OMSHomeUI(live_root=LOCAL_LIVE_RUNTIME_ROOT, operating_root=LOCAL_OPERATING_ROOT)
    runtime_source_policy = {
        "mode": "single_source_of_truth",
        "type": "local_live_runtime",
        "live_root": str(LOCAL_LIVE_RUNTIME_ROOT),
        "operating_root": str(LOCAL_OPERATING_ROOT),
        "cloud_role": "request_forwarding_only",
        "remote_data_generation_allowed": False,
        "remote_mock_allowed": False,
        "merge_remote_sources_allowed": False,
    }
    allowed_origins = {
        "https://ponslucia14-ux.github.io",
        "https://fepatfrt2v.feishu.cn",
    }

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True})

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0].rstrip("/")
        if path != "/api/oms/home":
            self._send_json({"ok": False, "error": "not_found"}, status=404)
            return
        user_id = self._query_value("user_id")
        self._send_home(user_id)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0].rstrip("/")
        if path not in {"/api/feishu/identity", "/api/oms/home"}:
            self._send_json({"ok": False, "error": "not_found"}, status=404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "invalid_json"}, status=400)
            return
        if path == "/api/oms/home":
            self._send_home(str(payload.get("user_id") or ""))
            return

        result = self.authenticator.authenticate_code(str(payload.get("code") or ""))
        self._write_audit(result)
        if not result.ok:
            self._send_json({"ok": False, "error": result.error, "data": result.data}, status=401)
            return
        self._send_json({"ok": True, "data": result.data})

    def _send_home(self, user_id: str) -> None:
        home = self.home_ui.build_home_from_saved_state(user_id=user_id)
        if home.get("home_type") == "identity_binding_error":
            self._send_json({"ok": False, "error": "identity_binding_required", "data": home}, status=401)
            return
        home = self._enforce_local_runtime_source(home)
        self._send_json({"ok": True, "data": self._compact_home_payload(home)})

    def _enforce_local_runtime_source(self, home: dict[str, Any]) -> dict[str, Any]:
        payload = dict(home)
        payload["runtime_source"] = dict(self.runtime_source_policy)
        dashboard = dict(payload.get("business_dashboard") or {})
        dashboard["runtime_source"] = dict(self.runtime_source_policy)
        dashboard["source"] = "local_live_runtime"
        dashboard["source_of_truth"] = str(LOCAL_LIVE_RUNTIME_ROOT)
        dashboard["remote_data_generation_allowed"] = False
        payload["business_dashboard"] = dashboard
        return payload

    def _compact_home_payload(self, home: dict[str, Any]) -> dict[str, Any]:
        compact = dict(home)
        sections = {}
        for key, section in (home.get("sections") or {}).items():
            if not isinstance(section, dict):
                continue
            items = section.get("items") if isinstance(section.get("items"), list) else []
            clipped = dict(section)
            clipped["items"] = items[:50]
            clipped["visible_count"] = len(clipped["items"])
            clipped["total_count"] = int(section.get("count") or len(items))
            sections[key] = clipped
        compact["sections"] = sections
        dashboard = compact.get("business_dashboard")
        if isinstance(dashboard, dict):
            compact_dashboard = dict(dashboard)
            for key in ("source_evidence_available_data", "source_evidence_verified_data"):
                compact_dashboard[key] = self._compact_source_evidence_data(compact_dashboard.get(key))
            compact["business_dashboard"] = compact_dashboard
        master_control = compact.get("master_control")
        if isinstance(master_control, dict):
            compact["master_control"] = self._compact_master_control(master_control)
        return compact

    def _compact_master_control(self, master_control: dict[str, Any], *, limit: int = 25) -> dict[str, Any]:
        compact = dict(master_control)
        execution_layer = compact.get("execution_layer")
        if isinstance(execution_layer, dict):
            compact_layer = dict(execution_layer)
            for key in ("all_tasks", "unfinished_tasks"):
                value = compact_layer.get(key)
                if isinstance(value, list):
                    compact_layer[f"{key}_total_count"] = len(value)
                    compact_layer[key] = value[:limit]
                    compact_layer[f"{key}_visible_count"] = len(compact_layer[key])
            sections = compact_layer.get("sections")
            if isinstance(sections, dict):
                compact_sections: dict[str, Any] = {}
                for key, value in sections.items():
                    if isinstance(value, list):
                        compact_sections[f"{key}_total_count"] = len(value)
                        compact_sections[key] = value[:limit]
                        compact_sections[f"{key}_visible_count"] = len(compact_sections[key])
                    else:
                        compact_sections[key] = value
                compact_layer["sections"] = compact_sections
            compact["execution_layer"] = compact_layer
        global_view = compact.get("global_view")
        if isinstance(global_view, dict):
            compact_global = dict(global_view)
            risk_register = compact_global.get("risk_register")
            if isinstance(risk_register, dict):
                compact_risk = dict(risk_register)
                items = compact_risk.get("items")
                if isinstance(items, list):
                    compact_risk["items_total_count"] = int(compact_risk.get("items_total_count") or len(items))
                    compact_risk["items"] = items[:limit]
                    compact_risk["items_visible_count"] = len(compact_risk["items"])
                compact_global["risk_register"] = compact_risk
            compact["global_view"] = compact_global
        compact["payload_policy"] = "compacted_for_feishu_h5_runtime"
        compact["payload_item_limit"] = limit
        return compact

    def _compact_source_evidence_data(self, source_data: Any, *, limit: int = 25) -> dict[str, Any]:
        if not isinstance(source_data, dict):
            return {
                "policy": "source_evidence_available_data",
                "warning": "source_evidence_payload_compacted",
            }
        compact: dict[str, Any] = {}
        for key, value in source_data.items():
            if isinstance(value, list):
                compact[key] = value[:limit]
                compact[f"{key}_visible_count"] = len(compact[key])
                compact[f"{key}_total_count"] = len(value)
            else:
                compact[key] = value
        compact["payload_policy"] = "compacted_for_feishu_h5_runtime"
        compact["payload_item_limit"] = limit
        return compact

    def _query_value(self, key: str) -> str:
        if "?" not in self.path:
            return ""
        query = self.path.split("?", 1)[1]
        for part in query.split("&"):
            name, _, value = part.partition("=")
            if name == key:
                from urllib.parse import unquote_plus

                return unquote_plus(value)
        return ""

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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
