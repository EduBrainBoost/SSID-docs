"""ssidctl evidence — WORM evidence query + integrity check."""

from __future__ import annotations

import argparse
import json
import sys

from ssidctl.config import EMSConfig
from ssidctl.core.evidence_store import EvidenceError, EvidenceStore


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("evidence", help="WORM evidence operations")
    sub = parser.add_subparsers(dest="evidence_action")

    sub.add_parser("list", help="List all sealed runs")

    show_p = sub.add_parser("show", help="Show run manifest")
    show_p.add_argument("run_id", type=str)

    verify_p = sub.add_parser("verify", help="Verify run integrity")
    verify_p.add_argument("run_id", type=str)

    parser.set_defaults(func=cmd_evidence)


def cmd_evidence(args: argparse.Namespace, config: EMSConfig) -> int:
    store = EvidenceStore(config.paths.evidence_dir)

    try:
        if args.evidence_action == "list":
            runs = store.list_runs()
            for r in runs:
                rid, tid = r["run_id"], r.get("task_id", "?")
                res = r.get("overall_result", "?")
                print(f"  {rid}: task={tid} result={res}")
        elif args.evidence_action == "show":
            manifest = store.get_manifest(args.run_id)
            print(json.dumps(manifest, indent=2))
        elif args.evidence_action == "verify":
            result = store.verify(args.run_id)
            status = "VALID" if result["valid"] else "INVALID"
            print(f"Integrity: {status}")
            for check, passed in result["checks"].items():
                mark = "OK" if passed else "FAIL"
                print(f"  {mark:4s}  {check}")
            return 0 if result["valid"] else 1
        else:
            print("Usage: ssidctl evidence {list|show|verify}", file=sys.stderr)
            return 1
    except EvidenceError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
