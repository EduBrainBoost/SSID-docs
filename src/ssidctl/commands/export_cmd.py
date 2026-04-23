"""Content export CLI command."""

from __future__ import annotations

import argparse

from ssidctl.modules.content import ContentPipeline
from ssidctl.modules.exporter import ContentExporter


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("export", help="Export content items")
    p.add_argument("content_id", help="Content ID to export")
    p.add_argument("--format", choices=["md", "json"], default="md", help="Output format")
    p.add_argument("--output", "-o", help="Output file path (prints to stdout if omitted)")
    p.set_defaults(func=cmd_export)


def cmd_export(args, config) -> int:
    cp = ContentPipeline(config.paths.state_dir / "content")
    exporter = ContentExporter(cp)
    if args.output:
        path = exporter.to_file(args.content_id, args.output, fmt=args.format)
        print(f"Exported to: {path}")
    else:
        if args.format == "md":
            print(exporter.to_markdown(args.content_id))
        else:
            import json

            print(json.dumps(exporter.to_json(args.content_id), indent=2))
    return 0
