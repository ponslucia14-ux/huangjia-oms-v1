import copy
import tempfile
import unittest
from pathlib import Path

from oms_v1.alert_engine import (
    ALERT_ACKNOWLEDGED,
    ALERT_APPROVAL_TIMEOUT,
    ALERT_HEALTH_CHECK_WARNING,
    ALERT_OPEN,
    ALERT_PAYABLE_EXCEPTION,
    ALERT_RECEIVABLE_EXCEPTION,
    ALERT_RESOLVED,
    ALERT_ROOM_RESOURCE_SHORTAGE,
    ALERT_STAY_CONFLICT,
    ExceptionEngine,
    AlertContext,
    default_alert_definitions,
)
from oms_v1.audit_log import AuditEngine
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from oms_v1.notification import NotificationEvent
from tests.test_health_check import write_identity, write_organization


class AlertEngineTests(unittest.TestCase):
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
        self.engine = ExceptionEngine(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _alert_context(self, **overrides):
        payload = {
            "actor_emp_id": "EMP001",
            "reason": "Evaluate operational exceptions.",
            "room_records": (
                {"room_id": "room_001", "status": "AVAILABLE"},
                {"room_id": "room_002", "status": "OCCUPIED"},
            ),
            "stay_records": (
                {"stay_id": "stay_001", "room_id": "room_002", "status": "in_house"},
                {"stay_id": "stay_002", "room_id": "room_002", "status": "checked_in"},
            ),
            "finance_records": (
                {"tx_id": "fin_001", "type": "receivable", "amount": "48000"},
                {"tx_id": "fin_002", "type": "payable", "amount": "6800"},
            ),
            "approval_records": (
                {"approval_id": "approval_001", "status": "PENDING", "age_hours": 48},
            ),
            "health_items": (
                {"code": "feishu_api_permission_status", "status": "warning", "message": "Permission warning."},
            ),
            "thresholds": {
                "required_available_rooms": 2,
                "receivable_threshold": "10000",
                "payable_threshold": "5000",
                "approval_timeout_hours": 24,
            },
            "correlation_id": "alert_corr_001",
        }
        payload.update(overrides)
        return AlertContext(**payload)

    def test_default_definitions_cover_first_alert_rule_batch(self):
        definitions = default_alert_definitions()

        self.assertEqual(
            [definition.alert_code for definition in definitions],
            [
                ALERT_ROOM_RESOURCE_SHORTAGE,
                ALERT_STAY_CONFLICT,
                ALERT_RECEIVABLE_EXCEPTION,
                ALERT_PAYABLE_EXCEPTION,
                ALERT_APPROVAL_TIMEOUT,
                ALERT_HEALTH_CHECK_WARNING,
            ],
        )
        self.assertTrue(all(definition.domain for definition in definitions))
        self.assertTrue(all(definition.severity for definition in definitions))

    def test_exception_engine_discovers_alerts_and_publishes_created_events(self):
        result = self.engine.evaluate(self._alert_context())

        self.assertEqual(result["alert_count"], 6)
        self.assertFalse(result["mutates_business_state"])
        self.assertEqual({alert["status"] for alert in result["alerts"]}, {ALERT_OPEN})
        self.assertEqual(
            {alert["alert_code"] for alert in result["alerts"]},
            {
                ALERT_ROOM_RESOURCE_SHORTAGE,
                ALERT_STAY_CONFLICT,
                ALERT_RECEIVABLE_EXCEPTION,
                ALERT_PAYABLE_EXCEPTION,
                ALERT_APPROVAL_TIMEOUT,
                ALERT_HEALTH_CHECK_WARNING,
            },
        )
        self.assertTrue(all(alert["receiver_emp_ids"] for alert in result["alerts"]))
        self.assertTrue(all(alert["events"][0]["event"]["event_type"] == "alert.created" for alert in result["alerts"]))
        self.assertTrue(all(alert["events"][0]["event"]["payload"]["notification_consumable"] for alert in result["alerts"]))
        self.assertTrue(all(not alert["events"][0]["event"]["payload"]["mutates_business_state"] for alert in result["alerts"]))

    def test_audit_records_are_written_for_created_alerts(self):
        result = self.engine.evaluate(self._alert_context())
        audit_events = self.audit.events(sort_by_time=False)

        self.assertEqual(len(audit_events), result["alert_count"])
        self.assertEqual({event["action"] for event in audit_events}, {"alert.create"})
        self.assertTrue(all(event["metadata"]["notification_consumable"] for event in audit_events))
        self.assertTrue(all(not event["metadata"]["mutates_business_state"] for event in audit_events))
        self.assertEqual(len(self.bus.events()), result["alert_count"])

    def test_alert_event_payload_can_be_consumed_by_notification_layer(self):
        result = self.engine.evaluate(
            self._alert_context(
                room_records=({"room_id": "room_001", "status": "OCCUPIED"},),
                stay_records=(),
                finance_records=(),
                approval_records=(),
                health_items=(),
                thresholds={"required_available_rooms": 1},
            )
        )
        event = result["alerts"][0]["events"][0]["event"]
        receiver_emp_id = event["payload"]["receiver_emp_ids"][0]

        notification_event = NotificationEvent(
            event_id=event["event_id"],
            event_type=event["event_type"],
            correlation_id=event["correlation_id"],
            receiver_emp_id=receiver_emp_id,
            reason=event["payload"]["reason"],
            payload=event["payload"],
            source_module=event["source_module"],
        )

        self.assertEqual(notification_event.event_id, event["event_id"])
        self.assertEqual(notification_event.receiver_emp_id, receiver_emp_id)
        self.assertTrue(notification_event.payload["notification_consumable"])

    def test_status_lifecycle_acknowledge_and_resolve(self):
        created = self.engine.evaluate(
            self._alert_context(
                room_records=({"room_id": "room_001", "status": "OCCUPIED"},),
                stay_records=(),
                finance_records=(),
                approval_records=(),
                health_items=(),
                thresholds={"required_available_rooms": 1},
            )
        )["alerts"][0]

        acknowledged = self.engine.acknowledge(
            created["alert_id"],
            actor_emp_id="EMP001",
            reason="Alert reviewed.",
            correlation_id="alert_corr_002",
        )
        resolved = self.engine.resolve(
            created["alert_id"],
            actor_emp_id="EMP001",
            reason="Room resource restored.",
            correlation_id="alert_corr_003",
        )

        self.assertEqual(acknowledged["status"], ALERT_ACKNOWLEDGED)
        self.assertEqual(acknowledged["events"][-1]["event"]["event_type"], "alert.acknowledged")
        self.assertEqual(resolved["status"], ALERT_RESOLVED)
        self.assertEqual(resolved["events"][-1]["event"]["event_type"], "alert.resolved")
        self.assertEqual([event["action"] for event in self.audit.events(sort_by_time=False)][-2:], ["alert.acknowledge", "alert.resolve"])
        with self.assertRaises(ValueError):
            self.engine.acknowledge(created["alert_id"], actor_emp_id="EMP001", reason="Cannot reopen terminal alert.")

    def test_ignore_is_audited_without_required_notification_event(self):
        created = self.engine.evaluate(
            self._alert_context(
                room_records=({"room_id": "room_001", "status": "OCCUPIED"},),
                stay_records=(),
                finance_records=(),
                approval_records=(),
                health_items=(),
                thresholds={"required_available_rooms": 1},
            )
        )["alerts"][0]

        ignored = self.engine.ignore(created["alert_id"], actor_emp_id="EMP001", reason="Known false positive.")

        self.assertEqual(ignored["status"], "IGNORED")
        self.assertEqual(ignored["events"][-1]["event"]["event_type"], "alert.created")
        self.assertEqual(self.audit.events(sort_by_time=False)[-1]["action"], "alert.ignore")

    def test_no_alerts_when_context_is_clear(self):
        result = self.engine.evaluate(
            self._alert_context(
                room_records=(
                    {"room_id": "room_001", "status": "AVAILABLE"},
                    {"room_id": "room_002", "status": "AVAILABLE"},
                ),
                stay_records=({"stay_id": "stay_001", "room_id": "room_002", "status": "in_house"},),
                finance_records=(
                    {"tx_id": "fin_001", "type": "receivable", "amount": "1000"},
                    {"tx_id": "fin_002", "type": "payable", "amount": "1000"},
                ),
                approval_records=({"approval_id": "approval_001", "status": "APPROVED", "age_hours": 48},),
                health_items=({"code": "startup", "status": "pass", "message": "OK"},),
            )
        )

        self.assertEqual(result["alert_count"], 0)
        self.assertEqual(result["alerts"], [])
        self.assertEqual(self.audit.events(sort_by_time=False), [])
        self.assertEqual(self.bus.events(), [])

    def test_evaluation_is_read_only_and_does_not_mutate_context(self):
        context = self._alert_context()
        original_context = copy.deepcopy(context.to_dict())

        result = self.engine.evaluate(context)

        self.assertEqual(context.to_dict(), original_context)
        self.assertFalse(result["mutates_business_state"])
        self.assertTrue(all(not alert["mutates_business_state"] for alert in result["alerts"]))

    def test_unknown_alert_id_and_missing_reason_are_rejected(self):
        with self.assertRaises(KeyError):
            self.engine.get_alert("missing_alert")
        created = self.engine.evaluate(
            self._alert_context(
                room_records=({"room_id": "room_001", "status": "OCCUPIED"},),
                stay_records=(),
                finance_records=(),
                approval_records=(),
                health_items=(),
                thresholds={"required_available_rooms": 1},
            )
        )["alerts"][0]
        with self.assertRaises(ValueError):
            self.engine.resolve(created["alert_id"], actor_emp_id="EMP001", reason="")


if __name__ == "__main__":
    unittest.main()
