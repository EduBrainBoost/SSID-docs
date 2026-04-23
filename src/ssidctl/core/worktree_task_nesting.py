"""Worktree Task Nesting — path resolution utilities for nested worktrees.

Provides standalone helpers for computing nested worktree paths
(worktrees_dir / run_id / task_id / {plan,apply,verify}) and
validating nesting layouts. Complements worktree_orchestrator.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKTREE_ROLES = ("plan", "apply", "verify")


class NestingError(Exception):
    pass


@dataclass(frozen=True)
class WorktreePaths:
    """Resolved paths for a nested worktree set."""

    run_id: str
    task_id: str
    base_dir: Path
    plan: Path
    apply: Path
    verify: Path

    @property
    def run_dir(self) -> Path:
        """The run-level or nested task-level directory."""
        if self.task_id:
            return self.base_dir / self.run_id / self.task_id
        return self.base_dir / self.run_id

    @property
    def branch_name(self) -> str:
        """Compute the canonical branch name."""
        if self.task_id:
            return f"cms/{self.task_id}/{self.run_id}"
        return f"cms/{self.run_id}"


def resolve_paths(
    worktrees_dir: Path,
    run_id: str,
    task_id: str = "",
) -> WorktreePaths:
    """Compute all 3 worktree paths for a given run_id / task_id combo."""
    if not run_id:
        raise NestingError("run_id must not be empty")

    run_dir = worktrees_dir / run_id / task_id if task_id else worktrees_dir / run_id

    return WorktreePaths(
        run_id=run_id,
        task_id=task_id,
        base_dir=worktrees_dir,
        plan=run_dir / "plan",
        apply=run_dir / "apply",
        verify=run_dir / "verify",
    )


def detect_layout(run_dir: Path) -> str:
    """Detect whether a run directory uses flat or nested layout.

    Returns:
        'flat' if run_dir/{plan,apply,verify} exist directly
        'nested' if run_dir/<task_id>/{plan,apply,verify} exist
        'empty' if directory has no worktree roles
        'mixed' if both patterns are found
    """
    if not run_dir.is_dir():
        return "empty"

    has_flat = any((run_dir / role).is_dir() for role in WORKTREE_ROLES)
    has_nested = False
    for child in run_dir.iterdir():
        has_sub = child.is_dir() and child.name not in WORKTREE_ROLES
        if has_sub and any((child / role).is_dir() for role in WORKTREE_ROLES):
            has_nested = True
            break

    if has_flat and has_nested:
        return "mixed"
    if has_flat:
        return "flat"
    if has_nested:
        return "nested"
    return "empty"


def list_task_ids(worktrees_dir: Path, run_id: str) -> list[str]:
    """List task_ids for a nested worktree run.

    Returns empty list if flat layout or directory doesn't exist.
    """
    run_dir = worktrees_dir / run_id
    if not run_dir.is_dir():
        return []

    task_ids: list[str] = []
    for child in sorted(run_dir.iterdir()):
        has_sub = child.is_dir() and child.name not in WORKTREE_ROLES
        if has_sub and any((child / role).is_dir() for role in WORKTREE_ROLES):
            task_ids.append(child.name)
    return task_ids


def validate_worktree_set(paths: WorktreePaths) -> dict[str, Any]:
    """Validate that a worktree set exists and is complete.

    Returns {valid: bool, existing: [...], missing: [...]}.
    """
    existing: list[str] = []
    missing: list[str] = []
    for role in WORKTREE_ROLES:
        role_path = getattr(paths, role)
        if role_path.is_dir():
            existing.append(role)
        else:
            missing.append(role)
    return {
        "valid": len(missing) == 0,
        "existing": existing,
        "missing": missing,
    }
