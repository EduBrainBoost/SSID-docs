"""ssidctl public-status — export sanitized Now/Next/Later status."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ssidctl.config import EMSConfig


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "public-status",
        help="Export sanitized Now/Next/Later public status",
    )
    sub = parser.add_subparsers(dest="public_status_action")

    export_p = sub.add_parser("export", help="Generate public_status.json")
    export_p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path for public_status.json (default: runs/public_status.json)",
    )
    export_p.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Evidence directory for hash-only record",
    )

    parser.set_defaults(func=cmd_public_status)


def cmd_public_status(args: argparse.Namespace, config: EMSConfig) -> int:
    if args.public_status_action != "export":
        print(
            "Usage: ssidctl public-status export [--out PATH] [--evidence-dir PATH]",
            file=sys.stderr,
        )
        return 1

    from ssidctl.modules.board import Board
    from ssidctl.modules.public_status import aggregate_board, write_public_status

    board = Board(config.paths.state_dir / "board")
    tasks = board.list_tasks()

    data = aggregate_board(tasks)

    # Determine output path
    out_path = args.out
    if out_path is None:
        out_path = config.paths.ems_repo / "runs" / "public_status.json"

    content_hash = write_public_status(data, out_path)

    print(f"Generated: {out_path}")
    print(f"Tasks:     {sum(data['counts'].values())}")
    print(
        f"Counts:    now={data['counts']['now']} next={data['counts']['next']} "
        f"later={data['counts']['later']} done={data['counts']['done']}"
    )
    print(f"Hash:      {content_hash}")

    # Write evidence (hash-only)
    evidence_dir = args.evidence_dir
    if evidence_dir is None:
        evidence_dir = config.paths.evidence_dir
    if evidence_dir and evidence_dir.exists():
        _write_evidence(evidence_dir, content_hash, data["counts"])

    return 0


def _write_evidence(evidence_dir: Path, content_hash: str, counts: dict) -> None:
    """Append hash-only evidence record."""
    from ssidctl.core.event_log import EventLog

    log = EventLog(evidence_dir / "index.jsonl")
    log.append(
        "public_status.exported",
        {
            "content_hash": content_hash,
            "counts": counts,
        },
        "ssidctl",
    )
    print(f"Evidence:  {evidence_dir / 'index.jsonl'}")
