"""ssidctl drift-sentinel — integrity, leakage, and docs-source checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ssidctl.config import EMSConfig


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "drift-sentinel",
        help="Integrity, leakage, and docs-source drift checks",
    )
    sub = parser.add_subparsers(dest="drift_sentinel_action")

    run_p = sub.add_parser("run", help="Run all drift sentinel checks")
    run_p.add_argument(
        "--open-core",
        type=Path,
        default=None,
        help="Path to SSID-open-core repo (default: from config)",
    )
    run_p.add_argument(
        "--docs",
        type=Path,
        default=None,
        help="Path to SSID-docs repo (default: from config)",
    )
    run_p.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="State directory for reports (default: from config)",
    )
    run_p.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Evidence directory for hash-only record (default: from config)",
    )
    run_p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output report as JSON",
    )

    parser.set_defaults(func=cmd_drift_sentinel)


def cmd_drift_sentinel(args: argparse.Namespace, config: EMSConfig) -> int:
    if args.drift_sentinel_action != "run":
        print(
            "Usage: ssidctl drift-sentinel run [--open-core PATH] [--docs PATH]", file=sys.stderr
        )
        return 1

    from ssidctl.modules.drift_sentinel import (
        run_sentinel,
        write_evidence,
        write_report,
    )

    # Resolve paths from args or config
    # Resolve paths: CLI args > sibling-directory convention > config
    open_core = args.open_core or (config.paths.ssid_repo.parent / "SSID-open-core")
    docs = args.docs or (config.paths.ssid_repo.parent / "SSID-docs")
    state_dir = args.state_dir or config.paths.state_dir
    evidence_dir = args.evidence_dir or config.paths.evidence_dir

    if not open_core or not open_core.exists():
        print(f"Error: open-core directory not found: {open_core}", file=sys.stderr)
        return 3

    docs_path = docs if docs and docs.exists() else None

    try:
        report = run_sentinel(open_core, docs=docs_path)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3

    # Write report to state dir
    if state_dir and state_dir.exists():
        report_path = write_report(report, state_dir)
        if not args.json_output:
            print(f"Report:   {report_path}")

    # Write evidence (hash-only)
    if evidence_dir and evidence_dir.exists():
        content_hash = write_evidence(report, evidence_dir)
        if not args.json_output:
            print(f"Evidence: {evidence_dir / 'index.jsonl'}")
            print(f"Hash:     {content_hash}")

    if args.json_output:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Verdict:  {report.verdict}")
        print(f"Checks:   {report.checks_passed}/{report.checks_run} passed")
        if report.findings:
            print(f"Findings: {len(report.findings)}")
            for f in report.findings:
                print(f"  [{f.severity}] {f.check}: {f.path} — {f.detail}")

    # Exit codes: 0=PASS, 2=FAIL
    return 0 if report.verdict == "PASS" else 2
