from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .adoption_engine import AdoptionEngine
from .data_parser import OMSDataParser
from .decision_engine import DecisionEngine
from .event_engine import EventEngine
from .execution_engine import ExecutionEngine
from .feishu_mapping import FeishuObjectSyncer
from .governance_engine import GovernanceEngine
from .input_hub import OMSInputHub
from .live_connector import LiveConnector
from .operational_core import OMSOperationalCore
from .reality_lock import RealityLock
from .system_switch_controller import SystemSwitchController


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="oms_v1", description="Huangjia OMS V1 input-to-JSON parser")
    sub = parser.add_subparsers(dest="command", required=True)

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

    args = parser.parse_args(argv)
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


def write_json(result: dict[str, Any], out: str | None, *, pretty: bool, echo: bool = True) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2 if pretty else None)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
    if echo:
        print(text)
