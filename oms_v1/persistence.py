from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any

from .audit_log import AuditEngine
from .schemas import new_id, now_iso


PERSISTENCE_SCHEMA_VERSION = "oms.v1.persistence"
DEFAULT_PERSISTENCE_ROOT = Path(__file__).resolve().parents[1] / "live_runtime" / "persistence"


@dataclass(frozen=True)
class EntitySerializer:
    """Serialize OMS domain objects into persistence-safe dictionaries."""

    schema_version: str = PERSISTENCE_SCHEMA_VERSION

    def serialize(self, entity: Any) -> dict[str, Any]:
        if hasattr(entity, "to_dict"):
            payload = entity.to_dict()
        elif is_dataclass(entity):
            payload = asdict(entity)
        elif isinstance(entity, dict):
            payload = dict(entity)
        else:
            raise TypeError("Entity must be a dict, dataclass, or expose to_dict().")
        return _json_safe(payload)

    def deserialize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return dict(payload)


@dataclass(frozen=True)
class PersistenceRecord:
    entity_type: str
    entity_id: str
    version: int
    payload: dict[str, Any]
    audit_id: str
    event_id: str
    correlation_id: str
    record_id: str = field(default_factory=lambda: new_id("persist"))
    saved_at: str = field(default_factory=now_iso)
    schema_version: str = PERSISTENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.entity_type.strip():
            raise ValueError("entity_type is required.")
        if not self.entity_id.strip():
            raise ValueError("entity_id is required.")
        if self.version < 1:
            raise ValueError("version must be >= 1.")
        if not self.audit_id.strip():
            raise ValueError("audit_id is required.")
        if not self.event_id.strip():
            raise ValueError("event_id is required.")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id is required.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StorageAdapter:
    """Local JSONL storage adapter for P17 persistence foundation."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or DEFAULT_PERSISTENCE_ROOT)

    def append(self, record: PersistenceRecord | dict[str, Any]) -> dict[str, Any]:
        payload = record.to_dict() if isinstance(record, PersistenceRecord) else dict(record)
        path = self._path(payload["entity_type"], payload["entity_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return payload

    def read_versions(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        path = self._path(entity_type, entity_id)
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return sorted(rows, key=lambda row: int(row.get("version") or 0))

    def _path(self, entity_type: str, entity_id: str) -> Path:
        return self.root / _safe_segment(entity_type) / f"{_safe_segment(entity_id)}.jsonl"


class DataRepository:
    """Repository boundary for saving and reading versioned domain objects."""

    def __init__(
        self,
        *,
        storage: StorageAdapter | None = None,
        serializer: EntitySerializer | None = None,
    ):
        self.storage = storage or StorageAdapter()
        self.serializer = serializer or EntitySerializer()

    def save(
        self,
        *,
        entity_type: str,
        entity_id: str,
        entity: Any,
        audit_id: str,
        event_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        version = self.next_version(entity_type, entity_id)
        record = PersistenceRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            version=version,
            payload=self.serializer.serialize(entity),
            audit_id=audit_id,
            event_id=event_id,
            correlation_id=correlation_id,
        )
        return self.storage.append(record)

    def get(self, *, entity_type: str, entity_id: str, version: int | None = None) -> dict[str, Any]:
        versions = self.versions(entity_type=entity_type, entity_id=entity_id)
        if not versions:
            raise KeyError(f"Unknown entity: {entity_type}/{entity_id}")
        if version is None:
            return versions[-1]
        for record in versions:
            if int(record["version"]) == version:
                return record
        raise KeyError(f"Unknown entity version: {entity_type}/{entity_id}@{version}")

    def versions(self, *, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        return self.storage.read_versions(entity_type, entity_id)

    def next_version(self, entity_type: str, entity_id: str) -> int:
        versions = self.versions(entity_type=entity_type, entity_id=entity_id)
        if not versions:
            return 1
        return int(versions[-1]["version"]) + 1


class PersistenceManager:
    """High-level persistence facade with audit linkage."""

    def __init__(
        self,
        *,
        repository: DataRepository | None = None,
        audit: AuditEngine | None = None,
    ):
        self.repository = repository or DataRepository()
        self.audit = audit or AuditEngine()

    def save_domain_object(
        self,
        *,
        entity_type: str,
        entity_id: str,
        entity: Any,
        actor_emp_id: str,
        actor_name: str,
        reason: str,
        event_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required.")
        audit_record = self.audit.record(
            emp_id=actor_emp_id,
            actor_name=actor_name,
            module="persistence",
            action="persistence.save",
            action_type="persistence.save",
            reason=reason,
            result="saved",
            target_type=entity_type,
            target_id=entity_id,
            correlation_id=correlation_id,
            metadata={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "event_id": event_id,
                "mutates_business_state": False,
            },
        )
        record = self.repository.save(
            entity_type=entity_type,
            entity_id=entity_id,
            entity=entity,
            audit_id=str(audit_record["audit_id"]),
            event_id=event_id,
            correlation_id=correlation_id,
        )
        return {
            "schema_version": PERSISTENCE_SCHEMA_VERSION,
            "record": record,
            "audit": audit_record,
            "mutates_business_state": False,
        }

    def read_domain_object(self, *, entity_type: str, entity_id: str, version: int | None = None) -> dict[str, Any]:
        record = self.repository.get(entity_type=entity_type, entity_id=entity_id, version=version)
        return {
            "schema_version": PERSISTENCE_SCHEMA_VERSION,
            "record": record,
            "mutates_business_state": False,
        }

    def history(self, *, entity_type: str, entity_id: str) -> dict[str, Any]:
        return {
            "schema_version": PERSISTENCE_SCHEMA_VERSION,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "versions": self.repository.versions(entity_type=entity_type, entity_id=entity_id),
            "mutates_business_state": False,
        }


def _safe_segment(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in {"_", "-"} else "_" for character in value.strip())
    if not safe:
        raise ValueError("Storage path segment cannot be blank.")
    return safe


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    return value
