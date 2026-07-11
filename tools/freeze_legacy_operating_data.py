from __future__ import annotations

import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from oms_v1.master_data import OMSMasterData


LIVE_ROOT = REPO_ROOT / "live_runtime"
SOURCE_ROOT = LIVE_ROOT / "emp001_uat_truth"
SNAPSHOT_ID = "TS-20260711-V1"
ARCHIVE_ROOT = LIVE_ROOT / "historical_archive" / SNAPSHOT_ID
FROZEN_AT = datetime.now().astimezone().isoformat(timespec="seconds")

RAW_FILES = [
    Path(r"D:\Users\758595\xwechat_files\wxid_vlgopee1wc6922_c124\msg\file\2026-07\2026年销售明细表（经验为王7.10）(1).xlsx"),
    Path(r"D:\Users\758595\xwechat_files\wxid_vlgopee1wc6922_c124\msg\file\2026-07\2026年财务报表（7月）.xlsx"),
    Path(r"D:\Users\758595\xwechat_files\wxid_vlgopee1wc6922_c124\msg\file\2026-07\①凰家母婴 2021房态表June(1).xlsx"),
    Path(r"D:\Users\758595\xwechat_files\wxid_vlgopee1wc6922_c124\msg\file\2026-07\A  凰家母婴签约客户一览表（挤牙膏）(1).xlsx"),
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def copy_frozen(source: Path, relative_target: str, files: list[dict[str, Any]]) -> None:
    if not source.is_file():
        files.append({"source": str(source), "archive_path": relative_target, "status": "MISSING"})
        return
    target = ARCHIVE_ROOT / relative_target
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and digest(target) != digest(source):
        raise FileExistsError(f"Frozen archive target differs: {target}")
    if not target.exists():
        shutil.copy2(source, target)
    files.append(
        {
            "source": str(source),
            "archive_path": relative_target,
            "status": "FROZEN",
            "size_bytes": target.stat().st_size,
            "sha256": digest(target),
        }
    )


def json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    manifest_path = ARCHIVE_ROOT / "archive_manifest.json"
    if manifest_path.exists():
        existing = json_file(manifest_path)
        print(
            json.dumps(
                {
                    "manifest": str(manifest_path),
                    "status": "ALREADY_FROZEN",
                    "frozen_at": existing.get("frozen_at"),
                    "counts": existing.get("counts") or {},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    files: list[dict[str, Any]] = []
    sales = json_file(SOURCE_ROOT / "sales.json")
    finance = json_file(SOURCE_ROOT / "finance.json")
    room = json_file(SOURCE_ROOT / "room.json")
    stay = json_file(SOURCE_ROOT / "stay.json")

    sales_entities = [item for item in sales.get("entities") or [] if isinstance(item, dict)]
    customer_names = {str(item.get("customer_name") or item.get("guest_name") or "").strip() for item in sales_entities}
    contract_ids = {str(item.get("contract_id") or "").strip() for item in sales_entities}
    customer_names.discard("")
    contract_ids.discard("")

    copy_frozen(SOURCE_ROOT / "sales.json", "Customer Archive/sales_legacy.json", files)
    copy_frozen(SOURCE_ROOT / "sales.json", "Contract Archive/contracts_legacy.json", files)
    copy_frozen(SOURCE_ROOT / "finance.json", "Finance Archive/finance_legacy.json", files)
    copy_frozen(SOURCE_ROOT / "room.json", "Room Archive/room_legacy.json", files)
    copy_frozen(SOURCE_ROOT / "stay.json", "Stay Archive/stay_legacy.json", files)
    copy_frozen(SOURCE_ROOT / "snapshots" / f"{SNAPSHOT_ID}.json", f"Snapshot/{SNAPSHOT_ID}.json", files)
    copy_frozen(SOURCE_ROOT / "snapshots" / "ACTIVE_SNAPSHOT.json", "Snapshot/legacy_active_pointer.json", files)
    copy_frozen(LIVE_ROOT / "audit_center" / "audit_events.jsonl", "Other Archive/Audit/audit_events.jsonl", files)
    copy_frozen(REPO_ROOT / "OMS_TRUTH_SOURCE" / "events.jsonl", "Other Archive/Event/events.jsonl", files)
    copy_frozen(LIVE_ROOT / "core_fusion" / "unified_task_stream.jsonl", "Other Archive/Task/unified_task_stream.jsonl", files)
    copy_frozen(REPO_ROOT / "master_data" / "OMS十一人飞书身份最终一致性报告.md", "Employee Archive/identity_consistency_report.md", files)
    copy_frozen(REPO_ROOT / "master_data" / "OMS数据变更权限设计.md", "Employee Archive/data_change_permissions.md", files)
    copy_frozen(REPO_ROOT / "master_data" / "OMS生产数据责任矩阵.md", "Employee Archive/data_responsibility_matrix.md", files)
    for source in RAW_FILES:
        copy_frozen(source, f"Raw Sources/{source.name}", files)

    employees = [asdict(employee) for employee in OMSMasterData().employees()]
    employee_path = ARCHIVE_ROOT / "Employee Archive" / "employees_legacy.json"
    employee_path.parent.mkdir(parents=True, exist_ok=True)
    employee_path.write_text(json.dumps(employees, ensure_ascii=False, indent=2), encoding="utf-8")
    files.append(
        {
            "source": "OMSMasterData",
            "archive_path": "Employee Archive/employees_legacy.json",
            "status": "FROZEN",
            "size_bytes": employee_path.stat().st_size,
            "sha256": digest(employee_path),
        }
    )

    manifest = {
        "schema_version": "oms.v1.historical_archive",
        "archive_id": f"ARCHIVE-{SNAPSHOT_ID}",
        "frozen_at": FROZEN_AT,
        "snapshot_id": SNAPSHOT_ID,
        "snapshot_status": "ARCHIVED_LEGACY",
        "legacy_current_label": "ARCHIVED",
        "future_current_eligible": False,
        "immutable": True,
        "physical_delete_allowed": False,
        "counts": {
            "customer_unique_names": len(customer_names),
            "customer_records": len(sales_entities),
            "contract_records": len(sales_entities),
            "contract_unique_ids": len(contract_ids),
            "finance_records": len(finance.get("financial_events") or finance.get("entities") or []),
            "finance_settlement_records": len(finance.get("settlement_records") or []),
            "room_records": len(room.get("room_records") or room.get("entities") or []),
            "stay_records": len(stay.get("stay_records") or stay.get("entities") or []),
            "employee_records": len(employees),
        },
        "known_issues": [
            "Legacy Current does not represent the real operating Current baseline.",
            "Historical, planned and inferred records are mixed in legacy Stay data.",
            "Legacy Room occupancy was inferred from calendar markers rather than verified Actual Stay Current.",
            "Legacy Finance is historical flow data rather than a verified current cash position.",
        ],
        "next_phase": "WORKSPACE_DESIGN_PHASE",
        "files": files,
    }
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    operating_state = {
        "schema_version": "oms.v1.operating_mode",
        "updated_at": FROZEN_AT,
        "phase": "WORKSPACE_DESIGN_PHASE",
        "current_operating_snapshot": None,
        "legacy_snapshot": SNAPSHOT_ID,
        "legacy_snapshot_status": "ARCHIVED_LEGACY",
        "legacy_current_label": "ARCHIVED",
        "cutover_allowed": False,
        "old_current_repair_allowed": False,
        "reason": "P0.19.1 legacy operating data frozen; waiting for eleven-workspace design.",
    }
    state_path = LIVE_ROOT / "operating_mode.json"
    state_path.write_text(json.dumps(operating_state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "state": str(state_path), "counts": manifest["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
