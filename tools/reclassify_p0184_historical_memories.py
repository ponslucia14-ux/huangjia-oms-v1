from __future__ import annotations

import argparse
import json
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

    sales_analysis = json.loads((args.candidate_root / "Sales_data_quality_candidate.json").read_text(encoding="utf-8"))
    inventory = {item["source_sheet"]: item for item in sales_analysis["inventory"]}

    original_entries = list(memory.entries())
    for entry in original_entries:
        domain = str(entry.get("domain") or "")
        status = str(entry.get("memory_status") or "")
        fact_type = str(entry.get("fact_type") or "")
        if domain == "ActualStay" and status == SheetSemanticMemory.TEMPORARY:
            memory.transition_status(
                str(entry["memory_version"]),
                status=SheetSemanticMemory.CONFIRMED,
                actor_emp_id="EMP001",
                actor_name="石磊",
                reason="Confirm in-residence Sheet as Actual Stay historical snapshot; it is not Current.",
            )
        if domain != "Sales" or status != SheetSemanticMemory.TEMPORARY or fact_type != "Sales Current Candidate":
            continue
        memory.transition_status(
            str(entry["memory_version"]),
            status=SheetSemanticMemory.DEPRECATED,
            actor_emp_id="EMP001",
            actor_name="石磊",
            reason="Historical-first cutover policy supersedes Sales Current candidate semantics.",
        )
        sheet_name = str(entry["source_sheet"])
        sheet = inventory[sheet_name]
        memory.confirm(
            source_file_pattern=str(entry["source_file_pattern"]),
            source_sheet=sheet_name,
            domain="Sales",
            fact_type="Sales Historical Import",
            owner=str(entry["owner"]),
            profile={
                "header_row": 1,
                "column_count": sheet["max_column"],
                "fields": [
                    {"source_field": name, "canonical_field": name}
                    for name in ("合同编号", "签约日期", "宝妈姓名", "全款费用")
                ],
            },
            workbook_sheets=[item["source_sheet"] for item in sales_analysis["inventory"]],
            quality_result="WARNING",
            memory_status=SheetSemanticMemory.CONFIRMED,
            actor_emp_id="EMP001",
            actor_name="石磊",
            reason="Confirm Sales Sheet historical import semantics with record-level warnings retained.",
        )

    entries = memory.entries()
    summary = {
        "total_versions": len(entries),
        "status_counts": {},
        "domain_status_counts": {},
        "audit_event_count": len(audit.events(sort_by_time=False)),
        "current_semantics_created": False,
        "active_snapshot_unchanged": "TS-20260711-V1",
    }
    for entry in entries:
        status = str(entry.get("memory_status") or "")
        domain = str(entry.get("domain") or "")
        summary["status_counts"][status] = summary["status_counts"].get(status, 0) + 1
        key = f"{domain}:{status}"
        summary["domain_status_counts"][key] = summary["domain_status_counts"].get(key, 0) + 1
    (args.candidate_root / "P0184_HISTORICAL_MEMORY_RECLASSIFICATION.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
