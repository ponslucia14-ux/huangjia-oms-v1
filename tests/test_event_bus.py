import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus, EventRegistry, OMSEvent


class EventBusTests(unittest.TestCase):
    def test_can_publish_and_subscribe_to_event(self):
        bus = EventBus()
        received = []
        bus.register_event_type("oms.bootstrap.ready", description="Bootstrap completed", owner_module="bootstrap")
        bus.subscribe(module="health_check", event_type="oms.bootstrap.ready", handler=lambda event: received.append(event.event_id) or "ok")

        event = OMSEvent(event_type="oms.bootstrap.ready", source_module="bootstrap", subject="startup", action="ready", payload={"ready": True})
        dispatch = bus.publisher.publish(event)

        self.assertEqual(dispatch["delivery_count"], 1)
        self.assertEqual(received, [event.event_id])
        self.assertEqual(bus.summary()["published_event_count"], 1)

    def test_one_event_can_be_listened_by_multiple_modules(self):
        bus = EventBus()
        received_modules = []
        for module in ["audit_log", "health_check", "metrics"]:
            bus.subscribe(
                module=module,
                event_type="oms.master_data.loaded",
                handler=lambda event, module=module: received_modules.append(module) or {"module": module},
            )

        dispatch = bus.publish(
            OMSEvent(
                event_type="oms.master_data.loaded",
                source_module="bootstrap",
                subject="master_data",
                action="loaded",
                payload={"employee_count": 11},
            )
        )

        self.assertEqual(dispatch["delivery_count"], 3)
        self.assertEqual(set(received_modules), {"audit_log", "health_check", "metrics"})
        self.assertEqual(len(bus.dispatch_log()), 3)

    def test_registry_tracks_event_types_and_subscribers(self):
        registry = EventRegistry()
        registry.register_event_type("oms.audit.event.created", description="Audit event created", owner_module="audit_log")
        subscriber = registry.register_subscriber(
            module="audit_log",
            event_type="oms.audit.event.created",
            handler=lambda event: "ok",
            subscriber_id="audit_subscriber",
        )

        self.assertEqual(registry.event_types()[0]["event_type"], "oms.audit.event.created")
        self.assertEqual(registry.subscribers()[0], subscriber)

    def test_audit_log_can_listen_to_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditEngine(Path(tmp) / "audit")
            bus = EventBus()

            def audit_listener(event):
                return audit.record(
                    emp_id=event.emp_id or "EMP001",
                    actor_name=event.actor_name or "石磊",
                    module="event_bus",
                    action="event_received",
                    reason=f"监听事件 {event.event_type}",
                    result="recorded",
                    target_type="event",
                    target_id=event.event_id,
                    correlation_id=event.correlation_id,
                    metadata={"source_module": event.source_module},
                )

            bus.subscribe(module="audit_log", event_type="*", handler=audit_listener)
            event = OMSEvent(
                event_type="oms.bootstrap.ready",
                source_module="bootstrap",
                subject="startup",
                action="ready",
                emp_id="EMP001",
                actor_name="石磊",
                payload={"ready": True},
            )

            dispatch = bus.publish(event)
            audit_events = audit.events(module="event_bus")

            self.assertEqual(dispatch["delivery_count"], 1)
            self.assertEqual(len(audit_events), 1)
            self.assertEqual(audit_events[0]["target_id"], event.event_id)
            self.assertEqual(audit_events[0]["reason"], "监听事件 oms.bootstrap.ready")


if __name__ == "__main__":
    unittest.main()
