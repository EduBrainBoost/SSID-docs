"""Dispatch matrix and execution decision models.

The dispatch matrix is the single source of truth for how action types
are routed: real execution, simulation, or blocked.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DISPATCH_MODES = ("real", "simulated", "blocked")


@dataclass(frozen=True)
class DispatchMatrixEntry:
    """Static entry in the dispatch matrix."""

    action_type: str
    dispatch_mode: str  # real | simulated | blocked
    adapter_ref: str | None  # e.g. "lint_fix_adapter"
    supports_dry_run: bool
    requires_approval: bool

    def __post_init__(self) -> None:
        if self.dispatch_mode not in DISPATCH_MODES:
            raise ValueError(f"Invalid dispatch_mode: {self.dispatch_mode}")


@dataclass
class ExecutionDecision:
    """Result of a dispatch policy evaluation."""

    action_type: str
    dispatch_mode: str  # real | simulated | blocked
    adapter_ref: str | None
    blocked_reason: str | None
    approval_status: str  # approved | not_required | missing | forbidden
    decided_at: str = ""
    dry_run: bool = False

    def is_executable(self) -> bool:
        return self.dispatch_mode == "real" and self.blocked_reason is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "dispatch_mode": self.dispatch_mode,
            "adapter_ref": self.adapter_ref,
            "blocked_reason": self.blocked_reason,
            "approval_status": self.approval_status,
            "decided_at": self.decided_at,
            "dry_run": self.dry_run,
        }


# ---------------------------------------------------------------------------
# Canonical dispatch matrix — static, no runtime modification
# ---------------------------------------------------------------------------

DISPATCH_MATRIX: dict[str, DispatchMatrixEntry] = {
    "lint_fix": DispatchMatrixEntry(
        action_type="lint_fix",
        dispatch_mode="real",
        adapter_ref="lint_fix_adapter",
        supports_dry_run=True,
        requires_approval=False,
    ),
    "format_fix": DispatchMatrixEntry(
        action_type="format_fix",
        dispatch_mode="real",
        adapter_ref="format_fix_adapter",
        supports_dry_run=True,
        requires_approval=False,
    ),
    "dependency_update": DispatchMatrixEntry(
        action_type="dependency_update",
        dispatch_mode="real",
        adapter_ref="dependency_update_adapter",
        supports_dry_run=True,
        requires_approval=True,
    ),
    "test_fix": DispatchMatrixEntry(
        action_type="test_fix",
        dispatch_mode="real",
        adapter_ref="test_fix_adapter",
        supports_dry_run=True,
        requires_approval=False,
    ),
    # Known simulated types
    "fix_validation_finding": DispatchMatrixEntry(
        action_type="fix_validation_finding",
        dispatch_mode="simulated",
        adapter_ref=None,
        supports_dry_run=True,
        requires_approval=False,
    ),
    "execute_repair_backlog": DispatchMatrixEntry(
        action_type="execute_repair_backlog",
        dispatch_mode="simulated",
        adapter_ref=None,
        supports_dry_run=True,
        requires_approval=True,
    ),
    "verify_recovery_basis": DispatchMatrixEntry(
        action_type="verify_recovery_basis",
        dispatch_mode="simulated",
        adapter_ref=None,
        supports_dry_run=True,
        requires_approval=False,
    ),
}

REAL_ACTION_TYPES: frozenset = frozenset(
    k for k, v in DISPATCH_MATRIX.items() if v.dispatch_mode == "real"
)


def resolve_dispatch(
    action_type: str,
    approval_status: str,
    decided_at: str = "",
    dry_run: bool = False,
) -> ExecutionDecision:
    """Resolve a dispatch decision from the matrix. Unknown -> blocked."""
    entry = DISPATCH_MATRIX.get(action_type)

    # Unknown action type -> blocked
    if entry is None:
        return ExecutionDecision(
            action_type=action_type,
            dispatch_mode="blocked",
            adapter_ref=None,
            blocked_reason="unknown_action_type",
            approval_status=approval_status,
            decided_at=decided_at,
            dry_run=dry_run,
        )

    # Check approval requirement
    if entry.requires_approval and approval_status != "approved":
        return ExecutionDecision(
            action_type=action_type,
            dispatch_mode="blocked",
            adapter_ref=entry.adapter_ref,
            blocked_reason="approval_required_but_missing",
            approval_status=approval_status,
            decided_at=decided_at,
            dry_run=dry_run,
        )

    # Valid dispatch
    return ExecutionDecision(
        action_type=action_type,
        dispatch_mode=entry.dispatch_mode,
        adapter_ref=entry.adapter_ref,
        blocked_reason=None,
        approval_status=approval_status if entry.requires_approval else "not_required",
        decided_at=decided_at,
        dry_run=dry_run,
    )
