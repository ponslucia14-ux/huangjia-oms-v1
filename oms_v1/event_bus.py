from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .schemas import new_id, now_iso


OMS_EVENT_SCHEMA_VERSION = "oms.v1.event_bus_event"
EventHandler = Callable[["OMSEvent"], Any]


@dataclass(frozen=True)
class OMSEvent:
    """Unified OMS event definition for infrastructure-level event dispatch."""

    event_type: str
    source_module: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: new_id("evtbus"))
    schema_version: str = OMS_EVENT_SCHEMA_VERSION
    timestamp: str = field(default_factory=now_iso)
    subject: str = ""
    action: str = ""
    emp_id: str = ""
    actor_name: str = ""
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventSubscriber:
    """Registered event listener."""

    subscriber_id: str
    module: str
    event_type: str
    handler: EventHandler
    description: str = ""

    def listens_to(self, event: OMSEvent) -> bool:
        return self.event_type in {"*", event.event_type}


class EventRegistry:
    """Track event types and subscribers."""

    def __init__(self):
        self._event_types: dict[str, dict[str, Any]] = {}
        self._subscribers: dict[str, EventSubscriber] = {}

    def register_event_type(self, event_type: str, *, description: str = "", owner_module: str = "") -> dict[str, Any]:
        record = {
            "event_type": event_type,
            "description": description,
            "owner_module": owner_module,
            "registered_at": now_iso(),
        }
        self._event_types[event_type] = record
        return dict(record)

    def register_subscriber(
        self,
        *,
        module: str,
        event_type: str,
        handler: EventHandler,
        subscriber_id: str | None = None,
        description: str = "",
    ) -> EventSubscriber:
        subscriber = EventSubscriber(
            subscriber_id=subscriber_id or new_id("sub"),
            module=module,
            event_type=event_type,
            handler=handler,
            description=description,
        )
        self._subscribers[subscriber.subscriber_id] = subscriber
        return subscriber

    def subscribers_for(self, event: OMSEvent) -> list[EventSubscriber]:
        return [subscriber for subscriber in self._subscribers.values() if subscriber.listens_to(event)]

    def event_types(self) -> list[dict[str, Any]]:
        return list(self._event_types.values())

    def subscribers(self) -> list[EventSubscriber]:
        return list(self._subscribers.values())


class EventPublisher:
    """Publish events through an EventBus."""

    def __init__(self, bus: "EventBus"):
        self.bus = bus

    def publish(self, event: OMSEvent | dict[str, Any]) -> dict[str, Any]:
        oms_event = event if isinstance(event, OMSEvent) else OMSEvent(**event)
        return self.bus.publish(oms_event)


class EventBus:
    """Synchronous in-process event bus for OMS infrastructure events."""

    def __init__(self, registry: EventRegistry | None = None):
        self.registry = registry or EventRegistry()
        self.publisher = EventPublisher(self)
        self._published_events: list[OMSEvent] = []
        self._dispatch_log: list[dict[str, Any]] = []

    def register_event_type(self, event_type: str, *, description: str = "", owner_module: str = "") -> dict[str, Any]:
        return self.registry.register_event_type(event_type, description=description, owner_module=owner_module)

    def subscribe(
        self,
        *,
        module: str,
        event_type: str,
        handler: EventHandler,
        subscriber_id: str | None = None,
        description: str = "",
    ) -> EventSubscriber:
        return self.registry.register_subscriber(
            module=module,
            event_type=event_type,
            handler=handler,
            subscriber_id=subscriber_id,
            description=description,
        )

    def publish(self, event: OMSEvent) -> dict[str, Any]:
        self._published_events.append(event)
        deliveries: list[dict[str, Any]] = []
        for subscriber in self.registry.subscribers_for(event):
            try:
                result = subscriber.handler(event)
                status = "delivered"
                error = ""
            except Exception as exc:  # pragma: no cover - exercised by future integration tests.
                result = None
                status = "failed"
                error = str(exc)
            delivery = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "subscriber_id": subscriber.subscriber_id,
                "subscriber_module": subscriber.module,
                "status": status,
                "error": error,
                "result": result,
                "delivered_at": now_iso(),
            }
            deliveries.append(delivery)
            self._dispatch_log.append(delivery)
        return {
            "schema_version": "oms.v1.event_bus_dispatch",
            "event": event.to_dict(),
            "delivery_count": len(deliveries),
            "deliveries": deliveries,
        }

    def events(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._published_events]

    def dispatch_log(self) -> list[dict[str, Any]]:
        return list(self._dispatch_log)

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": "oms.v1.event_bus_summary",
            "event_type_count": len(self.registry.event_types()),
            "subscriber_count": len(self.registry.subscribers()),
            "published_event_count": len(self._published_events),
            "dispatch_count": len(self._dispatch_log),
        }
