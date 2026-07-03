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

    def tearDown(self):
        self.tmp.cleanup()

    def _operating_stream(self, text, user_id="june"):
        envelope = self.hub.accept_text(text)
        parsed = self.parser.parse(envelope)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        execution_stream = self.execution.build_execution_stream(decision_stream)
        governance_stream = self.governance.build_governance_stream(execution_stream)
        live_stream = self.live.build_live_stream(execution_stream, governance_stream)
        return self.operational.build_operating_stream(execution_stream, governance_stream, live_stream, user_id=user_id)

    def test_home_is_user_workspace_not_operating_center(self):
        stream = self._operating_stream("备注：8月1日入住，需要六月排房，娜娜跟进入住准备。", user_id="june")
        home = OMSHomeUI(self.live_root, self.operating_root).build_home(stream)

        self.assertEqual(home["entry"], "personal_workspace")
        self.assertEqual(home["home_type"], "user_centric_operating_interface")
        self.assertEqual(home["current_user"]["role"], "店总 + 销售")
        self.assertEqual(home["home_title"], "店总工作台")
        self.assertEqual(set(home["sections"]), {"my_todos", "my_tasks", "my_approvals", "role_home"})
        self.assertEqual(home["sections"]["role_home"]["title"], "我的经营事务")
        self.assertNotIn("operating_center_structure", home)
        self.assertNotIn("structure_views", home)
        self.assertNotIn("audit", home)
        self.assertNotIn("work_items", home)

    def test_home_sections_use_role_specific_labels(self):
        finance_stream = self._operating_stream("刘姐收到客户定金 10000 元，7月3日到账，合同 HJ-2026-001", user_id="liujie")
        finance_home = OMSHomeUI(self.live_root, self.operating_root).build_home(finance_stream)
        sales_stream = self._operating_stream("销售欢欢签约客户张三，合同 HJ-2026-0703，定金 10000 元。", user_id="huanhuan")
        sales_home = OMSHomeUI(self.live_root, self.operating_root).build_home(sales_stream)
        service_stream = self._operating_stream("备注：8月1日入住，需要娜娜安排产护和入住服务。", user_id="nana")
        service_home = OMSHomeUI(self.live_root, self.operating_root).build_home(service_stream)
        kitchen_stream = self._operating_stream("备注：厨房需要准备特殊餐。", user_id="zhouchen")
        kitchen_home = OMSHomeUI(self.live_root, self.operating_root).build_home(kitchen_stream)

        self.assertEqual(finance_home["sections"]["role_home"]["title"], "我的财务")
        self.assertEqual(sales_home["sections"]["role_home"]["title"], "我的客户")
        self.assertEqual(service_home["sections"]["role_home"]["title"], "我的服务")
        self.assertEqual(kitchen_home["sections"]["role_home"]["title"], "我的料理")
        self.assertGreaterEqual(finance_home["sections"]["my_approvals"]["count"], 1)

    def test_saved_state_home_opens_without_new_business_input(self):
        self._operating_stream("备注：8月1日入住，需要六月排房，娜娜跟进入住准备。", user_id="june")
        home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="boss")

        self.assertEqual(home["entry"], "personal_workspace")
        self.assertEqual(home["current_user"]["role"], "总览 | 决策 | 授权")
        self.assertEqual(home["sections"]["role_home"]["title"], "经营总览")
        self.assertGreater(home["sections"]["my_todos"]["count"], 0)
        self.assertIn("sync_status", home)

    def test_cli_home_outputs_personal_workspace(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "home",
                    "--text",
                    "备注：8月1日入住，需要六月排房，娜娜跟进入住准备。",
                    "--user-id",
                    "june",
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

    def test_saved_state_home_binds_excel_and_finance_runtime_data(self):
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
                                "raw_row": {"入住时间": "7.4", "出馆时间": "7.4"},
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
                            "excel_record": {"source_type": "contracts", "raw_row": {}, "assignment": {"workspace_key": "huanhuan"}},
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
                            "excel_record": {"source_type": "room_status", "raw_row": {}, "assignment": {"workspace_key": "june"}},
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
                    "finance_record": {"source_type": "finance_daily"},
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        finance_root = self.live_root / "finance"
        finance_root.mkdir(parents=True, exist_ok=True)
        (finance_root / "financial_events.jsonl").write_text(
            json.dumps({"occurred_at": "7.4", "income_amount": "158600"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        boss_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="boss")
        june_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="june")
        sales_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="huanhuan")
        nana_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="nana")
        finance_home = OMSHomeUI(self.live_root, self.operating_root).build_home_from_saved_state(user_id="liujie")

        self.assertEqual(boss_home["business_dashboard"]["metrics"]["resident_count"], 1)
        self.assertEqual(boss_home["business_dashboard"]["metrics"]["sales_contracts"], 1)
        self.assertEqual(boss_home["business_dashboard"]["metrics"]["room_status_records"], 1)
        self.assertEqual(boss_home["business_dashboard"]["metrics"]["today_collection"], 158600)
        self.assertEqual(june_home["sections"]["role_home"]["count"], 1)
        self.assertEqual(june_home["business_dashboard"]["role_focus"]["房态"], 1)
        self.assertEqual(sales_home["sections"]["role_home"]["count"], 1)
        self.assertEqual(sales_home["business_dashboard"]["role_focus"]["签约"], 1)
        self.assertEqual(nana_home["sections"]["role_home"]["count"], 1)
        self.assertEqual(nana_home["business_dashboard"]["role_focus"]["服务"], 1)
        self.assertEqual(finance_home["sections"]["role_home"]["count"], 1)
        self.assertEqual(finance_home["business_dashboard"]["role_focus"]["财务"], 1)


if __name__ == "__main__":
    unittest.main()
