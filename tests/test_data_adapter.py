import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.data_adapter import (
    ADAPTER_COMPLETED,
    ADAPTER_FAILED,
    INPUT_MOCK_CSV,
    INPUT_MOCK_JSON,
    AdapterConfig,
    DataAdapter,
    DataMapper,
    DataValidator,
)
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class DataAdapterTests(unittest.TestCase):
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

    def tearDown(self):
        self.tmp.cleanup()

    def _config(self, **overrides):
        payload = {
            "adapter_id": "adapter_mock_sales_v1",
            "source_system": "mock_sales_csv",
            "source_version": "2026.07.v1",
            "target_domain": "Contract",
            "mapping_version": "contract.mapping.v1",
            "input_format": INPUT_MOCK_CSV,
            "required_fields": ("customer_name", "amount"),
            "field_mapping": {
                "customer_name": "customer_name",
                "amount": "contract_amount",
                "contract_no": "contract_no",
            },
            "last_sync_time": "2026-07-09T08:00:00",
        }
        payload.update(overrides)
        return AdapterConfig(**payload)

    def _adapter(self, config=None):
        return DataAdapter(
            config or self._config(),
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )

    def test_adapter_config_requires_version_and_supported_format(self):
        config = self._config()

        self.assertEqual(config.adapter_id, "adapter_mock_sales_v1")
        self.assertEqual(config.source_system, "mock_sales_csv")
        self.assertEqual(config.source_version, "2026.07.v1")
        self.assertEqual(config.target_domain, "Contract")
        self.assertEqual(config.mapping_version, "contract.mapping.v1")
        self.assertEqual(config.last_sync_time, "2026-07-09T08:00:00")
        with self.assertRaises(ValueError):
            self._config(source_version="")
        with self.assertRaises(ValueError):
            self._config(input_format="xlsx")

    def test_mock_csv_import_validates_maps_audits_and_events(self):
        csv_payload = "customer_name,amount,contract_no\nCustomer A,20000,HJ-001\nCustomer B,30000,HJ-002\n"

        result = self._adapter().import_data(
            csv_payload,
            actor_emp_id="EMP001",
            reason="Import mock sales CSV for adapter framework test.",
            correlation_id="adapter_corr_001",
        )

        self.assertEqual(result["status"], ADAPTER_COMPLETED)
        self.assertEqual(result["source_system"], "mock_sales_csv")
        self.assertEqual(result["source_version"], "2026.07.v1")
        self.assertEqual(result["mapping_version"], "contract.mapping.v1")
        self.assertTrue(result["import_time"])
        self.assertTrue(result["validation_result"]["is_valid"])
        self.assertEqual(result["validation_result"]["record_count"], 2)
        self.assertEqual(len(result["domain_objects"]), 2)
        self.assertEqual(result["domain_objects"][0]["domain"], "Contract")
        self.assertEqual(result["domain_objects"][0]["payload"]["contract_amount"], "20000")
        self.assertFalse(result["domain_objects"][0]["mutates_business_state"])
        self.assertFalse(result["mutates_business_state"])
        self.assertFalse(result["production_system_connected"])
        self.assertEqual(
            [item["action"] for item in self.audit.events(sort_by_time=False)],
            ["data.import.request", "data.import.completed"],
        )
        self.assertEqual([item["event_type"] for item in self.bus.events()], ["data.adapter.completed"])
        self.assertEqual(self.bus.events()[0]["payload"]["domain_object_count"], 2)
        self.assertFalse(self.bus.events()[0]["payload"]["production_system_connected"])

    def test_mock_json_import_supports_records_payload(self):
        config = self._config(
            adapter_id="adapter_mock_room_v1",
            source_system="mock_room_json",
            target_domain="Room",
            mapping_version="room.mapping.v1",
            input_format=INPUT_MOCK_JSON,
            required_fields=("room_id", "status"),
            field_mapping={"room_id": "room_id", "status": "status"},
        )

        result = self._adapter(config).import_data(
            {"records": [{"room_id": "301", "status": "AVAILABLE"}, {"room_id": "302", "status": "OCCUPIED"}]},
            actor_emp_id="EMP001",
            reason="Import mock room JSON for adapter framework test.",
        )

        self.assertEqual(result["status"], ADAPTER_COMPLETED)
        self.assertEqual(result["target_domain"], "Room")
        self.assertEqual(result["domain_objects"][0]["payload"]["room_id"], "301")
        self.assertEqual(result["domain_objects"][1]["source"]["row_index"], 2)

    def test_validation_failure_writes_failed_audit_and_event(self):
        csv_payload = "customer_name,amount,contract_no\nCustomer A,,HJ-001\n"

        result = self._adapter().import_data(
            csv_payload,
            actor_emp_id="EMP001",
            reason="Import invalid mock data.",
        )

        self.assertEqual(result["status"], ADAPTER_FAILED)
        self.assertFalse(result["validation_result"]["is_valid"])
        self.assertEqual(result["domain_objects"], [])
        self.assertIn("missing_required_field", result["failure_reasons"])
        self.assertEqual(
            [item["action"] for item in self.audit.events(sort_by_time=False)],
            ["data.import.request", "data.import.failed"],
        )
        self.assertEqual([item["event_type"] for item in self.bus.events()], ["data.adapter.failed"])
        self.assertEqual(self.bus.events()[0]["payload"]["failure_reasons"], ["missing_required_field"])

    def test_unknown_target_domain_is_validation_failure(self):
        config = self._config(target_domain="UnknownDomain")

        result = self._adapter(config).import_data(
            "customer_name,amount\nCustomer A,20000\n",
            actor_emp_id="EMP001",
            reason="Import with unknown domain.",
        )

        self.assertEqual(result["status"], ADAPTER_FAILED)
        self.assertIn("unknown_target_domain", result["failure_reasons"])

    def test_data_validator_reports_empty_records(self):
        validation = DataValidator().validate([], self._config())

        self.assertFalse(validation["is_valid"])
        self.assertEqual(validation["issues"][0]["code"], "empty_records")
        self.assertEqual(validation["source_version"], "2026.07.v1")
        self.assertEqual(validation["mapping_version"], "contract.mapping.v1")

    def test_data_mapper_keeps_source_trace_and_does_not_mutate_business_state(self):
        records = [{"customer_name": "Customer A", "amount": "20000", "contract_no": "HJ-001"}]
        mapped = DataMapper().map_records(records, self._config(), import_time="2026-07-09T10:00:00")

        self.assertEqual(mapped[0]["source"]["adapter_id"], "adapter_mock_sales_v1")
        self.assertEqual(mapped[0]["source"]["source_version"], "2026.07.v1")
        self.assertEqual(mapped[0]["mapping_version"], "contract.mapping.v1")
        self.assertEqual(mapped[0]["payload"]["contract_no"], "HJ-001")
        self.assertFalse(mapped[0]["mutates_business_state"])

    def test_adapter_rejects_real_file_formats_and_non_mock_input(self):
        with self.assertRaises(ValueError):
            self._config(input_format="xlsx")

        result = self._adapter().import_data(
            [{"customer_name": "Customer A", "amount": "20000"}],
            actor_emp_id="EMP001",
            reason="Wrong payload type for CSV.",
        )

        self.assertEqual(result["status"], ADAPTER_FAILED)
        self.assertIn("adapter_exception", result["failure_reasons"])

    def test_unknown_actor_is_rejected(self):
        with self.assertRaises(KeyError):
            self._adapter().import_data(
                "customer_name,amount\nCustomer A,20000\n",
                actor_emp_id="EMP999",
                reason="Unknown actor.",
            )


if __name__ == "__main__":
    unittest.main()
