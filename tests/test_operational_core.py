import os
import tempfile
import unittest
from pathlib import Path

from oms_v1.data_parser import OMSDataParser
from oms_v1.decision_engine import DecisionEngine
from oms_v1.event_engine import EventEngine
from oms_v1.execution_engine import ExecutionEngine
from oms_v1.governance_engine import GovernanceEngine
from oms_v1.input_hub import OMSInputHub
from oms_v1.live_connector import LiveConnector
from oms_v1.operating_center_source import OPERATING_CENTER_VERSION
from oms_v1.operational_core import OMSOperationalCore, OPERATING_CENTER_PEOPLE


class OperationalCoreTests(unittest.TestCase):
    def setUp(self):
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()
        self.events = EventEngine()
        self.decisions = DecisionEngine()
        self.execution = ExecutionEngine()
        self.governance = GovernanceEngine()
        self.tmp = tempfile.TemporaryDirectory()
        self.live = LiveConnector(Path(self.tmp.name) / "live")
        self.operational = OMSOperationalCore(Path(self.tmp.name) / "operational")

    def tearDown(self):
        self.tmp.cleanup()

    def _operating_stream(self, text, user_id=None):
        env = self.hub.accept_text(text)
        parsed = self.parser.parse(env)
        event_stream = self.events.build_event_stream(parsed)
        decision_stream = self.decisions.build_decision_stream(event_stream)
        execution_stream = self.execution.build_execution_stream(decision_stream)
        governance_stream = self.governance.build_governance_stream(execution_stream)
        live_stream = self.live.build_live_stream(execution_stream, governance_stream)
        return self.operational.build_operating_stream(execution_stream, governance_stream, live_stream, user_id=user_id)

    def test_operating_mode_default_entry_policy(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")

        self.assertEqual(stream["operating_mode"], "daily_operating_mode")
        self.assertEqual(stream["workspace_mode"], "personal_workspace_system")
        self.assertEqual(stream["default_entry_policy"]["default_entry"], "personal_workspace")
        self.assertEqual(stream["default_entry_policy"]["excel_role"], "只读历史和迁移来源")
        self.assertEqual(stream["default_entry_policy"]["wechat_role"], "输入来源和人工确认回写来源")

    def test_default_workspace_uses_user_id_instead_of_global_center(self):
        stream = self._operating_stream("备注：安排8月1日入住，需要六月排房，娜娜跟进入住准备。", user_id="june")
        default_workspace = stream["default_workspace"]

        self.assertEqual(stream["personal_workspace_system"]["current_user"]["role"], "店总 + 销售")
        self.assertEqual(default_workspace["title"], "店总工作台")
        self.assertEqual(default_workspace["home"], "我的任务流")
        self.assertTrue(all(item["role"] == "六月" for item in default_workspace["all_visible_items"]))
        self.assertGreater(default_workspace["counts"]["visible_items"], 0)

    def test_personal_workspaces_include_my_todos_approvals_and_tasks(self):
        stream = self._operating_stream("刘姐收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001", user_id="liujie")
        workspaces = stream["personal_workspace_system"]["workspaces"]
        liujie = stream["default_workspace"]

        self.assertEqual(liujie["title"], "财务工作台")
        self.assertIn("my_todos", liujie)
        self.assertIn("my_approvals", liujie)
        self.assertIn("my_tasks", liujie)
        self.assertGreaterEqual(liujie["counts"]["approvals"], 1)
        self.assertEqual(workspaces["boss"]["role"], "总览 | 决策 | 授权")
        self.assertGreaterEqual(workspaces["boss"]["counts"]["visible_items"], liujie["counts"]["visible_items"])

    def test_runtime_alias_cannot_open_other_workspaces(self):
        sales = self._operating_stream("销售欢欢签约客户张三，合同 HJ-2026-0703，定金 10000 元。", user_id="huanhuan")
        blocked_alias = self._operating_stream("销售欢欢签约客户张三，合同 HJ-2026-0703，定金 10000 元。", user_id="欢欢")
        nana = self._operating_stream("备注：8月1日入住，需要娜娜安排产护和厨房月子餐。", user_id="nana")

        self.assertEqual(sales["default_workspace"]["title"], "销售工作台")
        self.assertEqual(sales["personal_workspace_system"]["current_user"]["name"], "欢欢")
        self.assertEqual(blocked_alias["personal_workspace_system"]["current_user"]["workspace_key"], "__unresolved__")
        self.assertEqual(blocked_alias["personal_workspace_system"]["current_user"]["name"], "未绑定用户")
        self.assertEqual(nana["default_workspace"]["title"], "管家工作台")
        self.assertEqual(nana["personal_workspace_system"]["current_user"]["role"], "管家")

    def test_operating_center_people_is_single_source_for_eleven_workspaces(self):
        stream = self._operating_stream("备注：8月1日入住，需要六月排房，娜娜跟进入住准备。", user_id="boss")
        workspace_system = stream["personal_workspace_system"]

        self.assertEqual(len(OPERATING_CENTER_PEOPLE), 11)
        self.assertEqual(workspace_system["source_of_truth"], OPERATING_CENTER_VERSION)
        self.assertEqual(workspace_system["workspace_policy"], "one_user_one_workspace")
        self.assertEqual(set(workspace_system["workspaces"]), set(OPERATING_CENTER_PEOPLE))
        self.assertEqual(stream["audit"]["people_model_count"], 11)
        self.assertEqual(stream["audit"]["people_model_source"], OPERATING_CENTER_VERSION)

    def test_people_model_binds_user_role_and_workspace_from_v11(self):
        expected = {
            "boss": ("主理办（你）", "总览 | 决策 | 授权", "主理办工作台"),
            "huanhuan": ("欢欢", "销售", "销售工作台"),
            "june": ("六月", "店总 + 销售", "店总工作台"),
            "liujie": ("刘姐", "出纳", "财务工作台"),
            "zhangjie": ("张姐", "财务总监/会计", "财务总监工作台"),
            "nana": ("娜娜", "管家", "管家工作台"),
            "chenchangyi": ("陈昌辉", "产护部总监", "产护工作台"),
            "zhouchen": ("周厨", "厨师长", "料理工作台"),
            "yaowei": ("维维", "行政采购 + 照护师工资决算", "行政采购工作台"),
            "songxue": ("宗惠", "人事行政", "人事行政工作台"),
            "yuchun": ("子渝", "食材采购 + 销售", "食材采购 + 销售工作台"),
        }

        self.assertEqual(set(OPERATING_CENTER_PEOPLE), set(expected))
        for key, (name, role, title) in expected.items():
            person = OPERATING_CENTER_PEOPLE[key]
            self.assertEqual((person["name"], person["role"], person["title"]), (name, role, title))

    def test_feishu_user_id_routes_to_unique_workspace(self):
        os.environ["FEISHU_USER_ID_ZHOUCHEN"] = "ou_real_zhouchen"
        try:
            stream = self._operating_stream("备注：厨房需要准备特殊餐。", user_id="ou_real_zhouchen")
        finally:
            os.environ.pop("FEISHU_USER_ID_ZHOUCHEN", None)

        current_user = stream["personal_workspace_system"]["current_user"]
        self.assertEqual(current_user["workspace_key"], "zhouchen")
        self.assertEqual(current_user["identity_source"], "feishu_user_id")
        self.assertEqual(stream["default_workspace"]["title"], "料理工作台")

    def test_operating_center_structure_has_three_complete_layers(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")
        structure = stream["operating_center_structure"]

        self.assertEqual(set(structure), {"business_layer", "support_layer", "system_capability_layer"})
        self.assertEqual([unit["unit"] for unit in structure["business_layer"]["units"]], ["销售", "店长", "财务", "服务", "BOSS总览"])
        self.assertEqual([unit["owner"] for unit in structure["business_layer"]["units"]], ["欢欢", "六月", "刘姐", "娜娜", "BOSS"])
        self.assertEqual([unit["unit"] for unit in structure["support_layer"]["units"]], ["行政采购", "产护支持", "餐饮/厨房", "后勤保障"])
        self.assertEqual(
            [unit["unit"] for unit in structure["system_capability_layer"]["units"]],
            ["数据分析中心", "风险预警", "排房优化", "成本控制", "经营指标中心"],
        )
        for layer in structure.values():
            for unit in layer["units"]:
                self.assertEqual(set(unit["classification"]), {"人", "流程", "系统能力"})
                self.assertTrue(all(unit["classification"].values()))

    def test_structure_views_summarize_layers_without_splitting_main_flow(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")
        views = stream["structure_views"]

        self.assertEqual(stream["audit"]["structure_layer_count"], 3)
        self.assertEqual(views["business_layer"]["layer_name"], "业务层")
        self.assertIn("行政采购", views["support_layer"]["units"])
        self.assertIn("经营指标中心", views["system_capability_layer"]["units"])
        self.assertGreater(views["business_layer"]["work_item_count"], 0)

    def test_support_layer_generates_real_work_items_from_service_flow(self):
        stream = self._operating_stream("备注：8月1日入住，需要产护护理、厨房月子餐、房间清理和设备检查。")
        support_items = stream["support_layer_work_items"]
        support_roles = {item["role"] for item in support_items}

        self.assertIn("产护支持", support_roles)
        self.assertIn("餐饮/厨房", support_roles)
        self.assertIn("后勤保障", support_roles)
        self.assertTrue(stream["support_layer_status"]["active"])
        self.assertGreaterEqual(stream["support_layer_status"]["trigger_event_count"], 3)
        self.assertGreaterEqual(stream["structure_views"]["support_layer"]["work_item_count"], 3)
        self.assertTrue(stream["support_layer_status"]["pending_outbox_enabled"])

    def test_support_layer_generates_admin_procurement_from_purchase_flow(self):
        stream = self._operating_stream("维维报销厨房采购鸡蛋 360 元，美团，6.29 单据已发，需要消耗品补充。")
        support_roles = {item["role"] for item in stream["support_layer_work_items"]}
        pending_targets = [
            target
            for event in stream["support_layer_trigger_events"]
            for target in event["pending_targets"]
        ]

        self.assertIn("行政采购", support_roles)
        self.assertIn("餐饮/厨房", support_roles)
        self.assertTrue(any(target.startswith("支撑层_") for target in pending_targets))

    def test_room_and_service_work_items_are_routed_to_roles(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")
        roles = {item["role"] for item in stream["work_items"]}

        self.assertIn("六月", roles)
        self.assertIn("娜娜", roles)
        self.assertIn("BOSS", roles)
        self.assertIn("六月", stream["role_views"])

    def test_finance_confirmation_waits_for_liujie(self):
        stream = self._operating_stream("刘姐收到客户定金 10000 元，7月2日到账，合同 HJ-2026-001")
        finance_items = [item for item in stream["work_items"] if item["role"] == "刘姐"]

        self.assertTrue(finance_items)
        self.assertTrue(any(item["confirmation_required"] for item in finance_items))
        self.assertTrue(any(item["status"] == "waiting_confirmation" for item in finance_items))

    def test_legacy_system_policy_is_downgraded(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")

        for item in stream["work_items"]:
            self.assertEqual(item["legacy_policy"]["Excel"], "read_only_history")
            self.assertEqual(item["legacy_policy"]["微信"], "input_source_only")
            self.assertEqual(item["primary_entry"], "OMS")

    def test_management_cutover_is_explicit_not_faked(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")
        criteria = stream["operational_readiness"]["completion_criteria"]

        self.assertEqual(criteria["六月不再用Excel排房"], "requires_management_cutover")
        self.assertEqual(criteria["销售不再群里报数据"], "requires_management_cutover")

    def test_operational_work_items_are_persisted(self):
        stream = self._operating_stream("备注：安排8月1日入住，管家跟进服务。")
        path = Path(stream["audit"]["operating_root"]) / "daily_work_items.jsonl"

        self.assertTrue(path.exists())
        self.assertIn("primary_entry", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
