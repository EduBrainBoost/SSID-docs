"""Action adapter registry with static dispatch matrix.

No runtime discovery — all adapters are registered statically here.
The DISPATCH_MATRIX is the single source of truth for what actions
are executable and by which adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ExecutionKind(StrEnum):
    """Classification of how an action is executed."""

    REAL = "real"
    SIMULATED = "simulated"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class DispatchMatrixEntry:
    """Static configuration for a dispatchable action type."""

    action_type: str
    dispatch_mode: str  # "adapter" | "shell" | "noop"
    adapter_ref: str  # matches adapter.adapter_name
    supports_dry_run: bool
    requires_approval: bool
    execution_kind: ExecutionKind


# Static dispatch matrix — the only source of truth for executable actions.
DISPATCH_MATRIX: dict[str, DispatchMatrixEntry] = {
    "lint_fix": DispatchMatrixEntry(
        action_type="lint_fix",
        dispatch_mode="adapter",
        adapter_ref="lint_fix",
        supports_dry_run=True,
        requires_approval=False,
        execution_kind=ExecutionKind.REAL,
    ),
    "format_fix": DispatchMatrixEntry(
        action_type="format_fix",
        dispatch_mode="adapter",
        adapter_ref="format_fix",
        supports_dry_run=True,
        requires_approval=False,
        execution_kind=ExecutionKind.REAL,
    ),
    "dependency_update": DispatchMatrixEntry(
        action_type="dependency_update",
        dispatch_mode="adapter",
        adapter_ref="dependency_update",
        supports_dry_run=True,
        requires_approval=True,
        execution_kind=ExecutionKind.REAL,
    ),
    "test_fix": DispatchMatrixEntry(
        action_type="test_fix",
        dispatch_mode="adapter",
        adapter_ref="test_fix",
        supports_dry_run=True,
        requires_approval=False,
        execution_kind=ExecutionKind.REAL,
    ),
}


def get_dispatch_entry(action_type: str) -> DispatchMatrixEntry | None:
    """Return the dispatch matrix entry for an action type, or None."""
    return DISPATCH_MATRIX.get(action_type)


def get_adapter(action_type: str) -> Any | None:
    """Return a concrete adapter instance for the action type, or None."""
    from ssidctl.core.action_adapters.dependency_update_adapter import (
        DependencyUpdateAdapter,
    )
    from ssidctl.core.action_adapters.format_fix_adapter import FormatFixAdapter
    from ssidctl.core.action_adapters.lint_fix_adapter import LintFixAdapter
    from ssidctl.core.action_adapters.test_fix_adapter import TestFixAdapter

    _registry: dict[str, Any] = {
        "lint_fix": LintFixAdapter(),
        "format_fix": FormatFixAdapter(),
        "dependency_update": DependencyUpdateAdapter(),
        "test_fix": TestFixAdapter(),
    }
    return _registry.get(action_type)
