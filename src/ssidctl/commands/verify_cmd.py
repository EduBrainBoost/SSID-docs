"""ssidctl verify — evidence integrity verification."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.core.evidence_store import EvidenceError, EvidenceStore


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("verify", help="Verify evidence integrity")
    sub = parser.add_subparsers(dest="verify_action")

    run_p = sub.add_parser("run", help="Verify a single run's integrity")
    run_p.add_argument("run_id", type=str, help="Run ID to verify")

    sub.add_parser("chain", help="Verify the full evidence hash chain")

    parser.set_defaults(func=cmd_verify)


def cmd_verify(args: argparse.Namespace, config: EMSConfig) -> int:
    store = EvidenceStore(config.paths.evidence_dir)

    try:
        if args.verify_action == "run":
            return _verify_run(store, args.run_id)
        elif args.verify_action == "chain":
            return _verify_chain(store)
        else:
            print("Usage: ssidctl verify {run <id>|chain}", file=sys.stderr)
            return 1
    except EvidenceError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _verify_run(store: EvidenceStore, run_id: str) -> int:
    """Verify integrity of a single sealed run."""
    result = store.verify(run_id)
    status = "VALID" if result["valid"] else "INVALID"
    print(f"  Run:       {run_id}")
    print(f"  Integrity: {status}")

    for check, passed in result["checks"].items():
        mark = "OK" if passed else "FAIL"
        print(f"    {mark:4s}  {check}")

    return 0 if result["valid"] else 1


def _verify_chain(store: EvidenceStore) -> int:
    """Verify the full evidence hash chain."""
    result = store.verify_hash_chain()
    status = "VALID" if result["valid"] else "INVALID"
    print(f"  Hash chain: {status}")
    print(f"  Length:      {result['length']} entries")

    if result["errors"]:
        print()
        print("  Errors:")
        for err in result["errors"]:
            print(f"    FAIL  {err}")

    return 0 if result["valid"] else 1
