import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.knowledge import CATEGORY_BUSINESS_RULE, CATEGORY_POLICY, CATEGORY_SOP, KnowledgeEntry, KnowledgeRepository
from oms_v1.knowledge_retrieval import (
    KnowledgeQuery,
    KnowledgeRetrievalEngine,
    KnowledgeRetriever,
    matches_to_ai_context_reference,
)
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class KnowledgeRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_organization_master_data.md"
        identity_path = root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.repository = KnowledgeRepository(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )
        self.engine = KnowledgeRetrievalEngine(
            repository=self.repository,
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )
        self._seed_knowledge()

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_knowledge(self):
        entries = [
            KnowledgeEntry(
                knowledge_id="know_room_sop_001",
                title="Room check-in SOP",
                category=CATEGORY_SOP,
                source="sop",
                content="Confirm room readiness and maintenance status before check-in.",
                related_domain="Room",
                version="1.0",
            ),
            KnowledgeEntry(
                knowledge_id="know_fin_rule_001",
                title="Receivable evidence rule",
                category=CATEGORY_BUSINESS_RULE,
                source="business_rule",
                content="Receivable records require source evidence and settlement traceability.",
                related_domain="Finance",
                version="2.0",
            ),
            KnowledgeEntry(
                knowledge_id="know_fin_policy_001",
                title="Finance settlement policy",
                category=CATEGORY_POLICY,
                source="policy_file",
                content="Settlement must keep payment source and approval evidence.",
                related_domain="Finance",
                version="1.3",
            ),
        ]
        for entry in entries:
            self.repository.create_entry(
                entry,
                actor_emp_id="EMP001",
                reason=f"Seed {entry.knowledge_id} for retrieval tests.",
            )
        self.audit = AuditEngine(Path(self.tmp.name) / "retrieval_audit")
        self.bus = EventBus()
        self.engine = KnowledgeRetrievalEngine(
            repository=self.repository,
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )

    def test_query_requires_actor_query_and_valid_category(self):
        query = KnowledgeQuery(
            actor_emp_id="EMP001",
            query="room readiness",
            category=CATEGORY_SOP,
            related_domain="Room",
            context_scope=("operations",),
            correlation_id="retrieval_corr_001",
        )

        self.assertEqual(query.category, CATEGORY_SOP)
        self.assertEqual(query.to_dict()["context_scope"], ["operations"])
        with self.assertRaises(ValueError):
            KnowledgeQuery(actor_emp_id="", query="room")
        with self.assertRaises(ValueError):
            KnowledgeQuery(actor_emp_id="EMP001", query="")
        with self.assertRaises(ValueError):
            KnowledgeQuery(actor_emp_id="EMP001", query="room", category="generated")

    def test_keyword_retriever_ranks_traceable_matches(self):
        query = KnowledgeQuery(actor_emp_id="EMP001", query="room check-in readiness", related_domain="Room")
        matches = KnowledgeRetriever().retrieve(query, self.repository.entries())

        self.assertEqual(matches[0].knowledge_id, "know_room_sop_001")
        self.assertGreater(matches[0].relevance_score, 0)
        self.assertEqual(matches[0].source, "sop")
        self.assertEqual(matches[0].version, "1.0")
        self.assertEqual(matches[0].related_domains, ("Room",))
        self.assertIn("room", matches[0].matched_terms)

    def test_category_and_domain_filters_limit_results(self):
        query = KnowledgeQuery(
            actor_emp_id="EMP001",
            query="source evidence traceability",
            category=CATEGORY_BUSINESS_RULE,
            related_domain="Finance",
            context_scope=("funds",),
        )

        result = self.engine.retrieve(query)

        self.assertEqual(result["match_count"], 1)
        self.assertEqual(result["matched_knowledge"][0]["knowledge_id"], "know_fin_rule_001")
        self.assertEqual(result["matched_knowledge"][0]["category"], CATEGORY_BUSINESS_RULE)
        self.assertEqual(result["matched_knowledge"][0]["related_domains"], ["Finance"])

    def test_engine_writes_audit_and_event(self):
        result = self.engine.retrieve(
            KnowledgeQuery(
                actor_emp_id="EMP001",
                query="settlement evidence",
                related_domain="Finance",
                correlation_id="retrieval_corr_002",
            )
        )

        audit_events = self.audit.events(sort_by_time=False)
        events = self.bus.events()

        self.assertEqual([item["action"] for item in audit_events], ["knowledge.query", "knowledge.retrieve"])
        self.assertEqual(audit_events[1]["metadata"]["match_count"], result["match_count"])
        self.assertEqual([item["event_type"] for item in events], ["knowledge.retrieval.completed"])
        self.assertEqual(events[0]["payload"]["match_count"], result["match_count"])
        self.assertFalse(events[0]["payload"]["mutates_business_state"])
        self.assertFalse(events[0]["payload"]["external_vector_db_called"])
        self.assertFalse(events[0]["payload"]["external_search_called"])

    def test_retrieval_result_can_enter_ai_context(self):
        result = self.engine.retrieve(
            KnowledgeQuery(actor_emp_id="EMP001", query="payment source approval", related_domain="Finance")
        )
        ai_reference = result["ai_context_reference"]

        self.assertEqual(ai_reference["context_type"], "knowledge_retrieval")
        self.assertEqual(ai_reference["source_domains"], ["Finance"])
        self.assertGreaterEqual(len(ai_reference["knowledge_entries"]), 1)
        self.assertIn("know_fin_policy_001", ai_reference["matched_knowledge_ids"])
        self.assertFalse(ai_reference["mutates_business_state"])
        self.assertFalse(ai_reference["modifies_knowledge_content"])

    def test_retrieval_is_read_only_and_handles_no_matches(self):
        before = copy.deepcopy(self.repository.entries())

        result = self.engine.retrieve(KnowledgeQuery(actor_emp_id="EMP001", query="kitchen menu allergy"))

        self.assertEqual(self.repository.entries(), before)
        self.assertEqual(result["match_count"], 0)
        self.assertEqual(result["matched_knowledge"], [])
        self.assertFalse(result["mutates_business_state"])
        self.assertFalse(result["modifies_knowledge_content"])
        self.assertFalse(result["external_vector_db_called"])
        self.assertFalse(result["external_search_called"])

    def test_matches_to_ai_context_reference_is_traceable(self):
        matches = KnowledgeRetriever().retrieve(
            KnowledgeQuery(actor_emp_id="EMP001", query="room maintenance"),
            self.repository.entries(),
        )
        reference = matches_to_ai_context_reference(matches)

        self.assertIn("know_room_sop_001", reference["matched_knowledge_ids"])
        self.assertEqual(reference["source_domains"], ["Room"])
        self.assertEqual(reference["versions"], ["1.0"])


if __name__ == "__main__":
    unittest.main()
