"""ssidctl vault — Attachment Vault commands."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ssidctl.config import EMSConfig
from ssidctl.modules.vault import AttachmentVault, VaultError


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("vault", help="Attachment Vault")
    sub = parser.add_subparsers(dest="vault_action")

    add_p = sub.add_parser("add", help="Add an asset")
    add_p.add_argument("source", type=str, help="Path to source file")
    add_p.add_argument("--category", type=str, default="attachments")
    add_p.add_argument("--mime", type=str, default="application/octet-stream")

    sub.add_parser("list", help="List assets")

    retrieve_p = sub.add_parser("retrieve", help="Retrieve an asset by ID")
    retrieve_p.add_argument("asset_id", type=str, help="Asset ID (V-xxxxxxxx)")
    retrieve_p.add_argument(
        "--dest",
        type=str,
        default=None,
        help="Destination path (default: current dir)",
    )

    link_p = sub.add_parser("link", help="Link asset to task/run")
    link_p.add_argument("asset_id", type=str, help="Asset ID (V-xxxxxxxx)")
    link_p.add_argument("--task", default=None, help="Task ID to link")
    link_p.add_argument("--run", default=None, help="Run ID to link")

    parser.set_defaults(func=cmd_vault)


def cmd_vault(args: argparse.Namespace, config: EMSConfig) -> int:
    vault = AttachmentVault(config.paths.vault_dir)

    try:
        if args.vault_action == "add":
            entry = vault.add(Path(args.source), args.category, args.mime)
            print(f"Added: {entry['asset_id']} {entry['original_name']} ({entry['hash']})")
        elif args.vault_action == "list":
            assets = vault.list_assets()
            for a in assets:
                print(f"  {a['asset_id']}: {a['original_name']} ({a['mime']}, {a['size_bytes']}B)")
        elif args.vault_action == "retrieve":
            file_path, meta = vault.retrieve(args.asset_id)
            dest = Path(args.dest) if args.dest else Path.cwd() / meta["original_name"]
            shutil.copy2(str(file_path), str(dest))
            print(f"Retrieved: {meta['asset_id']} -> {dest}")
            print(f"  Hash: {meta['hash']}")
        elif args.vault_action == "link":
            link = vault.link(args.asset_id, task_id=args.task, run_id=args.run)
            print(
                f"Linked: {link['asset_id']}"
                f" task={link.get('task_id', '-')}"
                f" run={link.get('run_id', '-')}"
            )
        else:
            print("Usage: ssidctl vault {add|list|retrieve|link}", file=sys.stderr)
            return 1
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
