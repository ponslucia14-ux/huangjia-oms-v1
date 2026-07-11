import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from oms_v1.cli import main
from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_engine import EventEngine
from oms_v1.execution_engine import ExecutionEngine
from oms_v1.governance_engine import GovernanceEngine
from oms_v1.home_ui import OMSHomeUI
from oms_v1.input_hub import OMSInputHub
from oms_v1.live_connector import LiveConnector
from oms_v1.operational_core import OMSOperationalCore
from oms_v1.schemas import now_iso
from oms_v1.truth_source import TruthSourceStore


class HomeUITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.live_root = self.root / "live"
        self.operating_root = self.root / "operational"
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.events = EventEngine()
        self.decisions = DecisionEngine()
        self.execution = ExecutionEngine()
        self.governance = GovernanceEngine()
        self.live = LiveConnector(self.live_root)
        self.operational = OMSOperationalCore(self.operating_root)
        self._realworld_mapping(
            [
                {"name": "石磊", "role": "boss", "user_id": "a2c82cb4"},
                {"name": "杨欢欢", "role": "销售", "user_id": "e83f88ga"},
                {"name": "刘芳羽", "role": "店总 + 销售", "user_id": "39g7c1f2"},
                {"name": "刘晶", "role": "财务", "user_id": "8eag4627"},
                {"name": "尚丽娜", "role": "管家", "user_id": "9dcg7e27"},
                {"name": "周志朋", "role": "厨师长", "user_id": "7e6595fg"},
            ]
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _evidence(self, source_type, source_file, row_number, record_id, truth_source="Excel"):
        return {
            "truth_source": truth_source,
            "source_type": source_type,
            "source_file": str(self.root / source_file),
            "source_sheet": "",
            "row_number": row_number,
            "record_id": record_id,
            "trace_id": f"{source_type}:{source_file}::{row_number}:{record_id}",
        }

    def _today_short(self):
        date = now_iso().split("T", 1)[0]
        _, month, day = date.split("-")
        return f"{int(month)}.{int(day)}"

    def _write_room_stay_truth(self, *, stays=None, rooms=None):
        store = TruthSourceStore(self.live_root, self.operating_root)
        store.write_domain(
            "stay",
            {
                "stay_records": stays
                if stays is not None
                else [
                    {
                        "stay_id": "stay_verified",
                        "record_id": "excel_resident",
                        "guest_name": "入住客户",
                        "room_id": "201",
                        "checkin_date": self._today_short(),
                        "checkout_date": "2026-07-28",
                        "status": "IN_STAY",
                        "source_evidence": self._evidence("resident", "resident.csv", 2, "excel_resident"),
                    }
                ],
            },
        )
        store.write_domain(
            "room",
            {
                "room_records": rooms
                if rooms is not None
                else [
                    {
                        "record_id": "excel_room",
                        "room_id": "201",
                        "room_name": "201南双卫",
                        "status": "OCCUPIED",
                        "occupancy_markers": [{"kind": "name", "value": "入住客户"}],
                        "source_evidence": self._evidence("room_status", "room.csv", 3, "excel_room"),
                    }
                ],
            },
        )

    def _realworld_mapping(self, rows):
        for base in [self.live_root, self.operating_root.parent]:
            path = base / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
        return path

    def _write_operations_truth_source(self, *, stay_count=1, include_caregiver=True):
        store = TruthSourceStore(self.live_root, self.operating_root)
        room_domain = store.read_domain("room")
        source_file = str(self.root / "operations.csv")
        room_domain["stay_records"] = [
            {
                "stay_id": f"stay_{index}",
                "customer_name": f"Customer {index}",
                "room_id": f"20{index}",
                "caregiver_id": f"cg_{index}",
                "status": "IN_STAY",
                "checkin_date": self._today_short(),
                "checkout_date": self._today_short(),
                "source_evidence": self._evidence("stay", source_file, index + 2, f"stay_row_{index}", truth_source="OMS_TRUTH_SOURCE"),
            }
            for index in range(1, stay_count + 1)
        ]
        room_domain["room_records"] = [
            {
                "room_id": f"20{index}",
                "room_name": f"20{index}",
                "floor": "2",
                "status": "OCCUPIED",
                "current_stay_id": f"stay_{index}",
                "source_evidence": self._evidence("room_status", source_file, index + 20, f"room_row_{index}", truth_source="OMS_TRUTH_SOURCE"),
            }
            for index in range(1, stay_count + 1)
        ]
        room_domain["caregiver_records"] = (
            [
                {
                    "caregiver_id": "cg_1",
                    "caregiver_name": "Caregiver 1",
                    "status": "ASSIGNED",
                    "current_stay_id": "stay_1",
                    "source_evidence": self._evidence("caregiver", source_file, 40, "caregiver_row_1", truth_source="OMS_TRUTH_SOURCE"),
                }
            ]
            if include_caregiver
            else []
        )
        store.write_domain("room", room_domain)

    def _operating_stream(self, text, user_id="39g7c1f2"):
        envelope = self.hub.accept_text(text)
        parsed = self.parser.parse(envelope)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        execution_stream = self.execution.build_execution_stream(decision_stream)
        governance_stream = self.governance.build_governance_stream(execution_stream)
        live_stream = self.live.build_live_stream(execution_stream, governance_stream)
        return self.operational.build_operating_stream(execution_stream, governance_stream, live_stream, user_id=user_id)

    def test_home_is_user_workspace_not_operating_center(self):
        stream = self._operating_stream("备注：8月1日入住，需要刘芳羽排房，尚丽娜跟进入住准备。", user_id="39g7c1f2")
        home = OMSHomeUI(self.live_root, self.operating_root).build_home(stream)

        self.assertEqual(home["entry"], "personal_workspace")
        self.assertEqual(home["home_type"], "user_centric_operating_interface")
        self.assertEqual(home["current_user"]["role"], "店总 + 销售")
        self.assertEqual(home["home_title"], "店总工作台")
        self.assertEqual(set(home["sections"]), {"my_todos", "my_tasks", "my_approvals", "role_home", "event_execution_flow"})
        self.assertEqual(home["sections"]["role_home"]["title"], "我的经营事务")
        self.assertNotIn("operating_center_structure", home)
        self.assertNotIn("structure_views", home)
        self.assertNotIn("audit", home)
        self.assertNotIn("work_items", home)

    def test_home_sections_use_role_specific_labels(self):
        finance_stream = self._operating_stream("刘晶收到客户定金 10000 元，7月3日到账，合同 HJ-2026-001", user_id="8eag4627")
        finance_home = OMSHomeUI(self.live_root, self.operating_root).build_home(finance_stream)
        sales_stream = self._operating_stream("销售杨欢欢签约客户张三，合同 HJ-2026-0703，定金 10000 元。", user_id="e83f88ga")
        sales_home = OMSHomeUI(self.live_root, self.operating_root).build_home(sales_stream)
        service_stream = self._operating_stream("备注：8月1日入住，需要尚丽娜安排产护和入住服务。", user_id="9dcg7e27")
        service_home = OMSHomeUI(self.live_root, self.operating_root).build_home(service_stream)
        kitchen_stream = self._operating_stream("备注：厨房需要准备特殊餐。", user_id="7e6595fg")
        kitchen_home = OMSHomeUI(self.live_root, self.operating_root).build_home(kitchen_stream)

        self.assertEqual(finance_home["sections"]["role_home"]["title"], "我的财务")
        self.assertEqual(sales_home["sections"]["role_home"]["title"], "我的客户")
        self.assertEqual(service_home["sections"]["role_home"]["title"], "我的服务")
        self.assertEqual(kitchen_home["sections"]["role_home"]["title"], "我的料理")
        self.assertGreaterEqual(finance_home["sections"]["my_approvals"]["count"], 1)

    def test_saved_state_home_opens_without_new_business_input(self):
        self._operating_stream("备注：8月1日入住，需要刘芳羽排房，尚丽娜跟进入住准备。", user_id="39g7c1f2")
        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="a2c82cb4")

        self.assertEqual(home["entry"], "master_control_dashboard")
        self.assertEqual(home["home_type"], "boss_master_control_interface")
        self.assertEqual(home["current_user"]["role"], "总览 | 决策 | 授权")
        self.assertEqual(home["sections"]["role_home"]["title"], "经营总览")
        self.assertGreater(home["sections"]["my_todos"]["count"], 0)
        self.assertIn("sync_status", home)
        self.assertEqual(home["master_control"]["entry_type"], "master_control_dashboard")
        self.assertTrue(home["master_control"]["permissions"]["view_all_user_workspaces"])
        self.assertEqual(home["master_control"]["hierarchy"]["layer_1"], "Owner Master Control")

    def test_cli_home_outputs_personal_workspace(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "home",
                    "--text",
                    "备注：8月1日入住，需要刘芳羽排房，尚丽娜跟进入住准备。",
                    "--user-id",
                    "39g7c1f2",
                    "--live-root",
                    str(self.live_root),
                    "--operating-root",
                    str(self.operating_root),
                    "--pretty",
                ]
            )
        payload = json.loads(output.getvalue())

        self.assertEqual(code, 0)
        self.assertEqual(payload["entry"], "personal_workspace")
        self.assertEqual(payload["current_user"]["role"], "店总 + 销售")
        self.assertIn("我的待办", [section["title"] for section in payload["sections"].values()])

    def test_unresolved_identity_requires_login_error(self):
        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="unknown-user")

        self.assertEqual(home["home_type"], "identity_binding_error")
        self.assertEqual(home["entry"], "login_required")
        self.assertIsNone(home["current_user"])
        self.assertEqual(home["error"]["error_type"], "identity_binding_required")
        self.assertEqual(home["sections"], {})

    def test_realworld_mapping_user_id_opens_personal_workspace(self):
        mapping_path = self.live_root / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        mapping_path.write_text(
            json.dumps({"rows": [{"name": "刘晶", "role": "财务", "user_id": "8eag4627", "open_id": "ou_liujie"}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="8eag4627")

        self.assertEqual(home["home_type"], "user_centric_operating_interface")
        self.assertEqual(home["current_user"]["workspace_key"], "liujie")

    def test_saved_state_home_binds_excel_and_finance_runtime_data(self):
        today_short = self._today_short()
        self.operating_root.mkdir(parents=True, exist_ok=True)
        (self.operating_root / "excel_work_items.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "work_item_id": "op_resident",
                            "role": "管家",
                            "workspace": "管家工作台",
                            "daily_process": "入住服务跟进",
                            "status": "attention_required",
                            "confirmation_required": True,
                            "excel_record": {
                                "source_type": "resident",
                                "source_evidence": self._evidence("resident", "resident.csv", 2, "excel_resident"),
                                "raw_row": {"入住时间": today_short, "出馆时间": today_short},
                                "assignment": {"workspace_key": "nana"},
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "work_item_id": "op_contract",
                            "role": "销售",
                            "workspace": "销售工作台",
                            "daily_process": "签约客户提报",
                            "status": "attention_required",
                            "confirmation_required": True,
                            "excel_record": {
                                "source_type": "contracts",
                                "source_evidence": self._evidence("contracts", "contracts.csv", 2, "excel_contract"),
                                "raw_row": {},
                                "assignment": {"workspace_key": "huanhuan"},
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "work_item_id": "op_room",
                            "role": "店总 + 销售",
                            "workspace": "店总工作台",
                            "daily_process": "房态排房处理",
                            "status": "attention_required",
                            "confirmation_required": True,
                            "excel_record": {
                                "source_type": "room_status",
                                "source_evidence": self._evidence("room_status", "room.csv", 2, "excel_room"),
                                "raw_row": {},
                                "assignment": {"workspace_key": "june"},
                            },
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (self.operating_root / "finance_work_items.jsonl").write_text(
            json.dumps(
                {
                    "work_item_id": "op_finance",
                    "role": "财务",
                    "workspace": "财务工作台",
                    "daily_process": "财务日报复核",
                    "status": "attention_required",
                    "confirmation_required": True,
                    "finance_record": {
                        "source_type": "finance_daily",
                        "source_evidence": self._evidence("finance_daily", "daily.csv", 2, "fin_daily", truth_source="Finance Excel"),
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        finance_root = self.live_root / "finance"
        finance_root.mkdir(parents=True, exist_ok=True)
        (finance_root / "financial_events.jsonl").write_text(
            json.dumps(
                {
                    "occurred_at": today_short,
                    "income_amount": "158600",
                    "source_evidence": self._evidence("finance_daily", "daily.csv", 2, "fin_daily", truth_source="Finance Excel"),
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        TruthSourceStore(self.live_root, self.operating_root).migrate_from_runtime()
        self._write_operations_truth_source(stay_count=1)

        boss_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="a2c82cb4")
        june_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="39g7c1f2")
        sales_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="e83f88ga")
        nana_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="9dcg7e27")
        finance_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="8eag4627")

        self.assertEqual(boss_home["business_dashboard"]["metrics"]["resident_count"], 1)
        self.assertEqual(boss_home["entry"], "master_control_dashboard")
        self.assertEqual(boss_home["master_control"]["global_view"]["task_count"], boss_home["sections"]["role_home"]["count"])
        self.assertIn("business_workspaces", boss_home["master_control"])
        self.assertIn("execution_layer", boss_home["master_control"])
        self.assertEqual(boss_home["business_dashboard"]["metrics"]["sales_contracts"], 1)
        self.assertEqual(boss_home["business_dashboard"]["metrics"]["room_status_records"], 1)
        self.assertEqual(boss_home["business_dashboard"]["metrics"]["today_collection"], 158600)
        schema = boss_home["business_dashboard"]["business_schema"]
        self.assertEqual(boss_home["business_dashboard"]["schema_source"], "business_schema")
        self.assertEqual(boss_home["business_dashboard"]["source"], "real_business_source_of_truth")
        self.assertEqual(boss_home["business_dashboard"]["data_truth_alignment"]["status"], "aligned")
        self.assertEqual(boss_home["business_dashboard"]["data_truth_alignment"]["data_source"], "source_evidence_available_data")
        self.assertEqual(boss_home["business_dashboard"]["data_truth_alignment"]["display_policy"], "always_render_with_confidence_label")
        self.assertEqual(boss_home["business_dashboard"]["data_truth_alignment"]["verified_work_items"], 4)
        self.assertEqual(boss_home["business_dashboard"]["data_truth_alignment"]["verified_financial_events"], 1)
        source_data = boss_home["business_dashboard"]["source_evidence_available_data"]
        self.assertEqual(source_data["policy"], "source_evidence_available_data")
        self.assertEqual(len(source_data["resident_data"]), 1)
        self.assertEqual(len(source_data["room_status_data"]), 1)
        self.assertEqual(len(source_data["sales_contract_data"]), 1)
        self.assertEqual(len(source_data["finance_data"]), 1)
        self.assertEqual(len(source_data["financial_events"]), 1)
        self.assertEqual(source_data["resident_data"][0]["source_evidence"]["record_id"], "stay_row_1")
        self.assertEqual(source_data["resident_data"][0]["data_confidence"], "source_verified")
        self.assertEqual(source_data["finance_data"][0]["source_evidence"]["truth_source"], "Finance Excel")
        self.assertGreaterEqual(source_data["counts"]["current_user_visible_data"], 1)
        self.assertEqual(nana_home["business_dashboard"]["production_adapters"]["caregiver_adapter"]["data_status"], "missing_structured_production_data")
        self.assertEqual(schema["schema_version"], "oms.business.v1")
        self.assertEqual(schema["resident_flow_schema"]["resident_count"], 1)
        self.assertEqual(schema["resident_flow_schema"]["upcoming_checkins"], 1)
        self.assertEqual(schema["finance_schema"]["collected"], 158600)
        self.assertEqual(schema["finance_schema"]["receivable"], 1)
        self.assertEqual(schema["sales_schema"]["contracts"], 1)
        self.assertEqual(schema["service_schema"]["in_service"], 0)
        self.assertIn("hr_schema", schema)
        self.assertEqual(june_home["sections"]["role_home"]["count"], 1)
        self.assertEqual(june_home["business_dashboard"]["role_focus"]["房态"], 1)
        self.assertEqual(sales_home["sections"]["role_home"]["count"], 1)
        self.assertEqual(sales_home["business_dashboard"]["role_focus"]["签约"], 1)
        self.assertGreaterEqual(nana_home["sections"]["role_home"]["count"], 0)
        self.assertEqual(nana_home["business_dashboard"]["role_focus"]["服务"], 0)
        self.assertEqual(finance_home["sections"]["role_home"]["count"], 1)
        self.assertEqual(finance_home["business_dashboard"]["role_focus"]["财务"], 1)


    def test_home_rejects_uncalibrated_runtime_data_for_operations_center(self):
        self.operating_root.mkdir(parents=True, exist_ok=True)
        verified = {
            "work_item_id": "verified_resident",
            "role": "nana",
            "workspace": "nana_workspace",
            "daily_process": "resident_followup",
            "status": "attention_required",
            "confirmation_required": True,
            "excel_record": {
                "source_type": "resident",
                "source_evidence": self._evidence("resident", "resident.csv", 2, "excel_verified"),
                "raw_row": {},
                "assignment": {"workspace_key": "nana"},
            },
        }
        uncalibrated = {
            "work_item_id": "uncalibrated_resident",
            "role": "nana",
            "workspace": "nana_workspace",
            "daily_process": "resident_followup",
            "status": "attention_required",
            "confirmation_required": True,
            "excel_record": {
                "source_type": "resident",
                "raw_row": {},
                "assignment": {"workspace_key": "nana"},
            },
        }
        (self.operating_root / "excel_work_items.jsonl").write_text(
            json.dumps(verified, ensure_ascii=False) + "\n" + json.dumps(uncalibrated, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        TruthSourceStore(self.live_root, self.operating_root).migrate_from_runtime()
        self._write_room_stay_truth(
            stays=[
                {
                    "stay_id": "verified_resident",
                    "record_id": "excel_verified",
                    "guest_name": "已校验客户",
                    "room_id": "201",
                    "checkin_date": self._today_short(),
                    "checkout_date": "2026-07-28",
                    "status": "IN_STAY",
                    "source_evidence": self._evidence("resident", "resident.csv", 2, "excel_verified"),
                },
                {
                    "stay_id": "uncalibrated_resident",
                    "record_id": "excel_unverified",
                    "guest_name": "待校验客户",
                    "room_id": "202",
                    "checkin_date": self._today_short(),
                    "checkout_date": "2026-07-29",
                    "status": "IN_STAY",
                },
            ],
            rooms=[],
        )

        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="a2c82cb4")

        self.assertEqual(home["business_dashboard"]["metrics"]["resident_count"], 0)
        self.assertEqual(home["business_dashboard"]["metrics"]["room_status_records"], 0)
        self.assertEqual(home["business_dashboard"]["data_truth_alignment"]["verified_work_items"], 0)
        self.assertEqual(home["business_dashboard"]["data_truth_alignment"]["uncalibrated_work_items"], 0)
        self.assertEqual(home["business_dashboard"]["data_truth_alignment"]["status"], "aligned")
        source_data = home["business_dashboard"]["source_evidence_available_data"]
        self.assertEqual(len(source_data["resident_data"]), 0)
        self.assertEqual(len(source_data["stay_data"]), 0)
        self.assertEqual(len(source_data["room_status_data"]), 0)
        self.assertEqual(len(source_data["caregiver_data"]), 0)


if __name__ == "__main__":
    unittest.main()
