from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .audit_log import AuditEngine
from .data_quality import HEALTH_PASS, TruthSourceSnapshotManager
from .event_bus import EventBus
from .production_data_adapter import (
    FINANCE_ADAPTER_ID,
    PRODUCTION_MAPPING_VERSION,
    ROOM_ADAPTER_ID,
    SALES_ADAPTER_ID,
    STAY_ADAPTER_ID,
    ProductionDataAdapter,
)
from .schemas import now_iso
from .truth_source import TruthSourceStore


DEFAULT_EXPECTED_COUNTS = {"sales": 224, "finance": 1278, "room": 42, "stay": 172}


class ProductionSnapshotBuilder:
    """Build and activate an immutable snapshot from the current Truth Source."""

    def __init__(self, truth_root: str | Path, *, audit_root: str | Path | None = None):
        self.truth_root = Path(truth_root)
        self.store = TruthSourceStore(self.truth_root, self.truth_root, truth_root=self.truth_root)
        self.adapter = ProductionDataAdapter(self.store)
        self.manager = TruthSourceSnapshotManager(
            self.truth_root / "snapshots",
            audit=AuditEngine(audit_root or self.truth_root / "snapshots" / "audit"),
            event_bus=EventBus(),
        )

    def build(
        self,
        *,
        actor_emp_id: str = "EMP001",
        expected_counts: dict[str, int] | None = None,
        activate: bool = True,
    ) -> dict[str, Any]:
        expected = dict(expected_counts or DEFAULT_EXPECTED_COUNTS)
        records = {
            "sales": self.adapter.sales_records(),
            "finance": self.adapter.financial_event_records(),
            "finance_settlement": self.adapter.finance_records(),
            "room": self.adapter.room_records(),
            "stay": self.adapter.stay_records(),
        }
        actual = {domain: len(records[domain]) for domain in ("sales", "finance", "room", "stay")}
        unresolved = self._unresolved_anomalies(records, expected)
        quarantine = self._quarantine_counts()
        if any(quarantine.values()):
            unresolved.append(
                {
                    "code": "quarantine_not_empty",
                    "severity": "high",
                    "owner": "quality_check_owner",
                    "reason": "Quarantined records cannot enter the active production snapshot.",
                    "counts": quarantine,
                }
            )
        health = self.adapter.data_quality_summary()
        acceptance = HEALTH_PASS if health.get("status") == HEALTH_PASS and not unresolved else "FAIL"
        source_locks = self._source_locks()
        created_at = now_iso()
        run_id = f"DQ-SNAPSHOT-{created_at.replace(':', '').replace('-', '')}"
        source_sheets = self._source_sheets(records)
        source_versions = {
            domain: self.store.read_domain(domain).get("source_version")
            or self.store.read_domain(domain).get("updated_at")
            or source_locks[domain]["sha256"]
            for domain in ("sales", "finance", "room", "stay")
        }
        payload = self.manager.create(
            acceptance_date=date.today(),
            actor_emp_id=actor_emp_id,
            acceptance_run_id=run_id,
            acceptance_result=acceptance,
            source_files=[dict({"data_domain": domain}, **metadata) for domain, metadata in source_locks.items()],
            source_sheets=source_sheets,
            import_ids=[run_id],
            imported_at=[created_at],
            quality_report_ids=[f"{run_id}-QUALITY"],
            quality_results={
                "status": acceptance,
                "health_score": health.get("score"),
                "domain_scores": health.get("domain_scores") or {},
                "quarantine_counts": quarantine,
                "unresolved_anomalies": unresolved,
            },
            adapter_versions=[
                {"data_domain": "sales", "adapter_id": SALES_ADAPTER_ID, "mapping_version": PRODUCTION_MAPPING_VERSION},
                {"data_domain": "finance", "adapter_id": FINANCE_ADAPTER_ID, "mapping_version": PRODUCTION_MAPPING_VERSION},
                {"data_domain": "room", "adapter_id": ROOM_ADAPTER_ID, "mapping_version": PRODUCTION_MAPPING_VERSION},
                {"data_domain": "stay", "adapter_id": STAY_ADAPTER_ID, "mapping_version": PRODUCTION_MAPPING_VERSION},
            ],
            truth_source_record_counts={
                "sales_current": actual["sales"],
                "finance_current": actual["finance"],
                "room_current": actual["room"],
                "stay_current": actual["stay"],
                "finance_settlement_current": len(records["finance_settlement"]),
                "quarantine": sum(quarantine.values()),
            },
            metric_values={
                "sales": self.adapter.sales_metrics(),
                "finance": self.adapter.finance_metrics(),
                "operations": self.adapter.operations_metrics(),
            },
            data_health_scores={
                "overall": health.get("score"),
                "status": health.get("status"),
                "domains": health.get("domain_scores") or {},
            },
            snapshot_metadata={
                "data_versions": source_versions,
                "production_lock": {
                    "source_files": source_locks,
                    "current_record_ids": {
                        domain: [str(item.get("record_id") or "") for item in values]
                        for domain, values in records.items()
                    },
                    "quarantine_counts": quarantine,
                    "unresolved_anomalies": unresolved,
                    "replacement_policy": "create_new_snapshot_never_overwrite_active",
                },
            },
            hard_fail_reasons=[item["code"] for item in unresolved if item.get("severity") in {"critical", "high"}],
            activate_for_production=bool(activate and acceptance == HEALTH_PASS),
            correlation_id=run_id,
        )
        return payload

    def _source_locks(self) -> dict[str, dict[str, Any]]:
        locks: dict[str, dict[str, Any]] = {}
        for domain in ("sales", "finance", "room", "stay"):
            path = self.truth_root / f"{domain}.json"
            if not path.is_file():
                raise FileNotFoundError(path)
            content = path.read_bytes()
            locks[domain] = {
                "relative_path": path.name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                "source_version": self.store.read_domain(domain).get("source_version")
                or self.store.read_domain(domain).get("updated_at")
                or "",
            }
        return locks

    def _unresolved_anomalies(
        self,
        records: dict[str, list[dict[str, Any]]],
        expected: dict[str, int],
    ) -> list[dict[str, Any]]:
        anomalies: list[dict[str, Any]] = []
        for domain in ("sales", "finance", "room", "stay"):
            values = records[domain]
            if len(values) != expected.get(domain):
                anomalies.append(
                    {
                        "code": f"{domain}_current_count_mismatch",
                        "severity": "high",
                        "owner": self._owner(domain),
                        "reason": f"Expected {expected.get(domain)} Current records, found {len(values)}.",
                    }
                )
            ids = [str(item.get("record_id") or "") for item in values]
            if not all(ids) or len(ids) != len(set(ids)):
                anomalies.append(
                    {
                        "code": f"{domain}_record_id_invalid",
                        "severity": "high",
                        "owner": self._owner(domain),
                        "reason": "Current records must have unique non-empty record_id values.",
                    }
                )
            missing_trace = sum(
                1 for item in values if not self.adapter._trace_complete(item.get("source_evidence"))
            )
            if missing_trace:
                anomalies.append(
                    {
                        "code": f"{domain}_trace_incomplete",
                        "severity": "high",
                        "owner": self._owner(domain),
                        "reason": f"{missing_trace} Current records have incomplete source trace.",
                    }
                )
        return anomalies

    def _quarantine_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for domain in ("sales", "finance", "room", "stay"):
            payload = self.store.read_domain(domain)
            values = payload.get("quarantine") or payload.get("quarantine_records") or []
            counts[domain] = len(values) if isinstance(values, list) else 0
        return counts

    def _source_sheets(self, records: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for domain, values in records.items():
            if domain == "finance_settlement":
                continue
            grouped: dict[tuple[str, str], int] = {}
            for item in values:
                evidence = item.get("source_evidence") or {}
                key = (str(evidence.get("source_file") or ""), str(evidence.get("source_sheet") or ""))
                grouped[key] = grouped.get(key, 0) + 1
            rows.extend(
                {
                    "data_domain": domain,
                    "source_file": source_file,
                    "source_sheet": source_sheet,
                    "current_record_count": count,
                }
                for (source_file, source_sheet), count in sorted(grouped.items())
            )
        return rows

    @staticmethod
    def _owner(domain: str) -> str:
        return {"sales": "销售负责人", "finance": "财务负责人", "room": "店总", "stay": "店总"}[domain]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and activate an OMS production Truth Source snapshot.")
    parser.add_argument("--truth-root", required=True)
    parser.add_argument("--actor-emp-id", default="EMP001")
    parser.add_argument("--no-activate", action="store_true")
    args = parser.parse_args()
    result = ProductionSnapshotBuilder(args.truth_root).build(
        actor_emp_id=args.actor_emp_id,
        activate=not args.no_activate,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
