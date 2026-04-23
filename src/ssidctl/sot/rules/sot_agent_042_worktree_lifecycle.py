"""SOT_AGENT_042: Worktree Lifecycle enforcement.

3-worktree model: plan (read-only) → apply (branch) → verify (clean checkout).
State machine: INIT → PLAN → APPLY → VERIFY → COMPLETE | FAILED.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class LifecycleState(StrEnum):
    INIT = "INIT"
    PLAN = "PLAN"
    APPLY = "APPLY"
    VERIFY = "VERIFY"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.INIT: {LifecycleState.PLAN},
    LifecycleState.PLAN: {LifecycleState.APPLY, LifecycleState.FAILED},
    LifecycleState.APPLY: {LifecycleState.VERIFY, LifecycleState.FAILED},
    LifecycleState.VERIFY: {LifecycleState.COMPLETE, LifecycleState.FAILED},
    LifecycleState.COMPLETE: set(),
    LifecycleState.FAILED: set(),
}

WORKTREE_ROLES = ("plan", "apply", "verify")


@dataclass
class WorktreeInfo:
    """Info about a single worktree."""

    role: str  # plan | apply | verify
    path: Path | None = None
    exists: bool = False
    is_detached: bool = False
    branch: str | None = None
    is_dirty: bool = False


@dataclass
class Violation:
    worktree_role: str
    reason: str


@dataclass
class WorktreeLifecycleResult:
    rule_id: str = "SOT_AGENT_042"
    passed: bool = True
    current_state: LifecycleState | None = None
    worktrees: dict[str, WorktreeInfo] = field(default_factory=dict)
    violations: list[Violation] = field(default_factory=list)
    orphaned_worktrees: list[str] = field(default_factory=list)

    def add_violation(self, role: str, reason: str) -> None:
        self.violations.append(Violation(worktree_role=role, reason=reason))
        self.passed = False


class WorktreeLifecycleRule:
    """Validates worktree lifecycle compliance."""

    rule_id = "SOT_AGENT_042"
    description = "Worktree Lifecycle"
    category = "lifecycle"

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def check(
        self,
        run_id: str | None = None,
        task_id: str | None = None,
        **kwargs: Any,
    ) -> WorktreeLifecycleResult:
        """Check worktree lifecycle compliance."""
        result = WorktreeLifecycleResult()

        # Check for orphaned worktrees
        self._check_orphaned_worktrees(result)

        # If run context given, validate specific run's worktrees
        if run_id and task_id:
            self._check_run_worktrees(run_id, task_id, result)

        # Check lock file
        self._check_lock_file(result)

        return result

    def _check_orphaned_worktrees(self, result: WorktreeLifecycleResult) -> None:
        """Detect orphaned git worktrees."""
        try:
            output = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.project_root),
            )
            if output.returncode != 0:
                return

            worktree_dir = self.project_root / "worktrees"
            if not worktree_dir.exists():
                return

            for wt_path in worktree_dir.rglob("*"):
                if wt_path.is_dir() and (wt_path / ".git").exists():
                    # Check if this worktree has a state file
                    state_file = wt_path / ".worktree_state.json"
                    if state_file.exists():
                        try:
                            state = json.loads(state_file.read_text(encoding="utf-8"))
                            if state.get("state") == LifecycleState.FAILED.value:
                                # Check age for 24h cleanup
                                result.orphaned_worktrees.append(str(wt_path))
                        except (json.JSONDecodeError, OSError):
                            result.orphaned_worktrees.append(str(wt_path))
                    else:
                        result.orphaned_worktrees.append(str(wt_path))

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _check_run_worktrees(
        self, run_id: str, task_id: str, result: WorktreeLifecycleResult
    ) -> None:
        """Validate worktrees for a specific run."""
        base_path = self.project_root / "worktrees" / "ssid" / run_id / task_id

        for role in WORKTREE_ROLES:
            wt_path = base_path / role
            info = WorktreeInfo(role=role, path=wt_path)

            if wt_path.exists():
                info.exists = True
                self._inspect_worktree(wt_path, info, result)
            result.worktrees[role] = info

        # Validate plan is read-only (detached HEAD)
        plan_info = result.worktrees.get("plan")
        if plan_info and plan_info.exists and not plan_info.is_detached:
            result.add_violation("plan", "plan worktree must be detached HEAD (read-only)")

        # Validate apply has branch
        apply_info = result.worktrees.get("apply")
        if apply_info and apply_info.exists:
            expected_branch = f"cms/{task_id}/{run_id}"
            if apply_info.branch and apply_info.branch != expected_branch:
                result.add_violation(
                    "apply",
                    f"apply branch '{apply_info.branch}' doesn't match"
                    f" expected '{expected_branch}'",
                )

        # Validate verify is clean
        verify_info = result.worktrees.get("verify")
        if verify_info and verify_info.exists and verify_info.is_dirty:
            result.add_violation("verify", "verify worktree must be clean (no dirty state)")

    def _inspect_worktree(
        self, path: Path, info: WorktreeInfo, result: WorktreeLifecycleResult
    ) -> None:
        """Inspect a worktree's git state."""
        try:
            # Check if detached
            head_output = subprocess.run(
                ["git", "symbolic-ref", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(path),
            )
            if head_output.returncode != 0:
                info.is_detached = True
            else:
                info.branch = head_output.stdout.strip()
                info.is_detached = False

            # Check if dirty
            status_output = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(path),
            )
            info.is_dirty = bool(status_output.stdout.strip())

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _check_lock_file(self, result: WorktreeLifecycleResult) -> None:
        """Check concurrent run lock."""
        lock_path = self.project_root / "locks" / "ssid.lock"
        if lock_path.exists():
            try:
                lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
                result.current_state = LifecycleState(lock_data.get("state", "INIT"))
            except (json.JSONDecodeError, OSError, ValueError):
                result.add_violation("lock", "corrupt lock file — manual cleanup required")

    @staticmethod
    def validate_transition(current: LifecycleState, target: LifecycleState) -> bool:
        """Check if a state transition is valid."""
        return target in VALID_TRANSITIONS.get(current, set())
