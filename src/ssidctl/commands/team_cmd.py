"""ssidctl team — Team Registry + Team Hook commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.core.team_hooks import check_findings_complete, validate_output_contract
from ssidctl.modules.team import TeamError, TeamRegistry


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("team", help="Team Registry + Hooks")
    sub = parser.add_subparsers(dest="team_action")

    sub.add_parser("list", help="List all agents")

    show_p = sub.add_parser("show", help="Show agent details")
    show_p.add_argument("name", type=str)

    status_p = sub.add_parser("set-status", help="Set agent availability")
    status_p.add_argument("name", type=str)
    status_p.add_argument("availability", type=str, choices=["IDLE", "RUNNING", "BLOCKED"])

    # Team hook subcommands (for Claude Code TeammateIdle/TaskCompleted hooks)
    cfc_p = sub.add_parser("check-findings-complete", help="Validate output sections")
    cfc_p.add_argument(
        "--agent-type",
        type=str,
        default="unknown",
        choices=["planner", "scope", "security", "gate", "ops", "evidence", "pr", "unknown"],
    )

    sub.add_parser(
        "validate-output-contract", help="Validate PASS/FAIL contract (no scores/bundles)"
    )

    parser.set_defaults(func=cmd_team)


def cmd_team(args: argparse.Namespace, config: EMSConfig) -> int:
    action = args.team_action

    # Hook commands (read from stdin)
    if action == "check-findings-complete":
        output = sys.stdin.read()
        result = check_findings_complete(output, agent_type=args.agent_type)
        if result.passed:
            print("PASS: findings complete")
            return 0
        else:
            print(f"WARN: {result.reason}", file=sys.stderr)
            return 0  # Fail-open: hooks are supplementary

    elif action == "validate-output-contract":
        output = sys.stdin.read()
        result = validate_output_contract(output)
        if result.passed:
            print("PASS: output contract valid")
            return 0
        else:
            print(f"WARN: {result.reason}", file=sys.stderr)
            return 0  # Fail-open: hooks are supplementary

    # Registry commands
    registry = TeamRegistry(config.paths.state_dir / "team")

    try:
        if action == "list":
            agents = registry.list_agents()
            if not agents:
                print("No agents registered. Run team seed first.")
                return 0
            for a in agents:
                print(f"  [{a.get('availability', '?'):7s}] {a['name']:12s} {a['role']}")
        elif action == "show":
            agent = registry.show(args.name)
            for k, v in agent.items():
                print(f"  {k}: {v}")
        elif action == "set-status":
            agent = registry.set_status(args.name, args.availability)
            print(f"Updated: {agent['name']} -> {agent['availability']}")
        else:
            print(
                "Usage: ssidctl team "
                "{list|show|set-status|check-findings-complete|validate-output-contract}",
                file=sys.stderr,
            )
            return 1
    except TeamError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
