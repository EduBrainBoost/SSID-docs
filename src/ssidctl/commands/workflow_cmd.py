"""ssidctl workflow — Durable Workflow Engine commands."""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from datetime import UTC, datetime

from ssidctl.config import EMSConfig


def _utcnow_iso() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("workflow", help="Durable workflow engine")
    sub = parser.add_subparsers(dest="workflow_action")

    # workflow run
    run_p = sub.add_parser("run", help="Start a new workflow run")
    run_p.add_argument("workflow_name", type=str, help="Workflow definition name")
    run_p.add_argument(
        "--event-fp",
        dest="event_fp",
        type=str,
        default=None,
        help="Event fingerprint (default: manual-<utcnow>)",
    )
    run_p.add_argument(
        "--policy-version",
        dest="policy_version",
        type=str,
        default=None,
        help="Policy version to enforce (e.g. 1.0.0)",
    )
    run_p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output result as JSON",
    )

    # workflow resume
    resume_p = sub.add_parser("resume", help="Resume a paused workflow run")
    resume_p.add_argument("run_id", type=str, help="Workflow run ID")
    resume_p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output result as JSON",
    )

    # workflow status
    status_p = sub.add_parser("status", help="Show workflow run status")
    status_p.add_argument("run_id", type=str, help="Workflow run ID")

    # workflow cancel
    cancel_p = sub.add_parser("cancel", help="Cancel a workflow run")
    cancel_p.add_argument("run_id", type=str, help="Workflow run ID")

    # workflow list
    sub.add_parser("list", help="List all workflow runs")

    parser.set_defaults(func=cmd_workflow)


def cmd_workflow(args: argparse.Namespace, config: EMSConfig) -> int:
    from ssidctl.workflow.definitions.drift_sentinel_v1 import build_drift_sentinel_workflow
    from ssidctl.workflow.engine import EngineError, WorkflowEngine
    from ssidctl.workflow.store import WorkflowStore

    store = WorkflowStore(config.paths.state_dir / "workflows")
    engine = WorkflowEngine(store)

    # Register drift_sentinel_v1 (idempotent)
    with contextlib.suppress(Exception):
        engine.register(build_drift_sentinel_workflow())  # type: ignore[attr-defined]
    action = getattr(args, "workflow_action", None)

    if action == "run":
        workflow_name = args.workflow_name
        event_fp = args.event_fp or f"manual-{_utcnow_iso()}"
        policy_version = getattr(args, "policy_version", None)
        json_output = getattr(args, "json_output", False)

        input_data: dict = {}
        if workflow_name == "drift_sentinel_v1":
            open_core = config.paths.ssid_repo.parent / "SSID-open-core"
            docs_candidate = config.paths.ssid_repo.parent / "SSID-docs"
            input_data["open_core_path"] = str(open_core)
            if docs_candidate.exists():
                input_data["docs_path"] = str(docs_candidate)

        if policy_version is not None:
            input_data["policy_version"] = policy_version

        try:
            result = engine.run(  # type: ignore[attr-defined]
                workflow_name=workflow_name,
                event_fp=event_fp,
                input_data=input_data,
            )
        except EngineError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if json_output:
            print(
                json.dumps(
                    result if isinstance(result, dict) else vars(result), indent=2, default=str
                )
            )  # noqa: E501
        else:
            if isinstance(result, dict):
                run_id = result.get("run_id", "?")
                status = result.get("status", "?")
                verdict = result.get("verdict", result.get("result", ""))
            else:
                run_id = getattr(result, "run_id", "?")
                status = getattr(result, "status", "?")
                verdict = getattr(result, "verdict", getattr(result, "result", ""))
            print(f"Run ID:  {run_id}")
            print(f"Status:  {status}")
            if verdict:
                print(f"Verdict: {verdict}")
        return 0

    elif action == "resume":
        run_id = args.run_id
        json_output = getattr(args, "json_output", False)

        try:
            result = engine.resume(run_id)
        except EngineError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if json_output:
            print(
                json.dumps(
                    result if isinstance(result, dict) else vars(result), indent=2, default=str
                )
            )  # noqa: E501
        else:
            if isinstance(result, dict):
                status = result.get("status", "?")
                verdict = result.get("verdict", result.get("result", ""))
            else:
                status = getattr(result, "status", "?")
                verdict = getattr(result, "verdict", getattr(result, "result", ""))
            print(f"Run ID:  {run_id}")
            print(f"Status:  {status}")
            if verdict:
                print(f"Verdict: {verdict}")
        return 0

    elif action == "status":
        run_id = args.run_id
        try:
            info = engine.status(run_id)  # type: ignore[attr-defined]
        except EngineError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if isinstance(info, dict):
            for key, val in info.items():
                print(f"{key}: {val}")
        else:
            print(str(info))
        return 0

    elif action == "cancel":
        run_id = args.run_id
        try:
            engine.cancel(run_id)
        except EngineError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(f"Cancelled: {run_id}")
        return 0

    elif action == "list":
        try:
            runs = engine.list_runs()
        except EngineError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if not runs:
            print("No workflow runs found.")
            return 0
        for r in runs:
            if isinstance(r, dict):
                run_id = r.get("run_id", "?")
                wf = r.get("workflow_name", "?")
                status = r.get("status", "?")
                ts = r.get("started_at", r.get("timestamp", "?"))
            else:
                run_id = getattr(r, "run_id", "?")
                wf = getattr(r, "workflow_name", "?")
                status = getattr(r, "status", "?")
                ts = getattr(r, "started_at", getattr(r, "timestamp", "?"))
            print(f"  {run_id}: workflow={wf} status={status} at={ts}")
        return 0

    else:
        print("Usage: ssidctl workflow {run|resume|status|cancel|list}", file=sys.stderr)
        return 1
