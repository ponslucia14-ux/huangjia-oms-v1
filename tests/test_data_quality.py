import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from oms_v1.audit_log import AuditEngine
from oms_v1.data_quality import (
    ADMITTED_CURRENT,
    AUXILIARY_CALCULATION,
    CHANGED,
    CONFLICT,
    CURRENT_PRODUCTION,
    DataHealthInput,
    DataHealthScorer,
    DataQualityEngine,
    DataQualityReportWriter,
    SheetSemanticMemory,
    HEALTH_FAIL,
    HEALTH_PASS,
    HEALTH_WARNING,
    HISTORICAL,
    MISSING,
    NEW,
    NOTES,
    QUALITY_ADMISSIBLE,
    QUALITY_PARTIAL,
    QUALITY_REVIEW,
    QUARANTINED,
    SUMMARY,
    TruthSourceSnapshotManager,
    UNCHANGED,
    UNCONFIRMED,
    default_quality_policy,
)
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class DataQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        organization_path = self.root / "OMS_organization_master_data.md"
        identity_path = self.root / "OMS_feishu_identity.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(
            organization_path=organization_path,
            feishu_identity_path=identity_path,
        )
        self.audit = AuditEngine(self.root / "audit")
        self.bus = EventBus()
        self.engine = DataQualityEngine(
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
            report_root=self.root / "quality_reports",
        )
        self.policy = default_quality_policy("Sales", source_version="2026-07-10.v1")

    def tearDown(self):
        self.tmp.cleanup()

    def _save_workbook(self, name, sheets):
        path = self.root / name
        workbook = Workbook()
        workbook.remove(workbook.active)
        for sheet_name, rows, visibility in sheets:
            sheet = workbook.create_sheet(sheet_name)
            for row in rows:
                sheet.append(row)
            sheet.sheet_state = visibility
        workbook.save(path)
        return path

    def _sales_rows(self, *records):
        return [
            ["客户姓名", "合同号", "合同金额", "合同状态", "签约日期"],
            *records,
        ]

    def _analyze(self, path, **kwargs):
        return self.engine.analyze_excel(
            path,
            policy=self.policy,
            actor_emp_id="EMP001",
            reason="Analyze workbook before Truth Source admission.",
            imported_at="2026-07-10T09:00:00+08:00",
            **kwargs,
        )

    def test_analyzes_every_sheet_including_hidden_and_classifies_usage(self):
        path = self._save_workbook(
            "sales.xlsx",
            [
                (
                    "Current",
                    self._sales_rows(["Customer A", "C-001", 20000, "签约", "2026-07-10"]),
                    "visible",
                ),
                (
                    "History",
                    self._sales_rows(["Customer B", "C-002", 18000, "已结束", "2025-01-10"]),
                    "hidden",
                ),
                ("Summary", [["汇总", "金额"], ["合同金额", 38000]], "visible"),
                ("Calculation", [["项目", "计算"], ["合计", "=1+1"]], "visible"),
                ("Notes", [["说明"], ["本表由销售维护"], ["金额由财务复核"]], "visible"),
            ],
        )

        result = self._analyze(path)

        self.assertEqual(result["workbook_sheet_count"], 5)
        profiles = {item["source_sheet"]: item for item in result["sheet_profiles"]}
        self.assertEqual(profiles["Current"]["usage_class"], CURRENT_PRODUCTION)
        self.assertEqual(profiles["Current"]["time_range_start"], "2026-07-10")
        self.assertEqual(profiles["Current"]["time_range_end"], "2026-07-10")
        self.assertEqual(profiles["History"]["usage_class"], HISTORICAL)
        self.assertEqual(profiles["History"]["visibility"], "HIDDEN")
        self.assertEqual(profiles["Summary"]["usage_class"], SUMMARY)
        self.assertEqual(profiles["Calculation"]["usage_class"], AUXILIARY_CALCULATION)
        self.assertEqual(profiles["Notes"]["usage_class"], NOTES)
        self.assertEqual(result["quality_status"], QUALITY_ADMISSIBLE)
        self.assertEqual(result["counts"]["current"], 1)
        self.assertEqual(result["counts"]["historical"], 1)
        self.assertEqual(result["counts"]["excluded_sheets"], 3)
        record = result["current_records"][0]
        self.assertEqual(record["source_sheet"], "Current")
        self.assertEqual(record["source_row"], 2)
        self.assertEqual(record["source_cells"]["contract_id"], "B2")
        self.assertEqual(record["payload"]["amount"], "20000.00")
        self.assertTrue(record["record_version_id"])
        self.assertEqual(record["admission_status"], ADMITTED_CURRENT)
        self.assertTrue(record["is_current"])
        self.assertFalse(result["mutates_truth_source"])
        self.assertTrue(Path(result["report_path"]).exists())

    def test_unconfirmed_sheet_never_enters_admitted_records(self):
        rows = [["Unknown A", "Unknown B", "Unknown C"]]
        rows.extend([[f"a-{index}", f"b-{index}", f"c-{index}"] for index in range(8)])
        path = self._save_workbook("unknown.xlsx", [("Mystery", rows, "visible")])

        result = self._analyze(path)

        self.assertEqual(result["sheet_profiles"][0]["usage_class"], UNCONFIRMED)
        self.assertEqual(result["quality_status"], QUALITY_REVIEW)
        self.assertEqual(result["counts"]["admitted"], 0)
        self.assertEqual(result["excluded_records"][0]["record_count"], 8)

    def test_detects_new_changed_and_missing_without_deleting_previous(self):
        first_path = self._save_workbook(
            "sales-v1.xlsx",
            [
                (
                    "Current",
                    self._sales_rows(
                        ["Customer A", "C-001", 20000, "签约", "2026-07-09"],
                        ["Customer B", "C-002", 18000, "签约", "2026-07-09"],
                    ),
                    "visible",
                )
            ],
        )
        first = self._analyze(first_path)
        self.assertEqual({item["change_type"] for item in first["current_records"]}, {NEW})

        second_path = self._save_workbook(
            "sales-v2.xlsx",
            [
                (
                    "Current",
                    self._sales_rows(
                        ["Customer A", "C-001", 22000, "签约", "2026-07-09"],
                        ["Customer C", "C-003", 30000, "签约", "2026-07-10"],
                    ),
                    "visible",
                )
            ],
        )
        second = self._analyze(second_path, previous_records=first["current_records"])

        changes = {item["payload"]["contract_id"]: item["change_type"] for item in second["current_records"]}
        self.assertEqual(changes, {"C-001": CHANGED, "C-003": NEW})
        self.assertEqual(len(second["missing_records"]), 1)
        self.assertEqual(second["missing_records"][0]["payload"]["contract_id"], "C-002")
        self.assertEqual(second["missing_records"][0]["change_type"], MISSING)
        self.assertFalse(second["missing_records"][0]["is_current"])
        self.assertEqual(second["quality_status"], QUALITY_PARTIAL)

    def test_normalized_amount_and_date_do_not_create_false_changes(self):
        first_path = self._save_workbook(
            "sales-number-v1.xlsx",
            [("Current", self._sales_rows(["Customer A", "C-001", 20000, "签约", "2026/07/10"]), "visible")],
        )
        first = self._analyze(first_path)
        second_path = self._save_workbook(
            "sales-number-v2.xlsx",
            [("Current", self._sales_rows(["Customer A", "C-001", "20,000.00", "签约", "2026-07-10"]), "visible")],
        )

        second = self._analyze(second_path, previous_records=first["current_records"])

        self.assertEqual(second["current_records"][0]["change_type"], UNCHANGED)
        self.assertEqual(second["current_records"][0]["payload"]["amount"], "20000.00")
        self.assertEqual(second["current_records"][0]["payload"]["contract_date"], "2026-07-10")

    def test_conflicting_duplicate_business_key_is_quarantined(self):
        path = self._save_workbook(
            "conflict.xlsx",
            [
                (
                    "Current",
                    self._sales_rows(
                        ["Customer A", "C-001", 20000, "签约", "2026-07-10"],
                        ["Customer A", "C-001", 25000, "签约", "2026-07-10"],
                    ),
                    "visible",
                )
            ],
        )

        result = self._analyze(path)

        self.assertEqual(result["counts"]["current"], 0)
        self.assertEqual(result["counts"]["quarantine"], 2)
        self.assertTrue(all(item["change_type"] == CONFLICT for item in result["quarantine_records"]))
        self.assertTrue(all(item["admission_status"] == QUARANTINED for item in result["quarantine_records"]))
        self.assertIn("data_quality.conflict.detected", [item["event_type"] for item in self.bus.events()])

    def test_missing_required_business_key_is_quarantined(self):
        path = self._save_workbook(
            "missing-key.xlsx",
            [("Current", self._sales_rows(["Customer A", None, 20000, "签约", "2026-07-10"]), "visible")],
        )

        result = self._analyze(path)

        self.assertEqual(result["counts"]["admitted"], 0)
        self.assertEqual(result["counts"]["quarantine"], 1)
        codes = {item["code"] for item in result["quarantine_records"][0]["quality_issues"]}
        self.assertIn("missing_business_key", codes)

    def test_analysis_writes_audit_and_events_without_truth_source_mutation(self):
        path = self._save_workbook(
            "sales.xlsx",
            [("Current", self._sales_rows(["Customer A", "C-001", 20000, "签约", "2026-07-10"]), "visible")],
        )

        result = self._analyze(path)

        actions = [item["action"] for item in self.audit.events(sort_by_time=False)]
        self.assertEqual(actions[0], "data_quality.import.request")
        self.assertIn("data_quality.sheet.analyzed", actions)
        self.assertIn("data_quality.record.evaluated", actions)
        self.assertEqual(actions[-1], "data_quality.admission.completed")
        event_types = [item["event_type"] for item in self.bus.events()]
        self.assertIn("data_quality.analysis.completed", event_types)
        self.assertIn("data_quality.truth_source.admitted", event_types)
        self.assertFalse(result["mutates_truth_source"])

    def test_data_health_score_and_hard_fail_override(self):
        scorer = DataHealthScorer()

        passed = scorer.score(DataHealthInput(1, 1, 1, 1))
        warning = scorer.score(DataHealthInput(1, 1, 0.5, 1))
        failed = scorer.score(DataHealthInput(1, 1, 1, 1, hard_fail_reasons=("amount_mismatch",)))

        self.assertEqual(passed["score"], 100)
        self.assertEqual(passed["status"], HEALTH_PASS)
        self.assertEqual(warning["score"], 92.5)
        self.assertEqual(warning["status"], HEALTH_WARNING)
        self.assertEqual(failed["score"], 100)
        self.assertEqual(failed["status"], HEALTH_FAIL)
        self.assertTrue(failed["hard_fail_override"])
        overall = scorer.overall({"sales": passed, "finance": warning})
        self.assertEqual(overall["score"], 96.25)
        self.assertEqual(overall["status"], HEALTH_WARNING)

    def test_health_score_applies_weighted_anomaly_penalties(self):
        result = DataHealthScorer().score(
            DataHealthInput(1, 1, 1, 1, anomaly_counts={"high": 1, "medium": 2, "low": 3})
        )

        self.assertEqual(result["dimensions"]["anomalies"], 1.7)
        self.assertEqual(result["score"], 96.7)
        self.assertEqual(result["status"], HEALTH_PASS)

    def test_snapshot_versions_are_immutable_and_only_pass_can_activate(self):
        manager = TruthSourceSnapshotManager(
            self.root / "snapshots",
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )
        common = {
            "acceptance_date": date(2026, 7, 10),
            "actor_emp_id": "EMP001",
            "acceptance_run_id": "accept-001",
            "source_files": [{"name": "sales.xlsx", "sha256": "abc", "version": "v1"}],
            "source_sheets": [{"name": "Current", "usage_class": CURRENT_PRODUCTION}],
            "import_ids": ["dqimport-001"],
            "imported_at": ["2026-07-10T09:00:00+08:00"],
            "quality_report_ids": ["dqreport-001"],
            "quality_results": {"sales": HEALTH_PASS},
            "adapter_versions": [{"adapter_id": "sales_adapter_v1", "mapping_version": "v1"}],
            "truth_source_record_counts": {"sales": 224},
            "metric_values": {"sales_total": 100000},
            "data_health_scores": {"sales": {"score": 100, "status": HEALTH_PASS}},
        }
        first = manager.create(
            **common,
            acceptance_result=HEALTH_PASS,
            activate_for_production=True,
        )
        second = manager.create(
            **{**common, "acceptance_run_id": "accept-002"},
            acceptance_result=HEALTH_FAIL,
            activate_for_production=False,
            hard_fail_reasons=["amount_mismatch"],
        )

        self.assertEqual(first["snapshot_version"], "TS-20260710-V1")
        self.assertTrue(first["activated_for_production"])
        self.assertEqual(second["snapshot_version"], "TS-20260710-V2")
        self.assertFalse(second["activated_for_production"])
        self.assertEqual(second["previous_snapshot_version"], "TS-20260710-V1")
        self.assertEqual(manager.active()["snapshot_version"], "TS-20260710-V1")
        self.assertEqual(manager.read("TS-20260710-V2")["hard_fail_reasons"], ["amount_mismatch"])
        with self.assertRaises(ValueError):
            manager.create(
                **{**common, "acceptance_run_id": "accept-003"},
                acceptance_result=HEALTH_WARNING,
                activate_for_production=True,
            )

    def test_snapshot_integrity_detects_manual_mutation(self):
        manager = TruthSourceSnapshotManager(
            self.root / "snapshots",
            audit=self.audit,
            event_bus=self.bus,
            master_data=self.master_data,
        )
        snapshot = manager.create(
            acceptance_date="20260710",
            actor_emp_id="EMP001",
            acceptance_run_id="accept-001",
            acceptance_result=HEALTH_PASS,
            source_files=[],
            source_sheets=[],
            import_ids=[],
            imported_at=[],
            quality_report_ids=[],
            quality_results={},
            adapter_versions=[],
            truth_source_record_counts={},
            metric_values={},
            data_health_scores={},
        )
        path = self.root / "snapshots" / f"{snapshot['snapshot_version']}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["acceptance_result"] = HEALTH_FAIL
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(ValueError):
            manager.read(snapshot["snapshot_version"])

    def test_quality_report_contains_sheet_analysis_and_admission_counts(self):
        path = self._save_workbook(
            "sales.xlsx",
            [("Current", self._sales_rows(["Customer A", "C-001", 20000, "签约", "2026-07-10"]), "visible")],
        )
        result = self._analyze(path)

        report_path = DataQualityReportWriter().write(result, self.root / "sales数据质量报告.md")
        report = report_path.read_text(encoding="utf-8")

        self.assertIn("Sheet 分析", report)
        self.assertIn("Current", report)
        self.assertIn("当前记录：1", report)
        self.assertIn("不直接修改生产 Truth Source", report)

    def test_unknown_actor_is_rejected_before_workbook_analysis(self):
        path = self._save_workbook(
            "sales.xlsx",
            [("Current", self._sales_rows(["Customer A", "C-001", 20000, "签约", "2026-07-10"]), "visible")],
        )

        with self.assertRaises(KeyError):
            self.engine.analyze_excel(
                path,
                policy=self.policy,
                actor_emp_id="EMP999",
                reason="Unknown actor cannot analyze production data.",
            )

    def test_sheet_semantic_memory_reuses_confirmed_meaning_for_same_structure(self):
        memory = SheetSemanticMemory(self.root / "sheet_semantic_memory.json", audit=self.audit)
        profile = {
            "header_row": 1,
            "column_count": 3,
            "fields": [
                {"source_field": "客户姓名", "canonical_field": "customer_name"},
                {"source_field": "合同号", "canonical_field": "contract_id"},
                {"source_field": "金额", "canonical_field": "amount"},
            ],
        }
        first = memory.confirm(
            source_file_pattern="sales-*.xlsx",
            source_sheet="Current",
            domain="Sales",
            fact_type="Sales Current",
            owner="EMP006",
            profile=profile,
            workbook_sheets=["Current", "History"],
            quality_result=HEALTH_PASS,
        )
        self.assertEqual(first["memory_status"], SheetSemanticMemory.CONFIRMED)
        self.assertTrue(first["memory_version"].endswith("-V1"))
        resolved = memory.resolve(
            source_file="sales-20260712.xlsx",
            source_sheet="Current",
            domain="Sales",
            profile=profile,
            workbook_sheets=["Current", "History"],
            quality_result=HEALTH_PASS,
        )
        self.assertEqual(resolved["status"], SheetSemanticMemory.STATUS_AUTO)
        self.assertEqual(resolved["memory"]["owner"], "EMP006")
        self.assertEqual(resolved["memory"]["fact_type"], "Sales Current")

    def test_sheet_semantic_memory_versions_are_append_only_and_audited(self):
        memory = SheetSemanticMemory(self.root / "versioned_sheet_memory.json", audit=self.audit)
        profile = {"header_row": 1, "column_count": 1, "fields": [{"source_field": "房号", "canonical_field": "room_id"}]}
        common = {
            "source_file_pattern": "room-*.xlsx",
            "source_sheet": "Current",
            "domain": "Room",
            "fact_type": "Room Current",
            "owner": "EMP008",
            "profile": profile,
            "workbook_sheets": ["Current"],
            "quality_result": HEALTH_PASS,
        }
        first = memory.confirm(**common)
        second = memory.confirm(**common, reason="Confirm revised Room Sheet rule.")

        self.assertTrue(first["memory_version"].endswith("-V1"))
        self.assertTrue(second["memory_version"].endswith("-V2"))
        self.assertEqual(len(memory.entries()), 2)
        memory.transition_status(
            first["memory_version"],
            status=SheetSemanticMemory.DEPRECATED,
            actor_emp_id="EMP001",
            actor_name="石磊",
            reason="Superseded by V2.",
        )
        self.assertEqual(memory.entries()[0]["memory_status"], SheetSemanticMemory.DEPRECATED)
        actions = [item["action"] for item in self.audit.events(sort_by_time=False)]
        self.assertIn("sheet.semantic_memory.created", actions)
        self.assertIn("sheet.semantic_memory.status_changed", actions)

    def test_temporary_sheet_semantic_memory_never_auto_admits(self):
        memory = SheetSemanticMemory(self.root / "temporary_sheet_memory.json")
        profile = {"header_row": 1, "column_count": 1, "fields": [{"source_field": "日期", "canonical_field": "tx_date"}]}
        memory.confirm(
            source_file_pattern="finance-*.xlsx",
            source_sheet="日报",
            domain="Finance",
            fact_type="Finance Current",
            owner="EMP004",
            profile=profile,
            workbook_sheets=["日报"],
            quality_result=HEALTH_PASS,
            memory_status=SheetSemanticMemory.TEMPORARY,
        )
        resolved = memory.resolve(
            source_file="finance-20260711.xlsx",
            source_sheet="日报",
            domain="Finance",
            profile=profile,
            workbook_sheets=["日报"],
            quality_result=HEALTH_PASS,
        )
        self.assertEqual(resolved["status"], SheetSemanticMemory.STATUS_REVIEW)
        self.assertEqual(resolved["reasons"], ["temporary_memory_requires_review"])

    def test_sheet_semantic_memory_requires_review_on_sheet_field_structure_or_quality_change(self):
        memory = SheetSemanticMemory(self.root / "sheet_semantic_memory.json")
        profile = {
            "header_row": 1,
            "column_count": 2,
            "fields": [
                {"source_field": "房号", "canonical_field": "room_id"},
                {"source_field": "房态", "canonical_field": "status"},
            ],
        }
        memory.confirm(
            source_file_pattern="room-*.xlsx",
            source_sheet="RoomCurrent",
            domain="Room",
            fact_type="Room Current",
            owner="EMP008",
            profile=profile,
            workbook_sheets=["RoomCurrent"],
            quality_result=HEALTH_PASS,
        )
        changed = dict(profile, column_count=3, fields=[*profile["fields"], {"source_field": "客户", "canonical_field": "customer_name"}])
        resolved = memory.resolve(
            source_file="room-20260712.xlsx",
            source_sheet="RoomCurrent",
            domain="Room",
            profile=changed,
            workbook_sheets=["RoomCurrent", "NewSheet"],
            quality_result=HEALTH_WARNING,
        )
        self.assertEqual(resolved["status"], SheetSemanticMemory.STATUS_REVIEW)
        self.assertEqual(
            set(resolved["reasons"]),
            {"sheet_added", "fields_changed", "structure_changed", "data_quality_declined"},
        )


if __name__ == "__main__":
    unittest.main()
