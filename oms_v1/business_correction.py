from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .audit_log import AuditEngine
from .event_bus import EventBus, OMSEvent
from .master_data import OMSMasterData
from .schemas import new_id, now_iso


CORRECTION_SCHEMA_VERSION = "oms.v1.business_correction"

ELIGIBLE = "ELIGIBLE_FOR_CORRECTION"
INELIGIBLE = "INELIGIBLE_FOR_CORRECTION"

PROPOSED = "PROPOSED"
APPLIED = "APPLIED"
REJECTED = "REJECTED"

ALLOWED_CORRECTION_TYPES = {
    "DUPLICATE_IDENTIFIER",
    "FIELD_FORMAT_ERROR",
    "OBVIOUS_ENTRY_ERROR",
}

FORBIDDEN_DISPUTES = {
    "AMOUNT_DISPUTE",
    "CUSTOMER_OWNERSHIP_DISPUTE",
    "PAYMENT_FACT_DISPUTE",
}

DOMAIN_CORRECTION_ROLES = {
    "Sales": {"ROLE_SALES", "ROLE_ACCOUNTANT", "ROLE_OWNER"},
    "Finance": {"ROLE_CASHIER", "ROLE_ACCOUNTANT", "ROLE_OWNER"},
    "Room": {"ROLE_STORE_MANAGER", "ROLE_OWNER"},
    "ActualStay": {"ROLE_STORE_MANAGER", "ROLE_OWNER"},
    "ContractStayPlan": {"ROLE_SALES", "ROLE_STORE_MANAGER", "ROLE_OWNER"},
}


@dataclass(frozen=True)
class CorrectionAssessment:
    correction_type: str
    domain: str
    result: str
    reasons: tuple[str, ...]
    assessed_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        return payload


@dataclass
class BusinessCorrectionRecord:
    domain: str
    entity_id: str
    field_name: str
    original_value: str
    corrected_value: str
    correction_type: str
    correction_reason: str
    requested_by_emp_id: str
    source_file: str
    source_sheet: str
    source_row: int
    correlation_id: str
    correction_id: str = field(default_factory=lambda: new_id("correction"))
    schema_version: str = CORRECTION_SCHEMA_VERSION
    status: str = PROPOSED
    requested_at: str = field(default_factory=now_iso)
    confirmed_by_emp_id: str = ""
    applied_at: str = ""
    audit_id: str = ""
    event_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BusinessCorrectionEngine:
    """Create traceable derived corrections without mutating source records."""

    def __init__(
        self,
        *,
        master_data: OMSMasterData | None = None,
        audit: AuditEngine | None = None,
        event_bus: EventBus | None = None,
    ):
        self.master_data = master_data or OMSMasterData()
        self.audit = audit or AuditEngine()
        self.event_bus = event_bus or EventBus()
        self._records: dict[str, BusinessCorrectionRecord] = {}

    def assess(
        self,
        *,
        correction_type: str,
        domain: str,
        dispute_flags: Iterable[str] = (),
        original_value: str,
        corrected_value: str,
    ) -> dict[str, Any]:
        reasons: list[str] = []
        flags = {str(item).strip().upper() for item in dispute_flags}
        forbidden = sorted(flags & FORBIDDEN_DISPUTES)
        if correction_type not in ALLOWED_CORRECTION_TYPES:
            reasons.append("correction_type_not_allowed")
        if domain not in DOMAIN_CORRECTION_ROLES:
            reasons.append("domain_not_supported")
        if forbidden:
            reasons.extend(f"forbidden_dispute:{item}" for item in forbidden)
        if not str(original_value).strip():
            reasons.append("original_value_required")
        if not str(corrected_value).strip():
            reasons.append("corrected_value_required")
        if str(original_value) == str(corrected_value):
            reasons.append("corrected_value_must_differ")
        result = INELIGIBLE if reasons else ELIGIBLE
        return CorrectionAssessment(correction_type, domain, result, tuple(reasons)).to_dict()

    def propose(
        self,
        *,
        actor_emp_id: str,
        domain: str,
        entity_id: str,
        field_name: str,
        original_value: str,
        corrected_value: str,
        correction_type: str,
        correction_reason: str,
        source_file: str,
        source_sheet: str,
        source_row: int,
        correlation_id: str,
        dispute_flags: Iterable[str] = (),
    ) -> dict[str, Any]:
        if not correction_reason.strip():
            raise ValueError("correction_reason is required")
        actor = self._authorize(actor_emp_id, domain)
        assessment = self.assess(
            correction_type=correction_type,
            domain=domain,
            dispute_flags=dispute_flags,
            original_value=original_value,
            corrected_value=corrected_value,
        )
        if assessment["result"] != ELIGIBLE:
            raise ValueError("correction is not eligible: " + ", ".join(assessment["reasons"]))
        record = BusinessCorrectionRecord(
            domain=domain,
            entity_id=entity_id,
            field_name=field_name,
            original_value=str(original_value),
            corrected_value=str(corrected_value),
            correction_type=correction_type,
            correction_reason=correction_reason,
            requested_by_emp_id=actor.emp,
            source_file=source_file,
            source_sheet=source_sheet,
            source_row=int(source_row),
            correlation_id=correlation_id,
        )
        self._records[record.correction_id] = record
        audit = self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="business_correction",
            action="business.correction.propose",
            reason=correction_reason,
            result=PROPOSED,
            target_type=domain,
            target_id=entity_id,
            before_hash=self._value_hash(record.original_value),
            after_hash=self._value_hash(record.corrected_value),
            correlation_id=correlation_id,
            metadata={
                "field_name": field_name,
                "original_value": record.original_value,
                "corrected_value": record.corrected_value,
                "source_file": source_file,
                "source_sheet": source_sheet,
                "source_row": source_row,
                "correction_id": record.correction_id,
            },
        )
        event = self.event_bus.publish(
            OMSEvent(
                event_type="business.correction.proposed",
                source_module="business_correction",
                subject=domain,
                action="proposed",
                emp_id=actor.emp,
                actor_name=actor.name,
                correlation_id=correlation_id,
                payload=record.to_dict(),
            )
        )
        return {"assessment": assessment, "correction": record.to_dict(), "audit": audit, "event": event}

    def apply(
        self,
        correction_id: str,
        *,
        confirming_emp_id: str,
        reason: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("confirmation reason is required")
        record = self._records.get(correction_id)
        if record is None:
            raise KeyError(correction_id)
        if record.status != PROPOSED:
            raise ValueError("only proposed corrections can be applied")
        actor = self._authorize(confirming_emp_id, record.domain)
        record.status = APPLIED
        record.confirmed_by_emp_id = actor.emp
        record.applied_at = now_iso()
        audit = self.audit.record(
            emp_id=actor.emp,
            actor_name=actor.name,
            module="business_correction",
            action="business.correction.apply",
            reason=reason,
            result=APPLIED,
            target_type=record.domain,
            target_id=record.entity_id,
            before_hash=self._value_hash(record.original_value),
            after_hash=self._value_hash(record.corrected_value),
            correlation_id=record.correlation_id,
            metadata={
                "correction_id": record.correction_id,
                "field_name": record.field_name,
                "original_value": record.original_value,
                "corrected_value": record.corrected_value,
                "requested_by_emp_id": record.requested_by_emp_id,
                "confirmed_by_emp_id": record.confirmed_by_emp_id,
                "applied_at": record.applied_at,
            },
        )
        event = self.event_bus.publish(
            OMSEvent(
                event_type="business.correction.applied",
                source_module="business_correction",
                subject=record.domain,
                action="applied",
                emp_id=actor.emp,
                actor_name=actor.name,
                correlation_id=record.correlation_id,
                payload=record.to_dict(),
            )
        )
        record.audit_id = str(audit["audit_id"])
        record.event_id = str(event["event"]["event_id"])
        return {"correction": record.to_dict(), "audit": audit, "event": event}

    def corrected_record(self, source_record: dict[str, Any], correction_id: str) -> dict[str, Any]:
        record = self._records.get(correction_id)
        if record is None:
            raise KeyError(correction_id)
        if record.status != APPLIED:
            raise ValueError("correction is not applied")
        result = dict(source_record)
        result[record.field_name] = record.corrected_value
        result["source_original_values"] = {
            **dict(result.get("source_original_values") or {}),
            record.field_name: record.original_value,
        }
        result["business_correction_id"] = record.correction_id
        return result

    def record(self, correction_id: str) -> dict[str, Any]:
        if correction_id not in self._records:
            raise KeyError(correction_id)
        return self._records[correction_id].to_dict()

    def _authorize(self, emp_id: str, domain: str):
        employee = self.master_data.employee_by_emp(emp_id)
        if employee.role_code not in DOMAIN_CORRECTION_ROLES.get(domain, set()):
            raise PermissionError(f"{emp_id} cannot correct {domain}")
        return employee

    @staticmethod
    def _value_hash(value: str) -> str:
        import hashlib

        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()
