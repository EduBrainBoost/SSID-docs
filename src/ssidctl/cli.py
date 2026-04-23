"""ssidctl CLI — SSID External Management System."""

import argparse
import sys
from pathlib import Path

from ssidctl.config import ConfigError, load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ssidctl",
        description="SSID External Management System - Mission Control CLI",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to ems.yaml config file",
    )

    subparsers = parser.add_subparsers(dest="command")

    # Register all command modules
    from ssidctl.commands import (
        agents_cmd,
        approve_cmd,
        attest_cmd,
        autopilot_cmd,
        board_cmd,
        bootstrap_cmd,
        calendar_cmd,
        cloud_worm_cmd,
        content_cmd,
        doctor_cmd,
        drift_cmd,
        drift_sentinel_cmd,
        evidence_cmd,
        export_cmd,
        gates,
        guard_cmd,
        incident_cmd,
        lock_cmd,
        memory_cmd,
        notify_cmd,
        office_cmd,
        pr_cmd,
        public_export,
        public_status_cmd,
        quarantine_cmd,
        run_cmd,
        search_cmd,
        secret_patterns_cmd,
        serve,
        stack_cmd,
        team_cmd,
        triage_cmd,
        update_cmd,
        vault_cmd,
        webhook_cmd,
        worktree_cmd,
    )

    agents_cmd.register(subparsers)
    approve_cmd.register(subparsers)
    attest_cmd.register(subparsers)
    autopilot_cmd.register(subparsers)
    gates.register(subparsers)
    guard_cmd.register(subparsers)
    triage_cmd.register(subparsers)
    doctor_cmd.register(subparsers)
    board_cmd.register(subparsers)
    team_cmd.register(subparsers)
    content_cmd.register(subparsers)
    calendar_cmd.register(subparsers)
    memory_cmd.register(subparsers)
    vault_cmd.register(subparsers)
    search_cmd.register(subparsers)
    evidence_cmd.register(subparsers)
    incident_cmd.register(subparsers)
    lock_cmd.register(subparsers)
    drift_cmd.register(subparsers)
    drift_sentinel_cmd.register(subparsers)
    pr_cmd.register(subparsers)
    office_cmd.register(subparsers)
    bootstrap_cmd.register(subparsers)
    run_cmd.register(subparsers)
    quarantine_cmd.register(subparsers)
    notify_cmd.register(subparsers)
    webhook_cmd.register(subparsers)
    cloud_worm_cmd.register(subparsers)
    export_cmd.register(subparsers)
    worktree_cmd.register(subparsers)
    update_cmd.register(subparsers)
    secret_patterns_cmd.register(subparsers)
    serve.register(subparsers)
    stack_cmd.register(subparsers)
    public_export.register(subparsers)
    public_status_cmd.register(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Load config
    try:
        config = load_config(args.config, validate_paths=False)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    # Resolve caller identity and attach to args for command handlers
    from ssidctl.core.identity import IdentityResolveError, resolve_caller_from_config

    try:
        caller = resolve_caller_from_config(config)
    except IdentityResolveError as e:
        print(f"Identity error: {e}", file=sys.stderr)
        return 1
    args.caller = caller

    # Dispatch to command handler
    if hasattr(args, "func"):
        return args.func(args, config)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
