"""Cloud WORM CLI command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ssidctl.modules.cloud_worm import CloudWORM, LocalBackend


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("cloud-worm", help="Cloud WORM evidence storage")
    sub = p.add_subparsers(dest="cloud_worm_action")
    push_p = sub.add_parser("push")
    push_p.add_argument("run_id")
    push_p.add_argument("file_path")
    ver_p = sub.add_parser("verify")
    ver_p.add_argument("run_id")
    ver_p.add_argument("filename")
    sub.add_parser("list")
    p.set_defaults(func=cmd_cloud_worm)


def cmd_cloud_worm(args, config) -> int:
    backend = LocalBackend(config.paths.state_dir / "cloud_worm")
    cw = CloudWORM(backend=backend)
    action = args.cloud_worm_action
    if action == "push":
        result = cw.push(args.run_id, Path(args.file_path))
        print(f"Pushed: {result['file']} ({result['hash']})")
    elif action == "verify":
        ok = cw.verify(args.run_id, args.filename)
        print(f"Verify: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    elif action == "list":
        for run_id in cw.list_runs():
            print(f"  {run_id}")
    else:
        print("Usage: ssidctl cloud-worm {push|verify|list}")
        return 1
    return 0
