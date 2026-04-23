"""ssidctl memory — Memory Vault commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.modules.memory import MemoryError, MemoryVault


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("memory", help="Memory Vault")
    sub = parser.add_subparsers(dest="memory_action")

    add_p = sub.add_parser("add", help="Add a document")
    add_p.add_argument("title", type=str)
    add_p.add_argument("--tags", nargs="*", default=[])
    add_p.add_argument("--file", type=str, help="Read content from file")

    sub.add_parser("list", help="List documents")

    show_p = sub.add_parser("show", help="Show document")
    show_p.add_argument("doc_id", type=str)

    search_p = sub.add_parser("search", help="Search documents")
    search_p.add_argument("query", type=str)

    parser.set_defaults(func=cmd_memory)


def cmd_memory(args: argparse.Namespace, config: EMSConfig) -> int:
    vault = MemoryVault(config.paths.state_dir / "memory")

    try:
        if args.memory_action == "add":
            content = ""
            if hasattr(args, "file") and args.file:
                from pathlib import Path

                content = Path(args.file).read_text(encoding="utf-8")
            entry = vault.add(args.title, content, args.tags)
            print(f"Added: {entry['doc_id']} {entry['title']}")
        elif args.memory_action == "list":
            docs = vault.list_docs()
            for d in docs:
                tags = ", ".join(d.get("tags", []))
                print(f"  {d['doc_id']}: {d['title']} [{tags}]")
        elif args.memory_action == "show":
            doc = vault.show(args.doc_id)
            print(f"Title: {doc['title']}")
            print(f"Tags: {doc.get('tags', [])}")
            print(f"Hash: {doc.get('hash', '?')}")
            if "content" in doc:
                print(f"\n{doc['content']}")
        elif args.memory_action == "search":
            results = vault.search(args.query)
            for r in results:
                print(f"  {r['doc_id']}: {r['title']}")
        else:
            print("Usage: ssidctl memory {add|list|show|search}", file=sys.stderr)
            return 1
    except MemoryError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
