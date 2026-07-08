import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine, AuditEvent, AuditReader, AuditStorage, AuditWriter


class AuditLogTests(unittest.TestCase):
    def _storage(self, tmp: str) -> AuditStorage:
        return AuditStorage(Path(tmp) / "audit")

    def test_writer_appends_without_overwriting_existing_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = self._storage(tmp)
            writer = AuditWriter(storage)

            first = writer.write(emp_id="EMP001", actor_name="石磊", module="bootstrap", action="start", reason="启动系统", result="ok")
            first_size = storage.audit_path.stat().st_size
            second = writer.write(emp_id="EMP004", actor_name="刘晶", module="finance", action="review", reason="复核收款", result="pending")
            second_size = storage.audit_path.stat().st_size
            rows = storage.read_all()

            self.assertGreater(second_size, first_size)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["audit_id"], first["audit_id"])
            self.assertEqual(rows[1]["audit_id"], second["audit_id"])
            self.assertEqual(rows[1]["reason"], "复核收款")

    def test_storage_forbids_overwrite_delete_and_truncate(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = self._storage(tmp)
            storage.append(AuditEvent(emp_id="EMP001", actor_name="石磊", module="bootstrap", action="start", reason="启动系统", result="ok"))

            with self.assertRaises(PermissionError):
                storage.overwrite([])
            with self.assertRaises(PermissionError):
                storage.delete("anything")
            with self.assertRaises(PermissionError):
                storage.truncate()
            self.assertEqual(len(storage.read_all()), 1)

    def test_reader_sorts_by_time_and_queries_emp_and_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = self._storage(tmp)
            storage.append(
                AuditEvent(
                    emp_id="EMP004",
                    actor_name="刘晶",
                    module="finance",
                    action="review",
                    reason="复核收款",
                    result="pending",
                    timestamp="2026-07-08T12:03:00+08:00",
                )
            )
            storage.append(
                AuditEvent(
                    emp_id="EMP001",
                    actor_name="石磊",
                    module="bootstrap",
                    action="start",
                    reason="启动系统",
                    result="ok",
                    timestamp="2026-07-08T12:01:00+08:00",
                )
            )
            storage.append(
                AuditEvent(
                    emp_id="EMP004",
                    actor_name="刘晶",
                    module="finance",
                    action="approve",
                    reason="审批付款",
                    result="ok",
                    timestamp="2026-07-08T12:02:00+08:00",
                )
            )

            reader = AuditReader(storage)
            sorted_events = reader.all()
            finance_events = reader.query(module="finance")
            emp_events = reader.query(emp_id="EMP004")

            self.assertEqual([event["action"] for event in sorted_events], ["start", "approve", "review"])
            self.assertEqual([event["module"] for event in finance_events], ["finance", "finance"])
            self.assertEqual([event["action"] for event in emp_events], ["approve", "review"])

    def test_audit_engine_facade_records_and_summarizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = AuditEngine(Path(tmp) / "audit")

            engine.record(emp_id="EMP008", actor_name="刘芳羽", module="room", action="assign_room", reason="生成排房草案", result="draft")
            engine.record(emp_id="EMP008", actor_name="刘芳羽", module="room", action="confirm_room", reason="确认排房", result="ok")

            self.assertEqual(len(engine.events(emp_id="EMP008")), 2)
            self.assertEqual(len(engine.events(module="room")), 2)
            summary = engine.summary()
            self.assertEqual(summary["event_count"], 2)
            self.assertEqual(summary["modules"], ["room"])
            self.assertEqual(summary["employees"], ["EMP008"])
            self.assertTrue(summary["append_only"])

    def test_reason_is_required_for_modification_events(self):
        with self.assertRaises(ValueError):
            AuditEvent(emp_id="EMP008", actor_name="刘芳羽", module="room", action="assign_room", reason="", result="draft")

    def test_reason_is_stored_for_read_only_events_too(self):
        event = AuditEvent(emp_id="EMP001", actor_name="石磊", module="audit", action="view", reason="查看审计记录", result="ok")

        self.assertEqual(event.to_dict()["reason"], "查看审计记录")


if __name__ == "__main__":
    unittest.main()
