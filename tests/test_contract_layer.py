import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "oms_app"


class ContractLayerTests(unittest.TestCase):
    def contract(self):
        return json.loads((APP_ROOT / "contract.json").read_text(encoding="utf-8"))

    def test_contract_file_defines_single_truth_layer(self):
        contract = self.contract()

        self.assertEqual(contract["schema_version"], "oms.contract.v1.0")
        self.assertEqual(contract["source"], "OMS_TRUTH_SOURCE")
        self.assertEqual(contract["system_goal"], "OMS = Contract-driven System")
        self.assertTrue(contract["rules"]["api_must_return_contract_envelope"])
        self.assertTrue(contract["rules"]["ui_must_read_payload_not_raw_response"])
        self.assertTrue(contract["rules"]["ui_without_behavior_is_forbidden"])
        self.assertFalse(contract["rules"]["excel_as_runtime_source_allowed"])
        self.assertFalse(contract["rules"]["ui_calculated_truth_allowed"])
        self.assertFalse(contract["rules"]["multiple_data_sources_allowed"])

    def test_data_contract_requires_standard_envelope(self):
        envelope = self.contract()["data_contract"]["response_envelope"]

        self.assertEqual(
            envelope["required_fields"],
            ["entity", "id", "status", "payload", "timestamp", "source"],
        )
        self.assertEqual(envelope["entity_enum"], ["room", "finance", "sales", "task"])
        self.assertEqual(envelope["source_required_value"], "OMS_TRUTH_SOURCE")
        for status in ["ready", "pending", "blocked", "identity_binding_required", "invalid_json"]:
            self.assertIn(status, envelope["status_enum"])

    def test_api_field_spec_covers_runtime_endpoints(self):
        specs = {item["api"]: item for item in self.contract()["data_contract"]["api_field_spec_table"]}

        for api in ["/api/oms/home", "/api/feishu/identity", "/api/oms/execute", "/api/oms/history"]:
            self.assertIn(api, specs)
            self.assertEqual(specs[api]["source"] if "source" in specs[api] else "OMS_TRUTH_SOURCE", "OMS_TRUTH_SOURCE")
            self.assertEqual(
                specs[api]["required_response_fields"],
                ["entity", "id", "status", "payload", "timestamp", "source"],
            )
        self.assertEqual(specs["/api/oms/home"]["id"], "oms.home")
        self.assertIn("payload.sections.my_todos", specs["/api/oms/home"]["ui_required_fields"])
        self.assertIn("payload.business_dashboard.lifecycle", specs["/api/oms/home"]["ui_required_fields"])
        self.assertEqual(specs["/api/feishu/identity"]["id"], "feishu.identity.exchange")
        self.assertIn("user_id or open_id or union_id", specs["/api/feishu/identity"]["required_payload_fields"])
        self.assertEqual(specs["/api/oms/execute"]["id"], "oms.execute")
        self.assertIn("closure_status", specs["/api/oms/execute"]["required_payload_fields"])
        self.assertIn("decision_chain", specs["/api/oms/execute"]["required_payload_fields"])
        self.assertIn("retrigger_closure", specs["/api/oms/execute"]["required_payload_fields"])
        self.assertIn("business_state_writeback", specs["/api/oms/execute"]["required_payload_fields"])
        self.assertIn("lifecycle_closure", specs["/api/oms/execute"]["required_payload_fields"])
        self.assertIn("payload.decision_chain.decision_summary", specs["/api/oms/execute"]["ui_required_fields"])
        self.assertIn("payload.retrigger_closure.status", specs["/api/oms/execute"]["ui_required_fields"])
        self.assertIn("payload.business_state_writeback.truth_source_updated", specs["/api/oms/execute"]["ui_required_fields"])
        self.assertIn("payload.lifecycle_closure.current_stage", specs["/api/oms/execute"]["ui_required_fields"])
        self.assertIn("payload.lifecycle_closure.closure_detection.status", specs["/api/oms/execute"]["ui_required_fields"])
        self.assertIn("payload.trace_chain.execution_result_id", specs["/api/oms/execute"]["ui_required_fields"])
        self.assertEqual(specs["/api/oms/history"]["id"], "oms.history")
        self.assertIn("payload.traceability", specs["/api/oms/history"]["ui_required_fields"])

    def test_action_contract_maps_clicks_to_routes_state_and_api(self):
        mappings = self.contract()["action_contract"]["ui_behavior_mapping_table"]

        self.assertGreaterEqual(len(mappings), 10)
        for mapping in mappings:
            self.assertIn("ui_trigger", mapping)
            self.assertIn("route", mapping)
            self.assertIn("state_update", mapping)
            self.assertIn("api", mapping)
            self.assertIn("result", mapping)
        route_by_trigger = {item["ui_trigger"]: item["route"] for item in mappings}
        api_by_trigger = {item["ui_trigger"]: item["api"] for item in mappings}
        self.assertEqual(route_by_trigger["[data-work-action='open-action']"], "action")
        self.assertEqual(route_by_trigger["[data-work-action='open-room']"], "room")
        self.assertEqual(route_by_trigger["[data-work-action='trace-finance']"], "finance")
        self.assertEqual(route_by_trigger["[data-work-action contains '重新']"], "current_route")
        self.assertEqual(route_by_trigger["[data-nav-route='data']"], "data")
        for trigger in [
            "[data-work-action='open-action']",
            "[data-work-action='open-room']",
            "[data-work-action='trace-finance']",
            "[data-work-action='execute-task']",
            "[data-work-action contains '重新']",
        ]:
            self.assertEqual(api_by_trigger[trigger], "/api/oms/execute")

    def test_ui_render_contract_forces_contract_json_as_single_render_source(self):
        render_contract = self.contract()["ui_render_contract"]

        self.assertEqual(render_contract["render_source"], "contract.json")
        self.assertEqual(render_contract["render_pipeline"], "contract.json -> UI render engine -> DOM")
        self.assertFalse(render_contract["fallback_render_allowed"])
        self.assertFalse(render_contract["legacy_renderer_allowed"])
        self.assertFalse(render_contract["direct_api_field_mapping_allowed"])
        self.assertFalse(render_contract["mixed_rendering_allowed"])
        self.assertEqual(render_contract["required_home_sections"], ["Action", "Status", "Risk"])
        for section in ["Action", "Status", "Risk"]:
            self.assertIn(section, render_contract["home_sections"])
            self.assertIn("component_tree_key", render_contract["home_sections"][section])
            self.assertIn("payload_paths", render_contract["home_sections"][section])
            self.assertIn("route", render_contract["home_sections"][section])
        self.assertTrue(render_contract["validation"]["contract_render_validation_required"])
        self.assertTrue(render_contract["validation"]["ui_vs_contract_diff_check"])
        self.assertTrue(render_contract["validation"]["missing_required_payload_path_blocks_render"])
        self.assertGreaterEqual(len(render_contract["navigation_tree"]), 5)
        self.assertGreaterEqual(len(render_contract["payload_mapping"]), 3)

    def test_e2e_ui_chain_contract_requires_data_behavior_display_closure(self):
        chain = self.contract()["e2e_ui_chain_contract"]

        self.assertEqual(chain["chain_name"], "data -> behavior -> display")
        self.assertEqual(
            chain["required_steps"],
            [
                "contract_loaded",
                "api_payload_mapped",
                "component_tree_built",
                "dom_rendered",
                "interaction_bound",
                "api_refresh_bridge_bound",
            ],
        )
        for target in ["#todayWorkData", "#scoreboardCards", "#priorityCards", "#businessMenu"]:
            self.assertIn(target, chain["required_dom_targets"])
        for selector in ["[data-work-action]", "[data-nav-route]"]:
            self.assertIn(selector, chain["required_interaction_selectors"])
        self.assertEqual(chain["runtime_debug_state"], "window.OMS_UI_CHAIN_STATE")
        self.assertEqual(chain["dom_debug_flag"], "data-oms-ui-chain")
        self.assertTrue(chain["display_validation"]["empty_dom_blocks_chain"])
        self.assertTrue(chain["display_validation"]["click_without_state_update_blocks_chain"])
        self.assertTrue(chain["display_validation"]["api_refresh_without_render_update_blocks_chain"])

    def test_final_render_contract_requires_single_transactional_sink(self):
        final_render = self.contract()["final_render_contract"]

        self.assertEqual(final_render["sink_name"], "FINAL_RENDER_SINK")
        self.assertEqual(final_render["single_entry_function"], "render(source)")
        self.assertEqual(final_render["render_flow"], "data -> diff -> commit -> render -> commit DOM")
        self.assertTrue(final_render["snapshot_versioning_required"])
        self.assertTrue(final_render["dom_diff_lock_required"])
        self.assertTrue(final_render["render_queue_required"])
        self.assertEqual(final_render["queue_policy"], "latest_snapshot_wins")
        self.assertFalse(final_render["partial_render_allowed"])
        self.assertFalse(final_render["direct_component_dom_write_allowed"])
        self.assertFalse(final_render["async_race_render_allowed"])
        self.assertFalse(final_render["state_dom_mismatch_allowed"])
        self.assertEqual(
            final_render["required_snapshot_fields"],
            ["version", "source", "mode", "componentTree", "dom", "hash"],
        )
        for target in ["#homeTitle", "#scoreboardCards", "#sideBusinessMenu", "#todayWorkData"]:
            self.assertIn(target, final_render["required_dom_commit_targets"])
        self.assertEqual(final_render["runtime_debug_state"], "window.OMS_FINAL_RENDER_STATE")
        self.assertEqual(final_render["dom_debug_flag"], "data-oms-final-render")

    def test_semantic_contract_locks_business_terms(self):
        terms = self.contract()["semantic_contract"]["terms"]

        for term in ["在住", "任务", "财务", "排房", "报销"]:
            self.assertIn(term, terms)
            self.assertIn(terms[term]["entity"], ["room", "finance", "sales", "task"])
            self.assertIn("definition", terms[term])
            self.assertIn("source", terms[term])
            self.assertIn("ui_meaning", terms[term])
            self.assertIn("forbidden_meaning", terms[term])
        self.assertEqual(terms["在住"]["entity"], "room")
        self.assertEqual(terms["任务"]["entity"], "task")
        self.assertEqual(terms["财务"]["entity"], "finance")
        self.assertEqual(terms["排房"]["entity"], "room")

    def test_backend_and_frontend_reference_contract_v1(self):
        server = (ROOT / "oms_v1" / "feishu_auth_server.py").read_text(encoding="utf-8")
        config = (APP_ROOT / "oms-config.js").read_text(encoding="utf-8")
        script = (APP_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn('CONTRACT_VERSION = "oms.contract.v1.0"', server)
        self.assertIn("def _send_contract", server)
        for field in ['"entity": entity', '"id": response_id', '"status": contract_status', '"payload": payload', '"timestamp": now_iso()', '"source": "OMS_TRUTH_SOURCE"']:
            self.assertIn(field, server)
        self.assertIn('window.OMS_CONTRACT_VERSION = "oms.contract.v1.0"', config)
        self.assertIn("window.OMS_CONTRACT_URL", config)
        self.assertIn("unwrapContractPayload", script)
        self.assertIn("contract_status_", script)
        self.assertIn("ensureContractLayerLoaded", script)
        self.assertIn("validateContractLayer", script)
        self.assertIn("mapPayloadThroughContract", script)
        self.assertIn("requireContractMappedRuntimeHome", script)
        self.assertIn("applyContractRenderMetadata", script)
        self.assertIn("validateUiVsContractPayload", script)
        self.assertIn("target.dataset.renderSource = \"contract.json\"", script)
        self.assertIn("validateEndToEndUiChain", script)
        self.assertIn("window.OMS_UI_CHAIN_STATE", script)
        self.assertIn("document.documentElement.dataset.omsUiChain", script)
        self.assertIn("const FINAL_RENDER_SINK", script)
        self.assertIn("enqueueFinalRender", script)
        self.assertIn("commitFinalRenderQueue", script)
        self.assertIn("buildFinalRenderSnapshot", script)
        self.assertIn("diffFinalRenderSnapshot", script)
        self.assertIn("commitFinalRenderSnapshot", script)
        self.assertIn("window.OMS_FINAL_RENDER_STATE", script)


if __name__ == "__main__":
    unittest.main()
