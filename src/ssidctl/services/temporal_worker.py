"""Temporal Workflow Orchestrator — durable workflow scaffold.

Provides durable, retryable workflow execution for EMS operations.
Replaces stateless CLI invocation with persistent workflow state.
Requires: temporalio (optional dependency).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from temporalio import activity, workflow  # noqa: F401
    from temporalio.client import Client
    from temporalio.worker import Worker

    _HAS_TEMPORAL = True
except ImportError:
    _HAS_TEMPORAL = False


class TemporalError(Exception):
    pass


def _require_temporal() -> None:
    if not _HAS_TEMPORAL:
        raise TemporalError("temporalio not installed. Install with: pip install temporalio")


@dataclass
class WorkflowConfig:
    """Temporal connection and worker configuration."""

    task_queue: str = "ssid-ems-queue"
    namespace: str = "default"
    host: str = "localhost:7233"


@dataclass
class RunInput:
    """Input for an EMS run workflow."""

    run_id: str
    task_id: str
    repo_path: str
    base_sha: str
    scope: dict[str, Any] = field(default_factory=dict)


# --- Activities (stubs for CLI integration) ---


def run_gate_chain(run_input: dict[str, Any]) -> dict[str, Any]:
    """Execute the full gate chain for a run."""
    return {
        "status": "completed",
        "run_id": run_input["run_id"],
        "gates_passed": True,
    }


def create_evidence(run_input: dict[str, Any]) -> dict[str, Any]:
    """Create and seal evidence for a run."""
    return {
        "status": "created",
        "run_id": run_input["run_id"],
        "evidence_hash": "sha256:pending",
    }


def create_pr(run_input: dict[str, Any]) -> dict[str, Any]:
    """Create a pull request from the apply worktree."""
    return {
        "status": "created",
        "run_id": run_input["run_id"],
        "pr_number": None,
    }


def seal_evidence(run_input: dict[str, Any]) -> dict[str, Any]:
    """Seal evidence store (WORM)."""
    return {
        "status": "sealed",
        "run_id": run_input["run_id"],
    }


# --- Workflow Definition ---


@dataclass
class EMSRunWorkflow:
    """Durable EMS Run workflow: plan → approve → apply → verify → seal.

    When Temporal is available, this is registered as a Temporal workflow.
    Without Temporal, it executes synchronously as a fallback.
    """

    def execute(self, run_input: dict[str, Any]) -> dict[str, Any]:
        """Execute the full lifecycle synchronously (CLI fallback)."""
        results: dict[str, Any] = {"run_id": run_input.get("run_id", "unknown")}

        # Step 1: Gate chain
        gate_result = run_gate_chain(run_input)
        results["gates"] = gate_result
        if not gate_result.get("gates_passed"):
            results["status"] = "FAILED"
            return results

        # Step 2: Evidence creation
        evidence_result = create_evidence(run_input)
        results["evidence"] = evidence_result

        # Step 3: PR creation
        pr_result = create_pr(run_input)
        results["pr"] = pr_result

        # Step 4: Seal
        seal_result = seal_evidence(run_input)
        results["seal"] = seal_result

        results["status"] = "DONE"
        return results


async def create_worker(config: WorkflowConfig) -> Any:
    """Create and return a Temporal worker (requires temporalio)."""
    _require_temporal()
    client = await Client.connect(config.host, namespace=config.namespace)
    worker = Worker(
        client,
        task_queue=config.task_queue,
        activities=[run_gate_chain, create_evidence, create_pr, seal_evidence],
    )
    return worker
