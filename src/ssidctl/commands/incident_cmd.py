"""ssidctl incident — Security incidents (append-only)."""

from __future__ import annotations

import argparse
import sys
import uuid

from ssidctl.config import EMSConfig
from ssidctl.core.event_log import EventLog


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("incident", help="Security incidents")
    sub = parser.add_subparsers(dest="incident_action")

    open_p = sub.add_parser("open", help="Open a new incident")
    open_p.add_argument("summary", type=str)
    open_p.add_argument(
        "--severity",
        type=str,
        default="high",
        choices=["low", "medium", "high", "critical"],
    )

    close_p = sub.add_parser("close", help="Close an incident")
    close_p.add_argument("incident_id", type=str)

    sub.add_parser("list", help="List incidents")

    parser.set_defaults(func=cmd_incident)


def cmd_incident(args: argparse.Namespace, config: EMSConfig) -> int:
    log = EventLog(config.paths.state_dir / "incidents" / "incidents.jsonl")

    if args.incident_action == "open":
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        log.append(
            "incident.opened",
            {
                "incident_id": incident_id,
                "summary": args.summary,
                "severity": args.severity,
                "status": "OPEN",
            },
            actor="user",
        )
        print(f"Opened: {incident_id} [{args.severity}] {args.summary}")

    elif args.incident_action == "close":
        log.append(
            "incident.closed",
            {
                "incident_id": args.incident_id,
                "status": "CLOSED",
            },
            actor="user",
        )
        print(f"Closed: {args.incident_id}")

    elif args.incident_action == "list":
        events = log.read_all()
        # Build current state from events
        incidents: dict[str, dict] = {}
        for e in events:
            iid = e["payload"].get("incident_id", "?")
            if e["type"] == "incident.opened":
                incidents[iid] = e["payload"]
            elif e["type"] == "incident.closed" and iid in incidents:
                incidents[iid]["status"] = "CLOSED"
        for iid, inc in incidents.items():
            st = inc.get("status", "?")
            summ = inc.get("summary", "?")
            sev = inc.get("severity", "?")
            print(f"  [{st:6s}] {iid}: {summ} [{sev}]")
    else:
        print("Usage: ssidctl incident {open|close|list}", file=sys.stderr)
        return 1

    return 0
