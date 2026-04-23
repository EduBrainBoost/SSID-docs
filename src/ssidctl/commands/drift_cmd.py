"""ssidctl drift — Drift sentinel commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.modules.drift import DriftError, DriftSentinel


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("drift", help="Local vs remote drift check")
    sub = parser.add_subparsers(dest="drift_action")

    check_p = sub.add_parser("check", help="Check drift against origin")
    check_p.add_argument("--branch", type=str, default="main")
    check_p.add_argument(
        "--repo",
        type=str,
        choices=["ssid", "ems"],
        default="ssid",
        help="Which repo to check (default: ssid)",
    )

    parser.set_defaults(func=cmd_drift)


def cmd_drift(args: argparse.Namespace, config: EMSConfig) -> int:
    repo_path = (
        config.paths.ssid_repo
        if getattr(args, "repo", "ssid") == "ssid"
        else config.paths.ems_repo
    )

    try:
        if args.drift_action == "check":
            sentinel = DriftSentinel(repo_path)
            report = sentinel.check(args.branch)

            print(f"Repository: {repo_path}")
            print(f"Branch:     {args.branch}")
            print(f"Local SHA:  {report.local_sha[:12]}")
            if report.remote_sha:
                print(f"Remote SHA: {report.remote_sha[:12]}")
                print(f"Synced:     {'YES' if report.is_synced else 'NO'}")
                print(f"Ahead:      {report.ahead}")
                print(f"Behind:     {report.behind}")
            else:
                print("Remote:     not available")
            print(f"Dirty:      {report.dirty_files} file(s)")
            if report.worktrees:
                print(f"Worktrees:  {len(report.worktrees)}")
                for wt in report.worktrees:
                    print(f"  - {wt}")

            if report.has_drift:
                print("\nResult: DRIFT DETECTED")
                return 1
            print("\nResult: CLEAN")
            return 0
        else:
            print("Usage: ssidctl drift {check}", file=sys.stderr)
            return 1
    except DriftError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
