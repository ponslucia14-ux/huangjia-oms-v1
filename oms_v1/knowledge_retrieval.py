from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .knowledge import KnowledgeRepository, normalize_category
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


KNOWLEDGE_RETRIEVAL_SCHEMA_VERSION = "oms.v1.knowledge_retrieval"


@dataclass(frozen=True)
class KnowledgeQuery:
    """Read-only keyword retrieval request for P23."""

    actor_emp_id: str
    query: str
    category: str = ""
    related_domain: str = ""
    context_scope: tuple[str, ...] = ()
    query_id: str = field(default_factory=lambda: new_id("kqry"))
    correlation_id: str = ""
    requested_at: str = field(default_factory=now_iso)
    schema_version: str = KNOWLEDGE_RETRIEVAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.query_id.strip():
            raise ValueError("query_id is required.")
        if not self.actor_emp_id.strip():
            raise ValueError("actor_emp_id is required.")
        if not self.query.strip():
            raise ValueError("query is required.")
        category = normalize_category(self.category) if self.category.strip() else ""
        context_scope = tuple(item for item in self.context_scope if item.strip())
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "context_scope", context_scope)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["context_scope"] = list(self.context_scope)
        return payload


@dataclass(frozen=True)
class KnowledgeMatch:
    """Traceable retrieval match that can be passed to AI context."""

    knowledge_id: str
    title: str
    category: str
    relevance_score: float
    source: str
    version: str
    related_domains: tuple[str, ...]
    matched_terms: tuple[str, ...] = ()
    content_preview: str = ""
    schema_version: str = KNOWLEDGE_RETRIEVAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.knowledge_id.strip():
            raise ValueError("knowledge_id is required.")
        if not self.title.strip():
            raise ValueError("title is required.")
        if not self.source.strip():
            raise ValueError("source is required.")
        if not self.version.strip():
            raise ValueError("version is required.")
        if self.relevance_score < 0:
            raise ValueError("relevance_score cannot be negative.")
        object.__setattr__(self, "category", normalize_category(self.category))
        object.__setattr__(self, "related_domains", tuple(dict.fromkeys(self.related_domains)))
        object.__setattr__(self, "matched_terms", tuple(dict.fromkeys(self.matched_terms)))
        object.__setattr__(self, "relevance_score", round(float(self.relevance_score), 4))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["related_domains"] = list(self.related_domains)
        payload["matched_terms"] = list(self.matched_terms)
        return payload


class KnowledgeRetriever:
    """Pure keyword retriever. It does not mutate knowledge or business state."""

    def retrieve(self, query: KnowledgeQuery, entries: list[dict[str, Any]]) -> list[KnowledgeMatch]:
        terms = _terms(query.query, query.context_scope)
        matches: list[KnowledgeMatch] = []
        for entry in copy.deepcopy(entries):
            if query.category and entry.get("category") != query.category:
                continue
            if query.related_domain and entry.get("related_domain") != query.related_domain:
                continue
            match = self._match_entry(query, entry, terms)
            if match is not None:
                matches.append(match)
        return sorted(
            matches,
            key=lambda item: (-item.relevance_score, item.knowledge_id),
        )

    @staticmethod
    def _match_entry(
        query: KnowledgeQuery,
        entry: dict[str, Any],
        terms: tuple[str, ...],
    ) -> KnowledgeMatch | None:
        title = str(entry.get("title") or "")
        content = str(entry.get("content") or "")
        source = str(entry.get("source") or "")
        category = str(entry.get("category") or "")
        related_domain = str(entry.get("related_domain") or "")
        searchable = " ".join([title, content, source, category, related_domain]).lower()
        title_text = title.lower()
        content_text = content.lower()
        matched_terms = tuple(term for term in terms if term in searchable)

        score = 0.0
        if matched_terms:
            score += len(matched_terms) / max(len(terms), 1) * 0.55
            score += len([term for term in matched_terms if term in title_text]) * 0.12
            score += len([term for term in matched_terms if term in content_text]) * 0.05
        if query.query.strip().lower() in searchable:
            score += 0.2
        if query.category and category == query.category:
            score += 0.1
        if query.related_domain and related_domain == query.related_domain:
            score += 0.1
        if not matched_terms and not query.category and not query.related_domain:
            return None
        if score <= 0:
            return None
        return KnowledgeMatch(
            knowledge_id=str(entry.get("knowledge_id") or ""),
            title=title,
            category=category,
            relevance_score=min(score, 1.0),
            source=source,
            version=str(entry.get("version") or ""),
            related_domains=(related_domain,) if related_domain else (),
            matched_terms=matched_terms,
            content_preview=_preview(content),
        )


class KnowledgeRetrievalEngine:
    """Audited retrieval orchestrator that outputs traceable AI context references."""

    def __init__(
        self,
        *,
        repository: KnowledgeRepository | None = None,
        retriever: KnowledgeRetriever | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
    ):
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.repository = repository or KnowledgeRepository(
            audit=self.audit,
            event_bus=self.event_bus,
            master_data=self.master_data,
        )
        self.retriever = retriever or KnowledgeRetriever()

    def retrieve(
        self,
        query: KnowledgeQuery | dict[str, Any],
        *,
        knowledge_entries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        retrieval_query = query if isinstance(query, KnowledgeQuery) else KnowledgeQuery(**query)
        actor = self.master_data.employee_by_emp(retrieval_query.actor_emp_id)
        source_entries = copy.deepcopy(
            knowledge_entries
            if knowledge_entries is not None
            else self.repository.entries(
                category=retrieval_query.category or None,
                related_domain=retrieval_query.related_domain or None,
            )
        )
        matches = self.retriever.retrieve(retrieval_query, source_entries)
        query_audit = self._audit_query(retrieval_query, actor)
        retrieve_audit = self._audit_retrieve(retrieval_query, actor, matches)
        event = self._event_completed(retrieval_query, actor, matches)
        return {
            "schema_version": KNOWLEDGE_RETRIEVAL_SCHEMA_VERSION,
            "query": retrieval_query.to_dict(),
            "matched_knowledge": [match.to_dict() for match in matches],
            "match_count": len(matches),
            "source_entry_count": len(source_entries),
            "ai_context_reference": matches_to_ai_context_reference(matches),
            "audit_records": [query_audit, retrieve_audit],
            "event": event,
            "mutates_business_state": False,
            "modifies_knowledge_content": False,
            "external_vector_db_called": False,
            "external_search_called": False,
        }

    def _audit_query(self, query: KnowledgeQuery, actor: Employee) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="knowledge_retrieval",
            action="knowledge.query",
            action_type="knowledge.query",
            reason="Knowledge retrieval query requested.",
            result="success",
            target_type="knowledge_query",
            target_id=query.query_id,
            correlation_id=query.correlation_id,
            metadata={
                "query_id": query.query_id,
                "query": query.query,
                "category": query.category,
                "related_domain": query.related_domain,
                "context_scope": list(query.context_scope),
                "mutates_business_state": False,
                "modifies_knowledge_content": False,
                "external_vector_db_called": False,
                "external_search_called": False,
            },
        )

    def _audit_retrieve(
        self,
        query: KnowledgeQuery,
        actor: Employee,
        matches: list[KnowledgeMatch],
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="knowledge_retrieval",
            action="knowledge.retrieve",
            action_type="knowledge.retrieve",
            reason="Knowledge retrieval completed.",
            result="success",
            target_type="knowledge_retrieval",
            target_id=query.query_id,
            correlation_id=query.correlation_id,
            metadata={
                "query_id": query.query_id,
                "match_count": len(matches),
                "matched_knowledge_ids": [match.knowledge_id for match in matches],
                "mutates_business_state": False,
                "modifies_knowledge_content": False,
                "external_vector_db_called": False,
                "external_search_called": False,
            },
        )

    def _event_completed(
        self,
        query: KnowledgeQuery,
        actor: Employee,
        matches: list[KnowledgeMatch],
    ) -> dict[str, Any]:
        event = OMSEvent(
            event_type="knowledge.retrieval.completed",
            source_module="knowledge_retrieval",
            subject=query.query_id,
            action="retrieve",
            emp_id=actor.emp,
            actor_name=actor.name,
            correlation_id=query.correlation_id,
            payload={
                "query_id": query.query_id,
                "match_count": len(matches),
                "matched_knowledge_ids": [match.knowledge_id for match in matches],
                "category": query.category,
                "related_domain": query.related_domain,
                "mutates_business_state": False,
                "modifies_knowledge_content": False,
                "external_vector_db_called": False,
                "external_search_called": False,
            },
        )
        return self.event_bus.publish(event)


def matches_to_ai_context_reference(matches: list[KnowledgeMatch]) -> dict[str, Any]:
    domains: list[str] = []
    categories: list[str] = []
    versions: list[str] = []
    entries: list[dict[str, Any]] = []
    for match in matches:
        match_dict = match.to_dict()
        entries.append(match_dict)
        domains.extend(match.related_domains)
        categories.append(match.category)
        versions.append(match.version)
    return {
        "schema_version": KNOWLEDGE_RETRIEVAL_SCHEMA_VERSION,
        "context_type": "knowledge_retrieval",
        "source_domains": list(dict.fromkeys(domains)),
        "categories": list(dict.fromkeys(categories)),
        "versions": list(dict.fromkeys(versions)),
        "matched_knowledge_ids": [match.knowledge_id for match in matches],
        "knowledge_entries": entries,
        "mutates_business_state": False,
        "modifies_knowledge_content": False,
        "external_vector_db_called": False,
        "external_search_called": False,
    }


def _terms(query: str, context_scope: tuple[str, ...]) -> tuple[str, ...]:
    raw = " ".join([query, *context_scope]).lower()
    tokens = [item for item in re.split(r"[^a-z0-9_\u4e00-\u9fff]+", raw) if item]
    return tuple(dict.fromkeys(tokens))


def _preview(content: str, limit: int = 120) -> str:
    clean = " ".join(content.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."
