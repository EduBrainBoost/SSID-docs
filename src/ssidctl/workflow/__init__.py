"""Durable workflow execution kernel for SSID-EMS.

Provides shared primitives for crash-recoverable, idempotent workflow execution:
- WorkflowRun: top-level run container with FSM lifecycle
- Step: individual step with retry semantics and hash-based I/O
- Checkpoint: append-only journal record for crash recovery
- WorkflowStatus / StepStatus: deterministic state machines

Design: append-only JSONL journal, no external infra, concurrency=1.
See docs/decisions/ADR-drift-sentinel-durable-workflow.md.
"""

from ssidctl.workflow.models import (
    Checkpoint,
    Step,
    StepStatus,
    WorkflowRun,
    WorkflowStatus,
)

__all__ = [
    "Checkpoint",
    "Step",
    "StepStatus",
    "WorkflowRun",
    "WorkflowStatus",
]
