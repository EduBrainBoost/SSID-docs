"""ssidctl pr — PR queue and merge-readiness commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.modules.pr import GHNotInstalledError, PRError, PRManager


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("pr", help="PR queue and operations")
    sub = parser.add_subparsers(dest="pr_action")

    list_p = sub.add_parser("list", help="List PRs")
    list_p.add_argument("--state", type=str, default="open")

    status_p = sub.add_parser("status", help="Show PR status")
    status_p.add_argument("number", type=int)

    comment_p = sub.add_parser("comment", help="Comment on a PR")
    comment_p.add_argument("number", type=int)
    comment_p.add_argument("body", type=str)

    ready_p = sub.add_parser("ready", help="Mark PR as ready for review")
    ready_p.add_argument("number", type=int)

    parser.set_defaults(func=cmd_pr)


def cmd_pr(args: argparse.Namespace, config: EMSConfig) -> int:
    pr_mgr = PRManager(config.paths.ssid_repo)

    try:
        if args.pr_action == "list":
            prs = pr_mgr.list_prs(args.state)
            if not prs:
                print("No PRs found.")
                return 0
            for pr in prs:
                print(f"  #{pr.number} [{pr.state}] {pr.title} ({pr.branch}) by {pr.author}")
        elif args.pr_action == "status":
            pr = pr_mgr.status(args.number)
            print(f"PR #{pr.number}: {pr.title}")
            print(f"  State:     {pr.state}")
            print(f"  Branch:    {pr.branch}")
            print(f"  Author:    {pr.author}")
            print(f"  URL:       {pr.url}")
            print(f"  Mergeable: {pr.mergeable}")
            print(f"  Checks:    {pr.checks_pass}")
        elif args.pr_action == "comment":
            pr_mgr.comment(args.number, args.body)
            print(f"Comment added to PR #{args.number}")
        elif args.pr_action == "ready":
            pr_mgr.ready(args.number)
            print(f"PR #{args.number} marked as ready for review")
        else:
            print("Usage: ssidctl pr {list|status|comment|ready}", file=sys.stderr)
            return 1
    except GHNotInstalledError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except PRError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
