"""CLI command: ssidctl lock (acquire | release | status)."""

import argparse
import json
import sys

from ssidctl.core.write_lock import LockAcquireError, LockReleaseError, WriteLock


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("lock", help="EMS write-lock management")
    sub = parser.add_subparsers(dest="lock_action")

    acq = sub.add_parser("acquire", help="Acquire write lock")
    acq.add_argument("--repo", type=str, default="SSID", help="Repository name")
    acq.add_argument("--mode", type=str, default="WRITE", choices=["WRITE"])
    acq.add_argument("--ttl", type=int, default=300, help="TTL in seconds")
    acq.add_argument("--holder", type=str, default="lead", help="Lock holder ID")
    acq.add_argument("--sha", type=str, default="unknown", help="Repo git SHA")

    rel = sub.add_parser("release", help="Release write lock")
    rel.add_argument("--force", action="store_true", help="Force release (stale/orphan)")

    sub.add_parser("status", help="Show lock status")

    parser.set_defaults(func=cmd_lock)


def cmd_lock(args: argparse.Namespace, config) -> int:
    lock_dir = config.paths.state_dir / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    repo = getattr(args, "repo", "SSID")
    wl = WriteLock(lock_dir=lock_dir, repo_name=repo)

    action = args.lock_action

    if action == "acquire":
        try:
            data = wl.acquire(
                holder=args.holder,
                repo_git_sha=args.sha,
                ttl_seconds=args.ttl,
            )
            print(f"PASS: Lock acquired (holder={data['holder']}, ttl={data['ttl_seconds']}s)")
            return 0
        except LockAcquireError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            return 1

    elif action == "release":
        try:
            wl.release(force=getattr(args, "force", False))
            print("PASS: Lock released")
            return 0
        except LockReleaseError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            return 1

    elif action == "status":
        status = wl.status()
        print(json.dumps(status, indent=2))
        return 0

    else:
        print("Usage: ssidctl lock {acquire|release|status}", file=sys.stderr)
        return 1
