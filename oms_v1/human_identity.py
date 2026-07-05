from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .operating_center_source import OPERATING_CENTER_PEOPLE, OPERATING_CENTER_VERSION
from .schemas import now_iso


HUMAN_IDENTITY_SCHEMA_VERSION = "oms.v1.human_identity_table"
IDENTITY_ENRICHMENT_SCHEMA_VERSION = "oms.v1.identity_enrichment_layer"


HUMAN_IDENTITY_ALIASES = {
    "boss": ["BOSS", "老板", "主理办", "主理人", "晓磊", "总裁"],
    "liujie": ["刘姐", "刘晶"],
    "june": ["六月", "刘芳羽"],
    "nana": ["娜娜", "丽娜", "尚丽娜"],
    "chenchangyi": ["陈晶辉"],
    "yuchun": ["子渝", "薛子渝"],
}


class HumanIdentityLayer:
    """Build the human identity table from real Feishu identity evidence."""

    def __init__(self, live_root: str | Path | None = None):
        self.live_root = Path(live_root or DEFAULT_LIVE_ROOT)
        self.identity_root = self.live_root / "human_identity"
        self.mapping_path = self.live_root / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
        self.snapshot_path = self.live_root / "realworld_mapping" / "feishu_object_snapshot.json"
        self.last_auth_path = self.live_root / "auth_audit" / "last_identity_exchange.json"
        self.enrichment_path = self.identity_root / "identity_enrichment_layer.json"

    def rebuild(self, *, apply_to_mapping: bool = True) -> dict[str, Any]:
        mapping = self._read_json(self.mapping_path)
        snapshot = self._read_json(self.snapshot_path)
        last_auth = self._read_json(self.last_auth_path)
        candidates = self._identity_candidates(snapshot, last_auth)
        rows = [self._identity_row(workspace_key, candidates, mapping) for workspace_key in OPERATING_CENTER_PEOPLE]
        enrichment = self._build_enrichment_layer(rows)
        output = {
            "schema_version": HUMAN_IDENTITY_SCHEMA_VERSION,
            "created_at": now_iso(),
            "source_of_truth": "FEISHU_ORG_USER base identity + OMS identity enrichment",
            "people_model_source": OPERATING_CENTER_VERSION,
            "policy": {
                "missing_user_fallback_allowed": False,
                "group_level_execution_allowed": False,
                "system_generated_identity_allowed": False,
                "user_id_required_for_execution": True,
                "metadata_missing_blocks_execution": False,
                "identity_incomplete_handling": "enrich_and_mark_confidence",
                "role_inference_requires_source": True,
            },
            "summary": {
                "required_identity_count": len(rows),
                "mapped_identity_count": sum(1 for row in rows if row["identity_status"] == "mapped"),
                "missing_identity_count": sum(1 for row in rows if row["identity_status"] != "mapped"),
                "inferred_role_mapping_count": sum(1 for row in rows if row["binding_confidence"] == "inferred"),
                "metadata_enriched_count": enrichment["summary"]["metadata_enriched_count"],
                "metadata_missing_count": enrichment["summary"]["metadata_missing_count"],
            },
            "identity_enrichment_layer": {
                "schema_version": enrichment["schema_version"],
                "path": str(self.enrichment_path),
                "summary": enrichment["summary"],
            },
            "rows": rows,
            "unassigned_feishu_candidates": self._unassigned_candidates(candidates, rows),
        }
        self._write_table(output, enrichment)
        if apply_to_mapping:
            self._apply_to_realworld_mapping(output, enrichment)
        return output

    def _identity_row(
        self,
        workspace_key: str,
        candidates: list[dict[str, Any]],
        mapping: dict[str, Any],
    ) -> dict[str, Any]:
        person = OPERATING_CENTER_PEOPLE[workspace_key]
        candidate = self._candidate_from_mapping(workspace_key, mapping, candidates)
        if not candidate:
            candidate = self._candidate_from_workspace_hint(workspace_key, candidates)
        if not candidate:
            candidate = self._candidate_from_alias(workspace_key, candidates)
        if not candidate:
            candidate = self._candidate_from_role_inference(workspace_key, candidates)

        if candidate:
            return {
                "workspace_key": workspace_key,
                "feishu_user_id": candidate.get("user_id", ""),
                "open_id": candidate.get("open_id", ""),
                "union_id": candidate.get("union_id", ""),
                "feishu_name": candidate.get("name", ""),
                "oms_user_id": workspace_key,
                "role": person["role"],
                "department": person["unit"],
                "execution_scope": "global_oversight" if workspace_key == "boss" else "own_workspace",
                "workspace_mapping": person["title"],
                "identity_status": "mapped",
                "metadata_status": "enriched",
                "binding_source": candidate.get("binding_source", candidate.get("source", "feishu_identity_evidence")),
                "binding_confidence": candidate.get("binding_confidence", "confirmed"),
                "evidence": candidate.get("evidence", {}),
            }

        return {
            "workspace_key": workspace_key,
            "feishu_user_id": "",
            "open_id": "",
            "union_id": "",
            "feishu_name": "",
            "oms_user_id": workspace_key,
            "role": person["role"],
            "department": person["unit"],
            "execution_scope": "global_oversight" if workspace_key == "boss" else "own_workspace",
            "workspace_mapping": person["title"],
            "identity_status": "missing_required_user_id",
            "metadata_status": "enriched",
            "binding_source": "not_available_from_feishu_identity_evidence",
            "binding_confidence": "missing",
            "evidence": {},
        }

    def _candidate_from_mapping(
        self,
        workspace_key: str,
        mapping: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        person = OPERATING_CENTER_PEOPLE[workspace_key]
        expected = {person["name"], person["role"]}
        if workspace_key == "boss":
            expected.add("BOSS")
        for row in mapping.get("rows") or []:
            if not isinstance(row, dict):
                continue
            row_names = {str(row.get("name") or ""), str(row.get("role") or "")}
            row_workspace = str(row.get("workspace_key") or row.get("oms_user_id") or "").strip()
            if not ((row_workspace and row_workspace == workspace_key) or (expected & row_names)) or not row.get("user_id"):
                continue
            candidate = self._candidate_by_user_id(str(row.get("user_id") or ""), candidates) or {}
            binding_source = str(row.get("identity_binding_source") or "feishu_realworld_mapping")
            binding_confidence = str(row.get("identity_binding_confidence") or "confirmed")
            row_source = row.get("source") if isinstance(row.get("source"), dict) else {}
            if row_source.get("user_id") == "human_identity_layer":
                inferred = self._candidate_from_role_inference(workspace_key, candidates)
                if inferred and inferred.get("user_id") == str(row.get("user_id") or ""):
                    binding_source = str(inferred.get("binding_source") or binding_source)
                    binding_confidence = str(inferred.get("binding_confidence") or binding_confidence)
            return {
                "user_id": str(row.get("user_id") or ""),
                "open_id": str(row.get("open_id") or candidate.get("open_id") or ""),
                "union_id": str(row.get("union_id") or candidate.get("union_id") or ""),
                "name": str(row.get("feishu_name") or candidate.get("name") or ""),
                "binding_source": binding_source,
                "binding_confidence": binding_confidence,
                "evidence": {"mapping_row": row},
            }
        return None

    def _candidate_from_workspace_hint(self, workspace_key: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        matches = [candidate for candidate in candidates if candidate.get("workspace_key") == workspace_key and candidate.get("user_id")]
        if len(matches) != 1:
            return None
        result = dict(matches[0])
        result["binding_source"] = result.get("binding_source") or result.get("source") or "feishu_workspace_hint"
        result["binding_confidence"] = result.get("binding_confidence") or "confirmed"
        return result

    def _candidate_from_alias(self, workspace_key: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        aliases = HUMAN_IDENTITY_ALIASES.get(workspace_key, [])
        for candidate in candidates:
            name = str(candidate.get("name") or "")
            if any(alias and alias in name for alias in aliases):
                result = dict(candidate)
                result["binding_source"] = candidate.get("source", "feishu_name_match")
                result["binding_confidence"] = "confirmed"
                return result
        return None

    def _candidate_from_role_inference(self, workspace_key: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if workspace_key != "huanhuan":
            return None
        sales_members = [
            candidate
            for candidate in candidates
            if candidate.get("source_chat_name") == "销售群"
            and not self._candidate_from_alias("boss", [candidate])
            and not self._candidate_from_alias("yuchun", [candidate])
        ]
        if len(sales_members) != 1:
            return None
        result = dict(sales_members[0])
        result["binding_source"] = "feishu_chat_member_role_inference:sales_group_remaining_member"
        result["binding_confidence"] = "inferred"
        return result

    def _identity_candidates(self, snapshot: dict[str, Any], last_auth: dict[str, Any]) -> list[dict[str, Any]]:
        users_by_id: dict[str, dict[str, Any]] = {}
        for user in snapshot.get("users") or snapshot.get("org_users") or []:
            if not isinstance(user, dict) or not user.get("user_id"):
                continue
            users_by_id[str(user["user_id"])] = dict(user)

        candidates: dict[str, dict[str, Any]] = {}
        for user_id, user in users_by_id.items():
            candidates[user_id] = {
                "user_id": user_id,
                "open_id": str(user.get("open_id") or ""),
                "union_id": str(user.get("union_id") or ""),
                "name": str(user.get("name") or ""),
                "source": "feishu_org_user",
                "evidence": {"user": user},
            }

        identity = last_auth.get("identity") if isinstance(last_auth.get("identity"), dict) else {}
        if identity.get("user_id"):
            user_id = str(identity.get("user_id") or "")
            candidate = candidates.get(user_id, {})
            candidates[user_id] = {
                **candidate,
                "user_id": user_id,
                "open_id": str(identity.get("open_id") or candidate.get("open_id") or ""),
                "union_id": str(identity.get("union_id") or candidate.get("union_id") or ""),
                "name": candidate.get("name") or "authenticated_feishu_user",
                "workspace_key": str(identity.get("workspace_key") or candidate.get("workspace_key") or ""),
                "source": "feishu_webapp_sso",
                "binding_source": "feishu_webapp_sso",
                "binding_confidence": "confirmed",
                "evidence": {"last_identity_exchange": identity},
            }

        for member in snapshot.get("chat_members_as_users") or []:
            if not isinstance(member, dict) or not member.get("user_id"):
                continue
            user_id = str(member.get("user_id") or "")
            candidate = candidates.get(user_id, {})
            candidates[user_id] = {
                **candidate,
                "user_id": user_id,
                "open_id": str(member.get("open_id") or candidate.get("open_id") or ""),
                "union_id": str(member.get("union_id") or candidate.get("union_id") or ""),
                "name": str(member.get("name") or candidate.get("name") or ""),
                "source": "feishu_chat_member_identity",
                "source_chat_id": str(member.get("source_chat_id") or ""),
                "source_chat_name": str(member.get("source_chat_name") or ""),
                "evidence": {"chat_member": member, "org_user": users_by_id.get(user_id, {})},
            }
        return list(candidates.values())

    def _build_enrichment_layer(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        enriched_rows = [self._enriched_row(row) for row in rows]
        return {
            "schema_version": IDENTITY_ENRICHMENT_SCHEMA_VERSION,
            "created_at": now_iso(),
            "source_priority": [
                "feishu_org_api_base_identity",
                "feishu_chat_approval_task_context",
                "excel_business_history_context",
                "oms_internal_mapping_table",
                "operating_center_v1_1_business_metadata",
            ],
            "policy": {
                "user_id_required_for_execution": True,
                "name_role_department_required_for_execution": False,
                "missing_metadata_handling": "soft_label_and_continue",
                "missing_user_id_handling": "pending_identity_binding",
                "system_generated_user_id_allowed": False,
                "fallback_identity_allowed": False,
            },
            "summary": {
                "required_identity_count": len(enriched_rows),
                "execution_ready_count": sum(1 for row in enriched_rows if row["execution_status"] == "ready"),
                "execution_pending_user_id_count": sum(1 for row in enriched_rows if row["execution_status"] != "ready"),
                "metadata_enriched_count": sum(1 for row in enriched_rows if row["metadata_status"] == "enriched"),
                "metadata_missing_count": sum(1 for row in enriched_rows if row["metadata_status"] != "enriched"),
                "confirmed_identity_count": sum(1 for row in enriched_rows if row["identity_confidence"] == "confirmed"),
                "inferred_identity_count": sum(1 for row in enriched_rows if row["identity_confidence"] == "inferred"),
            },
            "rows": enriched_rows,
        }

    def _enriched_row(self, row: dict[str, Any]) -> dict[str, Any]:
        workspace_key = row["workspace_key"]
        person = OPERATING_CENTER_PEOPLE[workspace_key]
        user_id = str(row.get("feishu_user_id") or "")
        return {
            "workspace_key": workspace_key,
            "base_identity": {
                "feishu_user_id": user_id,
                "open_id": str(row.get("open_id") or ""),
                "union_id": str(row.get("union_id") or ""),
                "feishu_name": str(row.get("feishu_name") or ""),
                "base_source": row.get("binding_source") or "",
            },
            "enriched_identity": {
                "oms_user_id": workspace_key,
                "display_name": person["name"],
                "role": person["role"],
                "department": person["unit"],
                "workspace": person["title"],
                "execution_scope": row["execution_scope"],
            },
            "sources": {
                "user_id": row.get("binding_source") if user_id else "missing_feishu_base_identity",
                "feishu_name": row.get("binding_source") if row.get("feishu_name") else "",
                "display_name": "operating_center_v1_1_business_metadata",
                "role": "operating_center_v1_1_business_metadata",
                "department": "operating_center_v1_1_business_metadata",
                "workspace": "operating_center_v1_1_business_metadata",
            },
            "identity_status": "mapped" if user_id else "missing_required_user_id",
            "execution_status": "ready" if user_id else "pending_identity_binding",
            "metadata_status": "enriched" if person["name"] and person["role"] and person["unit"] and person["title"] else "metadata_missing",
            "identity_confidence": row.get("binding_confidence") or ("confirmed" if user_id else "missing"),
            "metadata_confidence": "confirmed_from_operating_center_v1_1",
            "evidence": row.get("evidence") or {},
        }

    def _unassigned_candidates(self, candidates: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        assigned = {row["feishu_user_id"] for row in rows if row.get("feishu_user_id")}
        return [
            {
                "user_id": candidate.get("user_id", ""),
                "open_id": candidate.get("open_id", ""),
                "union_id": candidate.get("union_id", ""),
                "name": candidate.get("name", ""),
                "source": candidate.get("source", ""),
                "source_chat_name": candidate.get("source_chat_name", ""),
            }
            for candidate in candidates
            if candidate.get("user_id") and candidate.get("user_id") not in assigned
        ]

    def _candidate_by_user_id(self, user_id: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        for candidate in candidates:
            if candidate.get("user_id") == user_id:
                return candidate
        return None

    def _apply_to_realworld_mapping(self, table: dict[str, Any], enrichment: dict[str, Any]) -> None:
        mapping = self._read_json(self.mapping_path)
        if not mapping:
            return
        rows = mapping.get("rows")
        if not isinstance(rows, list):
            return
        by_workspace = {row["workspace_key"]: row for row in table.get("rows") or []}
        enriched_by_workspace = {row["workspace_key"]: row for row in enrichment.get("rows") or []}
        for mapping_row in rows:
            workspace_key = self._workspace_key_for_mapping_row(mapping_row)
            identity = by_workspace.get(workspace_key)
            enriched = enriched_by_workspace.get(workspace_key)
            if enriched:
                mapping_row["identity_metadata_status"] = enriched["metadata_status"]
                mapping_row["identity_execution_status"] = enriched["execution_status"]
                mapping_row["identity_metadata_confidence"] = enriched["metadata_confidence"]
                mapping_row["workspace_key"] = workspace_key
                source = mapping_row.get("source") if isinstance(mapping_row.get("source"), dict) else {}
                source["metadata"] = "identity_enrichment_layer"
                mapping_row["source"] = source
            if not identity or identity["identity_status"] != "mapped":
                continue
            mapping_row["user_id"] = identity["feishu_user_id"]
            mapping_row["open_id"] = identity["open_id"]
            mapping_row["union_id"] = identity["union_id"]
            mapping_row["feishu_name"] = identity["feishu_name"]
            mapping_row["identity_status"] = identity["identity_status"]
            mapping_row["identity_binding_source"] = identity["binding_source"]
            mapping_row["identity_binding_confidence"] = identity["binding_confidence"]
            source = mapping_row.get("source") if isinstance(mapping_row.get("source"), dict) else {}
            source["user_id"] = "human_identity_layer"
            source["human_identity"] = identity["binding_source"]
            mapping_row["source"] = source
        mapping["human_identity_table"] = {
            "path": str(self.identity_root / "human_identity_table.json"),
            "mapped_identity_count": table["summary"]["mapped_identity_count"],
            "missing_identity_count": table["summary"]["missing_identity_count"],
        }
        mapping["identity_enrichment_layer"] = {
            "path": str(self.enrichment_path),
            "execution_ready_count": enrichment["summary"]["execution_ready_count"],
            "execution_pending_user_id_count": enrichment["summary"]["execution_pending_user_id_count"],
            "metadata_enriched_count": enrichment["summary"]["metadata_enriched_count"],
            "metadata_missing_count": enrichment["summary"]["metadata_missing_count"],
        }
        self.mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    def _workspace_key_for_mapping_row(self, row: dict[str, Any]) -> str:
        row_workspace = str(row.get("workspace_key") or row.get("oms_user_id") or "").strip()
        if row_workspace in OPERATING_CENTER_PEOPLE:
            return row_workspace
        row_names = {str(row.get("name") or ""), str(row.get("role") or "")}
        for workspace_key, person in OPERATING_CENTER_PEOPLE.items():
            candidates = {person["name"], person["role"]}
            if workspace_key == "boss":
                candidates.add("BOSS")
            if candidates & row_names:
                return workspace_key
        return ""

    def _read_json(self, path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_table(self, output: dict[str, Any], enrichment: dict[str, Any]) -> None:
        self.identity_root.mkdir(parents=True, exist_ok=True)
        (self.identity_root / "human_identity_table.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.enrichment_path.write_text(
            json.dumps(enrichment, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
