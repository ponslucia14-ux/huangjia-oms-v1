import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.knowledge import (
    CATEGORY_BUSINESS_RULE,
    CATEGORY_POLICY,
    CATEGORY_SOP,
    CATEGORY_TRAINING,
    SUPPORTED_KNOWLEDGE_CATEGORIES,
    KnowledgeContext,
    KnowledgeDocument,
    KnowledgeEntry,
    KnowledgeRepository,
    category_for_source,
    default_categories,
)
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class KnowledgeLayerTests(unittest.TestCase):
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

    def tearDown(self):
        self.tmp.cleanup()

    def _entry(self, **overrides):
        payload = {
            "knowledge_id": "know_room_sop_001",
            "title": "Room check-in SOP",
            "category": CATEGORY_SOP,
            "source": "sop",
            "content": "Confirm room readiness before check-in.",
            "related_domain": "Room",
            "version": "1.0",
        }
        payload.update(overrides)
        return KnowledgeEntry(**payload)

    def test_categories_and_document_model_are_fixed(self):
        categories = default_categories()
        category_ids = {item.category_id for item in categories}
        document = KnowledgeDocument(
            document_id="kdoc_policy_001",
            title="Finance policy",
            category=CATEGORY_POLICY,
            source="policy_file",
            content="Payment must be recorded before settlement.",
            related_domain="Finance",
            version="1.0",
            created_at="2026-07-09T08:00:00",
        )

        self.assertEqual(category_ids, SUPPORTED_KNOWLEDGE_CATEGORIES)
        self.assertEqual(category_for_source("SOP"), CATEGORY_SOP)
        self.assertEqual(document.to_dict()["knowledge_id"] if "knowledge_id" in document.to_dict() else document.document_id, "kdoc_policy_001")
        self.assertEqual(document.to_entry(knowledge_id="know_policy_001").knowledge_id, "know_policy_001")
        with self.assertRaises(ValueError):
            KnowledgeDocument(
                title="Bad category",
                category="runtime_generated",
                source="unknown",
                content="x",
                related_domain="Room",
                version="1.0",
            )

    def test_create_entry_writes_audit_and_event(self):
        result = self.repository.create_entry(
            self._entry(),
            actor_emp_id="EMP001",
            reason="Create knowledge for room operation.",
            correlation_id="know_corr_001",
        )

        self.assertEqual(result["entry"]["knowledge_id"], "know_room_sop_001")
        self.assertFalse(result["mutates_business_state"])
        self.assertFalse(result["external_vector_db_called"])
        self.assertEqual(result["audit_record"]["action"], "knowledge.created")
        self.assertEqual(result["audit_record"]["target_id"], "know_room_sop_001")
        self.assertEqual(result["event"]["event"]["event_type"], "knowledge.available")
        self.assertEqual(result["event"]["event"]["payload"]["action"], "created")
        self.assertEqual(self.repository.get_entry("know_room_sop_001")["title"], "Room check-in SOP")

    def test_update_entry_keeps_version_history(self):
        self.repository.create_entry(
            self._entry(),
            actor_emp_id="EMP001",
            reason="Create SOP before update.",
            correlation_id="know_corr_002",
        )

        result = self.repository.update_entry(
            "know_room_sop_001",
            actor_emp_id="EMP001",
            reason="Update room SOP content.",
            content="Confirm room readiness and maintenance status before check-in.",
            correlation_id="know_corr_003",
        )

        versions = self.repository.versions("know_room_sop_001")
        self.assertEqual(result["entry"]["version"], "1.1")
        self.assertEqual(len(versions), 2)
        self.assertEqual([item["version"] for item in versions], ["1.0", "1.1"])
        self.assertEqual([item["action"] for item in self.audit.events(sort_by_time=False)], ["knowledge.created", "knowledge.updated"])
        self.assertEqual([item["event_type"] for item in self.bus.events()], ["knowledge.available", "knowledge.available"])
        with self.assertRaises(ValueError):
            self.repository.update_entry("know_room_sop_001", actor_emp_id="EMP001", reason="")

    def test_read_classify_and_filter_by_domain(self):
        self.repository.create_entry(
            self._entry(),
            actor_emp_id="EMP001",
            reason="Create room SOP.",
        )
        self.repository.create_entry(
            self._entry(
                knowledge_id="know_fin_rule_001",
                title="Receivable rule",
                category=CATEGORY_BUSINESS_RULE,
                source="business_rule",
                content="Receivable records require source evidence.",
                related_domain="Finance",
            ),
            actor_emp_id="EMP001",
            reason="Create finance rule.",
        )

        sop_entries = self.repository.classify(CATEGORY_SOP)
        room_entries = self.repository.entries(related_domain="Room")

        self.assertEqual([item["knowledge_id"] for item in sop_entries], ["know_room_sop_001"])
        self.assertEqual([item["related_domain"] for item in room_entries], ["Room"])
        self.assertEqual(self.repository.entries(category=CATEGORY_BUSINESS_RULE)[0]["title"], "Receivable rule")

    def test_knowledge_context_can_feed_ai_context_as_read_only_reference(self):
        self.repository.create_entry(
            self._entry(),
            actor_emp_id="EMP001",
            reason="Create room knowledge for AI context.",
        )
        self.repository.create_entry(
            self._entry(
                knowledge_id="know_room_training_001",
                title="Room training note",
                category=CATEGORY_TRAINING,
                source="training_material",
                content="Room staff should check pending maintenance before assignment.",
                related_domain="Room",
                version="2.0",
            ),
            actor_emp_id="EMP001",
            reason="Create room training knowledge for AI context.",
        )

        context = self.repository.build_context(related_domain="Room")
        ai_reference = context.to_ai_context_reference()

        self.assertIsInstance(context, KnowledgeContext)
        self.assertEqual(ai_reference["context_type"], "knowledge")
        self.assertEqual(ai_reference["source_domains"], ["Room"])
        self.assertEqual(set(ai_reference["categories"]), {CATEGORY_SOP, CATEGORY_TRAINING})
        self.assertEqual(len(ai_reference["knowledge_entries"]), 2)
        self.assertFalse(ai_reference["mutates_business_state"])
        self.assertFalse(ai_reference["external_vector_db_called"])

    def test_repository_rejects_duplicate_and_unknown_entries(self):
        self.repository.create_entry(
            self._entry(),
            actor_emp_id="EMP001",
            reason="Create unique knowledge entry.",
        )

        with self.assertRaises(ValueError):
            self.repository.create_entry(
                self._entry(),
                actor_emp_id="EMP001",
                reason="Duplicate should be rejected.",
            )
        with self.assertRaises(KeyError):
            self.repository.get_entry("missing_knowledge")


if __name__ == "__main__":
    unittest.main()
