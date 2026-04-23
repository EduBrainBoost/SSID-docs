"""ssidctl autopilot — self-healing feedback loop CLI.

Subcommands:
    run     Execute autopilot loop with bounded iterations
    status  Show details of a specific run
    list    List all autopilot runs
"""

from __future__ import annotations

import argparse
import json
import sys

from ssidctl.config import EMSConfig


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = subparsers.add_parser(
        "autopilot",
        help="Self-healing feedback loop for SSID",
    )
    sub = parser.add_subparsers(dest="autopilot_action")

    # --- run ---
    run_p = sub.add_parser("run", help="Start an autopilot run")
    run_p.add_argument("--task-id", type=str, default="", help="Task ID for the run")
    run_p.add_argument(
        "--max-iter",
        type=int,
        default=5,
        help="Maximum iterations (default: 5)",
    )
    run_p.add_argument(
        "--run-id",
        type=str,
        default="",
        help="Run ID (auto-generated if empty)",
    )

    # --- status ---
    status_p = sub.add_parser("status", help="Show details of a run")
    status_p.add_argument("run_id", help="Run ID to show")

    # --- list ---
    sub.add_parser("list", help="List all autopilot runs")

    parser.set_defaults(func=cmd_autopilot)


def cmd_autopilot(args: argparse.Namespace, config: EMSConfig) -> int:
    action = getattr(args, "autopilot_action", None)

    if action == "run":
        return _cmd_run(args, config)
    elif action == "status":
        return _cmd_status(args, config)
    elif action == "list":
        return _cmd_list(config)
    else:
        print("Usage: ssidctl autopilot {run|status|list}", file=sys.stderr)
        return 1


def _cmd_run(args: argparse.Namespace, config: EMSConfig) -> int:
    from ssidctl.autopilot.board_sync import BoardSyncAdapter
    from ssidctl.autopilot.loop import AutopilotConfig, AutopilotLoop
    from ssidctl.core.authz import AuthzError, Permission
    from ssidctl.core.timeutil import utcnow_iso
    from ssidctl.modules.board import Board

    # RBAC gate: autopilot run requires LIFECYCLE_TRANSITION (OWNER or ADMIN)
    caller = getattr(args, "caller", None)
    if caller is not None:
        try:
            caller.require(Permission.LIFECYCLE_TRANSITION)
        except AuthzError:
            print(
                f"Access denied: user '{caller.username}' (role={caller.role.value}) "
                f"lacks permission '{Permission.LIFECYCLE_TRANSITION.value}' "
                f"required for 'autopilot run'.",
                file=sys.stderr,
            )
            return 1
        print(f"  Caller: {caller.username} (role={caller.role.value})")

    run_id = args.run_id or utcnow_iso().replace(":", "").replace("-", "")

    # Load limits from policy
    limits_path = config.paths.ems_repo / "policies" / "autopilot_limits.yaml"
    if limits_path.exists():
        ap_config = AutopilotConfig.from_yaml(limits_path)
    else:
        ap_config = AutopilotConfig()

    ap_config.task_id = args.task_id
    ap_config.max_iterations = args.max_iter

    # Create BoardSyncAdapter if task_id is provided
    board_sync = None
    if args.task_id:
        board = Board(config.paths.state_dir / "board")
        board_sync = BoardSyncAdapter(
            board=board,
            task_id=args.task_id,
            run_id=run_id,
            event_log_path=config.paths.state_dir / "runs" / run_id / "board_sync.jsonl",
            lifecycle_state_path=config.paths.state_dir / "runs" / run_id / "lifecycle_state.json",
        )

    loop = AutopilotLoop(
        ssid_repo=config.paths.ssid_repo,
        ems_repo=config.paths.ems_repo,
        state_dir=config.paths.state_dir,
        evidence_dir=config.paths.evidence_dir,
        config=ap_config,
        board_sync=board_sync,
    )

    print(f"Starting autopilot run: {run_id}")
    print(f"  Max iterations: {ap_config.max_iterations}")
    print(f"  Task ID: {ap_config.task_id or '(none)'}")
    print()

    result = loop.run(run_id)

    print(f"Result: {result.result}")
    print(f"Iterations: {result.iterations}")
    if result.handoff_path:
        print(f"Handoff: {result.handoff_path}")
    if result.error:
        print(f"Error: {result.error}", file=sys.stderr)

    return 0 if result.result == "PASS" else 1


def _cmd_status(args: argparse.Namespace, config: EMSConfig) -> int:
    run_dir = config.paths.state_dir / "runs" / args.run_id
    if not run_dir.exists():
        print(f"Run not found: {args.run_id}", file=sys.stderr)
        return 1

    # Read handoff if exists
    handoff = run_dir / "handoff.md"
    if handoff.exists():
        print(handoff.read_text(encoding="utf-8"))
    else:
        print(f"Run {args.run_id}: no handoff report yet")

    # Show convergence
    conv = run_dir / "convergence.json"
    if conv.exists():
        data = json.loads(conv.read_text(encoding="utf-8"))
        summary = data.get("summary", {})
        print(f"\nConvergence: {summary.get('verdict', '?')}")
        print(f"Trend: {summary.get('findings_trend', [])}")

    return 0


def _cmd_list(config: EMSConfig) -> int:
    runs_dir = config.paths.state_dir / "runs"
    if not runs_dir.exists():
        print("No runs found.")
        return 0

    found = False
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        handoff = run_dir / "handoff.md"
        status = "complete" if handoff.exists() else "in-progress"
        print(f"  {run_dir.name}  [{status}]")
        found = True

    if not found:
        print("No runs found.")

    return 0
