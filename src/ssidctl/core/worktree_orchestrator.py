"""Git worktree orchestrator — 3-worktree lifecycle management.

Per SSID-EMS Policy, each RUN creates 3 worktrees:
  - plan:   read-only (detached HEAD), for analysis/scope scan
  - apply:  write (new branch cms/{task_id}/{run_id}), for patch application
  - verify: read-only (detached HEAD), for clean reproducibility check

Worktrees are created at SSID_EMS_STATE/worktrees/{run_id}/{plan,apply,verify}.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

WORKTREE_ROLES = ("plan", "apply", "verify")


class WorktreeError(Exception):
    pass


class WorktreeOrchestrator:
    """Manages Git worktrees for EMS runs (3-worktree model)."""

    def __init__(self, ssid_repo: Path, worktrees_dir: Path) -> None:
        self._repo = ssid_repo
        self._base_dir = worktrees_dir

    def _resolve_run_dir(self, run_id: str, task_id: str = "") -> Path:
        """Compute the run directory path, accounting for optional task_id nesting."""
        if task_id:
            return self._base_dir / run_id / task_id
        return self._base_dir / run_id

    def create(
        self,
        run_id: str,
        task_id: str = "",
        base_ref: str = "HEAD",
    ) -> dict[str, Any]:
        """Create the 3-worktree set for a run.

        When task_id is provided, worktrees are nested under run_id/task_id/.
        Returns dict with {run_id, base_commit, worktrees: {plan, apply, verify}}.
        """
        run_dir = self._resolve_run_dir(run_id, task_id)
        if run_dir.exists():
            raise WorktreeError(f"Worktree set already exists: {run_id}")

        run_dir.mkdir(parents=True, exist_ok=True)
        base_commit = self._git("rev-parse", base_ref).strip()

        branch = f"cms/{task_id}/{run_id}" if task_id else f"cms/{run_id}"
        worktrees: dict[str, dict[str, Any]] = {}

        for role in WORKTREE_ROLES:
            wt_path = run_dir / role
            if role == "apply":
                # apply gets a real branch for commits
                self._git("worktree", "add", "-b", branch, str(wt_path), base_ref)
                worktrees[role] = {
                    "path": wt_path,
                    "branch": branch,
                    "mode": "write",
                }
            else:
                # plan + verify are detached (read-only by convention)
                self._git("worktree", "add", "--detach", str(wt_path), base_ref)
                worktrees[role] = {
                    "path": wt_path,
                    "branch": None,
                    "mode": "read-only",
                }

        return {
            "run_id": run_id,
            "task_id": task_id,
            "base_commit": base_commit,
            "branch": branch,
            "worktrees": worktrees,
        }

    def cleanup(self, run_id: str, task_id: str = "") -> None:
        """Remove all worktrees for a run (verify first, then apply, then plan)."""
        run_dir = self._resolve_run_dir(run_id, task_id)

        # Remove in reverse order: verify -> apply -> plan
        for role in reversed(WORKTREE_ROLES):
            wt_path = run_dir / role
            if wt_path.exists():
                with contextlib.suppress(WorktreeError):
                    self._git("worktree", "remove", str(wt_path), "--force")

        # Clean up the branch
        branches_to_try = [f"cms/{run_id}"]
        try:
            out = self._git("branch", "--list", f"cms/*/{run_id}")
            for line in out.strip().splitlines():
                b = line.strip().lstrip("* ")
                if b:
                    branches_to_try.append(b)
        except WorktreeError:
            pass
        for branch in branches_to_try:
            with contextlib.suppress(WorktreeError):
                self._git("branch", "-D", branch)

        # Remove empty run directory and parent if empty
        if run_dir.exists():
            with contextlib.suppress(OSError):
                run_dir.rmdir()
        if task_id:
            parent = self._base_dir / run_id
            if parent.exists():
                with contextlib.suppress(OSError):
                    parent.rmdir()

        # Prune stale worktrees
        with contextlib.suppress(WorktreeError):
            self._git("worktree", "prune")

    def gc(self) -> list[str]:
        """Garbage-collect stale worktree directories.

        Removes directories under worktrees_dir that have no matching
        git worktree entry. Returns list of removed directory names.
        """
        if not self._base_dir.exists():
            return []

        # Get list of registered worktrees from git
        try:
            out = self._git("worktree", "list", "--porcelain")
        except WorktreeError:
            return []

        registered: set[str] = set()
        for line in out.splitlines():
            if line.startswith("worktree "):
                registered.add(Path(line.split(" ", 1)[1]).resolve().as_posix())

        removed: list[str] = []
        for run_dir in sorted(self._base_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            # Check both flat (run_dir/role) and nested (run_dir/task_id/role) layouts
            has_live = False
            for sub in run_dir.iterdir():
                if sub.is_dir():
                    if sub.name in WORKTREE_ROLES:
                        if sub.resolve().as_posix() in registered:
                            has_live = True
                            break
                    else:
                        # Nested task_id dir
                        for role_dir in sub.iterdir():
                            is_role = role_dir.is_dir() and role_dir.name in WORKTREE_ROLES
                            if is_role and role_dir.resolve().as_posix() in registered:
                                has_live = True
                                break
                        if has_live:
                            break
            if not has_live:
                shutil.rmtree(run_dir, ignore_errors=True)
                removed.append(run_dir.name)

        with contextlib.suppress(WorktreeError):
            self._git("worktree", "prune")

        return removed

    def list_worktrees(self) -> list[str]:
        """List active EMS run IDs (directories under worktrees base)."""
        if not self._base_dir.exists():
            return []
        return [d.name for d in sorted(self._base_dir.iterdir()) if d.is_dir()]

    def get_worktree_path(self, run_id: str, role: str, task_id: str = "") -> Path:
        """Get path for a specific worktree role."""
        if role not in WORKTREE_ROLES:
            raise WorktreeError(f"Invalid role: {role}. Must be one of {WORKTREE_ROLES}")
        wt_path = self._resolve_run_dir(run_id, task_id) / role
        if not wt_path.exists():
            raise WorktreeError(f"Worktree not found: {run_id}/{role}")
        return wt_path

    def get_head_sha(self, run_id: str, role: str = "apply") -> str:
        """Get HEAD commit of a worktree."""
        wt_path = self.get_worktree_path(run_id, role)
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(wt_path),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Failed to get HEAD: {result.stderr}")
        return result.stdout.strip()

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Git failed: {result.stderr.strip()}")
        return result.stdout
