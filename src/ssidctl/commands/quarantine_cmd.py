"""Quarantine CLI command."""

from __future__ import annotations

import argparse

from ssidctl.modules.quarantine import QuarantineStore


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("quarantine", help="Security quarantine operations")
    sub = p.add_subparsers(dest="quarantine_action")
    add_p = sub.add_parser("add")
    add_p.add_argument("incident_id")
    add_p.add_argument("file_path")
    add_p.add_argument("reason")
    rel_p = sub.add_parser("release")
    rel_p.add_argument("quarantine_id")
    sub.add_parser("list")
    ver_p = sub.add_parser("verify")
    ver_p.add_argument("quarantine_id")
    p.set_defaults(func=cmd_quarantine)


def cmd_quarantine(args, config) -> int:
    qs = QuarantineStore(config.paths.state_dir / "quarantine")
    action = args.quarantine_action
    if action == "add":
        entry = qs.quarantine(args.incident_id, args.file_path, args.reason)
        print(f"Quarantined: {entry['quarantine_id']} ({entry['file_hash']})")
    elif action == "release":
        entry = qs.release(args.quarantine_id)
        print(f"Released: {entry['quarantine_id']}")
    elif action == "list":
        for e in qs.list_quarantined():
            print(
                f"  [{e['status']}] {e['quarantine_id']}: {e['reason']} ({e['file_hash'][:20]}...)"
            )
    elif action == "verify":
        ok = qs.verify(args.quarantine_id)
        print(f"Integrity: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    else:
        print("Usage: ssidctl quarantine {add|release|list|verify}")
        return 1
    return 0
