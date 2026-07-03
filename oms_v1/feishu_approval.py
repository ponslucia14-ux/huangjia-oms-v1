from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .feishu_mapping import DEFAULT_ENV_PATH, FeishuApiResult
from .schemas import now_iso


DEFAULT_APPROVAL_TYPES: dict[str, dict[str, Any]] = {
    "finance": {
        "name": "费用报销",
        "keywords": ["费用报销", "报销", "财务", "finance"],
    },
    "payment": {
        "name": "付款申请",
        "keywords": ["付款申请", "付款", "支付", "payment"],
    },
    "general": {
        "name": "通用审批",
        "keywords": ["通用审批", "通用", "审批", "general"],
    },
}


ACTION_APPROVAL_TYPES = {
    "generate_reconciliation_task": "finance",
    "create_payment_todo": "payment",
    "generate_service_amount_split_task": "finance",
    "flag_financial_risk": "finance",
    "create_service_risk_task": "general",
    "mark_oversell_risk": "general",
    "generate_room_exception_task": "general",
    "generate_room_assignment_plan": "general",
}


@dataclass
class ApprovalAttempt:
    ok: bool
    status: str
    approval_type: str
    default_name: str
    message: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "approval_type": self.approval_type,
            "default_name": self.default_name,
            "message": self.message,
            "data": self.data,
        }


class FeishuDefaultApprovalClient:
    """API-driven Feishu approval adapter with pending-safe failure semantics."""

    def __init__(self, env_path: str | Path | None = None):
        self.env_path = Path(env_path or os.getenv("OMS_FEISHU_ENV") or DEFAULT_ENV_PATH)
        self.env = self._read_env(self.env_path)
        self.token: str | None = None

    def create_default_approval(self, action: dict[str, Any], governance: dict[str, Any]) -> ApprovalAttempt:
        approval_type = self.default_type_for(action, governance)
        default_spec = DEFAULT_APPROVAL_TYPES[approval_type]
        token_result = self._tenant_access_token()
        if not token_result.ok:
            return self._pending(approval_type, "tenant_access_token unavailable", token_result)

        definitions_result = self.list_available_definitions()
        if not definitions_result.ok:
            return self._pending(approval_type, "approval definitions unavailable", definitions_result)

        definition = self.find_default_definition(approval_type, definitions_result.data or [])
        if not definition:
            return ApprovalAttempt(
                ok=False,
                status="pending",
                approval_type=approval_type,
                default_name=str(default_spec["name"]),
                message="default approval definition not found by Feishu API",
                data={
                    "available_default_types": sorted(DEFAULT_APPROVAL_TYPES),
                    "matched_approval_code": "",
                    "definitions_count": len(definitions_result.data or []),
                },
            )

        submitter_user_id = self._submitter_user_id(action, governance)
        if not submitter_user_id:
            return ApprovalAttempt(
                ok=False,
                status="pending",
                approval_type=approval_type,
                default_name=str(default_spec["name"]),
                message="missing submitter user_id from real Feishu mapping",
                data={
                    "matched_approval_code": definition.get("approval_code") or definition.get("code") or "",
                    "definition": definition,
                },
            )

        instance_result = self.create_instance(definition, submitter_user_id, action, governance)
        if not instance_result.ok or instance_result.data.get("code") != 0:
            return self._pending(approval_type, "approval instance create failed", instance_result, definition=definition)

        return ApprovalAttempt(
            ok=True,
            status="success",
            approval_type=approval_type,
            default_name=str(default_spec["name"]),
            message="approval instance created by Feishu API",
            data=instance_result.data.get("data", {}),
        )

    def list_available_definitions(self) -> FeishuApiResult:
        endpoint = "https://open.feishu.cn/open-apis/approval/v4/approvals"
        params = {"page_size": "100", "locale": "zh-CN"}
        result = self._request("GET", endpoint + "?" + urllib.parse.urlencode(params))
        if not result.ok or result.data.get("code") != 0:
            return FeishuApiResult(False, data=result.data, error=self._error_text(result), status_code=result.status_code, endpoint=endpoint)
        return FeishuApiResult(True, data=result.data.get("data", {}).get("items", []), endpoint=endpoint)

    def find_default_definition(self, approval_type: str, definitions: list[dict[str, Any]]) -> dict[str, Any] | None:
        spec = DEFAULT_APPROVAL_TYPES.get(approval_type) or DEFAULT_APPROVAL_TYPES["general"]
        keywords = [str(item) for item in spec["keywords"]]
        for definition in definitions:
            haystack = " ".join(
                str(definition.get(field) or "")
                for field in ["name", "approval_name", "description", "approval_code", "code"]
            )
            if any(keyword and keyword in haystack for keyword in keywords):
                return definition
        return None

    def create_instance(
        self,
        definition: dict[str, Any],
        submitter_user_id: str,
        action: dict[str, Any],
        governance: dict[str, Any],
    ) -> FeishuApiResult:
        approval_code = str(definition.get("approval_code") or definition.get("code") or "")
        if not approval_code:
            return FeishuApiResult(False, data={"reason": "definition has no approval_code"})
        endpoint = "https://open.feishu.cn/open-apis/approval/v4/instances"
        body = {
            "approval_code": approval_code,
            "user_id": submitter_user_id,
            "form": json.dumps(self._default_form(action, governance), ensure_ascii=False),
        }
        return self._request("POST", endpoint, body=body)

    def default_type_for(self, action: dict[str, Any], governance: dict[str, Any]) -> str:
        action_type = str(action.get("action_type") or governance.get("action_type") or "")
        if action_type in ACTION_APPROVAL_TYPES:
            return ACTION_APPROVAL_TYPES[action_type]
        target_module = str(action.get("target_module") or "").lower()
        required_roles = " ".join(str(role) for role in governance.get("required_roles") or [])
        text = f"{action_type} {target_module} {required_roles}"
        if any(term in text for term in ["付款", "payment", "pay"]):
            return "payment"
        if any(term in text for term in ["财务", "finance", "报销", "reconciliation"]):
            return "finance"
        return "general"

    def _default_form(self, action: dict[str, Any], governance: dict[str, Any]) -> list[dict[str, str]]:
        payload = action.get("execution_payload") or {}
        return [
            {"id": "oms_action_id", "value": str(action.get("action_id") or "")},
            {"id": "oms_action_type", "value": str(action.get("action_type") or "")},
            {"id": "oms_reason", "value": str(payload.get("reason") or governance.get("reason") or "")},
            {"id": "oms_recommended_action", "value": str(payload.get("recommended_action") or "")},
            {"id": "oms_created_at", "value": now_iso()},
        ]

    def _submitter_user_id(self, action: dict[str, Any], governance: dict[str, Any]) -> str:
        candidates = [
            action.get("submitter_user_id"),
            (action.get("execution_payload") or {}).get("submitter_user_id"),
            governance.get("submitter_user_id"),
            (governance.get("responsibility_chain") or {}).get("submitter_user_id"),
        ]
        for candidate in candidates:
            if candidate:
                return str(candidate)
        return ""

    def _tenant_access_token(self) -> FeishuApiResult:
        app_id = self.env.get("FEISHU_APP_ID", "")
        app_secret = self.env.get("FEISHU_APP_SECRET", "")
        if not app_id or not app_secret:
            return FeishuApiResult(False, error="missing FEISHU_APP_ID or FEISHU_APP_SECRET")
        result = self._request(
            "POST",
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            body={"app_id": app_id, "app_secret": app_secret},
            auth=False,
        )
        if not result.ok:
            return result
        if result.data.get("code") != 0:
            return FeishuApiResult(False, data=result.data, error=json.dumps(result.data, ensure_ascii=False))
        self.token = result.data.get("tenant_access_token")
        return FeishuApiResult(True, data={"expire": result.data.get("expire")})

    def _request(self, method: str, url: str, body: dict[str, Any] | None = None, *, auth: bool = True) -> FeishuApiResult:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
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

    def _pending(
        self,
        approval_type: str,
        message: str,
        result: FeishuApiResult,
        *,
        definition: dict[str, Any] | None = None,
    ) -> ApprovalAttempt:
        data = {
            "endpoint": result.endpoint,
            "status_code": result.status_code,
            "error": result.error or self._error_text(result),
            "response": result.data,
        }
        if definition:
            data["definition"] = definition
        return ApprovalAttempt(
            ok=False,
            status="pending",
            approval_type=approval_type,
            default_name=str(DEFAULT_APPROVAL_TYPES[approval_type]["name"]),
            message=message,
            data=data,
        )

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

    def _error_text(self, result: FeishuApiResult) -> str:
        if isinstance(result.data, dict):
            return json.dumps(result.data, ensure_ascii=False)
        if result.data:
            return str(result.data)
        if result.error:
            return result.error
        return ""
