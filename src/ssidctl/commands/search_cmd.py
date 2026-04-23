"""ssidctl search — Unified search across all modules."""

from __future__ import annotations

import argparse

from ssidctl.config import EMSConfig
from ssidctl.modules.search import UnifiedSearch


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("search", help="Unified search")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        choices=["task", "content", "memory", "run"],
        help="Filter by type",
    )
    parser.set_defaults(func=cmd_search)


def cmd_search(args: argparse.Namespace, config: EMSConfig) -> int:
    searcher = UnifiedSearch(config.paths.state_dir)
    results = searcher.search(args.query, type_filter=getattr(args, "type", None))

    if not results:
        print("No results found.")
        return 0

    for r in results:
        label = r.get("title", r.get("id", "?"))
        extra = r.get("status", r.get("stage", ""))
        print(f"  [{r['type']:7s}] {r['id']}: {label} {f'({extra})' if extra else ''}")

    return 0
