from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .adoption_engine import AdoptionEngine
from .autonomous_runner import OMSAutonomousRunner
from .business_event_engine import BusinessEventEngine
from .core_data_model import CoreDataModelLayer
from .core_fusion import CoreFusionLayer
from .data_parser import OMSDataParser
from .decision_engine import DecisionEngine
from .event_engine import EventEngine
from .excel_importer import ExcelOMSImporter
from .execution_engine import ExecutionEngine
from .feishu_mapping import FeishuObjectSyncer
from .finance_importer import FinanceDataImporter
from .governance_engine import GovernanceEngine
from .historical_view import HistoricalDataViewLayer
from .home_ui import OMSHomeUI
from .human_execution_closure import HumanExecutionClosure
from .input_hub import OMSInputHub
from .live_connector import LiveConnector
from .operational_core import OMSOperationalCore
from .reality_lock import RealityLock
from .room_allocation_engine import RoomAllocationEngine
from .system_switch_controller import SystemSwitchController


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="oms_v1", description="Huangjia OMS V1 personal workspace")
    sub = parser.add_subparsers(dest="command")

    home_cmd = sub.add_parser("home", help="Open OMS personal workspace home")
    home_cmd.add_argument("--text", help="Raw WeChat message text")
    home_cmd.add_argument("--file", help="Input file path")
    home_cmd.add_argument("--operational-stream", help="Existing operational stream JSON file")
    home_cmd.add_argument("--live-root", help="Live connector runtime root")
    home_cmd.add_argument("--operating-root", help="Operational core runtime root")
    home_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    home_cmd.add_argument("--group", help="WeChat group name")
    home_cmd.add_argument("--sender", help="Sender name")
    home_cmd.add_argument("--received-at", help="ISO received time")
    home_cmd.add_argument("--user-id", help="Current OMS user id or role alias for personal workspace entry")
    home_cmd.add_argument("--out", help="Write OMS home JSON to file")
    home_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    parse_cmd = sub.add_parser("parse", help="Parse one text or file input to JSON")
    parse_cmd.add_argument("--text", help="Raw WeChat message text")
    parse_cmd.add_argument("--file", help="Input file path")
    parse_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    parse_cmd.add_argument("--group", help="WeChat group name")
    parse_cmd.add_argument("--sender", help="Sender name")
    parse_cmd.add_argument("--received-at", help="ISO received time")
    parse_cmd.add_argument("--out", help="Write JSON to file")
    parse_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    events_cmd = sub.add_parser("events", help="Parse one input and convert it to business events")
    events_cmd.add_argument("--text", help="Raw WeChat message text")
    events_cmd.add_argument("--file", help="Input file path")
    events_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    events_cmd.add_argument("--group", help="WeChat group name")
    events_cmd.add_argument("--sender", help="Sender name")
    events_cmd.add_argument("--received-at", help="ISO received time")
    events_cmd.add_argument("--out", help="Write event stream JSON to file")
    events_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    decisions_cmd = sub.add_parser("decisions", help="Convert input or event stream to recommendation decisions")
    decisions_cmd.add_argument("--text", help="Raw WeChat message text")
    decisions_cmd.add_argument("--file", help="Input file path")
    decisions_cmd.add_argument("--event-stream", help="Existing event stream JSON file")
    decisions_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    decisions_cmd.add_argument("--group", help="WeChat group name")
    decisions_cmd.add_argument("--sender", help="Sender name")
    decisions_cmd.add_argument("--received-at", help="ISO received time")
    decisions_cmd.add_argument("--out", help="Write decision stream JSON to file")
    decisions_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    execute_cmd = sub.add_parser("execute", help="Convert input, event stream, or decision stream to reversible execution actions")
    execute_cmd.add_argument("--text", help="Raw WeChat message text")
    execute_cmd.add_argument("--file", help="Input file path")
    execute_cmd.add_argument("--event-stream", help="Existing event stream JSON file")
    execute_cmd.add_argument("--decision-stream", help="Existing decision stream JSON file")
    execute_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    execute_cmd.add_argument("--group", help="WeChat group name")
    execute_cmd.add_argument("--sender", help="Sender name")
    execute_cmd.add_argument("--received-at", help="ISO received time")
    execute_cmd.add_argument("--out", help="Write execution stream JSON to file")
    execute_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    govern_cmd = sub.add_parser("govern", help="Apply governance rules to execution actions")
    govern_cmd.add_argument("--text", help="Raw WeChat message text")
    govern_cmd.add_argument("--file", help="Input file path")
    govern_cmd.add_argument("--event-stream", help="Existing event stream JSON file")
    govern_cmd.add_argument("--decision-stream", help="Existing decision stream JSON file")
    govern_cmd.add_argument("--execution-stream", help="Existing execution stream JSON file")
    govern_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    govern_cmd.add_argument("--group", help="WeChat group name")
    govern_cmd.add_argument("--sender", help="Sender name")
    govern_cmd.add_argument("--received-at", help="ISO received time")
    govern_cmd.add_argument("--out", help="Write governance stream JSON to file")
    govern_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    live_cmd = sub.add_parser("live", help="Sync governed execution actions to live operating adapters")
    live_cmd.add_argument("--text", help="Raw WeChat message text")
    live_cmd.add_argument("--file", help="Input file path")
    live_cmd.add_argument("--event-stream", help="Existing event stream JSON file")
    live_cmd.add_argument("--decision-stream", help="Existing decision stream JSON file")
    live_cmd.add_argument("--execution-stream", help="Existing execution stream JSON file")
    live_cmd.add_argument("--governance-stream", help="Existing governance stream JSON file")
    live_cmd.add_argument("--live-root", help="Live connector runtime root")
    live_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    live_cmd.add_argument("--group", help="WeChat group name")
    live_cmd.add_argument("--sender", help="Sender name")
    live_cmd.add_argument("--received-at", help="ISO received time")
    live_cmd.add_argument("--out", help="Write live stream JSON to file")
    live_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    operate_cmd = sub.add_parser("operate", help="Build OMS daily operating work queues")
    operate_cmd.add_argument("--text", help="Raw WeChat message text")
    operate_cmd.add_argument("--file", help="Input file path")
    operate_cmd.add_argument("--event-stream", help="Existing event stream JSON file")
    operate_cmd.add_argument("--decision-stream", help="Existing decision stream JSON file")
    operate_cmd.add_argument("--execution-stream", help="Existing execution stream JSON file")
    operate_cmd.add_argument("--governance-stream", help="Existing governance stream JSON file")
    operate_cmd.add_argument("--live-stream", help="Existing live stream JSON file")
    operate_cmd.add_argument("--live-root", help="Live connector runtime root")
    operate_cmd.add_argument("--operating-root", help="Operational core runtime root")
    operate_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    operate_cmd.add_argument("--group", help="WeChat group name")
    operate_cmd.add_argument("--sender", help="Sender name")
    operate_cmd.add_argument("--received-at", help="ISO received time")
    operate_cmd.add_argument("--user-id", help="Current OMS user id or role alias for personal workspace entry")
    operate_cmd.add_argument("--out", help="Write operating stream JSON to file")
    operate_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    adopt_cmd = sub.add_parser("adopt", help="Assess organizational adoption of OMS as default work mode")
    adopt_cmd.add_argument("--text", help="Raw WeChat message text")
    adopt_cmd.add_argument("--file", help="Input file path")
    adopt_cmd.add_argument("--event-stream", help="Existing event stream JSON file")
    adopt_cmd.add_argument("--decision-stream", help="Existing decision stream JSON file")
    adopt_cmd.add_argument("--execution-stream", help="Existing execution stream JSON file")
    adopt_cmd.add_argument("--governance-stream", help="Existing governance stream JSON file")
    adopt_cmd.add_argument("--live-stream", help="Existing live stream JSON file")
    adopt_cmd.add_argument("--operational-stream", help="Existing operational stream JSON file")
    adopt_cmd.add_argument("--bypass-log", help="Optional bypass log JSON file")
    adopt_cmd.add_argument("--manual-override-log", help="Optional manual override log JSON file")
    adopt_cmd.add_argument("--live-root", help="Live connector runtime root")
    adopt_cmd.add_argument("--operating-root", help="Operational core runtime root")
    adopt_cmd.add_argument("--adoption-root", help="Adoption engine runtime root")
    adopt_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    adopt_cmd.add_argument("--group", help="WeChat group name")
    adopt_cmd.add_argument("--sender", help="Sender name")
    adopt_cmd.add_argument("--received-at", help="ISO received time")
    adopt_cmd.add_argument("--out", help="Write adoption stream JSON to file")
    adopt_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    switch_cmd = sub.add_parser("switch", help="Control OMS full operational switch state")
    switch_cmd.add_argument("--text", help="Raw WeChat message text")
    switch_cmd.add_argument("--file", help="Input file path")
    switch_cmd.add_argument("--event-stream", help="Existing event stream JSON file")
    switch_cmd.add_argument("--decision-stream", help="Existing decision stream JSON file")
    switch_cmd.add_argument("--execution-stream", help="Existing execution stream JSON file")
    switch_cmd.add_argument("--governance-stream", help="Existing governance stream JSON file")
    switch_cmd.add_argument("--live-stream", help="Existing live stream JSON file")
    switch_cmd.add_argument("--operational-stream", help="Existing operational stream JSON file")
    switch_cmd.add_argument("--adoption-stream", help="Existing adoption stream JSON file")
    switch_cmd.add_argument("--requested-state", default="SOFT_SWITCH", choices=["PRE_SWITCH", "SOFT_SWITCH", "HARD_SWITCH", "FULL_OPERATING"])
    switch_cmd.add_argument("--boss-authorized", action="store_true", help="BOSS has authorized the requested switch state")
    switch_cmd.add_argument("--bypass-log", help="Optional bypass log JSON file")
    switch_cmd.add_argument("--manual-override-log", help="Optional manual override log JSON file")
    switch_cmd.add_argument("--live-root", help="Live connector runtime root")
    switch_cmd.add_argument("--operating-root", help="Operational core runtime root")
    switch_cmd.add_argument("--adoption-root", help="Adoption engine runtime root")
    switch_cmd.add_argument("--switch-root", help="System switch runtime root")
    switch_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    switch_cmd.add_argument("--group", help="WeChat group name")
    switch_cmd.add_argument("--sender", help="Sender name")
    switch_cmd.add_argument("--received-at", help="ISO received time")
    switch_cmd.add_argument("--out", help="Write switch stream JSON to file")
    switch_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    lock_cmd = sub.add_parser("lock", help="Lock OMS final operating reality")
    lock_cmd.add_argument("--text", help="Raw WeChat message text")
    lock_cmd.add_argument("--file", help="Input file path")
    lock_cmd.add_argument("--event-stream", help="Existing event stream JSON file")
    lock_cmd.add_argument("--decision-stream", help="Existing decision stream JSON file")
    lock_cmd.add_argument("--execution-stream", help="Existing execution stream JSON file")
    lock_cmd.add_argument("--governance-stream", help="Existing governance stream JSON file")
    lock_cmd.add_argument("--live-stream", help="Existing live stream JSON file")
    lock_cmd.add_argument("--operational-stream", help="Existing operational stream JSON file")
    lock_cmd.add_argument("--adoption-stream", help="Existing adoption stream JSON file")
    lock_cmd.add_argument("--switch-stream", help="Existing switch stream JSON file")
    lock_cmd.add_argument("--requested-state", default="SOFT_SWITCH", choices=["PRE_SWITCH", "SOFT_SWITCH", "HARD_SWITCH", "FULL_OPERATING"])
    lock_cmd.add_argument("--requested-lock-state", choices=["LOCKED", "UNLOCKED", "READONLY", "MIGRATION"])
    lock_cmd.add_argument("--boss-authorized", action="store_true", help="BOSS has authorized the requested switch state")
    lock_cmd.add_argument("--debug-unlock", action="store_true", help="Temporarily unlock for debugging")
    lock_cmd.add_argument("--bypass-log", help="Optional bypass log JSON file")
    lock_cmd.add_argument("--manual-override-log", help="Optional manual override log JSON file")
    lock_cmd.add_argument("--live-root", help="Live connector runtime root")
    lock_cmd.add_argument("--operating-root", help="Operational core runtime root")
    lock_cmd.add_argument("--adoption-root", help="Adoption engine runtime root")
    lock_cmd.add_argument("--switch-root", help="System switch runtime root")
    lock_cmd.add_argument("--lock-root", help="Reality lock runtime root")
    lock_cmd.add_argument("--source", default="wechat", help="Input source, default: wechat")
    lock_cmd.add_argument("--group", help="WeChat group name")
    lock_cmd.add_argument("--sender", help="Sender name")
    lock_cmd.add_argument("--received-at", help="ISO received time")
    lock_cmd.add_argument("--out", help="Write reality lock stream JSON to file")
    lock_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    batch_cmd = sub.add_parser("batch", help="Parse files under a directory")
    batch_cmd.add_argument("--input-dir", required=True)
    batch_cmd.add_argument("--output-dir", required=True)
    batch_cmd.add_argument("--source", default="wechat")
    batch_cmd.add_argument("--pretty", action="store_true")

    feishu_map_cmd = sub.add_parser("feishu-map", help="Sync Feishu users/chats/approval codes into OMS real-world mapping")
    feishu_map_cmd.add_argument("--env", help="Path to feishu.env")
    feishu_map_cmd.add_argument("--mapping-root", help="Output directory for OMS_RealWorld_Mapping")
    feishu_map_cmd.add_argument("--out", help="Write mapping JSON to file")
    feishu_map_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    excel_import_cmd = sub.add_parser("excel-import", help="Import Excel business sources into OMS work_items")
    excel_import_cmd.add_argument("--resident", help="在住表 path (.xlsx/.csv/.tsv)")
    excel_import_cmd.add_argument("--room-status", help="房态表 path (.xlsx/.csv/.tsv)")
    excel_import_cmd.add_argument("--contracts", help="签约客户表 path (.xlsx/.csv/.tsv)")
    excel_import_cmd.add_argument("--live-root", help="Live connector runtime root")
    excel_import_cmd.add_argument("--operating-root", help="Operational core runtime root")
    excel_import_cmd.add_argument("--out", help="Write Excel import stream JSON to file")
    excel_import_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    finance_import_cmd = sub.add_parser("finance-import", help="Import finance Excel sources into OMS finance workflow")
    finance_import_cmd.add_argument("--checkin-registration", help="入住登记表 path (.xls/.xlsx/.csv/.tsv)")
    finance_import_cmd.add_argument("--finance-daily", help="财务日报表 path (.xls/.xlsx/.csv/.tsv)")
    finance_import_cmd.add_argument("--bank-cash-journal", help="银行现金日记账 path (.xls/.xlsx/.csv/.tsv)")
    finance_import_cmd.add_argument("--real-income", help="实入账 path (.xls/.xlsx/.csv/.tsv)")
    finance_import_cmd.add_argument("--service-refund", help="服务金额及退费 path (.xls/.xlsx/.csv/.tsv)")
    finance_import_cmd.add_argument("--sales-commission", help="销售提成明细 path (.xls/.xlsx/.csv/.tsv)")
    finance_import_cmd.add_argument("--care-wage", help="照护师拆分工资表 path (.xls/.xlsx/.csv/.tsv)")
    finance_import_cmd.add_argument("--sales-detail", help="销售明细表 path (.xls/.xlsx/.csv/.tsv)")
    finance_import_cmd.add_argument("--live-root", help="Live connector runtime root")
    finance_import_cmd.add_argument("--operating-root", help="Operational core runtime root")
    finance_import_cmd.add_argument("--out", help="Write finance import stream JSON to file")
    finance_import_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    business_events_cmd = sub.add_parser("business-events", help="Rebuild business event and HR execution flows from live_runtime")
    business_events_cmd.add_argument("--live-root", help="Live connector runtime root")
    business_events_cmd.add_argument("--operating-root", help="Operational core runtime root")
    business_events_cmd.add_argument("--out", help="Write business event flow summary JSON to file")
    business_events_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    core_data_model_cmd = sub.add_parser("core-data-model", help="Rebuild Room/Finance/Sales entity model from runtime data")
    core_data_model_cmd.add_argument("--live-root", help="Live connector runtime root")
    core_data_model_cmd.add_argument("--operating-root", help="Operational core runtime root")
    core_data_model_cmd.add_argument("--out", help="Write core data model state JSON to file")
    core_data_model_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    room_engine_cmd = sub.add_parser("room-engine", help="Run June Method RoomAllocationEngine from entity model")
    room_engine_cmd.add_argument("--live-root", help="Live connector runtime root")
    room_engine_cmd.add_argument("--operating-root", help="Operational core runtime root")
    room_engine_cmd.add_argument("--out", help="Write room allocation engine state JSON to file")
    room_engine_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    core_fusion_cmd = sub.add_parser("core-fusion", help="Rebuild Data + Identity + Workflow + Work Entry fusion layer")
    core_fusion_cmd.add_argument("--live-root", help="Live connector runtime root")
    core_fusion_cmd.add_argument("--operating-root", help="Operational core runtime root")
    core_fusion_cmd.add_argument("--user-id", help="Optional Feishu user_id to include a personal work entry view")
    core_fusion_cmd.add_argument("--out", help="Write core fusion state JSON to file")
    core_fusion_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    history_cmd = sub.add_parser("history", help="Build historical timeline and source traceability view")
    history_cmd.add_argument("--live-root", help="Live connector runtime root")
    history_cmd.add_argument("--operating-root", help="Operational core runtime root")
    history_cmd.add_argument("--date", help="Filter one date, YYYY-MM-DD")
    history_cmd.add_argument("--start-date", help="Filter start date, YYYY-MM-DD")
    history_cmd.add_argument("--end-date", help="Filter end date, YYYY-MM-DD")
    history_cmd.add_argument("--workspace-key", help="Filter one workspace key")
    history_cmd.add_argument("--event-type", help="Filter one business event type")
    history_cmd.add_argument("--limit", type=int, default=200, help="Maximum timeline items to return")
    history_cmd.add_argument("--out", help="Write historical view JSON to file")
    history_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    human_execution_cmd = sub.add_parser("human-execution", help="Close Feishu user_id -> hr_execution -> workspace loop")
    human_execution_cmd.add_argument("--env", help="Path to feishu.env for compatibility; execution identities come from realworld mapping")
    human_execution_cmd.add_argument("--live-root", help="Live connector runtime root")
    human_execution_cmd.add_argument("--operating-root", help="Operational core runtime root")
    human_execution_cmd.add_argument("--out", help="Write human execution closure JSON to file")
    human_execution_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    auto_run_cmd = sub.add_parser("auto-run", help="Run OMS continuously from Excel and business data changes")
    auto_run_cmd.add_argument("--resident", help="在住表 path")
    auto_run_cmd.add_argument("--room-status", help="房态表 path")
    auto_run_cmd.add_argument("--contracts", help="签约客户表 path")
    auto_run_cmd.add_argument("--checkin-registration", help="入住登记表 path")
    auto_run_cmd.add_argument("--finance-daily", help="财务日报表 path")
    auto_run_cmd.add_argument("--bank-cash-journal", help="银行现金日记账 path")
    auto_run_cmd.add_argument("--real-income", help="实入账 path")
    auto_run_cmd.add_argument("--service-refund", help="服务金额及退费 path")
    auto_run_cmd.add_argument("--sales-commission", help="销售提成明细 path")
    auto_run_cmd.add_argument("--care-wage", help="照护师拆分工资表 path")
    auto_run_cmd.add_argument("--sales-detail", help="销售明细表 path")
    auto_run_cmd.add_argument("--live-root", help="Live connector runtime root")
    auto_run_cmd.add_argument("--operating-root", help="Operational core runtime root")
    auto_run_cmd.add_argument("--state-path", help="Autonomous runner state file")
    auto_run_cmd.add_argument("--interval", type=int, default=30, help="Polling interval in seconds")
    auto_run_cmd.add_argument("--once", action="store_true", help="Run a single change-detection cycle")
    auto_run_cmd.add_argument("--baseline-existing", action="store_true", help="Record current file signatures without importing")
    auto_run_cmd.add_argument("--force", action="store_true", help="Force import all supplied sources on this cycle")
    auto_run_cmd.add_argument("--out", help="Write autonomous run JSON to file")
    auto_run_cmd.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    args = parser.parse_args(argv)
    if args.command is None:
        result = home_one(args)
        write_json(result, getattr(args, "out", None), pretty=bool(getattr(args, "pretty", False)))
        return 0
    if args.command == "home":
        result = home_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "parse":
        result = parse_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "events":
        result = events_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "decisions":
        result = decisions_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "execute":
        result = execute_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "govern":
        result = govern_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "live":
        result = live_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "operate":
        result = operate_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "adopt":
        result = adopt_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "switch":
        result = switch_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "lock":
        result = lock_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "batch":
        return parse_batch(args)
    if args.command == "feishu-map":
        result = feishu_map_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "excel-import":
        result = excel_import_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "finance-import":
        result = finance_import_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "business-events":
        result = business_events_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "core-data-model":
        result = core_data_model_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "room-engine":
        result = room_engine_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "core-fusion":
        result = core_fusion_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "history":
        result = history_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "human-execution":
        result = human_execution_one(args)
        write_json(result, args.out, pretty=args.pretty)
        return 0
    if args.command == "auto-run":
        result = auto_run_one(args)
        if result is not None:
            write_json(result, args.out, pretty=args.pretty)
        return 0
    return 2


def parse_one(args: argparse.Namespace) -> dict[str, Any]:
    hub = OMSInputHub()
    data_parser = OMSDataParser()
    if bool(args.text) == bool(args.file):
        raise SystemExit("exactly one of --text or --file is required")
    if args.text:
        envelope = hub.accept_text(args.text, source=args.source, group=args.group, sender=args.sender, received_at=args.received_at)
    else:
        envelope = hub.accept_file(args.file, source=args.source, group=args.group, sender=args.sender, received_at=args.received_at)
    return data_parser.parse(envelope)


def events_one(args: argparse.Namespace) -> dict[str, Any]:
    parsed = parse_one(args)
    return EventEngine().build_event_stream(parsed)


def decisions_one(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "event_stream", None):
        if args.text or args.file:
            raise SystemExit("--event-stream cannot be combined with --text or --file")
        event_stream = json.loads(Path(args.event_stream).read_text(encoding="utf-8"))
    else:
        event_stream = events_one(args)
    return DecisionEngine().build_decision_stream(event_stream)


def execute_one(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "decision_stream", None):
        if args.text or args.file or getattr(args, "event_stream", None):
            raise SystemExit("--decision-stream cannot be combined with --text, --file, or --event-stream")
        decision_stream = json.loads(Path(args.decision_stream).read_text(encoding="utf-8"))
    else:
        decision_stream = decisions_one(args)
    return ExecutionEngine().build_execution_stream(decision_stream)


def govern_one(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "execution_stream", None):
        if args.text or args.file or getattr(args, "event_stream", None) or getattr(args, "decision_stream", None):
            raise SystemExit("--execution-stream cannot be combined with --text, --file, --event-stream, or --decision-stream")
        execution_stream = json.loads(Path(args.execution_stream).read_text(encoding="utf-8"))
    else:
        execution_stream = execute_one(args)
    return GovernanceEngine().build_governance_stream(execution_stream)


def live_one(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "governance_stream", None):
        if not getattr(args, "execution_stream", None):
            raise SystemExit("--governance-stream requires --execution-stream")
        if args.text or args.file or getattr(args, "event_stream", None) or getattr(args, "decision_stream", None):
            raise SystemExit("--governance-stream cannot be combined with --text, --file, --event-stream, or --decision-stream")
        execution_stream = json.loads(Path(args.execution_stream).read_text(encoding="utf-8"))
        governance_stream = json.loads(Path(args.governance_stream).read_text(encoding="utf-8"))
    else:
        execution_stream = execute_one(args)
        governance_stream = GovernanceEngine().build_governance_stream(execution_stream)
    return LiveConnector(getattr(args, "live_root", None)).build_live_stream(execution_stream, governance_stream)


def operate_one(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "live_stream", None):
        if not getattr(args, "execution_stream", None) or not getattr(args, "governance_stream", None):
            raise SystemExit("--live-stream requires --execution-stream and --governance-stream")
        if args.text or args.file or getattr(args, "event_stream", None) or getattr(args, "decision_stream", None):
            raise SystemExit("--live-stream cannot be combined with --text, --file, --event-stream, or --decision-stream")
        execution_stream = json.loads(Path(args.execution_stream).read_text(encoding="utf-8"))
        governance_stream = json.loads(Path(args.governance_stream).read_text(encoding="utf-8"))
        live_stream = json.loads(Path(args.live_stream).read_text(encoding="utf-8"))
    else:
        execution_stream = execute_one(args)
        governance_stream = GovernanceEngine().build_governance_stream(execution_stream)
        live_stream = LiveConnector(getattr(args, "live_root", None)).build_live_stream(execution_stream, governance_stream)
    return OMSOperationalCore(getattr(args, "operating_root", None)).build_operating_stream(
        execution_stream, governance_stream, live_stream, user_id=getattr(args, "user_id", None)
    )


def home_one(args: argparse.Namespace) -> dict[str, Any]:
    home_ui = OMSHomeUI(getattr(args, "live_root", None), getattr(args, "operating_root", None))
    if getattr(args, "operational_stream", None):
        if getattr(args, "text", None) or getattr(args, "file", None):
            raise SystemExit("--operational-stream cannot be combined with --text or --file")
        operating_stream = json.loads(Path(args.operational_stream).read_text(encoding="utf-8"))
        return home_ui.build_home(operating_stream, user_id=getattr(args, "user_id", None))
    if getattr(args, "text", None) or getattr(args, "file", None):
        operating_stream = operate_one(args)
        return home_ui.build_home(operating_stream, user_id=getattr(args, "user_id", None))
    return home_ui.build_home_from_saved_state(user_id=getattr(args, "user_id", None))


def adopt_one(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "operational_stream", None):
        required = ["execution_stream", "governance_stream", "live_stream"]
        missing = [name for name in required if not getattr(args, name, None)]
        if missing:
            raise SystemExit("--operational-stream requires --execution-stream, --governance-stream, and --live-stream")
        if args.text or args.file or getattr(args, "event_stream", None) or getattr(args, "decision_stream", None):
            raise SystemExit("--operational-stream cannot be combined with --text, --file, --event-stream, or --decision-stream")
        execution_stream = json.loads(Path(args.execution_stream).read_text(encoding="utf-8"))
        governance_stream = json.loads(Path(args.governance_stream).read_text(encoding="utf-8"))
        live_stream = json.loads(Path(args.live_stream).read_text(encoding="utf-8"))
        operational_stream = json.loads(Path(args.operational_stream).read_text(encoding="utf-8"))
    else:
        execution_stream = execute_one(args)
        governance_stream = GovernanceEngine().build_governance_stream(execution_stream)
        live_stream = LiveConnector(getattr(args, "live_root", None)).build_live_stream(execution_stream, governance_stream)
        operational_stream = OMSOperationalCore(getattr(args, "operating_root", None)).build_operating_stream(
            execution_stream, governance_stream, live_stream
        )
    bypass_log = read_optional_json_list(getattr(args, "bypass_log", None))
    manual_override_log = read_optional_json_list(getattr(args, "manual_override_log", None))
    return AdoptionEngine(getattr(args, "adoption_root", None)).build_adoption_stream(
        operational_stream,
        live_stream,
        governance_stream,
        bypass_events=bypass_log,
        manual_overrides=manual_override_log,
    )


def switch_one(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "adoption_stream", None):
        if args.text or args.file or getattr(args, "event_stream", None) or getattr(args, "decision_stream", None):
            raise SystemExit("--adoption-stream cannot be combined with --text, --file, --event-stream, or --decision-stream")
        adoption_stream = json.loads(Path(args.adoption_stream).read_text(encoding="utf-8"))
    else:
        adoption_stream = adopt_one(args)
    bypass_log = read_optional_json_list(getattr(args, "bypass_log", None))
    manual_override_log = read_optional_json_list(getattr(args, "manual_override_log", None))
    return SystemSwitchController(getattr(args, "switch_root", None)).build_switch_stream(
        adoption_stream,
        requested_state=getattr(args, "requested_state", "SOFT_SWITCH"),
        boss_authorized=bool(getattr(args, "boss_authorized", False)),
        bypass_events=bypass_log,
        manual_overrides=manual_override_log,
    )


def lock_one(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "switch_stream", None):
        if args.text or args.file or getattr(args, "event_stream", None) or getattr(args, "decision_stream", None):
            raise SystemExit("--switch-stream cannot be combined with --text, --file, --event-stream, or --decision-stream")
        switch_stream = json.loads(Path(args.switch_stream).read_text(encoding="utf-8"))
    else:
        switch_stream = switch_one(args)
    return RealityLock(getattr(args, "lock_root", None)).build_lock_stream(
        switch_stream,
        requested_lock_state=getattr(args, "requested_lock_state", None),
        debug_unlock=bool(getattr(args, "debug_unlock", False)),
    )


def read_optional_json_list(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    raise SystemExit(f"{path} must contain a JSON list")


def parse_batch(args: argparse.Namespace) -> int:
    hub = OMSInputHub()
    data_parser = OMSDataParser()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for envelope in hub.accept_directory(args.input_dir):
        result = data_parser.parse(envelope)
        out_file = out_dir / f"{envelope.input_id}.json"
        write_json(result, str(out_file), pretty=args.pretty, echo=False)
        count += 1
    print(json.dumps({"status": "ok", "parsed_files": count, "output_dir": str(out_dir)}, ensure_ascii=False))
    return 0


def feishu_map_one(args: argparse.Namespace) -> dict[str, Any]:
    return FeishuObjectSyncer(env_path=getattr(args, "env", None), mapping_root=getattr(args, "mapping_root", None)).sync()


def excel_import_one(args: argparse.Namespace) -> dict[str, Any]:
    if not any([getattr(args, "resident", None), getattr(args, "room_status", None), getattr(args, "contracts", None)]):
        raise SystemExit("at least one of --resident, --room-status, or --contracts is required")
    return ExcelOMSImporter(getattr(args, "live_root", None), getattr(args, "operating_root", None)).import_sources(
        resident=getattr(args, "resident", None),
        room_status=getattr(args, "room_status", None),
        contracts=getattr(args, "contracts", None),
    )


def finance_import_one(args: argparse.Namespace) -> dict[str, Any]:
    source_values = {
        "checkin_registration": getattr(args, "checkin_registration", None),
        "finance_daily": getattr(args, "finance_daily", None),
        "bank_cash_journal": getattr(args, "bank_cash_journal", None),
        "real_income": getattr(args, "real_income", None),
        "service_refund": getattr(args, "service_refund", None),
        "sales_commission": getattr(args, "sales_commission", None),
        "care_wage": getattr(args, "care_wage", None),
        "sales_detail": getattr(args, "sales_detail", None),
    }
    if not any(source_values.values()):
        raise SystemExit("at least one finance source path is required")
    return FinanceDataImporter(getattr(args, "live_root", None), getattr(args, "operating_root", None)).import_sources(
        **source_values
    )


def business_events_one(args: argparse.Namespace) -> dict[str, Any]:
    return BusinessEventEngine(getattr(args, "live_root", None), getattr(args, "operating_root", None)).rebuild_from_saved_state()


def core_data_model_one(args: argparse.Namespace) -> dict[str, Any]:
    return CoreDataModelLayer(getattr(args, "live_root", None), getattr(args, "operating_root", None)).rebuild_from_saved_state()


def room_engine_one(args: argparse.Namespace) -> dict[str, Any]:
    entity_state = CoreDataModelLayer(getattr(args, "live_root", None), getattr(args, "operating_root", None)).rebuild_from_saved_state()
    return RoomAllocationEngine(getattr(args, "live_root", None), getattr(args, "operating_root", None)).rebuild_from_entity_model(entity_state)


def core_fusion_one(args: argparse.Namespace) -> dict[str, Any]:
    return CoreFusionLayer(getattr(args, "live_root", None), getattr(args, "operating_root", None)).rebuild_from_saved_state(
        user_id=getattr(args, "user_id", None)
    )


def history_one(args: argparse.Namespace) -> dict[str, Any]:
    return HistoricalDataViewLayer(
        getattr(args, "live_root", None),
        getattr(args, "operating_root", None),
    ).build_history_view(
        date=getattr(args, "date", None),
        start_date=getattr(args, "start_date", None),
        end_date=getattr(args, "end_date", None),
        workspace_key=getattr(args, "workspace_key", None),
        event_type=getattr(args, "event_type", None),
        limit=getattr(args, "limit", 200),
    )


def human_execution_one(args: argparse.Namespace) -> dict[str, Any]:
    return HumanExecutionClosure(
        getattr(args, "live_root", None),
        getattr(args, "operating_root", None),
        getattr(args, "env", None),
    ).close()


def auto_run_one(args: argparse.Namespace) -> dict[str, Any] | None:
    sources = {
        "resident": getattr(args, "resident", None),
        "room_status": getattr(args, "room_status", None),
        "contracts": getattr(args, "contracts", None),
        "checkin_registration": getattr(args, "checkin_registration", None),
        "finance_daily": getattr(args, "finance_daily", None),
        "bank_cash_journal": getattr(args, "bank_cash_journal", None),
        "real_income": getattr(args, "real_income", None),
        "service_refund": getattr(args, "service_refund", None),
        "sales_commission": getattr(args, "sales_commission", None),
        "care_wage": getattr(args, "care_wage", None),
        "sales_detail": getattr(args, "sales_detail", None),
    }
    if not any(sources.values()):
        raise SystemExit("at least one data source path is required for auto-run")
    runner = OMSAutonomousRunner(
        live_root=getattr(args, "live_root", None),
        operating_root=getattr(args, "operating_root", None),
        state_path=getattr(args, "state_path", None),
        interval_seconds=getattr(args, "interval", 30),
    )
    if getattr(args, "once", False):
        return runner.run_once(
            sources=sources,
            baseline_existing=bool(getattr(args, "baseline_existing", False)),
            force=bool(getattr(args, "force", False)),
        )
    runner.run_forever(
        sources=sources,
        baseline_existing=bool(getattr(args, "baseline_existing", False)),
        force_first_run=bool(getattr(args, "force", False)),
    )
    return None


def write_json(result: dict[str, Any], out: str | None, *, pretty: bool, echo: bool = True) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2 if pretty else None)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
    if echo:
        print(text)
