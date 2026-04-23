"""ssidctl content — Content Pipeline commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from ssidctl.config import EMSConfig
from ssidctl.core.hashing import sha256_bytes
from ssidctl.modules.content import ContentError, ContentPipeline


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("content", help="Content Pipeline")
    sub = parser.add_subparsers(dest="content_action")

    new_p = sub.add_parser("new", help="Create new content item")
    new_p.add_argument("content_id", type=str)
    new_p.add_argument("title", type=str)
    new_p.add_argument("--channel", type=str, default="blog")
    new_p.add_argument("--tags", nargs="*", default=[])

    stage_p = sub.add_parser("stage", help="Move content to new stage")
    stage_p.add_argument("content_id", type=str)
    stage_p.add_argument("new_stage", type=str)

    edit_p = sub.add_parser("edit", help="Edit content item fields")
    edit_p.add_argument("content_id", type=str)
    edit_p.add_argument("--title", type=str, default=None)
    edit_p.add_argument("--channel", type=str, default=None)
    edit_p.add_argument("--tags", nargs="*", default=None)

    attach_p = sub.add_parser("attach", help="Attach file to content item")
    attach_p.add_argument("content_id", type=str)
    attach_p.add_argument("path", type=str)
    attach_p.add_argument("--mime", type=str, default="application/octet-stream")

    sub.add_parser("export", help="Export content items as YAML")

    sub.add_parser("list", help="List content items")

    show_p = sub.add_parser("show", help="Show content details")
    show_p.add_argument("content_id", type=str)

    parser.set_defaults(func=cmd_content)


def cmd_content(args: argparse.Namespace, config: EMSConfig) -> int:
    pipeline = ContentPipeline(config.paths.state_dir / "content")

    try:
        if args.content_action == "new":
            item = pipeline.new(args.content_id, args.title, args.channel, args.tags)
            print(f"Created: {item['content_id']} [{item['stage']}] {item['title']}")
        elif args.content_action == "stage":
            item = pipeline.stage(args.content_id, args.new_stage)
            print(f"Staged: {item['content_id']} -> {item['stage']}")
        elif args.content_action == "edit":
            item = pipeline.edit(args.content_id, args.title, args.channel, args.tags)
            print(f"Updated: {item['content_id']} [{item['stage']}] {item['title']}")
        elif args.content_action == "attach":
            source = Path(args.path)
            try:
                data = source.read_bytes()
            except FileNotFoundError:
                print(f"Error: File not found: {args.path}", file=sys.stderr)
                return 1
            hash_val = sha256_bytes(data)
            item = pipeline.attach(args.content_id, args.path, hash_val, args.mime)
            n = len(item["attachments"])
            print(f"Attached: {source.name} to {item['content_id']} ({n} total)")
        elif args.content_action == "export":
            items = pipeline.list_items()
            print(yaml.dump({"items": items}, default_flow_style=False))
        elif args.content_action == "list":
            items = pipeline.list_items()
            for i in items:
                print(f"  [{i['stage']:10s}] {i['content_id']}: {i['title']}")
        elif args.content_action == "show":
            item = pipeline.show(args.content_id)
            for k, v in item.items():
                print(f"  {k}: {v}")
        else:
            print(
                "Usage: ssidctl content {new|stage|edit|attach|export|list|show}",
                file=sys.stderr,
            )
            return 1
    except ContentError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
