"""ssidctl calendar — Calendar/Cron commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.modules.calendar_mod import Calendar, CalendarError


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("calendar", help="Calendar/Cron Registry")
    sub = parser.add_subparsers(dest="calendar_action")

    add_p = sub.add_parser("add", help="Add a cron job")
    add_p.add_argument("cron_id", type=str)
    add_p.add_argument("schedule", type=str)
    add_p.add_argument("job", type=str)

    disable_p = sub.add_parser("disable", help="Disable a cron job")
    disable_p.add_argument("cron_id", type=str)

    enable_p = sub.add_parser("enable", help="Enable a cron job")
    enable_p.add_argument("cron_id", type=str)

    run_now_p = sub.add_parser("run-now", help="Trigger a cron job immediately")
    run_now_p.add_argument("cron_id", type=str)

    sub.add_parser("list", help="List cron jobs")

    sub.add_parser("export", help="Export as ICS")

    parser.set_defaults(func=cmd_calendar)


def cmd_calendar(args: argparse.Namespace, config: EMSConfig) -> int:
    cal = Calendar(config.paths.state_dir / "calendar")

    try:
        if args.calendar_action == "add":
            job = cal.add(args.cron_id, args.schedule, args.job)
            print(f"Added: {job['cron_id']} ({job['schedule']}) -> {job['job']}")
        elif args.calendar_action == "disable":
            job = cal.disable(args.cron_id)
            print(f"Disabled: {job['cron_id']}")
        elif args.calendar_action == "enable":
            job = cal.enable(args.cron_id)
            print(f"Enabled: {job['cron_id']}")
        elif args.calendar_action == "run-now":
            job = cal.trigger(args.cron_id)
            print(f"Triggered: {job['cron_id']} at {job['last_run']}")
        elif args.calendar_action == "list":
            jobs = cal.list_jobs()
            for j in jobs:
                status = "ON" if j["enabled"] else "OFF"
                print(f"  [{status:3s}] {j['cron_id']}: {j['schedule']} -> {j['job']}")
        elif args.calendar_action == "export":
            print(cal.export_ics())
        else:
            print("Usage: ssidctl calendar {add|disable|list|export}", file=sys.stderr)
            return 1
    except CalendarError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
