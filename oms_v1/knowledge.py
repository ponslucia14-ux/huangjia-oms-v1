from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


KNOWLEDGE_SCHEMA_VERSION = "oms.v1.knowledge"

CATEGORY_POLICY = "policy"
CATEGORY_SOP = "sop"
CATEGORY_BUSINESS_RULE = "business_rule"
CATEGORY_OPERATING_EXPERIENCE = "operating_experience"
CATEGORY_RETROSPECTIVE = "retrospective"
CATEGORY_TRAINING = "training"

SUPPORTED_KNOWLEDGE_CATEGORIES = {
    CATEGORY_POLICY,
    CATEGORY_SOP,
    CATEGORY_BUSINESS_RULE,
    CATEGORY_OPERATING_EXPERIENCE,
    CATEGORY_RETROSPECTIVE,
    CATEGORY_TRAINING,
}

CATEGORY_SOURCE_TYPES = {
    CATEGORY_POLICY: ("policy_file",),
    CATEGORY_SOP: ("sop",),
    CATEGORY_BUSINESS_RULE: ("business_rule",),
    CATEGORY_OPERATING_EXPERIENCE: ("operating_experience",),
    CATEGORY_RETROSPECTIVE: ("retrospective",),
    CATEGORY_TRAINING: ("training_material",),
}

SOURCE_CATEGORY_ALIASES = {
    "policy_file": CATEGORY_POLICY,
    "policy": CATEGORY_POLICY,
    "sop": CATEGORY_SOP,
    "business_rule": CATEGORY_BUSINESS_RULE,
    "rule": CATEGORY_BUSINESS_RULE,
    "operating_experience": CATEGORY_OPERATING_EXPERIENCE,
    "experience": CATEGORY_OPERATING_EXPERIENCE,
    "retrospective": CATEGORY_RETROSPECTIVE,
    "review": CATEGORY_RETROSPECTIVE,
    "training": CATEGORY_TRAINING,
    "training_material": CATEGORY_TRAINING,
}


@dataclass(frozen=True)
class KnowledgeCategory:
    """Fixed knowledge classification for P22 knowledge foundation."""

    category_id: str
    name: str
    source_types: tuple[str, ...]
    description: str = ""
    schema_version: str = KNOWLEDGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        category_id = normalize_category(self.category_id)
        if not self.name.strip():
            raise ValueError("name is required.")
        source_types = tuple(item for item in self.source_types if item.strip())
        if not source_types:
            raise ValueError("source_types is required.")
        object.__setattr__(self, "category_id", category_id)
        object.__setattr__(self, "source_types", source_types)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_types"] = list(self.source_types)
        return payload


@dataclass(frozen=True)
class KnowledgeDocument:
    """Source document metadata for knowledge assets."""

    title: str
    category: str
    source: str
    content: str
    related_domain: str
    version: str
    document_id: str = field(default_factory=lambda: new_id("kdoc"))
    created_at: str = field(default_factory=now_iso)
    schema_version: str = KNOWLEDGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_non_empty(self.document_id, "document_id")
        _require_non_empty(self.title, "title")
        _require_non_empty(self.source, "source")
        _require_non_empty(self.content, "content")
        _require_non_empty(self.related_domain, "related_domain")
        _require_non_empty(self.version, "version")
        object.__setattr__(self, "category", normalize_category(self.category))

    def to_entry(self, *, knowledge_id: str | None = None) -> "KnowledgeEntry":
        return KnowledgeEntry(
            knowledge_id=knowledge_id or new_id("know"),
            title=self.title,
            category=self.category,
            source=self.source,
            content=self.content,
            related_domain=self.related_domain,
            version=self.version,
            created_at=self.created_at,
            document_id=self.document_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeEntry:
    """Single versioned knowledge item that can be attached to AI context."""

    title: str
    category: str
    source: str
    content: str
    related_domain: str
    version: str
    knowledge_id: str = field(default_factory=lambda: new_id("know"))
    created_at: str = field(default_factory=now_iso)
    updated_at: str = ""
    document_id: str = ""
    schema_version: str = KNOWLEDGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_non_empty(self.knowledge_id, "knowledge_id")
        _require_non_empty(self.title, "title")
        _require_non_empty(self.source, "source")
        _require_non_empty(self.content, "content")
        _require_non_empty(self.related_domain, "related_domain")
        _require_non_empty(self.version, "version")
        object.__setattr__(self, "category", normalize_category(self.category))

    def with_updates(self, **updates: Any) -> "KnowledgeEntry":
        payload = self.to_dict()
        payload.update(updates)
        payload.setdefault("updated_at", now_iso())
        return KnowledgeEntry(**payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeContext:
    """Read-only knowledge context reference for AI assistant usage."""

    entries: tuple[dict[str, Any], ...]
    source_domains: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    versions: tuple[str, ...] = ()
    schema_version: str = KNOWLEDGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        frozen_entries = tuple(copy.deepcopy(dict(item)) for item in self.entries)
        source_domains = self.source_domains or tuple(
            str(item.get("related_domain") or "") for item in frozen_entries if item.get("related_domain")
        )
        categories = self.categories or tuple(
            str(item.get("category") or "") for item in frozen_entries if item.get("category")
        )
        versions = self.versions or tuple(
            str(item.get("version") or "") for item in frozen_entries if item.get("version")
        )
        object.__setattr__(self, "entries", frozen_entries)
        object.__setattr__(self, "source_domains", tuple(dict.fromkeys(source_domains)))
        object.__setattr__(self, "categories", tuple(dict.fromkeys(categories)))
        object.__setattr__(self, "versions", tuple(dict.fromkeys(versions)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "entries": [copy.deepcopy(item) for item in self.entries],
            "source_domains": list(self.source_domains),
            "categories": list(self.categories),
            "versions": list(self.versions),
        }

    def to_ai_context_reference(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "context_type": "knowledge",
            "source_domains": list(self.source_domains),
            "knowledge_entries": [copy.deepcopy(item) for item in self.entries],
            "categories": list(self.categories),
            "versions": list(self.versions),
            "mutates_business_state": False,
            "external_vector_db_called": False,
        }


class KnowledgeRepository:
    """In-memory P22 knowledge foundation with audit and event hooks."""

    def __init__(
        self,
        *,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
    ):
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.master_data = master_data or OMSMasterData()
        self._entries: dict[str, KnowledgeEntry] = {}
        self._versions: dict[str, list[KnowledgeEntry]] = {}

    def create_entry(
        self,
        entry: KnowledgeEntry | KnowledgeDocument | dict[str, Any],
        *,
        actor_emp_id: str,
        reason: str,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        knowledge_entry = self._coerce_entry(entry)
        if knowledge_entry.knowledge_id in self._entries:
            raise ValueError(f"Duplicate knowledge_id: {knowledge_entry.knowledge_id}")
        actor = self.master_data.employee_by_emp(actor_emp_id)
        self._entries[knowledge_entry.knowledge_id] = knowledge_entry
        self._versions[knowledge_entry.knowledge_id] = [knowledge_entry]
        audit_record = self._audit(
            action="knowledge.created",
            actor=actor,
            entry=knowledge_entry,
            reason=reason,
            correlation_id=correlation_id,
        )
        event = self._event(
            action="created",
            actor=actor,
            entry=knowledge_entry,
            correlation_id=correlation_id,
        )
        return self._result(knowledge_entry, audit_record, event, "created")

    def update_entry(
        self,
        knowledge_id: str,
        *,
        actor_emp_id: str,
        reason: str,
        correlation_id: str = "",
        title: str | None = None,
        category: str | None = None,
        source: str | None = None,
        content: str | None = None,
        related_domain: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required.")
        current = self._require_entry(knowledge_id)
        actor = self.master_data.employee_by_emp(actor_emp_id)
        updates: dict[str, Any] = {
            "title": title if title is not None else current.title,
            "category": normalize_category(category) if category is not None else current.category,
            "source": source if source is not None else current.source,
            "content": content if content is not None else current.content,
            "related_domain": related_domain if related_domain is not None else current.related_domain,
            "version": version if version is not None else next_version(current.version),
            "updated_at": now_iso(),
        }
        updated = current.with_updates(**updates)
        self._entries[knowledge_id] = updated
        self._versions.setdefault(knowledge_id, []).append(updated)
        audit_record = self._audit(
            action="knowledge.updated",
            actor=actor,
            entry=updated,
            reason=reason,
            correlation_id=correlation_id,
        )
        event = self._event(
            action="updated",
            actor=actor,
            entry=updated,
            correlation_id=correlation_id,
        )
        return self._result(updated, audit_record, event, "updated")

    def get_entry(self, knowledge_id: str) -> dict[str, Any]:
        return self._require_entry(knowledge_id).to_dict()

    def entries(self, *, category: str | None = None, related_domain: str | None = None) -> list[dict[str, Any]]:
        rows = list(self._entries.values())
        if category is not None:
            normalized = normalize_category(category)
            rows = [entry for entry in rows if entry.category == normalized]
        if related_domain is not None:
            rows = [entry for entry in rows if entry.related_domain == related_domain]
        return [entry.to_dict() for entry in rows]

    def classify(self, category: str) -> list[dict[str, Any]]:
        return self.entries(category=category)

    def versions(self, knowledge_id: str) -> list[dict[str, Any]]:
        self._require_entry(knowledge_id)
        return [entry.to_dict() for entry in self._versions.get(knowledge_id, [])]

    def build_context(
        self,
        *,
        category: str | None = None,
        related_domain: str | None = None,
    ) -> KnowledgeContext:
        return KnowledgeContext(tuple(self.entries(category=category, related_domain=related_domain)))

    def _require_entry(self, knowledge_id: str) -> KnowledgeEntry:
        if knowledge_id not in self._entries:
            raise KeyError(f"Unknown knowledge_id: {knowledge_id}")
        return self._entries[knowledge_id]

    @staticmethod
    def _coerce_entry(entry: KnowledgeEntry | KnowledgeDocument | dict[str, Any]) -> KnowledgeEntry:
        if isinstance(entry, KnowledgeEntry):
            return entry
        if isinstance(entry, KnowledgeDocument):
            return entry.to_entry()
        return KnowledgeEntry(**dict(entry))

    def _audit(
        self,
        *,
        action: str,
        actor: Employee,
        entry: KnowledgeEntry,
        reason: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="knowledge",
            action=action,
            action_type=action,
            reason=reason,
            result="success",
            target_type="knowledge",
            target_id=entry.knowledge_id,
            correlation_id=correlation_id,
            metadata={
                "knowledge_id": entry.knowledge_id,
                "category": entry.category,
                "source": entry.source,
                "related_domain": entry.related_domain,
                "version": entry.version,
                "mutates_business_state": False,
                "external_vector_db_called": False,
            },
        )

    def _event(
        self,
        *,
        action: str,
        actor: Employee,
        entry: KnowledgeEntry,
        correlation_id: str,
    ) -> dict[str, Any]:
        payload = {
            "knowledge_id": entry.knowledge_id,
            "title": entry.title,
            "category": entry.category,
            "source": entry.source,
            "related_domain": entry.related_domain,
            "version": entry.version,
            "action": action,
            "mutates_business_state": False,
            "external_vector_db_called": False,
        }
        event = OMSEvent(
            event_type="knowledge.available",
            source_module="knowledge",
            subject=entry.knowledge_id,
            action=action,
            emp_id=actor.emp,
            actor_name=actor.name,
            correlation_id=correlation_id,
            payload=payload,
        )
        return self.event_bus.publish(event)

    @staticmethod
    def _result(
        entry: KnowledgeEntry,
        audit_record: dict[str, Any],
        event: dict[str, Any],
        action: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": KNOWLEDGE_SCHEMA_VERSION,
            "action": action,
            "entry": entry.to_dict(),
            "audit_record": audit_record,
            "event": event,
            "mutates_business_state": False,
            "external_vector_db_called": False,
        }


def default_categories() -> list[KnowledgeCategory]:
    return [
        KnowledgeCategory(category_id=category, name=category, source_types=CATEGORY_SOURCE_TYPES[category])
        for category in sorted(SUPPORTED_KNOWLEDGE_CATEGORIES)
    ]


def category_for_source(source: str) -> str:
    key = source.strip().lower().replace(" ", "_").replace("-", "_")
    if key not in SOURCE_CATEGORY_ALIASES:
        raise ValueError(f"Unsupported knowledge source: {source}")
    return SOURCE_CATEGORY_ALIASES[key]


def normalize_category(category: str) -> str:
    value = category.strip()
    if value not in SUPPORTED_KNOWLEDGE_CATEGORIES:
        raise ValueError(f"Unsupported knowledge category: {category}")
    return value


def next_version(version: str) -> str:
    parts = version.strip().split(".")
    if len(parts) >= 2 and parts[-1].isdigit():
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    if version.strip().isdigit():
        return f"{version.strip()}.1"
    return f"{version.strip()}.1"


def _require_non_empty(value: str, field_name: str) -> None:
    if not str(value).strip():
        raise ValueError(f"{field_name} is required.")
