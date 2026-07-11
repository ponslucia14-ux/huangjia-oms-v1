from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.data_quality import SheetSemanticMemory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, required=True)
    args = parser.parse_args()

    memory_path = args.candidate_root / "sheet_semantic_memory_candidates.json"
    audit = AuditEngine(args.candidate_root / "semantic_memory_audit")
    memory = SheetSemanticMemory(memory_path, audit=audit)

    confirmed_domains = {"Finance", "ContractStayPlan"}
    for entry in memory.entries():
        if entry.get("domain") not in confirmed_domains:
            continue
        memory.transition_status(
            str(entry["memory_version"]),
            status=SheetSemanticMemory.CONFIRMED,
            actor_emp_id="EMP001",
            actor_name="石磊",
            reason="P0.18.4 domain anomaly disposition completed; confirm Sheet semantic purpose without bypassing record quality.",
        )

    entries = memory.entries()
    status_counts: dict[str, int] = {}
    domain_counts: dict[str, dict[str, int]] = {}
    for entry in entries:
        status = str(entry.get("memory_status") or "")
        domain = str(entry.get("domain") or "")
        status_counts[status] = status_counts.get(status, 0) + 1
        bucket = domain_counts.setdefault(domain, {})
        bucket[status] = bucket.get(status, 0) + 1

    closure = {
        "schema_version": "oms.p0184.anomaly_closure",
        "generated_at": datetime.now().astimezone().isoformat(),
        "active_snapshot_unchanged": "TS-20260711-V1",
        "candidate_snapshot": "TS-20260711-V2",
        "domains": {
            "Sales": {
                "status": "BLOCKED",
                "admissible_candidate_count": 184,
                "quarantine_count": 2,
                "blocking_issue": "NSEKI94131081 maps to two different customers in every available sales workbook version",
                "required_evidence": "original signed contract or authoritative payment/contract record",
            },
            "Finance": {
                "status": "CLOSED",
                "historical_count": 470,
                "current_status": "NOT_INITIALIZED",
                "quarantine_count": 0,
            },
            "ContractStayPlan": {
                "status": "CLOSED_WITH_QUARANTINE",
                "admitted_plan_count": 1319,
                "quarantine_count": 7,
                "admitted_quality_result": "PASS",
                "quarantine_disposition": "excluded from Plan because required plan fields are incomplete; source rows retained",
            },
            "ActualStay": {
                "status": "BLOCKED",
                "historical_snapshot_count": 33,
                "quarantine_count": 5,
                "source_effective_date": "2026-07-02",
                "reported_resident_count": 30,
                "calculated_active_count": 33,
                "blocking_issue": "source is older than cutover and detail/summary counts disagree",
                "required_evidence": "latest original in-residence workbook or OMS Current confirmation by EMP008",
            },
        },
        "semantic_memory": {
            "total": len(entries),
            "status_counts": status_counts,
            "domain_counts": domain_counts,
            "audit_event_count": len(audit.events(sort_by_time=False)),
        },
        "v2_gate": {
            "status": "BLOCKED",
            "ready": False,
            "unresolved_domains": ["Sales", "ActualStay"],
            "v2_generated": False,
            "v1_modified": False,
        },
    }
    target = args.candidate_root / "P0184_ANOMALY_CLOSURE.json"
    target.write_text(json.dumps(closure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(closure, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
