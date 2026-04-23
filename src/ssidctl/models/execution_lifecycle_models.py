"""Canonical execution lifecycle status model.

Defines the deterministic state machine for execution items:
queued -> claimed -> running -> succeeded/failed
                            -> blocked/expired/abandoned
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EXECUTION_STATUSES: tuple[str, ...] = (
    "queued",
    "claimed",
    "running",
    "succeeded",
    "failed",
    "blocked",
    "expired",
    "abandoned",
)

TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        "succeeded",
        "failed",
        "blocked",
        "expired",
        "abandoned",
    }
)

EXECUTION_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"claimed", "blocked", "expired"}),
    "claimed": frozenset({"running", "blocked", "expired", "abandoned"}),
    "running": frozenset({"succeeded", "failed", "blocked", "expired", "abandoned"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "blocked": frozenset(),
    "expired": frozenset({"queued"}),  # expired items can be re-queued
    "abandoned": frozenset({"queued"}),  # abandoned items can be re-queued
}


class LifecycleError(Exception):
    """Raised on invalid lifecycle transitions."""


def validate_transition(current: str, target: str) -> bool:
    """Check if a status transition is valid."""
    if current not in EXECUTION_TRANSITIONS:
        return False
    return target in EXECUTION_TRANSITIONS[current]


def enforce_transition(current: str, target: str) -> None:
    """Enforce a valid transition, raise LifecycleError otherwise."""
    if not validate_transition(current, target):
        raise LifecycleError(
            f"Invalid transition: {current} -> {target}. "
            f"Allowed from {current}: {sorted(EXECUTION_TRANSITIONS.get(current, set()))}"
        )


@dataclass
class ExecutionItem:
    """Canonical execution item with full lifecycle tracking."""

    item_id: str
    action_type: str
    target_ref: str  # e.g. "repo:module:file"
    status: str = "queued"
    worker_id: str | None = None
    claim_id: str | None = None
    created_at: str = ""
    claimed_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    lease_expires_at: str | None = None
    blocked_reason: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    approval: dict[str, Any] | None = None
    dry_run: bool = False

    def transition_to(self, target: str) -> None:
        """Transition to a new status with validation."""
        enforce_transition(self.status, target)
        self.status = target

    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def is_claimable(self) -> bool:
        return self.status == "queued"

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "action_type": self.action_type,
            "target_ref": self.target_ref,
            "status": self.status,
            "worker_id": self.worker_id,
            "claim_id": self.claim_id,
            "created_at": self.created_at,
            "claimed_at": self.claimed_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "lease_expires_at": self.lease_expires_at,
            "blocked_reason": self.blocked_reason,
            "dry_run": self.dry_run,
        }
