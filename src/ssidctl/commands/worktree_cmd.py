"""ssidctl worktree — worktree management commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.core.worktree_orchestrator import WorktreeOrchestrator


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("worktree", help="Worktree management")
    sub = parser.add_subparsers(dest="worktree_action")

    sub.add_parser("list", help="List active worktree sets")
    sub.add_parser("gc", help="Garbage-collect stale worktrees")

    parser.set_defaults(func=cmd_worktree)


def cmd_worktree(args: argparse.Namespace, config: EMSConfig) -> int:
    wt_dir = config.paths.state_dir / "worktrees"
    orch = WorktreeOrchestrator(config.paths.ssid_repo, wt_dir)

    if args.worktree_action == "list":
        runs = orch.list_worktrees()
        if not runs:
            print("No active worktree sets.")
            return 0
        for r in runs:
            print(f"  {r}")
        return 0

    if args.worktree_action == "gc":
        removed = orch.gc()
        if removed:
            print(f"Removed {len(removed)} stale worktree(s):")
            for r in removed:
                print(f"  {r}")
        else:
            print("No stale worktrees found.")
        return 0

    print("Usage: ssidctl worktree {list|gc}", file=sys.stderr)
    return 1
