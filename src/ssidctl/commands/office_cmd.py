"""ssidctl office — Office Screen dashboard."""

from __future__ import annotations

import argparse
import json
import time

from ssidctl.config import EMSConfig
from ssidctl.modules.office import OfficeScreen


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("office", help="Office Screen dashboard")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Polling mode — refresh every N seconds",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Watch refresh interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--export-json",
        type=str,
        default=None,
        help="Export status to JSON file",
    )
    parser.add_argument(
        "--export-md",
        type=str,
        default=None,
        help="Export status as Markdown",
    )
    parser.set_defaults(func=cmd_office)


def cmd_office(args: argparse.Namespace, config: EMSConfig) -> int:
    screen = OfficeScreen(config.paths.state_dir)

    if args.export_md:
        md = screen.render_markdown()
        with open(args.export_md, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Status exported to {args.export_md}")
        return 0

    if args.export_json:
        status = screen.export_status()
        with open(args.export_json, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
        print(f"Status exported to {args.export_json}")
        return 0

    if args.watch:
        try:
            while True:
                # Clear screen (ANSI escape)
                print("\033[2J\033[H", end="")
                print(screen.render_text())
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
    else:
        print(screen.render_text())
        return 0
