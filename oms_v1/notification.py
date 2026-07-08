from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .schemas import new_id, now_iso


NOTIFICATION_SCHEMA_VERSION = "oms.v1.notification"

NOTIFICATION_PENDING = "PENDING"
NOTIFICATION_SENT = "SENT"
NOTIFICATION_FAILED = "FAILED"
NOTIFICATION_RETRY = "RETRY"
NOTIFICATION_STATUSES = {
    NOTIFICATION_PENDING,
    NOTIFICATION_SENT,
    NOTIFICATION_FAILED,
    NOTIFICATION_RETRY,
}

CHANNEL_INTERNAL_LOG = "internal_log"
CHANNEL_FEISHU_MOCK = "feishu_mock"
SUPPORTED_CHANNELS = {
    CHANNEL_INTERNAL_LOG,
    CHANNEL_FEISHU_MOCK,
}


@dataclass(frozen=True)
class NotificationEvent:
    """Input event for the P16 notification foundation."""

    event_id: str
    event_type: str
    correlation_id: str
    receiver_emp_id: str
    reason: str
    payload: dict[str, Any] = field(default_factory=dict)
    source_module: str = "oms"
    notification_event_id: str = field(default_factory=lambda: new_id("notievt"))
    timestamp: str = field(default_factory=now_iso)
    schema_version: str = NOTIFICATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id is required.")
        if not self.event_type.strip():
            raise ValueError("event_type is required.")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id is required.")
        if not self.receiver_emp_id.strip():
            raise ValueError("receiver_emp_id is required.")
        if not self.reason.strip():
            raise ValueError("reason is required.")
        object.__setattr__(self, "payload", dict(self.payload))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NotificationMessage:
    """Routed notification message before channel delivery."""

    notification_event: dict[str, Any]
    receiver_emp_id: str
    title: str
    body: str
    channel: str
    message_id: str = field(default_factory=lambda: new_id("notimsg"))
    delivery_status: str = NOTIFICATION_PENDING
    correlation_id: str = ""
    event_id: str = ""
    timestamp: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = NOTIFICATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.channel not in SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported notification channel: {self.channel}")
        if self.delivery_status not in NOTIFICATION_STATUSES:
            raise ValueError(f"Unknown delivery_status: {self.delivery_status}")
        if not self.receiver_emp_id.strip():
            raise ValueError("receiver_emp_id is required.")
        if not self.title.strip():
            raise ValueError("title is required.")
        if not self.body.strip():
            raise ValueError("body is required.")
        event_id = self.event_id or str(self.notification_event.get("event_id") or "")
        correlation_id = self.correlation_id or str(self.notification_event.get("correlation_id") or "")
        if not event_id:
            raise ValueError("event_id is required.")
        if not correlation_id:
            raise ValueError("correlation_id is required.")
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "correlation_id", correlation_id)
        object.__setattr__(self, "notification_event", dict(self.notification_event))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NotificationDelivery:
    """Channel delivery result."""

    message: dict[str, Any]
    channel: str
    delivery_status: str
    delivery_id: str = field(default_factory=lambda: new_id("notidelivery"))
    receiver_emp_id: str = ""
    event_id: str = ""
    correlation_id: str = ""
    error: str = ""
    delivered_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = NOTIFICATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.channel not in SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported notification channel: {self.channel}")
        if self.delivery_status not in NOTIFICATION_STATUSES:
            raise ValueError(f"Unknown delivery_status: {self.delivery_status}")
        object.__setattr__(self, "message", dict(self.message))
        object.__setattr__(self, "receiver_emp_id", self.receiver_emp_id or str(self.message.get("receiver_emp_id") or ""))
        object.__setattr__(self, "event_id", self.event_id or str(self.message.get("event_id") or ""))
        object.__setattr__(self, "correlation_id", self.correlation_id or str(self.message.get("correlation_id") or ""))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NotificationChannel:
    """P16 channel abstraction for internal log and mock Feishu delivery."""

    def __init__(self, channel_name: str):
        if channel_name not in SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported notification channel: {channel_name}")
        self.channel_name = channel_name
        self.delivery_log: list[dict[str, Any]] = []

    def send(self, message: NotificationMessage | dict[str, Any]) -> dict[str, Any]:
        notification_message = message if isinstance(message, NotificationMessage) else NotificationMessage(**message)
        if notification_message.metadata.get("force_fail"):
            delivery = NotificationDelivery(
                message=notification_message.to_dict(),
                channel=self.channel_name,
                delivery_status=NOTIFICATION_FAILED,
                error="Forced failure for notification channel test.",
                metadata={"mock_delivery": self.channel_name == CHANNEL_FEISHU_MOCK},
            )
        else:
            delivery = NotificationDelivery(
                message=notification_message.to_dict(),
                channel=self.channel_name,
                delivery_status=NOTIFICATION_SENT,
                metadata={
                    "internal_log": self.channel_name == CHANNEL_INTERNAL_LOG,
                    "mock_delivery": self.channel_name == CHANNEL_FEISHU_MOCK,
                    "external_api_called": False,
                },
            )
        payload = delivery.to_dict()
        self.delivery_log.append(payload)
        return payload


class NotificationRouter:
    """Route notification events to supported P16 channels without real external calls."""

    def __init__(
        self,
        *,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
        channels: dict[str, NotificationChannel] | None = None,
    ):
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.channels = channels or {
            CHANNEL_INTERNAL_LOG: NotificationChannel(CHANNEL_INTERNAL_LOG),
            CHANNEL_FEISHU_MOCK: NotificationChannel(CHANNEL_FEISHU_MOCK),
        }

    def route(
        self,
        notification_event: NotificationEvent | dict[str, Any],
        *,
        channels: tuple[str, ...] = (CHANNEL_INTERNAL_LOG,),
        title: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        event = notification_event if isinstance(notification_event, NotificationEvent) else NotificationEvent(**notification_event)
        receiver = self.master_data.employee_by_emp(event.receiver_emp_id)
        selected_channels = tuple(channels)
        if not selected_channels:
            raise ValueError("At least one notification channel is required.")

        audit_records: list[dict[str, Any]] = [
            self._audit(
                action="notification.request",
                event=event,
                actor_name=receiver.name,
                result=NOTIFICATION_PENDING,
                metadata={
                    "requested_channels": list(selected_channels),
                    "delivery_status": NOTIFICATION_PENDING,
                },
            )
        ]
        events: list[dict[str, Any]] = [
            self._event(
                event_type="notification.requested",
                event=event,
                actor_name=receiver.name,
                payload={
                    "event_id": event.event_id,
                    "correlation_id": event.correlation_id,
                    "receiver_emp_id": event.receiver_emp_id,
                    "channels": list(selected_channels),
                    "delivery_status": NOTIFICATION_PENDING,
                },
            )
        ]

        messages: list[dict[str, Any]] = []
        deliveries: list[dict[str, Any]] = []
        for channel_name in selected_channels:
            if channel_name not in self.channels:
                delivery = self._failed_delivery(
                    event=event,
                    channel_name=channel_name,
                    title=title,
                    body=body,
                    error=f"Unsupported notification channel: {channel_name}",
                )
            else:
                message = NotificationMessage(
                    notification_event=event.to_dict(),
                    receiver_emp_id=event.receiver_emp_id,
                    title=title or event.event_type,
                    body=body or event.reason,
                    channel=channel_name,
                    metadata=dict(event.payload),
                )
                messages.append(message.to_dict())
                delivery = self.channels[channel_name].send(message)
            deliveries.append(delivery)

        overall_status = _overall_delivery_status(deliveries)
        terminal_action = "notification.sent" if overall_status == NOTIFICATION_SENT else "notification.fail"
        terminal_event = "notification.sent" if overall_status == NOTIFICATION_SENT else "notification.failed"
        audit_records.append(
            self._audit(
                action=terminal_action,
                event=event,
                actor_name=receiver.name,
                result=overall_status,
                metadata={
                    "delivery_status": overall_status,
                    "delivery_count": len(deliveries),
                    "channels": [delivery["channel"] for delivery in deliveries],
                },
            )
        )
        events.append(
            self._event(
                event_type=terminal_event,
                event=event,
                actor_name=receiver.name,
                payload={
                    "event_id": event.event_id,
                    "correlation_id": event.correlation_id,
                    "receiver_emp_id": event.receiver_emp_id,
                    "delivery_status": overall_status,
                    "deliveries": deliveries,
                },
            )
        )

        return {
            "schema_version": NOTIFICATION_SCHEMA_VERSION,
            "notification_event": event.to_dict(),
            "messages": messages,
            "deliveries": deliveries,
            "delivery_status": overall_status,
            "audit_records": audit_records,
            "events": events,
            "mutates_business_state": False,
            "external_api_called": False,
        }

    @staticmethod
    def _failed_delivery(
        *,
        event: NotificationEvent,
        channel_name: str,
        title: str,
        body: str,
        error: str,
    ) -> dict[str, Any]:
        message = NotificationMessage(
            notification_event=event.to_dict(),
            receiver_emp_id=event.receiver_emp_id,
            title=title or event.event_type,
            body=body or event.reason,
            channel=CHANNEL_INTERNAL_LOG,
            metadata={"requested_channel": channel_name},
        )
        return NotificationDelivery(
            message=message.to_dict(),
            channel=CHANNEL_INTERNAL_LOG,
            delivery_status=NOTIFICATION_FAILED,
            error=error,
            metadata={"requested_channel": channel_name, "external_api_called": False},
        ).to_dict()

    def _audit(
        self,
        *,
        action: str,
        event: NotificationEvent,
        actor_name: str,
        result: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=event.receiver_emp_id,
            actor_name=actor_name,
            module="notification",
            action=action,
            action_type=action,
            reason=event.reason,
            result=result,
            target_type="notification_event",
            target_id=event.event_id,
            correlation_id=event.correlation_id,
            metadata={
                "event_id": event.event_id,
                "notification_event_id": event.notification_event_id,
                "receiver_emp_id": event.receiver_emp_id,
                "mutates_business_state": False,
                **metadata,
            },
        )

    def _event(
        self,
        *,
        event_type: str,
        event: NotificationEvent,
        actor_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.event_bus.publish(
            OMSEvent(
                event_type=event_type,
                source_module="notification",
                subject="notification",
                action=event_type.removeprefix("notification."),
                emp_id=event.receiver_emp_id,
                actor_name=actor_name,
                payload={
                    "mutates_business_state": False,
                    **payload,
                },
                correlation_id=event.correlation_id,
                metadata={
                    "event_id": event.event_id,
                    "notification_event_id": event.notification_event_id,
                    "receiver_emp_id": event.receiver_emp_id,
                    "mutates_business_state": False,
                },
            )
        )


def _overall_delivery_status(deliveries: list[dict[str, Any]]) -> str:
    if not deliveries:
        return NOTIFICATION_FAILED
    statuses = {str(delivery.get("delivery_status") or "") for delivery in deliveries}
    if statuses == {NOTIFICATION_SENT}:
        return NOTIFICATION_SENT
    if NOTIFICATION_SENT in statuses and NOTIFICATION_FAILED in statuses:
        return NOTIFICATION_RETRY
    if NOTIFICATION_RETRY in statuses:
        return NOTIFICATION_RETRY
    return NOTIFICATION_FAILED
