"""Durable workflow execution engine.

Orchestrates step-by-step execution of registered workflows with:
- Workflow-level idempotency (duplicate execute calls return the existing run)
- Per-step retry with configurable policy
- Checkpoint journaling for crash-recovery replay
- Approval gates (BLOCKED state) with resume support
- Cancel and replay (verify-only) operations

Concurrency: single-flight (concurrency=1). No threading or async.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from ssidctl.core.timeutil import utcnow_iso
from ssidctl.workflow.idempotency import compute_idempotency_key, compute_input_hash
from ssidctl.workflow.models import (
    Checkpoint,
    Step,
    StepStatus,
    WorkflowRun,
    WorkflowStatus,
)
from ssidctl.workflow.registry import WorkflowDefinition, get_workflow
from ssidctl.workflow.retry import RetryPolicy

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class EngineError(Exception):
    """Raised when the engine encounters an unrecoverable error."""


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class WorkflowEngine:
    """Durable workflow execution engine.

    Args:
        store: A WorkflowStore instance providing persistence for runs,
            checkpoints, and idempotency keys.
    """

    def __init__(self, store: Any) -> None:
        self.store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        workflow_name: str,
        event_fingerprint: str,
        policy_version: str,
        input_data: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        """Execute a registered workflow.

        Checks workflow-level idempotency first. If the same workflow has
        already been triggered for the given event/policy combination, the
        existing run is returned without re-execution.

        Args:
            workflow_name: Name of the registered workflow definition.
            event_fingerprint: SHA-256 fingerprint of the triggering event.
            policy_version: Version of the governing policy.
            input_data: Optional input data dict passed to step functions.

        Returns:
            The WorkflowRun (either newly created or the existing idempotent one).
        """
        idem_key = compute_idempotency_key(
            workflow_name, event_fingerprint, policy_version, "__workflow__"
        )

        if self.store.has_idempotency_key(idem_key):
            entry = self.store.get_idempotency_entry(idem_key)
            existing = self.store.load_run(entry["run_id"])
            if existing is not None:
                return existing

        definition = get_workflow(workflow_name)

        run_id = f"WF-{uuid.uuid4().hex[:12]}"
        run = WorkflowRun(
            run_id=run_id,
            workflow_name=workflow_name,
            workflow_version=definition.version,
            status=WorkflowStatus.PENDING,
            event_fingerprint=event_fingerprint,
            policy_version=policy_version,
        )

        if input_data is None:
            input_data = {}

        input_hash = compute_input_hash(input_data)

        for idx, step_def in enumerate(definition.steps):
            step_idem = compute_idempotency_key(
                workflow_name, event_fingerprint, policy_version, step_def.step_type
            )
            step = Step(
                step_type=step_def.step_type,
                step_index=idx,
                input_hash=input_hash,
                idempotency_key=step_idem,
                max_attempts=step_def.max_attempts,
                retryable=step_def.retryable,
            )
            run.steps.append(step)

        self.store.save_run(run)
        self.store.record_idempotency_key(idem_key, run_id, "__workflow__")

        run._input_data = input_data  # type: ignore[attr-defined]
        return self._run_steps(run, definition)

    def resume(self, run_id: str) -> WorkflowRun:
        """Resume a previously failed or blocked workflow run.

        Args:
            run_id: The run identifier to resume.

        Returns:
            The resumed WorkflowRun after execution continues.

        Raises:
            EngineError: If the run is not found or is cancelled.
        """
        run = self.store.load_run(run_id)
        if run is None:
            raise EngineError(f"Run '{run_id}' not found")

        if run.status == WorkflowStatus.COMPLETED:
            return run

        if run.status == WorkflowStatus.CANCELLED:
            raise EngineError(f"Run '{run_id}' is cancelled and cannot be resumed")

        definition = get_workflow(run.workflow_name)
        checkpoints = self.store.load_checkpoints(run_id)

        completed_indices: set[int] = set()
        for cp in checkpoints:
            if cp.status == StepStatus.COMPLETED:
                completed_indices.add(cp.step_index)

        # Handle BLOCKED (approval gate) resume: mark the approval step as
        # COMPLETED and advance past it.
        was_blocked = run.status == WorkflowStatus.BLOCKED

        # Find first non-completed step
        first_pending = 0
        for idx in range(len(run.steps)):
            if idx not in completed_indices:
                first_pending = idx
                break
        else:
            first_pending = len(run.steps)

        if was_blocked and first_pending < len(run.steps):
            step = run.steps[first_pending]
            step_def = definition.steps[first_pending]
            if step_def.requires_approval:
                step.status = StepStatus.COMPLETED
                step.finished_at = utcnow_iso()
                self.store.save_checkpoint(
                    Checkpoint(
                        run_id=run_id,
                        step_id=step.step_id,
                        step_index=step.step_index,
                        status=StepStatus.COMPLETED,
                    )
                )
                completed_indices.add(first_pending)
                first_pending += 1

        run.current_step_index = first_pending

        # Reset the step at current_step_index to PENDING if it was FAILED
        # Also reset attempt counter so the step gets fresh retry budget.
        if first_pending < len(run.steps):
            step = run.steps[first_pending]
            if step.status == StepStatus.FAILED:
                step.status = StepStatus.PENDING
                step.attempt = 0
                step.error = None

        run._input_data = {}  # type: ignore[attr-defined]
        self.store.save_run(run)
        return self._run_steps(run, definition)

    def replay(self, run_id: str) -> WorkflowRun:
        """Verify-only replay of a workflow run. No side effects.

        Loads the run and its checkpoints and verifies consistency.
        Does NOT call any step functions.

        Args:
            run_id: The run identifier to replay.

        Returns:
            The WorkflowRun as loaded from the store.

        Raises:
            EngineError: If the run is not found or checkpoints are inconsistent.
        """
        run = self.store.load_run(run_id)
        if run is None:
            raise EngineError(f"Run '{run_id}' not found")

        checkpoints = self.store.load_checkpoints(run_id)

        # Verify checkpoint consistency: each checkpoint's step_id must match
        # the corresponding step in the run.
        for cp in checkpoints:
            if cp.step_index < len(run.steps):
                step = run.steps[cp.step_index]
                if cp.step_id != step.step_id:
                    raise EngineError(
                        f"Checkpoint inconsistency at step_index {cp.step_index}: "
                        f"checkpoint step_id={cp.step_id} != run step_id={step.step_id}"
                    )

        return run

    def cancel(self, run_id: str) -> WorkflowRun:
        """Cancel a workflow run.

        Args:
            run_id: The run identifier to cancel.

        Returns:
            The cancelled WorkflowRun.

        Raises:
            EngineError: If the run is not found.
        """
        run = self.store.load_run(run_id)
        if run is None:
            raise EngineError(f"Run '{run_id}' not found")

        run.transition_to(WorkflowStatus.CANCELLED)
        run.finished_at = utcnow_iso()
        self.store.save_run(run)
        return run

    def get_run(self, run_id: str) -> WorkflowRun | None:
        """Return a single run by ID, or None if not found."""
        return self.store.load_run(run_id)

    def list_runs(self) -> list[WorkflowRun]:
        """Return all runs from the store."""
        return self.store.list_runs()

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _run_steps(self, run: WorkflowRun, definition: WorkflowDefinition) -> WorkflowRun:
        """Execute steps sequentially from current_step_index.

        Transitions the run to RUNNING, then iterates through steps.
        Stops on failure, approval gate (BLOCKED), or completion.
        """
        run.transition_to(WorkflowStatus.RUNNING)
        run.started_at = run.started_at or utcnow_iso()
        self.store.save_run(run)

        input_data: dict[str, Any] = getattr(run, "_input_data", {})

        for idx in range(run.current_step_index, len(run.steps)):
            step = run.steps[idx]
            step_def = definition.steps[idx]
            run.current_step_index = idx

            # Skip already completed steps
            if step.status == StepStatus.COMPLETED:
                continue

            # Approval gate: block execution
            if step_def.requires_approval:
                run.transition_to(WorkflowStatus.BLOCKED)
                self.store.save_run(run)
                return run

            # Execute the step
            success = self._execute_step(run, step, step_def, input_data)
            if not success:
                run.transition_to(WorkflowStatus.FAILED)
                run.error = step.error
                run.finished_at = utcnow_iso()
                self.store.save_run(run)
                return run

        # All steps completed
        run.transition_to(WorkflowStatus.COMPLETED)
        run.finished_at = utcnow_iso()
        self.store.save_run(run)
        return run

    def _execute_step(
        self,
        run: WorkflowRun,
        step: Step,
        step_def: Any,
        input_data: dict[str, Any],
    ) -> bool:
        """Execute a single step with retry logic.

        Returns True on success, False on permanent failure.
        """
        retry_policy = RetryPolicy(
            max_attempts=step.max_attempts,
        )

        context = {
            "run_id": run.run_id,
            "step_index": step.step_index,
            **input_data,
        }

        while retry_policy.should_retry(step.attempt):
            # Transition to RUNNING
            if step.status == StepStatus.PENDING or step.status == StepStatus.FAILED:
                step.transition_to(StepStatus.RUNNING)

            step.attempt += 1
            step.started_at = utcnow_iso()
            self.store.save_run(run)

            try:
                result = step_def.function(context)
                # Success
                step.transition_to(StepStatus.COMPLETED)
                step.finished_at = utcnow_iso()

                # Compute output hash
                if result is not None:
                    output_json = json.dumps(result, sort_keys=True, separators=(",", ":"))
                    from ssidctl.core.hashing import sha256_str

                    step.output_hash = sha256_str(output_json)

                self.store.save_checkpoint(
                    Checkpoint(
                        run_id=run.run_id,
                        step_id=step.step_id,
                        step_index=step.step_index,
                        status=StepStatus.COMPLETED,
                        output_hash=step.output_hash,
                    )
                )
                self.store.save_run(run)
                return True

            except Exception as exc:
                step.error = str(exc)

                # Check if we can retry
                if step.retryable and retry_policy.should_retry(step.attempt):
                    step.transition_to(StepStatus.FAILED)
                    self.store.save_run(run)
                    # In a real engine we'd sleep here; in this sync engine we
                    # loop immediately.
                    continue
                else:
                    step.transition_to(StepStatus.FAILED)
                    step.finished_at = utcnow_iso()
                    self.store.save_checkpoint(
                        Checkpoint(
                            run_id=run.run_id,
                            step_id=step.step_id,
                            step_index=step.step_index,
                            status=StepStatus.FAILED,
                        )
                    )
                    self.store.save_run(run)
                    return False

        # Exhausted retries without success
        step.finished_at = utcnow_iso()
        self.store.save_checkpoint(
            Checkpoint(
                run_id=run.run_id,
                step_id=step.step_id,
                step_index=step.step_index,
                status=StepStatus.FAILED,
            )
        )
        self.store.save_run(run)
        return False
