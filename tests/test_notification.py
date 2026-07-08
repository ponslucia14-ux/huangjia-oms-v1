import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.notification import (
    CHANNEL_FEISHU_MOCK,
    CHANNEL_INTERNAL_LOG,
    NOTIFICATION_FAILED,
    NOTIFICATION_PENDING,
    NOTIFICATION_RETRY,
    NOTIFICATION_SENT,
    NotificationChannel,
    NotificationEvent,
    NotificationMessage,
    NotificationRouter,
)
from tests.test_health_check import write_identity, write_organization


class NotificationTests(unittest.TestCase):
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
        self.router = NotificationRouter(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _event(self, **overrides):
        payload = {
            "event_id": "evt_001",
            "event_type": "execution.completed",
            "correlation_id": "corr_001",
            "receiver_emp_id": "EMP008",
            "reason": "Notify receiver about execution result.",
            "payload": {"summary": "Execution simulation completed."},
            "source_module": "execution",
        }
        payload.update(overrides)
        return NotificationEvent(**payload)

    def test_notification_event_requires_trace_fields(self):
        event = self._event()

        payload = event.to_dict()
        self.assertEqual(payload["event_id"], "evt_001")
        self.assertEqual(payload["correlation_id"], "corr_001")
        self.assertEqual(payload["receiver_emp_id"], "EMP008")
        self.assertEqual(payload["source_module"], "execution")

    def test_message_requires_supported_channel_and_trace_fields(self):
        event = self._event()
        message = NotificationMessage(
            notification_event=event.to_dict(),
            receiver_emp_id="EMP008",
            title="Execution update",
            body="Execution completed.",
            channel=CHANNEL_INTERNAL_LOG,
        )

        payload = message.to_dict()
        self.assertEqual(payload["delivery_status"], NOTIFICATION_PENDING)
        self.assertEqual(payload["event_id"], "evt_001")
        self.assertEqual(payload["correlation_id"], "corr_001")
        with self.assertRaises(ValueError):
            NotificationMessage(
                notification_event=event.to_dict(),
                receiver_emp_id="EMP008",
                title="Bad channel",
                body="Should fail.",
                channel="real_feishu",
            )

    def test_internal_log_delivery_records_sent_status(self):
        result = self.router.route(
            self._event(),
            channels=(CHANNEL_INTERNAL_LOG,),
            title="Execution update",
            body="Execution completed.",
        )

        self.assertEqual(result["delivery_status"], NOTIFICATION_SENT)
        self.assertFalse(result["mutates_business_state"])
        self.assertFalse(result["external_api_called"])
        self.assertEqual(result["deliveries"][0]["channel"], CHANNEL_INTERNAL_LOG)
        self.assertEqual(result["deliveries"][0]["delivery_status"], NOTIFICATION_SENT)
        self.assertEqual([event["event_type"] for event in self.bus.events()], ["notification.requested", "notification.sent"])
        self.assertEqual([event["action"] for event in self.audit.events(sort_by_time=False)], ["notification.request", "notification.sent"])

    def test_feishu_mock_delivery_does_not_call_external_api(self):
        result = self.router.route(
            self._event(),
            channels=(CHANNEL_FEISHU_MOCK,),
            title="Mock message",
            body="Mock delivery.",
        )

        self.assertEqual(result["delivery_status"], NOTIFICATION_SENT)
        self.assertEqual(result["deliveries"][0]["channel"], CHANNEL_FEISHU_MOCK)
        self.assertTrue(result["deliveries"][0]["metadata"]["mock_delivery"])
        self.assertFalse(result["deliveries"][0]["metadata"]["external_api_called"])

    def test_multiple_channels_route_to_each_delivery_target(self):
        result = self.router.route(
            self._event(),
            channels=(CHANNEL_INTERNAL_LOG, CHANNEL_FEISHU_MOCK),
            title="Multi channel",
            body="Route to both channels.",
        )

        self.assertEqual(result["delivery_status"], NOTIFICATION_SENT)
        self.assertEqual({delivery["channel"] for delivery in result["deliveries"]}, {CHANNEL_INTERNAL_LOG, CHANNEL_FEISHU_MOCK})
        self.assertEqual(len(result["messages"]), 2)

    def test_failed_channel_records_failed_event_and_audit(self):
        failing_channel = NotificationChannel(CHANNEL_INTERNAL_LOG)
        router = NotificationRouter(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
            channels={CHANNEL_INTERNAL_LOG: failing_channel},
        )

        result = router.route(
            self._event(payload={"force_fail": True}),
            channels=(CHANNEL_INTERNAL_LOG,),
            title="Failing notification",
            body="Force failure.",
        )

        self.assertEqual(result["delivery_status"], NOTIFICATION_FAILED)
        self.assertEqual(result["deliveries"][0]["delivery_status"], NOTIFICATION_FAILED)
        self.assertEqual([event["event_type"] for event in self.bus.events()], ["notification.requested", "notification.failed"])
        self.assertEqual([event["action"] for event in self.audit.events(sort_by_time=False)], ["notification.request", "notification.fail"])

    def test_partial_failure_returns_retry_status(self):
        result = self.router.route(
            self._event(payload={"force_fail": True}),
            channels=(CHANNEL_INTERNAL_LOG, CHANNEL_FEISHU_MOCK),
            title="Partial failure",
            body="Both channels receive same test payload.",
        )

        self.assertEqual(result["delivery_status"], NOTIFICATION_FAILED)

        custom_internal = NotificationChannel(CHANNEL_INTERNAL_LOG)
        custom_mock = NotificationChannel(CHANNEL_FEISHU_MOCK)
        router = NotificationRouter(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
            channels={
                CHANNEL_INTERNAL_LOG: custom_internal,
                CHANNEL_FEISHU_MOCK: custom_mock,
            },
        )
        retry_result = router.route(
            self._event(),
            channels=(CHANNEL_INTERNAL_LOG, "unknown_channel"),
            title="Retry status",
            body="One supported and one unsupported channel.",
        )

        self.assertEqual(retry_result["delivery_status"], NOTIFICATION_RETRY)
        self.assertEqual({delivery["delivery_status"] for delivery in retry_result["deliveries"]}, {NOTIFICATION_SENT, NOTIFICATION_FAILED})

    def test_unknown_receiver_is_rejected_by_master_data(self):
        with self.assertRaises(KeyError):
            self.router.route(self._event(receiver_emp_id="EMP999"), channels=(CHANNEL_INTERNAL_LOG,))

    def test_notification_does_not_mutate_source_event(self):
        event = self._event()
        before = event.to_dict()

        result = self.router.route(event, channels=(CHANNEL_INTERNAL_LOG,))

        self.assertEqual(event.to_dict(), before)
        self.assertFalse(result["mutates_business_state"])


if __name__ == "__main__":
    unittest.main()
