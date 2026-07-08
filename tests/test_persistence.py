import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.persistence import (
    DataRepository,
    EntitySerializer,
    PersistenceManager,
    StorageAdapter,
)
from oms_v1.room_engine import RoomRecord


@dataclass
class SampleDomainObject:
    sample_id: str
    status: str


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.storage = StorageAdapter(self.root / "storage")
        self.repository = DataRepository(storage=self.storage)
        self.audit = AuditEngine(self.root / "audit")
        self.manager = PersistenceManager(repository=self.repository, audit=self.audit)

    def tearDown(self):
        self.tmp.cleanup()

    def test_entity_serializer_supports_dict_dataclass_and_to_dict_object(self):
        serializer = EntitySerializer()
        room = RoomRecord(room_number="A-101", room_type="single", floor="1", created_by_emp="EMP008")

        self.assertEqual(serializer.serialize({"id": "dict_001"})["id"], "dict_001")
        self.assertEqual(serializer.serialize(SampleDomainObject("sample_001", "active"))["sample_id"], "sample_001")
        self.assertEqual(serializer.serialize(room)["room_number"], "A-101")

    def test_repository_saves_and_reads_domain_object(self):
        record = self.repository.save(
            entity_type="Room",
            entity_id="room_001",
            entity={"room_id": "room_001", "status": "AVAILABLE"},
            audit_id="audit_001",
            event_id="event_001",
            correlation_id="corr_001",
        )

        loaded = self.repository.get(entity_type="Room", entity_id="room_001")

        self.assertEqual(record["version"], 1)
        self.assertEqual(loaded["payload"]["status"], "AVAILABLE")
        self.assertEqual(loaded["audit_id"], "audit_001")
        self.assertEqual(loaded["event_id"], "event_001")
        self.assertEqual(loaded["correlation_id"], "corr_001")

    def test_repository_records_versions(self):
        self.repository.save(
            entity_type="Room",
            entity_id="room_001",
            entity={"room_id": "room_001", "status": "AVAILABLE"},
            audit_id="audit_001",
            event_id="event_001",
            correlation_id="corr_001",
        )
        self.repository.save(
            entity_type="Room",
            entity_id="room_001",
            entity={"room_id": "room_001", "status": "RESERVED"},
            audit_id="audit_002",
            event_id="event_002",
            correlation_id="corr_002",
        )

        latest = self.repository.get(entity_type="Room", entity_id="room_001")
        first = self.repository.get(entity_type="Room", entity_id="room_001", version=1)
        versions = self.repository.versions(entity_type="Room", entity_id="room_001")

        self.assertEqual(latest["version"], 2)
        self.assertEqual(latest["payload"]["status"], "RESERVED")
        self.assertEqual(first["payload"]["status"], "AVAILABLE")
        self.assertEqual([record["version"] for record in versions], [1, 2])

    def test_manager_saves_with_audit_and_event_linkage(self):
        result = self.manager.save_domain_object(
            entity_type="Room",
            entity_id="room_001",
            entity={"room_id": "room_001", "status": "AVAILABLE"},
            actor_emp_id="EMP008",
            actor_name="Store Manager",
            reason="Persist room snapshot for P17 test.",
            event_id="event_001",
            correlation_id="corr_001",
        )

        record = result["record"]
        self.assertFalse(result["mutates_business_state"])
        self.assertEqual(record["audit_id"], result["audit"]["audit_id"])
        self.assertEqual(record["event_id"], "event_001")
        self.assertEqual(record["correlation_id"], "corr_001")
        self.assertEqual(self.audit.events(sort_by_time=False)[0]["action"], "persistence.save")

    def test_manager_reads_latest_and_specific_version(self):
        self.manager.save_domain_object(
            entity_type="Room",
            entity_id="room_001",
            entity={"room_id": "room_001", "status": "AVAILABLE"},
            actor_emp_id="EMP008",
            actor_name="Store Manager",
            reason="Persist first version.",
            event_id="event_001",
            correlation_id="corr_001",
        )
        self.manager.save_domain_object(
            entity_type="Room",
            entity_id="room_001",
            entity={"room_id": "room_001", "status": "RESERVED"},
            actor_emp_id="EMP008",
            actor_name="Store Manager",
            reason="Persist second version.",
            event_id="event_002",
            correlation_id="corr_002",
        )

        latest = self.manager.read_domain_object(entity_type="Room", entity_id="room_001")
        first = self.manager.read_domain_object(entity_type="Room", entity_id="room_001", version=1)
        history = self.manager.history(entity_type="Room", entity_id="room_001")

        self.assertEqual(latest["record"]["version"], 2)
        self.assertEqual(latest["record"]["payload"]["status"], "RESERVED")
        self.assertEqual(first["record"]["payload"]["status"], "AVAILABLE")
        self.assertEqual(len(history["versions"]), 2)

    def test_missing_entity_and_version_raise_key_error(self):
        with self.assertRaises(KeyError):
            self.repository.get(entity_type="Room", entity_id="missing")

        self.repository.save(
            entity_type="Room",
            entity_id="room_001",
            entity={"room_id": "room_001"},
            audit_id="audit_001",
            event_id="event_001",
            correlation_id="corr_001",
        )
        with self.assertRaises(KeyError):
            self.repository.get(entity_type="Room", entity_id="room_001", version=99)

    def test_persistence_requires_audit_event_and_correlation_links(self):
        with self.assertRaises(ValueError):
            self.repository.save(
                entity_type="Room",
                entity_id="room_001",
                entity={"room_id": "room_001"},
                audit_id="",
                event_id="event_001",
                correlation_id="corr_001",
            )
        with self.assertRaises(ValueError):
            self.repository.save(
                entity_type="Room",
                entity_id="room_001",
                entity={"room_id": "room_001"},
                audit_id="audit_001",
                event_id="",
                correlation_id="corr_001",
            )


if __name__ == "__main__":
    unittest.main()
