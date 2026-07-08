from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = "oms.v1.structured_message"
EVENT_SCHEMA_VERSION = "oms.v1.business_event"
DECISION_SCHEMA_VERSION = "oms.v1.recommendation"
EXECUTION_SCHEMA_VERSION = "oms.v1.execution_action"
GOVERNANCE_SCHEMA_VERSION = "oms.v1.governance_decision"
LIVE_SCHEMA_VERSION = "oms.v1.live_sync_result"
OPERATIONAL_SCHEMA_VERSION = "oms.v1.operational_work_item"
ADOPTION_SCHEMA_VERSION = "oms.v1.adoption_status"
SWITCH_SCHEMA_VERSION = "oms.v1.system_switch"
REALITY_LOCK_SCHEMA_VERSION = "oms.v1.reality_lock"
RULES_VERSION = "oms-v1-rules-2026-07-02"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class BusinessEvent:
    event_type: str
    source: str
    entity: str
    action: str
    payload: dict[str, Any]
    timestamp: str
    event_id: str = field(default_factory=lambda: new_id("evt"))
    schema_version: str = EVENT_SCHEMA_VERSION
    subscriptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionRecommendation:
    event_id: str
    decision_type: str
    recommended_action: str
    priority: str
    risk_level: str
    reason: str
    decision_id: str = field(default_factory=lambda: new_id("dec"))
    schema_version: str = DECISION_SCHEMA_VERSION
    human_override_allowed: bool = True
    override_roles: list[str] = field(default_factory=list)
    source_event_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionAction:
    action_type: str
    target_module: str
    execution_result: str
    status: str
    timestamp: str
    rollback_supported: bool
    action_id: str = field(default_factory=lambda: new_id("act"))
    decision_id: str | None = None
    source_decision_type: str | None = None
    schema_version: str = EXECUTION_SCHEMA_VERSION
    rollback_plan: dict[str, Any] = field(default_factory=dict)
    human_override_allowed: bool = True
    override_roles: list[str] = field(default_factory=list)
    execution_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceDecision:
    action_id: str
    allowed: bool
    approval_required: bool
    required_roles: list[str]
    risk_level: str
    reason: str
    override_policy: str
    governance_id: str = field(default_factory=lambda: new_id("gov"))
    schema_version: str = GOVERNANCE_SCHEMA_VERSION
    action_type: str | None = None
    target_module: str | None = None
    responsibility_chain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LiveSyncResult:
    sync_target: str
    sync_type: str
    sync_result: str
    status: str
    rollback_supported: bool
    audit_log: str
    live_id: str = field(default_factory=lambda: new_id("live"))
    schema_version: str = LIVE_SCHEMA_VERSION
    action_id: str | None = None
    governance_id: str | None = None
    source_of_truth: str | None = None
    rollback_plan: dict[str, Any] = field(default_factory=dict)
    external_status: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationalWorkItem:
    role: str
    workspace: str
    daily_process: str
    primary_entry: str
    legacy_policy: dict[str, str]
    action_id: str
    action_type: str
    status: str
    confirmation_required: bool
    next_operator_action: str
    work_item_id: str = field(default_factory=lambda: new_id("op"))
    schema_version: str = OPERATIONAL_SCHEMA_VERSION
    source_sync_targets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdoptionStatus:
    role: str
    adoption_status: str
    blockers: list[str]
    migration_tasks: list[str]
    recommended_actions: list[str]
    risk_level: str
    adoption_id: str = field(default_factory=lambda: new_id("adopt"))
    schema_version: str = ADOPTION_SCHEMA_VERSION
    bypass_log: list[dict[str, Any]] = field(default_factory=list)
    manual_override_log: list[dict[str, Any]] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SystemSwitchStatus:
    switch_state: str
    oms_truth_role: str
    legacy_system_role: dict[str, str]
    role_switches: list[dict[str, Any]]
    blockers: list[str]
    required_authorization: list[str]
    bypass_log: list[dict[str, Any]]
    manual_override_log: list[dict[str, Any]]
    switch_id: str = field(default_factory=lambda: new_id("switch"))
    schema_version: str = SWITCH_SCHEMA_VERSION
    success_criteria: dict[str, list[str]] = field(default_factory=dict)
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RealityLockStatus:
    lock_state: str
    reality_binding: dict[str, str]
    fixed_architecture: list[str]
    trace_requirements: list[str]
    locked_principles: list[str]
    allowed_change_scope: str
    blockers: list[str]
    lock_id: str = field(default_factory=lambda: new_id("lock"))
    schema_version: str = REALITY_LOCK_SCHEMA_VERSION
    switch_state: str | None = None
    boss_final_authority: str = "石磊"
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InputEnvelope:
    input_id: str
    source: str
    channel: str
    received_at: str
    content_type: str
    text: str = ""
    file_path: str | None = None
    wechat_group: str | None = None
    sender: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        source: str = "manual",
        channel: str = "text",
        wechat_group: str | None = None,
        sender: str | None = None,
        received_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "InputEnvelope":
        return cls(
            input_id=new_id("in"),
            source=source,
            channel=channel,
            received_at=received_at or now_iso(),
            content_type="text/plain",
            text=text,
            wechat_group=wechat_group,
            sender=sender,
            metadata=metadata or {},
        )

    @classmethod
    def from_file(
        cls,
        file_path: str | Path,
        *,
        source: str = "wechat_file",
        channel: str = "file",
        wechat_group: str | None = None,
        sender: str | None = None,
        received_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "InputEnvelope":
        path = Path(file_path)
        return cls(
            input_id=new_id("in"),
            source=source,
            channel=channel,
            received_at=received_at or now_iso(),
            content_type=guess_content_type(path),
            file_path=str(path),
            wechat_group=wechat_group,
            sender=sender,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".csv"}:
        return "text/plain"
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}:
        return f"image/{suffix.lstrip('.')}"
    return "application/octet-stream"


@dataclass
class TextExtraction:
    status: str
    text: str
    source: str
    engine: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
