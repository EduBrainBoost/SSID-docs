"""ssidctl approve — Approval Ledger commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.core.approval_ledger import ApprovalError, ApprovalLedger


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("approve", help="Approval Ledger operations")
    sub = parser.add_subparsers(dest="approve_action")

    record_p = sub.add_parser("record", help="Record an approval")
    record_p.add_argument("--task", required=True, help="Task ID")
    record_p.add_argument("--run", required=True, help="Run ID")
    record_p.add_argument("--diff-hash", required=True, help="SHA-256 of diff (sha256:...)")
    record_p.add_argument("--approver", default="user")
    record_p.add_argument("--toolchain-hash", default="sha256:unset")
    record_p.add_argument("--scope-hash", default="sha256:unset")

    list_p = sub.add_parser("list", help="List approvals")
    list_p.add_argument("--task", default=None, help="Filter by task ID")

    check_p = sub.add_parser("check", help="Check if approval exists")
    check_p.add_argument("--task", required=True)
    check_p.add_argument("--diff-hash", required=True)

    parser.set_defaults(func=cmd_approve)


def cmd_approve(args: argparse.Namespace, config: EMSConfig) -> int:
    ledger = ApprovalLedger(config.paths.state_dir / "approvals" / "approvals.jsonl")
    try:
        if args.approve_action == "record":
            record = ledger.record(
                task_id=args.task,
                run_id=args.run,
                approver=args.approver,
                diff_hash=args.diff_hash,
                toolchain_hash=args.toolchain_hash,
                scope_hash=args.scope_hash,
            )
            aid = record["approval_id"]
            print(f"Approved: {aid} task={record['task_id']} run={record['run_id']}")
        elif args.approve_action == "list":
            records = ledger.read_by_task(args.task) if args.task else ledger.read_all()
            if not records:
                print("No approvals found.")
                return 0
            for r in records:
                aid = r["approval_id"]
                tid, rid = r["task_id"], r["run_id"]
                print(f"  {aid}: task={tid} run={rid} by={r['approver']} at={r['approved_utc']}")
        elif args.approve_action == "check":
            if ledger.has_approval(args.task, args.diff_hash):
                approval = ledger.find_approval(args.task, args.diff_hash)
                assert approval is not None  # guarded by has_approval above
                print(f"APPROVED: {approval['approval_id']} by={approval['approver']}")
            else:
                print("NOT APPROVED")
                return 1
        else:
            print("Usage: ssidctl approve {record|list|check}", file=sys.stderr)
            return 1
    except ApprovalError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0
