from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .audit_log import AuditEngine
from .business_execution_closure import BusinessExecutionClosureLayer
from .feishu_auth import FeishuIdentityAuthenticator
from .feishu_mapping import DEFAULT_ENV_PATH
from .historical_view import HistoricalDataViewLayer
from .home_ui import OMSHomeUI
from .master_data import OMSMasterData
from .operating_center_source import workspace_key_for_feishu_identity
from .auth_session import AuthSessionSigner
from .current_operations import CurrentOperationsService
from .operational_core import PERSONAL_WORKSPACES
from .production_data_adapter import ProductionDataAdapter
from .schemas import now_iso
from .truth_source import TruthSourceStore, default_truth_root


REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_APP_ROOT = REPO_ROOT / "oms_app"
LOCAL_LIVE_RUNTIME_ROOT = Path(os.getenv("OMS_LIVE_ROOT") or REPO_ROOT / "live_runtime")
LOCAL_OPERATING_ROOT = Path(os.getenv("OMS_OPERATING_ROOT") or LOCAL_LIVE_RUNTIME_ROOT / "operational_core")
LOCAL_TRUTH_SOURCE_ROOT = default_truth_root(LOCAL_LIVE_RUNTIME_ROOT)
CONTRACT_VERSION = "oms.contract.v1.0"
LOCAL_OWNER_USER_ID = os.getenv("OMS_LOCAL_OWNER_USER_ID", "a2c82cb4")
SOURCE_EVIDENCE_DETAIL_LIMIT = 500
LIST_ENDPOINTS = {
    "/api/oms/sales": "sales",
    "/api/oms/contracts": "contracts",
    "/api/oms/finance": "finance",
    "/api/oms/rooms": "rooms",
    "/api/oms/room-resources": "room_resources",
    "/api/oms/stays": "stays",
}


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
    historical_view = HistoricalDataViewLayer(live_root=LOCAL_LIVE_RUNTIME_ROOT, operating_root=LOCAL_OPERATING_ROOT)
    execution_closure = BusinessExecutionClosureLayer(live_root=LOCAL_LIVE_RUNTIME_ROOT, operating_root=LOCAL_OPERATING_ROOT)
    audit_root = LOCAL_LIVE_RUNTIME_ROOT / "audit_center"
    local_owner_user_id = LOCAL_OWNER_USER_ID
    local_owner_access_enabled = os.getenv("OMS_LOCAL_OWNER_ACCESS_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
    session_signer = AuthSessionSigner.from_environment()
    current_operations = CurrentOperationsService(LOCAL_LIVE_RUNTIME_ROOT)
    runtime_source_policy = {
        "mode": "single_source_of_truth",
        "type": "OMS_TRUTH_SOURCE",
        "truth_root": str(LOCAL_TRUTH_SOURCE_ROOT),
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
        "http://127.0.0.1:8787",
        "http://localhost:8787",
        "http://127.0.0.1:8790",
        "http://localhost:8790",
        "null",
    }

    def do_OPTIONS(self) -> None:
        self._send_contract(
            entity="task",
            response_id="api.options",
            contract_status="ready",
            payload={"allowed_methods": ["GET", "POST", "OPTIONS"]},
        )

    def do_GET(self) -> None:
        raw_path = self.path.split("?", 1)[0]
        path = raw_path.rstrip("/") or "/"
        if self._send_static_asset(path):
            return
        if path in {"/api/oms/production", "/api/oms/production/sales", "/api/oms/production/finance", "/api/oms/production/rooms", "/api/oms/production/contracts"}:
            dataset = self._production_dataset_from_path(path) or self._query_value("dataset")
            self._send_production_dataset(dataset)
            return
        if path in {"/api/oms/history", "/history"}:
            self._send_history(self._query_payload())
            return
        if path in LIST_ENDPOINTS:
            self._send_list_endpoint(path, self._query_payload())
            return
        if path == "/api/oms/current/summary":
            self._send_current_summary()
            return
        if path != "/api/oms/home":
            self._send_contract(
                entity="task",
                response_id="api.not_found",
                contract_status="not_found",
                payload={"path": path},
                http_status=404,
                error="not_found",
            )
            return
        user_id = self._query_value("user_id")
        self._send_home(user_id)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0].rstrip("/")
        if path not in {
            "/api/feishu/identity",
            "/api/oms/home",
            "/api/oms/history",
            "/api/oms/production",
            "/api/oms/production/sales",
            "/api/oms/production/finance",
            "/api/oms/production/rooms",
            "/api/oms/production/contracts",
            "/api/oms/execute",
            "/api/oms/local-owner-access",
            "/history",
            "/api/oms/current/finance/record",
            "/api/oms/current/finance/review",
            "/api/oms/current/rooms/publish",
            "/api/oms/current/rooms/update",
            "/api/oms/current/stays/publish",
            "/api/oms/current/stays/check-in",
            "/api/oms/current/stays/check-out",
            "/api/oms/current/stays/verify",
        } and path not in LIST_ENDPOINTS:
            self._send_contract(
                entity="task",
                response_id="api.not_found",
                contract_status="not_found",
                payload={"path": path},
                http_status=404,
                error="not_found",
            )
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_contract(
                entity="task",
                response_id="api.invalid_json",
                contract_status="invalid_json",
                payload={"path": path},
                http_status=400,
                error="invalid_json",
            )
            return
        if path in {"/api/oms/history", "/history"}:
            self._send_history(payload)
            return
        if path in {"/api/oms/production", "/api/oms/production/sales", "/api/oms/production/finance", "/api/oms/production/rooms", "/api/oms/production/contracts"}:
            dataset = self._production_dataset_from_path(path) or str(payload.get("dataset") or "")
            self._send_production_dataset(dataset)
            return
        if path.startswith("/api/oms/current/"):
            self._send_current_operation(path, payload)
            return
        if path in LIST_ENDPOINTS:
            self._send_list_endpoint(path, payload)
            return
        if path == "/api/oms/execute":
            self._send_execute(payload)
            return
        if path == "/api/oms/local-owner-access":
            self._send_local_owner_access(payload)
            return
        if path == "/api/oms/home":
            self._send_home(str(payload.get("user_id") or ""))
            return

        result = self.authenticator.authenticate_code(str(payload.get("code") or ""))
        self._write_audit(result)
        if not result.ok:
            self._send_contract(
                entity="task",
                response_id="feishu.identity.exchange",
                contract_status="blocked",
                payload=result.data if isinstance(result.data, dict) else {"data": result.data},
                http_status=401,
                error=result.error,
            )
            return
        identity_payload = dict(result.data) if isinstance(result.data, dict) else {"data": result.data}
        identity_payload.update(self._issue_session(identity_payload))
        self._send_contract(
            entity="task",
            response_id="feishu.identity.exchange",
            contract_status="ready",
            payload=identity_payload,
        )

    def _send_home(self, user_id: str) -> None:
        if not hasattr(self.home_ui, "_resolve_identity"):
            home = self.home_ui.build_home_from_saved_state(user_id=user_id)
            if home.get("home_type") == "identity_binding_error":
                self._send_contract(
                    entity="task",
                    response_id="oms.home",
                    contract_status="identity_binding_required",
                    payload=home,
                    http_status=401,
                    error="identity_binding_required",
                )
                return
            home = self._enforce_local_runtime_source(home)
            self._send_contract(
                entity="task",
                response_id="oms.home",
                contract_status="ready",
                payload=self._compact_home_payload(home),
            )
            return
        identity = self.home_ui._resolve_identity(user_id, None)
        if identity.get("binding_status") == "error":
            home = self.home_ui._identity_binding_error(identity)
            self._send_contract(
                entity="task",
                response_id="oms.home",
                contract_status="identity_binding_required",
                payload=home,
                http_status=401,
                error="identity_binding_required",
            )
            return
        self._send_contract(
            entity="task",
            response_id="oms.home",
            contract_status="ready",
            payload=self._build_production_home_payload(identity),
        )

    def _build_production_home_payload(self, identity: dict[str, str]) -> dict[str, Any]:
        identity = self._canonical_display_identity(identity)
        truth_store = TruthSourceStore(LOCAL_LIVE_RUNTIME_ROOT, LOCAL_OPERATING_ROOT, truth_root=LOCAL_TRUTH_SOURCE_ROOT)
        adapter = ProductionDataAdapter(
            truth_store,
            operational_baseline_root=LOCAL_LIVE_RUNTIME_ROOT / "operational_baseline",
        )
        sales_records = adapter.sales_records()
        finance_records = adapter.finance_records()
        financial_events = adapter.financial_event_records()
        room_records = adapter.room_records()
        stay_records = adapter.stay_records()
        resident_records = adapter.resident_records()
        caregiver_records = adapter.caregiver_records()
        sales_metrics = adapter.sales_metrics()
        finance_metrics = adapter.finance_metrics()
        data_quality = adapter.data_quality_summary()
        operating_mode = adapter.operating_mode()
        truth_summary = truth_store.summary()
        source_counts = {
            "resident_data": len(resident_records),
            "room_status_data": len(room_records),
            "sales_contract_data": len(sales_records),
            "finance_data": len(finance_records),
            "financial_events": len(financial_events),
            "stay_records": len(stay_records),
            "service_data": len(caregiver_records),
            "current_user_visible_data": len(financial_events) if identity.get("workspace_key") == "boss" else 0,
            "visible_limit": 500,
        }
        business_schema = {
            "schema_version": "oms.business.v1",
            "semantic_status": {
                "pending_work_items": 0,
                "risk_items": 0 if data_quality.get("snapshot_status") == "PASS" else 1,
                "data_quality_status": data_quality.get("snapshot_status"),
            },
            "resident_flow_schema": {
                "resident_count": len(resident_records),
                "active_stays": len(resident_records),
                "room_status_records": len(room_records),
            },
            "finance_schema": {
                "income": finance_metrics.get("income", 0),
                "receivable": finance_metrics.get("receivable", 0),
                "collected": finance_metrics.get("collected", 0),
                "expenses": finance_metrics.get("expenses", 0),
                "pending_payment_amount": finance_metrics.get("pending_payment_amount", 0),
                "profit": finance_metrics.get("profit", 0),
                "event_records": len(financial_events),
                "payment_records": len(finance_records),
            },
            "sales_schema": {
                "signed_customers": sales_metrics.get("signed_customers", 0),
                "contracts": sales_metrics.get("contracts", 0),
                "sales_results": sales_metrics.get("sales_results", 0),
                "sales_amount": sales_metrics.get("sales_amount", 0),
            },
            "service_schema": {
                "in_service": len(caregiver_records),
                "data_status": "available" if caregiver_records else "missing_structured_production_data",
                "message": "" if caregiver_records else "暂无结构化生产数据",
            },
        }
        business_dashboard = {
            "title": "当前经营",
            "source": "OMS_TRUTH_SOURCE",
            "source_of_truth": str(LOCAL_TRUTH_SOURCE_ROOT),
            "runtime_source": dict(self.runtime_source_policy),
            "metrics": {
                "resident_count": len(resident_records),
                "room_status_records": len(room_records),
                "sales_contracts": len(sales_records),
                "finance_records": len(finance_records),
                "financial_events": len(financial_events),
                "caregiver_records": len(caregiver_records),
                "today_todos": 0,
                "risk_alerts": 0 if data_quality.get("snapshot_status") == "PASS" else 1,
            },
            "business_schema": business_schema,
            "data_quality": data_quality,
            "operating_mode": operating_mode,
            "truth_source": {
                "schema_version": truth_summary.get("schema_version"),
                "mode": truth_summary.get("mode"),
                "counts": truth_summary.get("counts") or {},
            },
            "production_adapters": {
                "sales_adapter": {"adapter_id": "sales_adapter_v1", "records": len(sales_records)},
                "finance_adapter": {
                    "adapter_id": "finance_adapter_v1",
                    "records": len(finance_records),
                    "financial_events": len(financial_events),
                },
                "room_adapter": {"adapter_id": "room_adapter_v1", "records": len(room_records)},
                "stay_adapter": {
                    "adapter_id": "stay_adapter_v1",
                    "records": len(stay_records),
                    "resident_records": len(resident_records),
                },
                "caregiver_adapter": {
                    "adapter_id": "caregiver_adapter_v1",
                    "records": len(caregiver_records),
                    "data_status": "available" if caregiver_records else "missing_structured_production_data",
                    "message": "" if caregiver_records else "暂无结构化生产数据",
                },
            },
            "source_evidence_available_data": {
                "policy": "counts_only_home_summary",
                "counts": source_counts,
                "resident_data_total_count": len(resident_records),
                "room_status_data_total_count": len(room_records),
                "sales_contract_data_total_count": len(sales_records),
                "finance_data_total_count": len(finance_records),
                "financial_events_total_count": len(financial_events),
                "caregiver_message": "" if caregiver_records else "暂无结构化生产数据",
            },
            "risk_summary": {
                "risk_alerts": 0 if data_quality.get("snapshot_status") == "PASS" else 1,
                "today_todos": 0,
                "data_quality_status": data_quality.get("snapshot_status"),
            },
            "data_updated_at": self._home_data_updated_at(truth_summary),
        }
        sections = {
            "my_todos": {
                "title": "我的待办",
                "count": 0,
                "total_count": 0,
                "items": [],
                "items_endpoint": "/api/oms/home",
                "empty_text": "暂无待办",
            },
            "my_tasks": {
                "title": "我的任务",
                "count": 0,
                "total_count": 0,
                "items": [],
                "items_endpoint": "/api/oms/home",
                "empty_text": "暂无任务",
            },
            "my_approvals": {
                "title": "我的审批",
                "count": 0,
                "total_count": 0,
                "items": [],
                "items_endpoint": "/api/oms/home",
                "empty_text": "暂无审批",
            },
            "operations": {
                "title": "运营中心",
                "count": len(room_records),
                "total_count": len(room_records),
                "items": [],
                "items_endpoint": "/api/oms/rooms",
                "empty_text": "",
            },
            "sales": {
                "title": "销售中心",
                "count": len(sales_records),
                "total_count": len(sales_records),
                "items": [],
                "items_endpoint": "/api/oms/sales",
                "empty_text": "",
            },
            "finance": {
                "title": "财务中心",
                "count": len(finance_records),
                "total_count": len(finance_records),
                "items": [],
                "items_endpoint": "/api/oms/finance",
                "empty_text": "",
            },
        }
        payload = {
            "schema_version": "oms.v1.home",
            "home_type": "boss_master_control_interface"
            if identity.get("workspace_key") == "boss"
            else "user_centric_operating_interface",
            "entry": "master_control_dashboard" if identity.get("workspace_key") == "boss" else "personal_workspace",
            "opened_at": now_iso(),
            "current_user": {
                "user_id": identity.get("user_id"),
                "workspace_key": identity.get("workspace_key"),
                "name": identity.get("name"),
                "role": identity.get("role"),
                "role_code": identity.get("role_code"),
                "emp_id": identity.get("emp_id"),
                "home_title": identity.get("title"),
            },
            "home_title": identity.get("title"),
            "runtime_source": dict(self.runtime_source_policy),
            "sync_status": {
                "title": "production_truth_source",
                "state": "ready",
                "pending_count": 0,
                "failed_count": 0,
            },
            "decision_assist": {"title": "今日关注", "messages": []},
            "bottom_tabs": self.home_ui._bottom_tabs(identity.get("workspace_key", "")),
            "payload_policy": "home_summary_only",
            "detail_policy": "details_loaded_from_paginated_endpoints",
            "center_entries": self._center_entries(),
            "sections": sections,
            "business_dashboard": business_dashboard,
            "master_control": None,
        }
        if identity.get("workspace_key") == "boss":
            payload["master_control"] = {
                "schema_version": "oms.v1.master_control",
                "entry_type": "master_control_dashboard",
                "control_user": payload["current_user"],
                "payload_policy": "home_summary_only",
                "business_dashboard": business_dashboard,
            }
        return payload

    def _canonical_display_identity(self, identity: dict[str, str]) -> dict[str, str]:
        canonical = dict(identity)
        workspace_key = str(canonical.get("workspace_key") or "")
        workspace = PERSONAL_WORKSPACES.get(workspace_key) or {}
        user_id = str(canonical.get("user_id") or "")
        employee = None
        try:
            employee = next(
                (item for item in OMSMasterData().active_employees() if item.user_id == user_id),
                None,
            )
        except (OSError, ValueError, KeyError):
            employee = None
        if employee is not None:
            canonical.update(
                {
                    "name": employee.feishu_name or employee.name,
                    "emp_id": employee.emp,
                    "role_code": employee.role_code,
                }
            )
        canonical["name"] = str(canonical.get("name") or workspace.get("name") or "")
        canonical["role"] = str(workspace.get("unit") or workspace.get("role") or canonical.get("role") or "")
        canonical["title"] = str(workspace.get("title") or canonical.get("title") or "")
        return canonical

    def _send_list_endpoint(self, path: str, payload: dict[str, Any]) -> None:
        domain = LIST_ENDPOINTS[path]
        records = self._records_for_endpoint(domain)
        page_payload = self._paginate_records(domain, records, payload)
        self._send_contract(
            entity=self._entity_for_endpoint(domain),
            response_id=f"oms.{domain}",
            contract_status="ready",
            payload=page_payload,
        )

    def _records_for_endpoint(self, domain: str) -> list[dict[str, Any]]:
        adapter = ProductionDataAdapter(
            TruthSourceStore(LOCAL_LIVE_RUNTIME_ROOT, LOCAL_OPERATING_ROOT, truth_root=LOCAL_TRUTH_SOURCE_ROOT),
            operational_baseline_root=LOCAL_LIVE_RUNTIME_ROOT / "operational_baseline",
        )
        if domain in {"sales", "contracts"}:
            return adapter.sales_records()
        if domain == "finance":
            return adapter.financial_event_records()
        if domain == "rooms":
            return adapter.room_records()
        if domain == "room_resources":
            store = TruthSourceStore(LOCAL_LIVE_RUNTIME_ROOT, LOCAL_OPERATING_ROOT, truth_root=LOCAL_TRUTH_SOURCE_ROOT)
            resources = store.read_entities().get("rooms") or []
            return [
                {
                    "room_id": str(item.get("room_id") or item.get("room_number") or item.get("room_no") or item.get("name") or ""),
                    "room_number": str(item.get("room_number") or item.get("room_no") or item.get("room_id") or item.get("name") or ""),
                    "room_type": str(item.get("room_type") or item.get("type") or ""),
                    "source": "OMS_ROOM_MASTER_DATA",
                }
                for item in resources
                if isinstance(item, dict)
            ]
        if domain == "stays":
            return adapter.stay_records()
        return []

    def _entity_for_endpoint(self, domain: str) -> str:
        return {
            "sales": "sales",
            "contracts": "sales",
            "finance": "finance",
            "rooms": "room",
            "room_resources": "room",
            "stays": "room",
        }.get(domain, "task")

    def _paginate_records(self, domain: str, records: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
        try:
            page = max(1, int(payload.get("page") or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(payload.get("page_size") or 50)
        except (TypeError, ValueError):
            page_size = 50
        page_size = min(max(page_size, 1), 500)
        include_trace = str(payload.get("include_trace") or "").lower() in {"1", "true", "yes"}
        keyword = str(payload.get("keyword") or "").strip().lower()
        status = str(payload.get("status") or "").strip().lower()
        record_id = str(payload.get("record_id") or payload.get("id") or "").strip()
        start_date = self._normalize_date(payload.get("start_date") or payload.get("date_from") or "")
        end_date = self._normalize_date(payload.get("end_date") or payload.get("date_to") or "")

        filtered = []
        for record in records:
            if record_id and record_id not in {
                str(record.get("record_id") or ""),
                str(record.get("domain_id") or ""),
                str(record.get("work_item_id") or ""),
                str(record.get("contract_id") or ""),
                str(record.get("tx_id") or ""),
                str(record.get("room_id") or ""),
                str(record.get("stay_id") or ""),
            }:
                continue
            if keyword and keyword not in json.dumps(record, ensure_ascii=False).lower():
                continue
            record_status = str(record.get("status") or record.get("payment_status") or record.get("room_status") or "").lower()
            if status and status not in record_status:
                continue
            record_date = self._record_date(record)
            if start_date and record_date and record_date < start_date:
                continue
            if end_date and record_date and record_date > end_date:
                continue
            filtered.append(record)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        page_records = filtered[start:end]
        trace_allowed = include_trace or bool(record_id)
        return {
            "schema_version": "oms.v1.paginated_query",
            "domain": domain,
            "page": page,
            "page_size": page_size,
            "total": total,
            "returned": len(page_records),
            "filters": {
                "keyword": keyword,
                "status": status,
                "start_date": start_date,
                "end_date": end_date,
                "record_id": record_id,
            },
            "records": [self._public_record(record, include_trace=trace_allowed) for record in page_records],
            "trace_policy": "trace_loaded_on_demand" if not trace_allowed else "trace_included_for_detail_request",
            "source": "OMS_TRUTH_SOURCE",
            "generated_at": now_iso(),
        }

    def _public_record(self, record: dict[str, Any], *, include_trace: bool) -> dict[str, Any]:
        if include_trace:
            return dict(record)
        blocked_keys = {
            "source_evidence",
            "trace_chain",
            "event_chain",
            "raw_row",
            "normalized",
            "source_file",
            "row_id",
            "row_number",
            "source_version",
            "occupancy_markers",
        }
        public = {key: value for key, value in record.items() if key not in blocked_keys}
        public["trace_available"] = bool(record.get("source_evidence") or record.get("trace_chain"))
        return public

    def _record_date(self, record: dict[str, Any]) -> str:
        for key in ("occurred_at", "tx_date", "checkin_date", "planned_checkin_date", "checkout_date", "current_date_basis"):
            normalized = self._normalize_date(record.get(key))
            if normalized:
                return normalized
        return ""

    def _normalize_date(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        parts = [part for part in re.split(r"\D+", text) if part]
        if len(parts) >= 3:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            if year < 100:
                year += 2000
            return f"{year:04d}-{month:02d}-{day:02d}"
        return ""

    def _send_history(self, payload: dict[str, Any]) -> None:
        try:
            limit = int(payload.get("limit") or 200)
        except (TypeError, ValueError):
            limit = 200
        history = self.historical_view.build_history_view(
            date=str(payload.get("date") or "") or None,
            start_date=str(payload.get("start_date") or "") or None,
            end_date=str(payload.get("end_date") or "") or None,
            workspace_key=str(payload.get("workspace_key") or "") or None,
            event_type=str(payload.get("event_type") or "") or None,
            limit=limit,
        )
        history["runtime_source"] = dict(self.runtime_source_policy)
        self._send_contract(
            entity="task",
            response_id="oms.history",
            contract_status="ready",
            payload=self._compact_history_payload(history),
        )

    def _send_production_dataset(self, dataset: str) -> None:
        try:
            adapter = ProductionDataAdapter(
                TruthSourceStore(
                    LOCAL_LIVE_RUNTIME_ROOT,
                    LOCAL_OPERATING_ROOT,
                    truth_root=LOCAL_TRUTH_SOURCE_ROOT,
                )
            )
            payload = adapter.production_page_dataset(dataset)
        except ValueError as error:
            self._send_contract(
                entity="task",
                response_id="oms.production",
                contract_status="not_found",
                payload={"dataset": dataset, "reason": str(error)},
                http_status=404,
                error="production_dataset_not_found",
            )
            return
        payload["runtime_source"] = dict(self.runtime_source_policy)
        self._send_contract(
            entity="task",
            response_id=f"oms.production.{payload.get('dataset')}",
            contract_status="ready",
            payload=payload,
        )

    def _production_dataset_from_path(self, path: str) -> str:
        prefix = "/api/oms/production/"
        if path.startswith(prefix):
            return path[len(prefix):]
        return ""

    def _send_execute(self, payload: dict[str, Any]) -> None:
        result = self.execution_closure.execute_action(payload)
        status = str(result.get("status") or "blocked")
        self._send_contract(
            entity=str((result.get("business_command") or {}).get("entity") or "task"),
            response_id="oms.execute",
            contract_status="ready" if status == "completed" else "blocked",
            payload=result,
            http_status=200,
            error=str(result.get("blocking_reason") or "") or None,
        )

    def _send_local_owner_access(self, payload: dict[str, Any]) -> None:
        reason = str(payload.get("reason") or "local_owner_access_recovery")
        request_audit = self._write_login_recovery_audit(
            action="login.recovery.request",
            result="requested",
            reason=reason,
            metadata={"client": self.client_address[0] if self.client_address else "", "href": str(payload.get("href") or "")},
        )
        if not self.local_owner_access_enabled:
            self._write_login_recovery_audit(
                action="login.recovery.failed",
                result="blocked",
                reason="local owner access disabled",
                metadata={"request_audit_id": request_audit.get("audit_id", "")},
            )
            self._send_contract(
                entity="task",
                response_id="oms.local_owner_access",
                contract_status="blocked",
                payload={"reason": "local_owner_access_disabled"},
                http_status=403,
                error="local_owner_access_disabled",
            )
            return
        if not self._is_local_request():
            self._write_login_recovery_audit(
                action="login.recovery.failed",
                result="blocked",
                reason="non-local request rejected",
                metadata={"request_audit_id": request_audit.get("audit_id", "")},
            )
            self._send_contract(
                entity="task",
                response_id="oms.local_owner_access",
                contract_status="blocked",
                payload={"reason": "local_request_required"},
                http_status=403,
                error="local_request_required",
            )
            return

        workspace_key, identity_source = workspace_key_for_feishu_identity(
            {self.local_owner_user_id},
            live_root=LOCAL_LIVE_RUNTIME_ROOT,
        )
        if workspace_key != "boss" or workspace_key not in PERSONAL_WORKSPACES:
            self._write_login_recovery_audit(
                action="login.recovery.failed",
                result="blocked",
                reason="owner user id not bound",
                metadata={"request_audit_id": request_audit.get("audit_id", ""), "user_id": self.local_owner_user_id},
            )
            self._send_contract(
                entity="task",
                response_id="oms.local_owner_access",
                contract_status="identity_binding_required",
                payload={"reason": "owner_identity_binding_required"},
                http_status=401,
                error="owner_identity_binding_required",
            )
            return

        workspace = PERSONAL_WORKSPACES[workspace_key]
        current_user = {
            "user_id": self.local_owner_user_id,
            "workspace_key": workspace_key,
            "name": workspace["name"],
            "role": workspace["role"],
            "home_title": workspace["title"],
        }
        success_audit = self._write_login_recovery_audit(
            action="login.recovery.success",
            result="ready",
            reason="local owner access granted",
            metadata={
                "request_audit_id": request_audit.get("audit_id", ""),
                "user_id": current_user.get("user_id", ""),
                "workspace_key": current_user.get("workspace_key", ""),
                "identity_source": identity_source,
                "entry": "master_control_dashboard",
            },
        )
        session_payload = self._issue_session(
            {
                "user_id": current_user.get("user_id", ""),
                "workspace_key": current_user.get("workspace_key", ""),
                "source": "local_owner_access",
            }
        )
        self._send_contract(
            entity="task",
            response_id="oms.local_owner_access",
            contract_status="ready",
            payload={
                "user_id": current_user.get("user_id", ""),
                "workspace_key": current_user.get("workspace_key", ""),
                "source": "local_owner_access",
                "policy": "EMP_permission_audit_master_data_preserved",
                "audit_id": success_audit.get("audit_id", ""),
                **session_payload,
            },
        )

    def _issue_session(self, identity: dict[str, Any]) -> dict[str, Any]:
        if self.session_signer is None:
            return {"session_status": "read_only_session_unavailable"}
        issued = self.session_signer.issue(
            user_id=str(identity.get("user_id") or ""),
            workspace_key=str(identity.get("workspace_key") or ""),
            source=str(identity.get("source") or "feishu_webapp_sso"),
        )
        return {
            "session_token": issued["token"],
            "session_expires_at": issued["session"]["expires_at"],
            "session_status": "ready",
        }

    def _session_claims(self) -> dict[str, Any]:
        if self.session_signer is None:
            raise PermissionError("production_session_signer_unavailable")
        authorization = str(self.headers.get("Authorization") or "").strip()
        if not authorization.startswith("Bearer "):
            raise PermissionError("missing_bearer_session")
        return self.session_signer.verify(authorization[7:].strip())

    def _send_current_summary(self) -> None:
        try:
            claims = self._session_claims()
            payload = self.current_operations.current_summary()
            payload["session_identity"] = {
                "user_id": claims.get("user_id"),
                "workspace_key": claims.get("workspace_key"),
            }
            self._send_contract(
                entity="task",
                response_id="oms.current.summary",
                contract_status="ready",
                payload=payload,
            )
        except PermissionError as exc:
            self._send_contract(
                entity="task",
                response_id="oms.current.summary",
                contract_status="blocked",
                payload={"reason": str(exc)},
                http_status=401,
                error=str(exc),
            )

    def _send_current_operation(self, path: str, payload: dict[str, Any]) -> None:
        operations = {
            "/api/oms/current/finance/record": self.current_operations.record_finance_current,
            "/api/oms/current/finance/review": self.current_operations.review_finance_current,
            "/api/oms/current/rooms/publish": self.current_operations.publish_room_current,
            "/api/oms/current/rooms/update": self.current_operations.update_room_status,
            "/api/oms/current/stays/publish": self.current_operations.publish_actual_stay,
            "/api/oms/current/stays/check-in": self.current_operations.check_in,
            "/api/oms/current/stays/check-out": self.current_operations.check_out,
            "/api/oms/current/stays/verify": self.current_operations.verify_actual_stay,
        }
        try:
            claims = self._session_claims()
            result = operations[path](claims, payload)
            self._send_contract(
                entity="task",
                response_id=path.removeprefix("/api/oms/").replace("/", "."),
                contract_status="ready",
                payload={"record": result, "source": "OMS_DOMAIN_CURRENT"},
            )
        except PermissionError as exc:
            self._send_contract(
                entity="task",
                response_id="oms.current.operation",
                contract_status="blocked",
                payload={"reason": str(exc)},
                http_status=403 if str(exc) != "missing_bearer_session" else 401,
                error=str(exc),
            )
        except KeyError as exc:
            self._send_contract(
                entity="task",
                response_id="oms.current.operation",
                contract_status="not_found",
                payload={"reason": str(exc)},
                http_status=404,
                error=str(exc),
            )
        except ValueError as exc:
            self._send_contract(
                entity="task",
                response_id="oms.current.operation",
                contract_status="invalid",
                payload={"reason": str(exc)},
                http_status=400,
                error=str(exc),
            )

    def _is_local_request(self) -> bool:
        client_host = self.client_address[0] if self.client_address else ""
        host = str(self.headers.get("Host") or "")
        return client_host in {"127.0.0.1", "::1"} and (
            host.startswith("127.0.0.1") or host.startswith("localhost")
        )

    def _write_login_recovery_audit(self, *, action: str, result: str, reason: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return AuditEngine(audit_root=self.audit_root).record(
            emp_id="EMP001",
            actor_name="石磊",
            module="auth",
            action=action,
            action_type="login",
            target_type="oms_entry",
            target_id="local_owner_access",
            reason=reason,
            result=result,
            source="oms.local_owner_access",
            metadata=metadata,
        )

    def _send_static_asset(self, path: str) -> bool:
        static_files = {
            "/": "index.html",
            "/index.html": "index.html",
            "/app.js": "app.js",
            "/styles.css": "styles.css",
            "/oms-config.js": "oms-config.js",
            "/oms-config.dev.js": "oms-config.dev.js",
            "/oms-config.prod.js": "oms-config.prod.js",
            "/contract.json": "contract.json",
            "/assets/huangjia-operations-brand.png": "assets/huangjia-operations-brand.png",
            "/assets/emp001-boss-avatar.jpg": "assets/emp001-boss-avatar.jpg",
            "/assets/emp008-liufangyu-avatar.jpg": "assets/emp008-liufangyu-avatar.jpg",
        }
        relative_name = static_files.get(path)
        if not relative_name:
            return False
        target = (STATIC_APP_ROOT / relative_name).resolve()
        if not str(target).startswith(str(STATIC_APP_ROOT.resolve())) or not target.exists():
            self._send_contract(
                entity="task",
                response_id="api.not_found",
                contract_status="not_found",
                payload={"path": path},
                http_status=404,
                error="not_found",
            )
            return True
        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".json":
            content_type = "application/json; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return True

    def _enforce_local_runtime_source(self, home: dict[str, Any]) -> dict[str, Any]:
        payload = dict(home)
        payload["runtime_source"] = dict(self.runtime_source_policy)
        dashboard = dict(payload.get("business_dashboard") or {})
        dashboard["runtime_source"] = dict(self.runtime_source_policy)
        dashboard["source"] = "OMS_TRUTH_SOURCE"
        dashboard["source_of_truth"] = str(LOCAL_TRUTH_SOURCE_ROOT)
        dashboard["remote_data_generation_allowed"] = False
        payload["business_dashboard"] = dashboard
        return payload

    def _compact_home_payload(self, home: dict[str, Any]) -> dict[str, Any]:
        compact = {
            "schema_version": home.get("schema_version"),
            "home_type": home.get("home_type"),
            "entry": home.get("entry"),
            "opened_at": home.get("opened_at"),
            "current_user": home.get("current_user"),
            "home_title": home.get("home_title"),
            "runtime_source": dict(self.runtime_source_policy),
            "sync_status": home.get("sync_status") or {},
            "decision_assist": home.get("decision_assist") or {},
            "bottom_tabs": home.get("bottom_tabs") or [],
            "payload_policy": "home_summary_only",
            "detail_policy": "details_loaded_from_paginated_endpoints",
            "center_entries": self._center_entries(),
        }
        sections: dict[str, Any] = {}
        for key, section in (home.get("sections") or {}).items():
            if not isinstance(section, dict):
                continue
            sections[key] = {
                "title": section.get("title") or key,
                "count": int(section.get("count") or 0),
                "total_count": int(section.get("count") or 0),
                "items": [],
                "items_endpoint": "/api/oms/stays" if key == "role_home" else "/api/oms/home",
                "empty_text": section.get("empty_text") or "",
            }
        compact["sections"] = sections
        dashboard = compact.get("business_dashboard")
        dashboard = home.get("business_dashboard")
        if isinstance(dashboard, dict):
            compact["business_dashboard"] = self._home_dashboard_summary(dashboard)
        master_control = compact.get("master_control")
        master_control = home.get("master_control")
        if isinstance(master_control, dict):
            compact["master_control"] = self._compact_master_control(master_control)
        core_fusion = home.get("core_fusion")
        if isinstance(core_fusion, dict):
            compact["core_fusion"] = {
                "schema_version": core_fusion.get("schema_version"),
                "mode": core_fusion.get("mode"),
                "counts": core_fusion.get("counts") or {},
                "validation": core_fusion.get("validation") or {},
            }
        return compact

    def _center_entries(self) -> list[dict[str, str]]:
        return [
            {"key": "sales", "title": "销售中心", "endpoint": "/api/oms/sales"},
            {"key": "finance", "title": "财务中心", "endpoint": "/api/oms/finance"},
            {"key": "operations", "title": "运营中心", "endpoint": "/api/oms/rooms"},
            {"key": "rooms", "title": "房态", "endpoint": "/api/oms/rooms"},
            {"key": "stays", "title": "入住", "endpoint": "/api/oms/stays"},
            {"key": "contracts", "title": "合同", "endpoint": "/api/oms/contracts"},
        ]

    def _home_dashboard_summary(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        source_data = dashboard.get("source_evidence_available_data") if isinstance(dashboard.get("source_evidence_available_data"), dict) else {}
        source_counts = source_data.get("counts") if isinstance(source_data.get("counts"), dict) else {}
        metrics = dashboard.get("metrics") if isinstance(dashboard.get("metrics"), dict) else {}
        schema = dashboard.get("business_schema") if isinstance(dashboard.get("business_schema"), dict) else {}
        truth_source = dashboard.get("truth_source") if isinstance(dashboard.get("truth_source"), dict) else {}
        production_adapters = dashboard.get("production_adapters") if isinstance(dashboard.get("production_adapters"), dict) else {}
        return {
            "title": dashboard.get("title") or "今日经营",
            "source": "OMS_TRUTH_SOURCE",
            "source_of_truth": dashboard.get("source_of_truth") or str(LOCAL_TRUTH_SOURCE_ROOT),
            "runtime_source": dict(self.runtime_source_policy),
            "metrics": metrics,
            "business_schema": schema,
            "truth_source": {
                "schema_version": truth_source.get("schema_version"),
                "mode": truth_source.get("mode"),
                "counts": truth_source.get("counts") or {},
            },
            "production_adapters": production_adapters,
            "source_evidence_available_data": {
                "policy": "counts_only_home_summary",
                "counts": source_counts,
                "resident_data_total_count": int(source_counts.get("resident_data") or 0),
                "room_status_data_total_count": int(source_counts.get("room_status_data") or 0),
                "sales_contract_data_total_count": int(source_counts.get("sales_contract_data") or 0),
                "finance_data_total_count": int(source_counts.get("finance_data") or 0),
                "financial_events_total_count": int(source_counts.get("financial_events") or 0),
                "caregiver_message": "暂无结构化生产数据"
                if int(source_counts.get("service_data") or 0) == 0
                else "",
            },
            "risk_summary": {
                "risk_alerts": metrics.get("risk_alerts", 0),
                "today_todos": metrics.get("today_todos", 0),
            },
            "data_updated_at": self._home_data_updated_at(truth_source),
        }

    def _home_data_updated_at(self, truth_source: dict[str, Any]) -> str:
        return str(truth_source.get("updated_at") or now_iso())

    def _compact_history_payload(self, history: dict[str, Any], *, limit: int = 80) -> dict[str, Any]:
        compact = dict(history)
        timeline = history.get("timeline")
        if isinstance(timeline, list):
            compact["timeline_total_count"] = len(timeline)
            compact["timeline"] = timeline[:limit]
            compact["timeline_visible_count"] = len(compact["timeline"])
        multidimensional = compact.get("multidimensional_history")
        if isinstance(multidimensional, dict):
            compact_multi: dict[str, Any] = {}
            for key, value in multidimensional.items():
                if not isinstance(value, dict):
                    compact_multi[key] = value
                    continue
                bucket = dict(value)
                items = bucket.get("items")
                if isinstance(items, list):
                    bucket["items_total_count"] = len(items)
                    bucket["items"] = items[:limit]
                    bucket["items_visible_count"] = len(bucket["items"])
                compact_multi[key] = bucket
            compact["multidimensional_history"] = compact_multi
        compact["payload_policy"] = "compacted_for_feishu_h5_runtime"
        compact["payload_item_limit"] = limit
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
        nested_dashboard = compact.get("business_dashboard")
        if isinstance(nested_dashboard, dict):
            compact["business_dashboard"] = self._home_dashboard_summary(nested_dashboard)
        compact["payload_policy"] = "compacted_for_feishu_h5_runtime"
        compact["payload_item_limit"] = limit
        return compact

    def _compact_source_evidence_data(self, source_data: Any, *, limit: int = SOURCE_EVIDENCE_DETAIL_LIMIT) -> dict[str, Any]:
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

    def _compact_business_state(self, business_state: dict[str, Any], *, limit: int = 25) -> dict[str, Any]:
        compact = dict(business_state)
        domains = business_state.get("domains")
        if isinstance(domains, dict):
            compact_domains: dict[str, Any] = {}
            for domain, value in domains.items():
                if not isinstance(value, dict):
                    compact_domains[domain] = value
                    continue
                domain_state = dict(value)
                current_state = domain_state.get("current_state")
                if isinstance(current_state, dict):
                    items = list(current_state.items())
                    domain_state["current_state_total_count"] = len(items)
                    domain_state["current_state"] = dict(items[:limit])
                    domain_state["current_state_visible_count"] = len(domain_state["current_state"])
                compact_domains[domain] = domain_state
            compact["domains"] = compact_domains
        compact["payload_policy"] = "compacted_for_feishu_h5_runtime"
        compact["payload_item_limit"] = limit
        return compact

    def _compact_lifecycle(self, lifecycle: dict[str, Any], *, limit: int = 25) -> dict[str, Any]:
        compact = dict(lifecycle)
        for key in ("open_lifecycles", "action_queue"):
            value = compact.get(key)
            if isinstance(value, list):
                compact[f"{key}_total_count"] = len(value)
                compact[key] = value[:limit]
                compact[f"{key}_visible_count"] = len(compact[key])
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

    def _query_payload(self) -> dict[str, Any]:
        if "?" not in self.path:
            return {}
        from urllib.parse import unquote_plus

        payload: dict[str, Any] = {}
        query = self.path.split("?", 1)[1]
        for part in query.split("&"):
            name, _, value = part.partition("=")
            if name:
                payload[name] = unquote_plus(value)
        return payload

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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_contract(
        self,
        *,
        entity: str,
        response_id: str,
        contract_status: str,
        payload: dict[str, Any],
        http_status: int = 200,
        error: str | None = None,
    ) -> None:
        contract_payload: dict[str, Any] = {
            "entity": entity,
            "id": response_id,
            "status": contract_status,
            "payload": payload,
            "timestamp": now_iso(),
            "source": "OMS_TRUTH_SOURCE",
            "contract_version": CONTRACT_VERSION,
        }
        if error:
            contract_payload["error"] = error
        self._send_json(contract_payload, status=http_status)

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
