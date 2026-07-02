from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from .schemas import LiveSyncResult, now_iso


DEFAULT_LIVE_ROOT = Path(__file__).resolve().parents[1] / "live_runtime"
FEISHU_STATUS_PENDING_REVIEW = "PENDING_REVIEW"
EXTERNAL_WRITE_DISABLED = "DISABLED"
OUTBOX_ACTIVE = "ACTIVE"


class LiveConnector:
    """Sync governed OMS actions into Huangjia's live operating adapters."""

    def __init__(self, live_root: str | Path | None = None):
        self.live_root = Path(live_root or os.getenv("OMS_LIVE_ROOT") or DEFAULT_LIVE_ROOT)
        self.feishu_status = os.getenv("OMS_FEISHU_STATUS", FEISHU_STATUS_PENDING_REVIEW)
        self.external_write_mode = os.getenv("OMS_EXTERNAL_WRITE_MODE", EXTERNAL_WRITE_DISABLED)
        self.outbox_mode = os.getenv("OMS_OUTBOX_MODE", OUTBOX_ACTIVE)

    def build_live_stream(self, execution_stream: dict[str, Any], governance_stream: dict[str, Any]) -> dict[str, Any]:
        results = self.sync(execution_stream, governance_stream)
        return {
            "schema_version": "oms.v1.live_stream",
            "input_id": execution_stream.get("input_id") or governance_stream.get("input_id"),
            "flow": [
                "input",
                "parsed_json",
                "business_events",
                "recommendations",
                "execution_actions",
                "governance_decisions",
                "live_sync",
            ],
            "sync_results": [result.to_dict() for result in results],
            "audit": {
                "created_at": now_iso(),
                "sync_count": len(results),
                "requires_execution_stream": True,
                "requires_governance_stream": True,
                "source_of_truth_priority": ["飞书", "Excel", "微信", "OMS"],
                "oms_role": "同步 + 结构化 + 增强；不替代真实系统。",
                "live_root": str(self.live_root),
                "mode": "Feishu_Pending_Mode",
                "feishu_status": self.feishu_status,
                "external_write_mode": self.external_write_mode,
                "outbox_mode": self.outbox_mode,
                "external_dependency_policy": "飞书是外部依赖，不是系统能力；OMS 不依赖外部 API、不阻塞内部运行、不丢失事件流。",
            },
        }

    def sync(self, execution_stream: dict[str, Any], governance_stream: dict[str, Any]) -> list[LiveSyncResult]:
        actions = execution_stream.get("actions")
        governance = governance_stream.get("governance")
        if actions is None:
            raise ValueError("LiveConnector requires an ExecutionEngine execution stream")
        if governance is None:
            raise ValueError("LiveConnector requires a GovernanceEngine governance stream")

        governance_by_action = {item.get("action_id"): item for item in governance}
        results: list[LiveSyncResult] = []
        for action in actions:
            gov = governance_by_action.get(action.get("action_id"))
            if gov is None:
                results.append(self._failed_missing_governance(action))
                continue
            results.extend(self._sync_action(action, gov))
        return results

    def _sync_action(self, action: dict[str, Any], governance: dict[str, Any]) -> list[LiveSyncResult]:
        if governance.get("approval_required"):
            return [self._write_pending_outbox("人工审批流", "approval_request", action, governance)]

        targets = self._targets(action)
        return [self._write_target(target, action, governance) for target in targets]

    def _targets(self, action: dict[str, Any]) -> list[dict[str, str]]:
        action_type = action.get("action_type", "")
        targets = {
            "create_sales_operation_followup": [
                {"sync_target": "飞书任务系统", "sync_type": "write_task"},
                {"sync_target": "Excel_CRM历史数据", "sync_type": "append_row"},
            ],
            "generate_room_assignment_plan": [
                {"sync_target": "Excel_六月排房表", "sync_type": "append_row"},
                {"sync_target": "飞书排房任务", "sync_type": "write_task"},
            ],
            "create_checkin_preparation_task": [
                {"sync_target": "飞书任务系统", "sync_type": "write_task"},
            ],
            "create_service_followup_task": [
                {"sync_target": "飞书任务系统", "sync_type": "write_task"},
            ],
            "create_service_coordination_task": [
                {"sync_target": "飞书任务系统", "sync_type": "write_task"},
            ],
            "generate_reconciliation_task": [
                {"sync_target": "Excel_刘姐日结表", "sync_type": "append_row"},
            ],
            "create_payment_todo": [
                {"sync_target": "Excel_刘姐日结表", "sync_type": "append_row"},
            ],
            "generate_service_amount_split_task": [
                {"sync_target": "Excel_刘姐日结表", "sync_type": "append_row"},
            ],
            "create_service_risk_task": [
                {"sync_target": "人工审批流", "sync_type": "approval_request"},
            ],
            "flag_financial_risk": [
                {"sync_target": "人工审批流", "sync_type": "approval_request"},
            ],
            "mark_oversell_risk": [
                {"sync_target": "人工审批流", "sync_type": "approval_request"},
            ],
            "generate_room_exception_task": [
                {"sync_target": "BOSS审批流", "sync_type": "approval_request"},
            ],
        }
        return targets.get(action_type, [{"sync_target": "人工审批流", "sync_type": "approval_request"}])

    def _write_target(self, target: dict[str, str], action: dict[str, Any], governance: dict[str, Any]) -> LiveSyncResult:
        sync_target = target["sync_target"]
        sync_type = target["sync_type"]
        if sync_target.startswith("Excel_"):
            return self._write_excel_ledger(sync_target, sync_type, action, governance)
        if sync_target.startswith("飞书"):
            return self._write_pending_outbox(sync_target, sync_type, action, governance)
        if "审批流" in sync_target or sync_target.startswith("微信"):
            return self._write_pending_outbox(sync_target, sync_type, action, governance)
        return self._write_external_outbox("external_outbox", sync_target, sync_type, action, governance)

    def _write_excel_ledger(
        self, sync_target: str, sync_type: str, action: dict[str, Any], governance: dict[str, Any]
    ) -> LiveSyncResult:
        path = self.live_root / "excel_sync" / f"{sync_target}.csv"
        row = self._base_row(action, governance)
        self._append_csv(path, row)
        audit_path = self._append_audit("excel", sync_target, sync_type, action, governance, "success")
        return LiveSyncResult(
            sync_target=sync_target,
            sync_type=sync_type,
            sync_result=f"已写入本地 Excel 同步台账：{path}",
            status="success",
            rollback_supported=True,
            audit_log=audit_path,
            action_id=action.get("action_id"),
            governance_id=governance.get("governance_id"),
            source_of_truth="Excel",
            rollback_plan={
                "method": "按 action_id 追加撤销记录，不覆盖原始 Excel/CSV 行。",
                "target": str(path),
            },
            external_status=self._external_status("LOCAL_CACHE"),
        )

    def _write_pending_outbox(
        self, sync_target: str, sync_type: str, action: dict[str, Any], governance: dict[str, Any]
    ) -> LiveSyncResult:
        path = self.live_root / "pending_outbox" / f"{sync_target}.jsonl"
        self._append_jsonl(path, self._base_payload(action, governance, sync_target, sync_type, "pending"))
        audit_path = self._append_audit("pending_outbox", sync_target, sync_type, action, governance, "pending")
        return LiveSyncResult(
            sync_target=sync_target,
            sync_type=sync_type,
            sync_result=(
                f"Feishu_Pending_Mode：{sync_target} 已进入 pending_outbox；"
                "飞书应用审核中，external_write_mode=DISABLED，未调用真实飞书写入 API。"
            ),
            status="pending",
            rollback_supported=True,
            audit_log=audit_path,
            action_id=action.get("action_id"),
            governance_id=governance.get("governance_id"),
            source_of_truth="OMS pending_outbox",
            rollback_plan={
                "method": "逻辑级回滚：按 action_id 将 pending_outbox 记录标记为 cancelled；审核通过前不需要外部系统回滚。",
                "target": str(path),
                "external_write_executed": False,
            },
            external_status=self._external_status("PENDING_OUTBOX"),
        )

    def _write_external_outbox(
        self, folder: str, sync_target: str, sync_type: str, action: dict[str, Any], governance: dict[str, Any]
    ) -> LiveSyncResult:
        path = self.live_root / folder / f"{sync_target}.jsonl"
        self._append_jsonl(path, self._base_payload(action, governance, sync_target, sync_type, "pending"))
        audit_path = self._append_audit(folder, sync_target, sync_type, action, governance, "pending")
        return LiveSyncResult(
            sync_target=sync_target,
            sync_type=sync_type,
            sync_result=f"已进入 {sync_target} 待同步 outbox；缺少真实 API 授权，未直接写入外部系统。",
            status="pending",
            rollback_supported=True,
            audit_log=audit_path,
            action_id=action.get("action_id"),
            governance_id=governance.get("governance_id"),
            source_of_truth=sync_target,
            rollback_plan={
                "method": "从 outbox 标记为 cancelled；若外部系统已同步，必须调用外部系统回滚接口。",
                "target": str(path),
            },
            external_status=self._external_status("LEGACY_OUTBOX"),
        )

    def _write_manual_approval(
        self,
        action: dict[str, Any],
        governance: dict[str, Any],
        *,
        sync_target: str = "人工审批流",
        sync_type: str = "approval_request",
    ) -> LiveSyncResult:
        path = self.live_root / "manual_approval" / f"{sync_target}.jsonl"
        self._append_jsonl(path, self._base_payload(action, governance, sync_target, sync_type, "pending"))
        audit_path = self._append_audit("manual_approval", sync_target, sync_type, action, governance, "pending")
        roles = "、".join(governance.get("required_roles") or [])
        return LiveSyncResult(
            sync_target=sync_target,
            sync_type=sync_type,
            sync_result=f"已生成审批请求，等待 {roles} 确认后才能同步真实系统。",
            status="pending",
            rollback_supported=True,
            audit_log=audit_path,
            action_id=action.get("action_id"),
            governance_id=governance.get("governance_id"),
            source_of_truth="微信/人工审批",
            rollback_plan={
                "method": "取消审批请求；已审批的动作必须由审批人或 BOSS 回滚。",
                "target": str(path),
            },
            external_status=self._external_status("MANUAL_PENDING"),
        )

    def _failed_missing_governance(self, action: dict[str, Any]) -> LiveSyncResult:
        audit_path = self._append_audit("failed", "GovernanceEngine", "missing_governance", action, {}, "failed")
        return LiveSyncResult(
            sync_target="GovernanceEngine",
            sync_type="missing_governance",
            sync_result="找不到 action_id 对应的治理判断，禁止同步真实系统。",
            status="failed",
            rollback_supported=False,
            audit_log=audit_path,
            action_id=action.get("action_id"),
            source_of_truth="OMS",
            external_status=self._external_status("BLOCKED"),
        )

    def _base_row(self, action: dict[str, Any], governance: dict[str, Any]) -> dict[str, Any]:
        payload = action.get("execution_payload") or {}
        return {
            "synced_at": now_iso(),
            "action_id": action.get("action_id", ""),
            "governance_id": governance.get("governance_id", ""),
            "action_type": action.get("action_type", ""),
            "target_module": action.get("target_module", ""),
            "risk_level": governance.get("risk_level", ""),
            "approved_by": "|".join((governance.get("responsibility_chain") or {}).get("approved_by") or []),
            "executed_by": "|".join((governance.get("responsibility_chain") or {}).get("executed_by") or []),
            "recommended_action": payload.get("recommended_action", ""),
            "reason": payload.get("reason", ""),
            "sync_status": "active",
        }

    def _base_payload(
        self, action: dict[str, Any], governance: dict[str, Any], sync_target: str, sync_type: str, status: str
    ) -> dict[str, Any]:
        return {
            "created_at": now_iso(),
            "sync_target": sync_target,
            "sync_type": sync_type,
            "status": status,
            "mode": "Feishu_Pending_Mode",
            "feishu_status": self.feishu_status,
            "external_write_mode": self.external_write_mode,
            "outbox_mode": self.outbox_mode,
            "action": action,
            "governance": governance,
        }

    def _external_status(self, route: str) -> dict[str, Any]:
        return {
            "mode": "Feishu_Pending_Mode",
            "route": route,
            "feishu_status": self.feishu_status,
            "external_write_mode": self.external_write_mode,
            "outbox_mode": self.outbox_mode,
            "real_feishu_api_called": False,
        }

    def _append_csv(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        exists = path.exists()
        with path.open("a", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
            if not exists:
                writer.writeheader()
            writer.writerow(row)

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _append_audit(
        self,
        folder: str,
        sync_target: str,
        sync_type: str,
        action: dict[str, Any],
        governance: dict[str, Any],
        status: str,
    ) -> str:
        path = self.live_root / "audit" / f"{folder}.jsonl"
        self._append_jsonl(path, self._base_payload(action, governance, sync_target, sync_type, status))
        return str(path)
