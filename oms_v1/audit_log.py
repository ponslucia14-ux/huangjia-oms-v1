from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .live_connector import DEFAULT_LIVE_ROOT
from .schemas import new_id, now_iso


AUDIT_SCHEMA_VERSION = "oms.v1.audit_event"
DEFAULT_AUDIT_ROOT = DEFAULT_LIVE_ROOT / "audit_center"
DEFAULT_AUDIT_FILE = "audit_events.jsonl"


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event record for append-only OMS audit logs."""

    emp_id: str
    actor_name: str
    module: str
    action: str
    reason: str
    result: str
    audit_id: str = field(default_factory=lambda: new_id("audit"))
    schema_version: str = AUDIT_SCHEMA_VERSION
    timestamp: str = field(default_factory=now_iso)
    action_type: str = ""
    target_type: str = ""
    target_id: str = ""
    severity: str = "info"
    source: str = "oms"
    correlation_id: str = ""
    request_id: str = ""
    before_hash: str = ""
    after_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self._requires_reason() and not self.reason.strip():
            raise ValueError("reason is required for modification audit events.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def _requires_reason(self) -> bool:
        text = " ".join([self.action, self.action_type, self.target_type]).lower()
        modification_terms = {
            "create",
            "update",
            "modify",
            "delete",
            "write",
            "approve",
            "reject",
            "confirm",
            "assign",
            "sync",
            "import",
            "export",
            "close",
            "open",
        }
        return any(term in text for term in modification_terms)


class AuditStorage:
    """Append-only JSONL storage for OMS audit events."""

    def __init__(self, audit_root: str | Path | None = None, audit_file: str = DEFAULT_AUDIT_FILE):
        root = Path(audit_root or os.getenv("OMS_AUDIT_ROOT") or DEFAULT_AUDIT_ROOT)
        self.audit_root = root
        self.audit_path = root / audit_file

    def append(self, event: AuditEvent | dict[str, Any]) -> dict[str, Any]:
        payload = event.to_dict() if isinstance(event, AuditEvent) else dict(event)
        self.audit_root.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return payload

    def read_all(self) -> list[dict[str, Any]]:
        if not self.audit_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.audit_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def overwrite(self, *_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("OMS Audit Log is append-only; overwrite is forbidden.")

    def delete(self, *_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("OMS Audit Log is append-only; delete is forbidden.")

    def truncate(self, *_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("OMS Audit Log is append-only; truncate is forbidden.")


class AuditWriter:
    """Write audit events through the append-only storage boundary."""

    def __init__(self, storage: AuditStorage | None = None):
        self.storage = storage or AuditStorage()

    def write(
        self,
        *,
        emp_id: str,
        actor_name: str,
        module: str,
        action: str,
        reason: str,
        result: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        event = AuditEvent(
            emp_id=emp_id,
            actor_name=actor_name,
            module=module,
            action=action,
            reason=reason,
            result=result,
            **kwargs,
        )
        return self.storage.append(event)


class AuditReader:
    """Read and query audit events without mutating storage."""

    def __init__(self, storage: AuditStorage | None = None):
        self.storage = storage or AuditStorage()

    def all(self, *, sort_by_time: bool = True) -> list[dict[str, Any]]:
        rows = self.storage.read_all()
        if not sort_by_time:
            return rows
        return sorted(rows, key=self._time_key)

    def query(
        self,
        *,
        emp_id: str | None = None,
        module: str | None = None,
        action: str | None = None,
        sort_by_time: bool = True,
    ) -> list[dict[str, Any]]:
        rows = self.all(sort_by_time=sort_by_time)
        if emp_id is not None:
            rows = [row for row in rows if row.get("emp_id") == emp_id]
        if module is not None:
            rows = [row for row in rows if row.get("module") == module]
        if action is not None:
            rows = [row for row in rows if row.get("action") == action]
        return rows

    @staticmethod
    def _time_key(row: dict[str, Any]) -> tuple[datetime, str]:
        raw = str(row.get("timestamp") or "")
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            parsed = datetime.min
        return parsed, str(row.get("audit_id") or "")


class AuditEngine:
    """Unified facade for OMS audit writing and reading."""

    def __init__(self, audit_root: str | Path | None = None, storage: AuditStorage | None = None):
        self.storage = storage or AuditStorage(audit_root)
        self.writer = AuditWriter(self.storage)
        self.reader = AuditReader(self.storage)

    def record(self, **kwargs: Any) -> dict[str, Any]:
        return self.writer.write(**kwargs)

    def events(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.reader.query(**kwargs)

    def summary(self) -> dict[str, Any]:
        rows = self.reader.all()
        modules = sorted({str(row.get("module") or "") for row in rows if row.get("module")})
        employees = sorted({str(row.get("emp_id") or "") for row in rows if row.get("emp_id")})
        return {
            "schema_version": "oms.v1.audit_summary",
            "audit_path": str(self.storage.audit_path),
            "event_count": len(rows),
            "modules": modules,
            "employees": employees,
            "append_only": True,
        }
