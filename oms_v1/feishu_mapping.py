from __future__ import annotations

import csv
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .master_data import OMSMasterData
from .schemas import now_iso


DEFAULT_ENV_PATH = Path(__file__).resolve().parents[1] / "config" / "secrets" / "feishu.env"
DEFAULT_MAPPING_ROOT = Path(__file__).resolve().parents[1] / "live_runtime" / "realworld_mapping"


@dataclass
class FeishuApiResult:
    ok: bool
    data: Any = None
    error: str | None = None
    status_code: int | None = None
    endpoint: str | None = None


@dataclass
class MappingRow:
    name: str
    user_id: str = ""
    open_id: str = ""
    chat_id: str = ""
    approval_code: str = ""
    approval_type: str = ""
    role: str = ""
    source: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "user_id": self.user_id,
            "open_id": self.open_id,
            "chat_id": self.chat_id,
            "approval_code": self.approval_code,
            "approval_type": self.approval_type,
            "role": self.role,
            "source": self.source,
        }


class FeishuObjectSyncer:
    """Synchronize Feishu real-world objects into a local OMS mapping table."""

    def __init__(
        self,
        env_path: str | Path | None = None,
        mapping_root: str | Path | None = None,
        identity_mapping_path: str | Path | None = None,
        master_data: OMSMasterData | None = None,
    ):
        self.env_path = Path(env_path or os.getenv("OMS_FEISHU_ENV") or DEFAULT_ENV_PATH)
        self.mapping_root = Path(mapping_root or os.getenv("OMS_MAPPING_ROOT") or DEFAULT_MAPPING_ROOT)
        self.master_data = master_data or OMSMasterData(feishu_identity_path=identity_mapping_path)
        self.env = self._read_env(self.env_path)
        self.token: str | None = None

    def sync(self) -> dict[str, Any]:
        self.mapping_root.mkdir(parents=True, exist_ok=True)
        snapshot = self.fetch_snapshot()
        rows = self.build_mapping(snapshot)
        capabilities = self.build_capabilities(rows)
        output = {
            "schema_version": "oms.v1.realworld_mapping",
            "created_at": now_iso(),
            "mapping_name": "OMS_RealWorld_Mapping",
            "env_path": str(self.env_path),
            "source": "feishu_real_api_only",
            "sync_status": snapshot["sync_status"],
            "sync_errors": snapshot["sync_errors"],
            "rows": [row.to_dict() for row in rows],
            "capabilities": capabilities,
            "questions_answered": [
                "我要发给谁？",
                "我要审批找谁？",
                "我要写入谁的飞书？",
            ],
            "manual_id_policy": "disabled; IDs must come from Feishu real APIs",
        }
        self._write_mapping(output)
        return output

    def fetch_snapshot(self) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        token_result = self._tenant_access_token()
        if not token_result.ok:
            errors.append({"target": "tenant_access_token", "error": token_result.error})
            return {
                "sync_status": "failed",
                "sync_errors": errors,
                "users": [],
                "chats": [],
                "approvals": [],
            }

        users = self._list_users()
        chats = self._list_chats()
        chat_members = self._list_chat_members(chats.data if chats.ok else [])
        approvals = self._list_approvals()

        for name, result in [("users", users), ("chats", chats), ("chat_members", chat_members), ("approvals", approvals)]:
            if not result.ok:
                errors.append(
                    {
                        "target": name,
                        "endpoint": result.endpoint,
                        "status_code": result.status_code,
                        "error": result.error,
                    }
                )

        snapshot = {
            "sync_status": "success" if not errors else "partial",
            "sync_errors": errors,
            "users": users.data if users.ok else [],
            "org_users": users.data if users.ok else [],
            "chats": chats.data if chats.ok else [],
            "chat_members_as_users": chat_members.data if chat_members.ok else [],
            "approvals": approvals.data if approvals.ok else [],
            "identity_source_policy": "FEISHU_ORG_USERS_PRIMARY; chat members may provide individual identity evidence only when source is recorded",
        }
        (self.mapping_root / "feishu_object_snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return snapshot

    def build_mapping(self, snapshot: dict[str, Any]) -> list[MappingRow]:
        rows: list[MappingRow] = []
        users = list(snapshot.get("org_users") or snapshot.get("users") or [])
        for seed in self._role_seeds():
            row = MappingRow(name=seed["name"], role=seed["role"])
            row.approval_type = self._default_approval_type(seed)
            self._apply_env_overrides(row, seed["env_key"])
            self._apply_user_match(row, seed, users)
            self._apply_chat_match(row, seed, snapshot.get("chats") or [])
            self._apply_approval_match(row, seed, snapshot.get("approvals") or [])
            rows.append(row)
        return rows

    def _role_seeds(self) -> list[dict[str, Any]]:
        return [
            {
                "emp": row["emp"],
                "name": row["name"],
                "role": row["role"],
                "env_key": row["emp"],
                "match_terms": row["match_terms"],
                "chat_match_terms": row["match_terms"],
            }
            for row in self.master_data.feishu_identity_rows()
        ]

    def build_capabilities(self, rows: list[MappingRow]) -> dict[str, Any]:
        return {
            "send_message(to_role)": {row.name: self.resolve_action(row, "send_message") for row in rows},
            "create_approval(to_role)": {row.name: self.resolve_action(row, "create_approval") for row in rows},
            "assign_task(to_role)": {row.name: self.resolve_action(row, "assign_task") for row in rows},
        }

    def action_for_role(self, action: str, to_role: str, mapping: dict[str, Any] | None = None) -> dict[str, Any]:
        data = mapping or json.loads((self.mapping_root / "OMS_RealWorld_Mapping.json").read_text(encoding="utf-8"))
        row = self._find_mapping_row(data.get("rows") or [], to_role)
        if row is None:
            return {"ready": False, "action": action, "to_role": to_role, "reason": "role not found in OMS_RealWorld_Mapping"}
        mapping_row = MappingRow(**{k: row.get(k, "") for k in ["name", "user_id", "open_id", "chat_id", "approval_code", "approval_type", "role"]})
        if not mapping_row.approval_type:
            mapping_row.approval_type = self._default_approval_type(
                {"name": mapping_row.name, "role": mapping_row.role, "match_terms": [mapping_row.name, mapping_row.role]}
            )
        resolved = self.resolve_action(mapping_row, action)
        resolved.update({"action": action, "to_role": to_role})
        return resolved

    def send_message(self, to_role: str, mapping: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.action_for_role("send_message", to_role, mapping)

    def create_approval(self, to_role: str, mapping: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.action_for_role("create_approval", to_role, mapping)

    def assign_task(self, to_role: str, mapping: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.action_for_role("assign_task", to_role, mapping)

    def resolve_action(self, row: MappingRow, action: str) -> dict[str, Any]:
        if action == "send_message":
            target_type = "chat_id" if row.chat_id else "open_id" if row.open_id else ""
            target_id = row.chat_id or row.open_id
            return {
                "ready": bool(target_id),
                "target_type": target_type,
                "target_id": target_id,
                "reason": "ready" if target_id else "missing chat_id/open_id",
            }
        if action == "create_approval":
            approval_type = row.approval_type or "general"
            ready = bool(approval_type and (row.user_id or row.open_id))
            return {
                "ready": ready,
                "approval_type": approval_type,
                "approval_code": row.approval_code,
                "approver_user_id": row.user_id,
                "approver_open_id": row.open_id,
                "approval_code_policy": "auto_discover_by_api; no manual configuration",
                "reason": "ready" if ready else "missing approver user identity",
            }
        if action == "assign_task":
            target_id = row.user_id or row.open_id
            return {
                "ready": bool(target_id),
                "target_type": "user_id" if row.user_id else "open_id" if row.open_id else "",
                "target_id": target_id,
                "reason": "ready" if target_id else "missing user_id/open_id",
            }
        raise ValueError(f"Unsupported action: {action}")

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

    def _list_users(self) -> FeishuApiResult:
        scope_result = self._list_contact_scope()
        scope_data = scope_result.data if scope_result.ok else {}
        department_refs = self._department_refs_from_scope(scope_data)
        user_ids = self._user_ids_from_scope(scope_data)
        users = self._users_from_ids(user_ids)
        errors: list[str] = []
        endpoint = "https://open.feishu.cn/open-apis/contact/v3/users/find_by_department"
        for department_id, department_id_type in self._expand_department_refs(department_refs):
            page_token = ""
            while True:
                params = {
                    "department_id": department_id,
                    "page_size": "50",
                    "user_id_type": "user_id",
                    "department_id_type": department_id_type,
                }
                if page_token:
                    params["page_token"] = page_token
                result = self._request("GET", endpoint + "?" + urllib.parse.urlencode(params))
                if result.ok and result.data.get("code") == 0:
                    data = result.data.get("data", {})
                    users.extend(data.get("items", []))
                    if not data.get("has_more"):
                        break
                    page_token = str(data.get("page_token") or "")
                    if not page_token:
                        break
                else:
                    errors.append(self._error_text(result))
                    break
        users = self._unique_users(users)
        if users:
            return FeishuApiResult(True, data=users, endpoint=endpoint)
        return FeishuApiResult(False, data=[], error="; ".join(errors) or self._error_text(scope_result), status_code=400, endpoint=endpoint)

    def _list_contact_scope(self) -> FeishuApiResult:
        endpoint = "https://open.feishu.cn/open-apis/contact/v3/scopes"
        params = {"user_id_type": "user_id", "department_id_type": "department_id", "page_size": "100"}
        result = self._request("GET", endpoint + "?" + urllib.parse.urlencode(params))
        if not result.ok or result.data.get("code") != 0:
            return FeishuApiResult(False, data=result.data, error=self._error_text(result), status_code=result.status_code, endpoint=endpoint)
        return FeishuApiResult(True, data=result.data.get("data", {}), endpoint=endpoint)

    def _list_chats(self) -> FeishuApiResult:
        chats: list[dict[str, Any]] = []
        errors: list[str] = []
        list_endpoint = "https://open.feishu.cn/open-apis/im/v1/chats"
        list_params = {"page_size": "50", "user_id_type": "open_id", "sort_type": "ByCreateTimeAsc"}
        list_result = self._request("GET", list_endpoint + "?" + urllib.parse.urlencode(list_params))
        if list_result.ok and list_result.data.get("code") == 0:
            chats.extend(list_result.data.get("data", {}).get("items", []))
        else:
            errors.append(self._error_text(list_result))

        search_endpoint = "https://open.feishu.cn/open-apis/im/v1/chats/search"
        for keyword in ["运营", "财务", "销售", "刘芳羽", "刘晶", "尚丽娜", "石磊"]:
            params = {"page_size": "20", "user_id_type": "open_id", "query": keyword}
            result = self._request("GET", search_endpoint + "?" + urllib.parse.urlencode(params))
            if result.ok and result.data.get("code") == 0:
                chats.extend(result.data.get("data", {}).get("items", []))
            else:
                errors.append(f"{keyword}: {self._error_text(result)}")
        unique = {chat.get("chat_id"): chat for chat in chats if chat.get("chat_id")}
        if unique:
            return FeishuApiResult(True, data=list(unique.values()), endpoint=list_endpoint)
        return FeishuApiResult(False, data=[], error="; ".join(errors), status_code=400, endpoint=list_endpoint)

    def _list_chat_members(self, chats: list[dict[str, Any]]) -> FeishuApiResult:
        members: list[dict[str, Any]] = []
        errors: list[str] = []
        endpoint_template = "https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members"
        for chat in chats:
            chat_id = str(chat.get("chat_id") or "")
            if not chat_id:
                continue
            endpoint = endpoint_template.format(chat_id=urllib.parse.quote(chat_id))
            params = {"page_size": "100", "member_id_type": "user_id"}
            page_token = ""
            while True:
                query = dict(params)
                if page_token:
                    query["page_token"] = page_token
                result = self._request("GET", endpoint + "?" + urllib.parse.urlencode(query))
                if result.ok and result.data.get("code") == 0:
                    data = result.data.get("data", {})
                    for item in data.get("items", []):
                        if not isinstance(item, dict):
                            continue
                        user_id = str(item.get("member_id") or "")
                        member = {
                            "user_id": user_id,
                            "open_id": "",
                            "union_id": "",
                            "name": str(item.get("name") or ""),
                            "source_chat_id": chat_id,
                            "source_chat_name": str(chat.get("name") or ""),
                            "member_id_type": str(item.get("member_id_type") or ""),
                            "_source": "chat_member",
                        }
                        members.append(member)
                    if not data.get("has_more"):
                        break
                    page_token = str(data.get("page_token") or "")
                    if not page_token:
                        break
                else:
                    errors.append(f"{chat_id}: {self._error_text(result)}")
                    break
        unique: dict[tuple[str, str], dict[str, Any]] = {}
        for member in members:
            key = (str(member.get("user_id") or ""), str(member.get("source_chat_id") or ""))
            if key[0]:
                unique[key] = member
        if unique or not chats:
            return FeishuApiResult(True, data=list(unique.values()), endpoint=endpoint_template)
        return FeishuApiResult(False, data=[], error="; ".join(errors), status_code=400, endpoint=endpoint_template)

    def _list_approvals(self) -> FeishuApiResult:
        endpoint = "https://open.feishu.cn/open-apis/approval/v4/approvals"
        params = {"page_size": "100", "locale": "zh-CN"}
        result = self._request("GET", endpoint + "?" + urllib.parse.urlencode(params))
        if not result.ok or result.data.get("code") != 0:
            return FeishuApiResult(False, data=result.data, error=self._error_text(result), status_code=result.status_code, endpoint=endpoint)
        return FeishuApiResult(True, data=result.data.get("data", {}).get("items", []), endpoint=endpoint)

    def _apply_env_overrides(self, row: MappingRow, key: str) -> None:
        # Real-world IDs must come from Feishu APIs. Env overrides are intentionally disabled
        # during Feishu reality initialization to prevent virtual or guessed IDs.
        return

    def _apply_user_match(self, row: MappingRow, seed: dict[str, Any], users: list[dict[str, Any]]) -> None:
        if row.user_id and row.open_id:
            return
        match = self._find_by_terms(users, seed["match_terms"], ["name", "en_name", "nickname"])
        if not match:
            return
        if not row.user_id:
            row.user_id = str(match.get("user_id") or "")
            if row.user_id:
                row.source["user_id"] = "feishu_org_user_match"
        if not row.open_id:
            row.open_id = str(match.get("open_id") or "")
            if row.open_id:
                row.source["open_id"] = "feishu_org_user_match"

    def _apply_chat_match(self, row: MappingRow, seed: dict[str, Any], chats: list[dict[str, Any]]) -> None:
        if row.chat_id:
            return
        match = self._find_by_terms(chats, seed.get("chat_match_terms") or seed["match_terms"], ["name", "description"])
        if match:
            row.chat_id = str(match.get("chat_id") or "")
            if row.chat_id:
                row.source["chat_id"] = "feishu_chat_match"

    def _apply_approval_match(self, row: MappingRow, seed: dict[str, Any], approvals: list[dict[str, Any]]) -> None:
        if row.approval_code:
            return
        match = self._find_by_terms(approvals, seed["match_terms"], ["name", "role", "approval_name"])
        if match:
            row.approval_code = str(match.get("approval_code") or "")
            if row.approval_code:
                row.source["approval_code"] = "approval_match"

    def _default_approval_type(self, seed: dict[str, Any]) -> str:
        text = " ".join(str(item) for item in [seed.get("name"), seed.get("role"), *(seed.get("match_terms") or [])])
        if any(term in text for term in ["财务", "刘晶", "会计", "出纳", "finance"]):
            return "finance"
        if any(term in text for term in ["付款", "payment"]):
            return "payment"
        return "general"

    def _find_by_terms(self, items: list[dict[str, Any]], terms: list[str], fields: list[str]) -> dict[str, Any] | None:
        for item in items:
            haystack = " ".join(str(item.get(field) or "") for field in fields)
            if any(term and term in haystack for term in terms):
                return item
        return None

    def _find_mapping_row(self, rows: list[dict[str, Any]], to_role: str) -> dict[str, Any] | None:
        for row in rows:
            if to_role in {str(row.get("name") or ""), str(row.get("role") or "")}:
                return row
        for row in rows:
            if to_role and (to_role in str(row.get("name") or "") or to_role in str(row.get("role") or "")):
                return row
        return None

    def _users_from_scope(self, scope_data: dict[str, Any]) -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        for key in ["user_list", "users", "visible_users"]:
            value = scope_data.get(key)
            if isinstance(value, list):
                users.extend(value)
        return users

    def _user_ids_from_scope(self, scope_data: dict[str, Any]) -> list[str]:
        ids: list[str] = []
        for key in ["user_ids", "user_list", "users", "visible_users"]:
            value = scope_data.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        user_id = item.get("user_id")
                        if user_id:
                            ids.append(str(user_id))
                    elif item:
                        ids.append(str(item))
        return list(dict.fromkeys(ids))

    def _users_from_ids(self, user_ids: list[str]) -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        for user_id in user_ids:
            endpoint = f"https://open.feishu.cn/open-apis/contact/v3/users/{urllib.parse.quote(user_id)}"
            params = {"user_id_type": "user_id", "department_id_type": "department_id"}
            result = self._request("GET", endpoint + "?" + urllib.parse.urlencode(params))
            if result.ok and result.data.get("code") == 0:
                user = result.data.get("data", {}).get("user")
                if isinstance(user, dict):
                    users.append(user)
        return users

    def _department_refs_from_scope(self, scope_data: dict[str, Any]) -> list[tuple[str, str]]:
        refs: list[tuple[str, str]] = []
        for key in ["department_ids", "department_list", "departments", "visible_departments"]:
            value = scope_data.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        dept_id = item.get("department_id") or item.get("open_department_id")
                        if dept_id:
                            dept_type = "open_department_id" if str(dept_id).startswith("od-") else "department_id"
                            refs.append((str(dept_id), dept_type))
                    elif item:
                        dept_id = str(item)
                        dept_type = "open_department_id" if dept_id.startswith("od-") else "department_id"
                        refs.append((dept_id, dept_type))
        return list(dict.fromkeys(refs))

    def _expand_department_refs(self, roots: list[tuple[str, str]]) -> list[tuple[str, str]]:
        seen: set[tuple[str, str]] = set()
        queue = list(roots)
        expanded: list[tuple[str, str]] = []
        while queue:
            department_id, department_id_type = queue.pop(0)
            ref = (department_id, department_id_type)
            if ref in seen:
                continue
            seen.add(ref)
            expanded.append(ref)
            endpoint = f"https://open.feishu.cn/open-apis/contact/v3/departments/{urllib.parse.quote(department_id)}/children"
            params = {"department_id_type": department_id_type, "fetch_child": "false", "page_size": "50"}
            result = self._request("GET", endpoint + "?" + urllib.parse.urlencode(params))
            if not result.ok or result.data.get("code") != 0:
                continue
            for item in result.data.get("data", {}).get("items", []):
                if not isinstance(item, dict):
                    continue
                child_id = item.get("open_department_id") or item.get("department_id")
                if child_id:
                    child_type = "open_department_id" if str(child_id).startswith("od-") else "department_id"
                    queue.append((str(child_id), child_type))
        return expanded

    def _unique_users(self, users: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: dict[str, dict[str, Any]] = {}
        for user in users:
            if not isinstance(user, dict):
                continue
            key = str(user.get("user_id") or user.get("open_id") or user.get("union_id") or "")
            if not key:
                continue
            existing = unique.get(key, {})
            merged = {**existing, **{k: v for k, v in user.items() if v not in ("", None) and v != []}}
            unique[key] = merged
        return list(unique.values())

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
            parsed: Any
            try:
                parsed = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                parsed = payload
            return FeishuApiResult(False, data=parsed, error=str(exc), status_code=exc.code, endpoint=url)
        except Exception as exc:
            return FeishuApiResult(False, error=str(exc), endpoint=url)

    def _write_mapping(self, output: dict[str, Any]) -> None:
        json_path = self.mapping_root / "OMS_RealWorld_Mapping.json"
        csv_path = self.mapping_root / "OMS_RealWorld_Mapping.csv"
        json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["name", "user_id", "open_id", "chat_id", "approval_code", "approval_type", "role"])
            writer.writeheader()
            for row in output["rows"]:
                writer.writerow({key: row.get(key, "") for key in writer.fieldnames})

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
