from __future__ import annotations

import copy
import csv
import io
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .audit_log import AuditEngine
from .domain import DomainRegistry, default_domain_registry
from .event_bus import EventBus, OMSEvent
from .master_data import Employee, OMSMasterData
from .schemas import new_id, now_iso


DATA_ADAPTER_SCHEMA_VERSION = "oms.v1.data_adapter"

INPUT_MOCK_CSV = "mock_csv"
INPUT_MOCK_JSON = "mock_json"
SUPPORTED_INPUT_FORMATS = {INPUT_MOCK_CSV, INPUT_MOCK_JSON}

ADAPTER_COMPLETED = "COMPLETED"
ADAPTER_FAILED = "FAILED"
SUPPORTED_ADAPTER_STATUSES = {ADAPTER_COMPLETED, ADAPTER_FAILED}


@dataclass(frozen=True)
class AdapterConfig:
    """Versioned adapter configuration for mock external data sources."""

    adapter_id: str
    source_system: str
    source_version: str
    target_domain: str
    mapping_version: str
    input_format: str
    required_fields: tuple[str, ...] = ()
    field_mapping: dict[str, str] = field(default_factory=dict)
    last_sync_time: str = ""
    schema_version: str = DATA_ADAPTER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_non_empty(self.adapter_id, "adapter_id")
        _require_non_empty(self.source_system, "source_system")
        _require_non_empty(self.source_version, "source_version")
        _require_non_empty(self.target_domain, "target_domain")
        _require_non_empty(self.mapping_version, "mapping_version")
        if self.input_format not in SUPPORTED_INPUT_FORMATS:
            raise ValueError(f"Unsupported input_format: {self.input_format}")
        object.__setattr__(self, "required_fields", tuple(dict.fromkeys(self.required_fields)))
        object.__setattr__(self, "field_mapping", copy.deepcopy(dict(self.field_mapping)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_fields"] = list(self.required_fields)
        payload["field_mapping"] = copy.deepcopy(self.field_mapping)
        return payload


@dataclass(frozen=True)
class AdapterResult:
    """Result of one adapter import attempt."""

    adapter_id: str
    source_system: str
    source_version: str
    target_domain: str
    mapping_version: str
    import_time: str
    validation_result: dict[str, Any]
    domain_objects: tuple[dict[str, Any], ...] = ()
    raw_records: tuple[dict[str, Any], ...] = ()
    status: str = ADAPTER_COMPLETED
    failure_reasons: tuple[str, ...] = ()
    audit_records: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    mutates_business_state: bool = False
    production_system_connected: bool = False
    schema_version: str = DATA_ADAPTER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_non_empty(self.adapter_id, "adapter_id")
        _require_non_empty(self.source_system, "source_system")
        _require_non_empty(self.source_version, "source_version")
        _require_non_empty(self.target_domain, "target_domain")
        _require_non_empty(self.mapping_version, "mapping_version")
        _require_non_empty(self.import_time, "import_time")
        if self.status not in SUPPORTED_ADAPTER_STATUSES:
            raise ValueError(f"Unsupported adapter status: {self.status}")
        if self.mutates_business_state:
            raise ValueError("Data adapter cannot mutate business state.")
        if self.production_system_connected:
            raise ValueError("P28 data adapter framework cannot connect production systems.")
        object.__setattr__(self, "validation_result", copy.deepcopy(dict(self.validation_result)))
        object.__setattr__(self, "domain_objects", _freeze_records(self.domain_objects))
        object.__setattr__(self, "raw_records", _freeze_records(self.raw_records))
        object.__setattr__(self, "failure_reasons", tuple(dict.fromkeys(self.failure_reasons)))
        object.__setattr__(self, "audit_records", _freeze_records(self.audit_records))
        object.__setattr__(self, "events", _freeze_records(self.events))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validation_result"] = copy.deepcopy(self.validation_result)
        payload["domain_objects"] = [copy.deepcopy(item) for item in self.domain_objects]
        payload["raw_records"] = [copy.deepcopy(item) for item in self.raw_records]
        payload["failure_reasons"] = list(self.failure_reasons)
        payload["audit_records"] = [copy.deepcopy(item) for item in self.audit_records]
        payload["events"] = [copy.deepcopy(item) for item in self.events]
        return payload


class DataValidator:
    """Validate parsed mock external records before mapping."""

    def __init__(self, *, domain_registry: DomainRegistry | None = None):
        self.domain_registry = domain_registry or default_domain_registry()

    def validate(self, records: list[dict[str, Any]], config: AdapterConfig) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        try:
            self.domain_registry.get(config.target_domain)
        except KeyError as exc:
            issues.append({"code": "unknown_target_domain", "detail": str(exc), "row_index": None})

        if not config.source_version.strip():
            issues.append({"code": "missing_source_version", "detail": "source_version is required.", "row_index": None})
        if not config.mapping_version.strip():
            issues.append({"code": "missing_mapping_version", "detail": "mapping_version is required.", "row_index": None})
        if not records:
            issues.append({"code": "empty_records", "detail": "No records were provided.", "row_index": None})

        valid_count = 0
        invalid_rows: set[int] = set()
        for index, record in enumerate(records, start=1):
            row_failed = False
            for field_name in config.required_fields:
                if str(record.get(field_name, "")).strip() == "":
                    issues.append(
                        {
                            "code": "missing_required_field",
                            "detail": f"{field_name} is required.",
                            "field": field_name,
                            "row_index": index,
                        }
                    )
                    row_failed = True
            if row_failed:
                invalid_rows.add(index)
            else:
                valid_count += 1

        if any(issue["row_index"] is None for issue in issues):
            valid_count = 0 if issues else valid_count
            invalid_rows.update(range(1, len(records) + 1))

        invalid_count = len(invalid_rows)
        return {
            "schema_version": DATA_ADAPTER_SCHEMA_VERSION,
            "is_valid": not issues,
            "record_count": len(records),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "issues": issues,
            "source_system": config.source_system,
            "source_version": config.source_version,
            "target_domain": config.target_domain,
            "mapping_version": config.mapping_version,
        }


class DataMapper:
    """Map validated mock external records into generic Domain Object payloads."""

    def map_records(self, records: list[dict[str, Any]], config: AdapterConfig, *, import_time: str) -> list[dict[str, Any]]:
        domain_objects: list[dict[str, Any]] = []
        for index, record in enumerate(records, start=1):
            payload = self._payload(record, config)
            domain_objects.append(
                {
                    "schema_version": DATA_ADAPTER_SCHEMA_VERSION,
                    "domain_object_id": new_id(config.target_domain.lower()),
                    "domain": config.target_domain,
                    "source": {
                        "adapter_id": config.adapter_id,
                        "source_system": config.source_system,
                        "source_version": config.source_version,
                        "mapping_version": config.mapping_version,
                        "row_index": index,
                    },
                    "payload": payload,
                    "mapping_version": config.mapping_version,
                    "import_time": import_time,
                    "mutates_business_state": False,
                }
            )
        return domain_objects

    def _payload(self, record: dict[str, Any], config: AdapterConfig) -> dict[str, Any]:
        if not config.field_mapping:
            return copy.deepcopy(record)
        payload: dict[str, Any] = {}
        for external_field, domain_field in config.field_mapping.items():
            payload[domain_field] = copy.deepcopy(record.get(external_field, ""))
        return payload


class DataAdapter:
    """P28 framework adapter for mock CSV / JSON input only."""

    def __init__(
        self,
        config: AdapterConfig | dict[str, Any],
        *,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
        master_data: OMSMasterData | None = None,
        validator: DataValidator | None = None,
        mapper: DataMapper | None = None,
    ):
        self.config = config if isinstance(config, AdapterConfig) else AdapterConfig(**config)
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self.master_data = master_data or OMSMasterData()
        self.validator = validator or DataValidator()
        self.mapper = mapper or DataMapper()

    def import_data(
        self,
        external_data: str | list[dict[str, Any]] | dict[str, Any],
        *,
        actor_emp_id: str,
        reason: str,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required.")
        actor = self.master_data.employee_by_emp(actor_emp_id)
        import_time = now_iso()
        request_audit = self._audit(
            action="data.import.request",
            actor=actor,
            reason=reason,
            result="requested",
            import_time=import_time,
            validation_result={},
            correlation_id=correlation_id,
        )
        try:
            records = self._parse_external_data(external_data)
            validation_result = self.validator.validate(records, self.config)
            if not validation_result["is_valid"]:
                failure_reasons = tuple(issue["code"] for issue in validation_result["issues"])
                failed_audit = self._audit(
                    action="data.import.failed",
                    actor=actor,
                    reason="Data adapter validation failed.",
                    result="failed",
                    import_time=import_time,
                    validation_result=validation_result,
                    correlation_id=correlation_id,
                    metadata={"failure_reasons": list(failure_reasons)},
                )
                failed_event = self._event(
                    event_type="data.adapter.failed",
                    action="failed",
                    actor=actor,
                    import_time=import_time,
                    validation_result=validation_result,
                    domain_objects=(),
                    correlation_id=correlation_id,
                    failure_reasons=failure_reasons,
                )
                return AdapterResult(
                    adapter_id=self.config.adapter_id,
                    source_system=self.config.source_system,
                    source_version=self.config.source_version,
                    target_domain=self.config.target_domain,
                    mapping_version=self.config.mapping_version,
                    import_time=import_time,
                    validation_result=validation_result,
                    raw_records=tuple(records),
                    status=ADAPTER_FAILED,
                    failure_reasons=failure_reasons,
                    audit_records=(request_audit, failed_audit),
                    events=(failed_event,),
                ).to_dict()

            domain_objects = self.mapper.map_records(records, self.config, import_time=import_time)
            completed_audit = self._audit(
                action="data.import.completed",
                actor=actor,
                reason="Data adapter import completed.",
                result="success",
                import_time=import_time,
                validation_result=validation_result,
                correlation_id=correlation_id,
                metadata={"domain_object_count": len(domain_objects)},
            )
            completed_event = self._event(
                event_type="data.adapter.completed",
                action="completed",
                actor=actor,
                import_time=import_time,
                validation_result=validation_result,
                domain_objects=tuple(domain_objects),
                correlation_id=correlation_id,
            )
            return AdapterResult(
                adapter_id=self.config.adapter_id,
                source_system=self.config.source_system,
                source_version=self.config.source_version,
                target_domain=self.config.target_domain,
                mapping_version=self.config.mapping_version,
                import_time=import_time,
                validation_result=validation_result,
                domain_objects=tuple(domain_objects),
                raw_records=tuple(records),
                status=ADAPTER_COMPLETED,
                audit_records=(request_audit, completed_audit),
                events=(completed_event,),
            ).to_dict()
        except Exception as exc:
            validation_result = {
                "schema_version": DATA_ADAPTER_SCHEMA_VERSION,
                "is_valid": False,
                "record_count": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "issues": [{"code": "adapter_exception", "detail": str(exc), "row_index": None}],
                "source_system": self.config.source_system,
                "source_version": self.config.source_version,
                "target_domain": self.config.target_domain,
                "mapping_version": self.config.mapping_version,
            }
            failed_audit = self._audit(
                action="data.import.failed",
                actor=actor,
                reason="Data adapter import failed.",
                result="failed",
                import_time=import_time,
                validation_result=validation_result,
                correlation_id=correlation_id,
                metadata={"failure_reasons": ["adapter_exception"]},
            )
            failed_event = self._event(
                event_type="data.adapter.failed",
                action="failed",
                actor=actor,
                import_time=import_time,
                validation_result=validation_result,
                domain_objects=(),
                correlation_id=correlation_id,
                failure_reasons=("adapter_exception",),
            )
            return AdapterResult(
                adapter_id=self.config.adapter_id,
                source_system=self.config.source_system,
                source_version=self.config.source_version,
                target_domain=self.config.target_domain,
                mapping_version=self.config.mapping_version,
                import_time=import_time,
                validation_result=validation_result,
                status=ADAPTER_FAILED,
                failure_reasons=("adapter_exception",),
                audit_records=(request_audit, failed_audit),
                events=(failed_event,),
            ).to_dict()

    def _parse_external_data(self, external_data: str | list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
        if self.config.input_format == INPUT_MOCK_CSV:
            if not isinstance(external_data, str):
                raise ValueError("mock_csv input requires a CSV string.")
            reader = csv.DictReader(io.StringIO(external_data))
            return [self._clean_row(row) for row in reader]
        if self.config.input_format == INPUT_MOCK_JSON:
            payload = json.loads(external_data) if isinstance(external_data, str) else copy.deepcopy(external_data)
            if isinstance(payload, dict):
                records = payload.get("records", [])
            else:
                records = payload
            if not isinstance(records, list):
                raise ValueError("mock_json input requires a list or {'records': [...]} payload.")
            return [self._clean_row(dict(record)) for record in records]
        raise ValueError(f"Unsupported input_format: {self.config.input_format}")

    def _audit(
        self,
        *,
        action: str,
        actor: Employee,
        reason: str,
        result: str,
        import_time: str,
        validation_result: dict[str, Any],
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="data_adapter",
            action=action,
            action_type=action,
            reason=reason,
            result=result,
            target_type="data_adapter",
            target_id=self.config.adapter_id,
            correlation_id=correlation_id or self.config.adapter_id,
            metadata={
                "adapter_id": self.config.adapter_id,
                "source_system": self.config.source_system,
                "source_version": self.config.source_version,
                "target_domain": self.config.target_domain,
                "mapping_version": self.config.mapping_version,
                "import_time": import_time,
                "validation_result": copy.deepcopy(validation_result),
                "mutates_business_state": False,
                "production_system_connected": False,
                **(metadata or {}),
            },
        )

    def _event(
        self,
        *,
        event_type: str,
        action: str,
        actor: Employee,
        import_time: str,
        validation_result: dict[str, Any],
        domain_objects: tuple[dict[str, Any], ...],
        correlation_id: str,
        failure_reasons: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        event = OMSEvent(
            event_type=event_type,
            source_module="data_adapter",
            subject=self.config.adapter_id,
            action=action,
            emp_id=actor.emp,
            actor_name=actor.name,
            correlation_id=correlation_id or self.config.adapter_id,
            payload={
                "adapter_id": self.config.adapter_id,
                "source_system": self.config.source_system,
                "source_version": self.config.source_version,
                "target_domain": self.config.target_domain,
                "mapping_version": self.config.mapping_version,
                "import_time": import_time,
                "domain_object_count": len(domain_objects),
                "validation_result": copy.deepcopy(validation_result),
                "failure_reasons": list(failure_reasons),
                "mutates_business_state": False,
                "production_system_connected": False,
            },
        )
        return self.event_bus.publish(event)

    @staticmethod
    def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
        return {str(key).strip(): "" if value is None else value for key, value in row.items() if str(key).strip()}


def _freeze_records(records: Any) -> tuple[dict[str, Any], ...]:
    return tuple(copy.deepcopy(dict(item)) for item in records)


def _require_non_empty(value: str, field_name: str) -> None:
    if not str(value).strip():
        raise ValueError(f"{field_name} is required.")
