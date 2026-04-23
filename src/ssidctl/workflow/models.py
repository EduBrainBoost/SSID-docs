"""Durable workflow execution models.

Defines the core data structures for the SSID-EMS durable workflow engine:
- WorkflowStatus: top-level run FSM with explicit transition map
- StepStatus: per-step FSM with terminal detection
- Step: individual execution unit with retry, hashing, and idempotency
- Checkpoint: append-only journal record for crash-recovery replay
- WorkflowRun: top-level run container aggregating steps

All hashes use the canonical 'sha256:<hex>' prefix format (ssidctl.core.hashing).
Timestamps are UTC ISO 8601 strings from ssidctl.core.timeutil.utcnow_iso().

See docs/decisions/ADR-drift-sentinel-durable-workflow.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ssidctl.core.timeutil import utcnow_iso

# ---------------------------------------------------------------------------
# Status enumerations
# ---------------------------------------------------------------------------


class WorkflowStatus(StrEnum):
    """Lifecycle states for a WorkflowRun.

    Transition map (explicit; all other transitions are invalid):
        PENDING  -> RUNNING
        RUNNING  -> COMPLETED | FAILED | BLOCKED | CANCELLED
        BLOCKED  -> RUNNING | CANCELLED
        FAILED   -> RUNNING
        COMPLETED -> (terminal — no further transitions)
        CANCELLED -> (terminal — no further transitions)
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


#: Explicit FSM transition map for WorkflowStatus.
WORKFLOW_TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.PENDING: frozenset({WorkflowStatus.RUNNING}),
    WorkflowStatus.RUNNING: frozenset(
        {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.BLOCKED,
            WorkflowStatus.CANCELLED,
        }
    ),
    WorkflowStatus.BLOCKED: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
    WorkflowStatus.FAILED: frozenset({WorkflowStatus.RUNNING}),
    WorkflowStatus.COMPLETED: frozenset(),
    WorkflowStatus.CANCELLED: frozenset(),
}

#: Terminal workflow states — no further transitions are possible.
WORKFLOW_TERMINAL_STATUSES: frozenset[WorkflowStatus] = frozenset(
    {WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED}
)


class StepStatus(StrEnum):
    """Lifecycle states for a single Step.

    Transition map:
        PENDING -> RUNNING
        RUNNING -> COMPLETED | FAILED | SKIPPED
        COMPLETED -> (terminal)
        FAILED    -> RUNNING  (retry)
        SKIPPED   -> (terminal)
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

    def is_terminal(self) -> bool:
        """Return True if this status allows no further transitions."""
        return self in _STEP_TERMINAL_STATUSES


#: Explicit FSM transition map for StepStatus.
STEP_TRANSITIONS: dict[StepStatus, frozenset[StepStatus]] = {
    StepStatus.PENDING: frozenset({StepStatus.RUNNING, StepStatus.SKIPPED}),
    StepStatus.RUNNING: frozenset({StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED}),
    StepStatus.COMPLETED: frozenset(),
    StepStatus.FAILED: frozenset({StepStatus.RUNNING}),  # retry path
    StepStatus.SKIPPED: frozenset(),
}

#: Terminal step states — populated after class definition to avoid forward-ref.
_STEP_TERMINAL_STATUSES: frozenset[StepStatus] = frozenset(
    {StepStatus.COMPLETED, StepStatus.SKIPPED}
)


# ---------------------------------------------------------------------------
# Lifecycle errors
# ---------------------------------------------------------------------------


class WorkflowTransitionError(Exception):
    """Raised when an invalid WorkflowStatus transition is attempted."""


class StepTransitionError(Exception):
    """Raised when an invalid StepStatus transition is attempted."""


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------


@dataclass
class Step:
    """A single executable unit within a WorkflowRun.

    Fields
    ------
    step_id:
        Unique identifier for this step instance (UUID4 by default).
    step_type:
        Logical type/name of the step (e.g. ``"drift_check"``, ``"approval_gate"``).
    step_index:
        Zero-based position of this step in the workflow's step list.
    input_hash:
        SHA-256 hash of the step's input in ``sha256:<hex>`` format.
        Computed before the step executes; used for idempotency.
    idempotency_key:
        Deterministic key that uniquely identifies this step invocation
        across retries. Typically derived via ``workflow.idempotency.compute_idempotency_key``.
    status:
        Current lifecycle state (StepStatus FSM).
    attempt:
        Number of execution attempts so far (starts at 0, incremented before each run).
    max_attempts:
        Maximum number of allowed attempts before the step is permanently failed.
    output_hash:
        SHA-256 hash of the step's output in ``sha256:<hex>`` format.
        Set on COMPLETED; None otherwise.
    error:
        Human-readable error description on FAILED; None otherwise.
    started_at:
        UTC ISO 8601 timestamp when the most recent attempt started.
    finished_at:
        UTC ISO 8601 timestamp when the step reached a terminal state.
    retryable:
        Whether the step is eligible for retry on failure.
    """

    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_type: str = ""
    step_index: int = 0
    input_hash: str = ""
    idempotency_key: str = ""
    status: StepStatus = StepStatus.PENDING
    attempt: int = 0
    max_attempts: int = 3
    output_hash: str | None = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    retryable: bool = True

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def transition_to(self, target: StepStatus) -> None:
        """Transition to ``target`` status, enforcing the FSM.

        Raises
        ------
        StepTransitionError
            If the transition from the current status to ``target`` is not allowed.
        """
        allowed = STEP_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise StepTransitionError(
                f"Invalid step transition: {self.status.value} -> {target.value}. "
                f"Allowed from {self.status.value}: "
                f"{sorted(s.value for s in allowed)}"
            )
        self.status = target

    def can_retry(self) -> bool:
        """Return True if this step may be retried."""
        return (
            self.retryable
            and self.status == StepStatus.FAILED
            and self.attempt < self.max_attempts
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "step_index": self.step_index,
            "input_hash": self.input_hash,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "output_hash": self.output_hash,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "retryable": self.retryable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Step:
        """Deserialise from a JSON-compatible dict."""
        return cls(
            step_id=data["step_id"],
            step_type=data["step_type"],
            step_index=data["step_index"],
            input_hash=data["input_hash"],
            idempotency_key=data["idempotency_key"],
            status=StepStatus(data["status"]),
            attempt=data["attempt"],
            max_attempts=data["max_attempts"],
            output_hash=data.get("output_hash"),
            error=data.get("error"),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            retryable=data.get("retryable", True),
        )


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


@dataclass
class Checkpoint:
    """Append-only journal record for crash-recovery replay.

    A checkpoint is written to the JSONL journal whenever a step changes
    state. On restart, the executor replays all checkpoints to reconstruct
    the current ``WorkflowRun`` state without re-executing completed steps.

    Fields
    ------
    run_id:
        The ``WorkflowRun.run_id`` this checkpoint belongs to.
    step_id:
        The ``Step.step_id`` this checkpoint describes.
    step_index:
        The step's position in the workflow (denormalised for fast replay).
    status:
        The step status at the time this checkpoint was written.
    output_hash:
        SHA-256 hash of the step's output (``sha256:<hex>``), or None.
    payload:
        Optional free-form metadata dict (non-PII; e.g. ``{"gate": "PASS"}``).
    timestamp:
        UTC ISO 8601 timestamp when this checkpoint was written.
    """

    run_id: str
    step_id: str
    step_index: int
    status: StepStatus
    output_hash: str | None = None
    payload: dict[str, Any] | None = None
    timestamp: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict (suitable for JSONL append)."""
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "step_index": self.step_index,
            "status": self.status.value,
            "output_hash": self.output_hash,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        """Deserialise from a JSON-compatible dict."""
        return cls(
            run_id=data["run_id"],
            step_id=data["step_id"],
            step_index=data["step_index"],
            status=StepStatus(data["status"]),
            output_hash=data.get("output_hash"),
            payload=data.get("payload"),
            timestamp=data["timestamp"],
        )


# ---------------------------------------------------------------------------
# WorkflowRun
# ---------------------------------------------------------------------------


@dataclass
class WorkflowRun:
    """Top-level container for a single durable workflow execution.

    Fields
    ------
    run_id:
        Unique identifier for this run (UUID4 by default).
    workflow_name:
        Stable logical name of the workflow (e.g. ``"drift_sentinel"``).
    workflow_version:
        Semantic version of the workflow definition (e.g. ``"1.0.0"``).
    status:
        Current lifecycle state (WorkflowStatus FSM).
    steps:
        Ordered list of Step objects comprising this run.
    current_step_index:
        Zero-based index of the step currently executing (or last executed).
    created_at:
        UTC ISO 8601 timestamp when the run record was created.
    started_at:
        UTC ISO 8601 timestamp when execution began (RUNNING transition).
    finished_at:
        UTC ISO 8601 timestamp when the run reached a terminal state.
    event_fingerprint:
        SHA-256 hash of the triggering event (``sha256:<hex>``).
        Acts as the run-level idempotency key.
    policy_version:
        Version of the governing policy active at execution time.
    error:
        Human-readable description of the run-level failure; None otherwise.
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = ""
    workflow_version: str = "1.0.0"
    status: WorkflowStatus = WorkflowStatus.PENDING
    steps: list[Step] = field(default_factory=list)
    current_step_index: int = 0
    created_at: str = field(default_factory=utcnow_iso)
    started_at: str | None = None
    finished_at: str | None = None
    event_fingerprint: str = ""
    policy_version: str = ""
    error: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def transition_to(self, target: WorkflowStatus) -> None:
        """Transition to ``target`` status, enforcing the FSM.

        Raises
        ------
        WorkflowTransitionError
            If the transition from the current status to ``target`` is not allowed.
        """
        allowed = WORKFLOW_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise WorkflowTransitionError(
                f"Invalid workflow transition: {self.status.value} -> {target.value}. "
                f"Allowed from {self.status.value}: "
                f"{sorted(s.value for s in allowed)}"
            )
        self.status = target

    def is_terminal(self) -> bool:
        """Return True if the run has reached a terminal state."""
        return self.status in WORKFLOW_TERMINAL_STATUSES

    def current_step(self) -> Step | None:
        """Return the Step at ``current_step_index``, or None if the list is empty."""
        if not self.steps:
            return None
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return {
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "event_fingerprint": self.event_fingerprint,
            "policy_version": self.policy_version,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowRun:
        """Deserialise from a JSON-compatible dict."""
        return cls(
            run_id=data["run_id"],
            workflow_name=data["workflow_name"],
            workflow_version=data.get("workflow_version", "1.0.0"),
            status=WorkflowStatus(data["status"]),
            steps=[Step.from_dict(s) for s in data.get("steps", [])],
            current_step_index=data.get("current_step_index", 0),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            event_fingerprint=data.get("event_fingerprint", ""),
            policy_version=data.get("policy_version", ""),
            error=data.get("error"),
        )
