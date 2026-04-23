"""ssidctl run — Run management commands."""

from __future__ import annotations

import argparse
import json
import sys

from ssidctl.config import EMSConfig
from ssidctl.modules.run import RunError, RunManager


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("run", help="Run management")
    sub = parser.add_subparsers(dest="run_action")
    sub.add_parser("list", help="List all runs")
    show_p = sub.add_parser("show", help="Show run details")
    show_p.add_argument("run_id", type=str)
    replay_p = sub.add_parser("replay", help="Replay gates (no Claude)")
    replay_p.add_argument("run_id", type=str)
    parser.set_defaults(func=cmd_run)


def cmd_run(args: argparse.Namespace, config: EMSConfig) -> int:
    mgr = RunManager(config.paths.state_dir, config.paths.evidence_dir)
    try:
        if args.run_action == "list":
            runs = mgr.list_runs()
            if not runs:
                print("No runs found.")
                return 0
            for r in runs:
                payload = r.get("payload", {})
                run_id = payload.get("run_id", r.get("event_id", "?"))
                task_id = payload.get("task_id", "?")
                ts = r.get("timestamp", "?")
                print(f"  {run_id}: task={task_id} at={ts}")
        elif args.run_action == "show":
            info = mgr.show(args.run_id)
            print(json.dumps(info, indent=2, default=str))
        elif args.run_action == "replay":
            result = mgr.replay_gates(args.run_id, config.paths.ssid_repo)
            print(f"Run: {result['run_id']}")
            print(f"Original: {result['original_result']}")
            print(f"Replay:   {result['replay_overall']}")
            for gr in result["replay_gates"]:
                print(f"  {gr['result']:4s}  {gr['gate']} (exit={gr['exit_code']})")
            return 0 if result["replay_overall"] == "PASS" else 1
        else:
            print("Usage: ssidctl run {list|show|replay}", file=sys.stderr)
            return 1
    except RunError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0
