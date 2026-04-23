"""ssidctl update — self-update commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.modules.updater import UpdateError, check_update, self_update


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("update", help="Check for updates or self-update")
    parser.add_argument(
        "--check",
        action="store_true",
        default=True,
        help="Check for updates (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply update via pip",
    )
    parser.set_defaults(func=cmd_update)


def cmd_update(args: argparse.Namespace, config: EMSConfig) -> int:
    if getattr(args, "apply", False):
        print("Updating ssidctl...")
        try:
            result = self_update()
            if result["success"]:
                print("Update successful.")
                print(result["output"])
                return 0
            else:
                print(f"Update failed: {result['output']}", file=sys.stderr)
                return 1
        except UpdateError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Default: check
    info = check_update()
    print(f"Current version: {info['current']}")
    print(f"Latest version:  {info['latest']}")
    if info.get("error"):
        print(f"Warning: {info['error']}")
    if info["update_available"]:
        print("\nUpdate available! Run: ssidctl update --apply")
    else:
        print("\nYou are up to date.")
    return 0
