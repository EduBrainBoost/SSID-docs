"""Executor — runs agent tasks under write-lock with budget enforcement.

Dispatches routed tasks to agents, enforces scope firewall and budget
limits, and records all actions in the worklog.

Supports TaskSpec-driven operations: run_gates, git_pr_upsert.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ssidctl.autopilot.router import RoutedTask
from ssidctl.core.event_log import EventLog
from ssidctl.gates.matrix import GateDef


@dataclass
class ExecutionResult:
    """Result of executing a single task."""

    task_finding_type: str
    agent: str
    exit_code: int
    success: bool
    files_touched: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_finding_type": self.task_finding_type,
            "agent": self.agent,
            "exit_code": self.exit_code,
            "success": self.success,
            "files_touched": self.files_touched,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


@dataclass
class ExecutionBudget:
    """Tracks cumulative resource usage across iterations."""

    max_files_per_iter: int = 8
    max_lines_per_iter: int = 400
    max_total_files: int = 20
    max_total_lines: int = 1200
    files_this_iter: int = 0
    lines_this_iter: int = 0
    files_total: int = 0
    lines_total: int = 0

    @property
    def iter_exceeded(self) -> bool:
        return (
            self.files_this_iter > self.max_files_per_iter
            or self.lines_this_iter > self.max_lines_per_iter
        )

    @property
    def total_exceeded(self) -> bool:
        return self.files_total > self.max_total_files or self.lines_total > self.max_total_lines

    def record(self, files: int, lines: int) -> None:
        self.files_this_iter += files
        self.lines_this_iter += lines
        self.files_total += files
        self.lines_total += lines

    def new_iteration(self) -> None:
        self.files_this_iter = 0
        self.lines_this_iter = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_this_iter": self.files_this_iter,
            "lines_this_iter": self.lines_this_iter,
            "files_total": self.files_total,
            "lines_total": self.lines_total,
            "iter_exceeded": self.iter_exceeded,
            "total_exceeded": self.total_exceeded,
        }


class BudgetExceededError(Exception):
    """Raised when execution budget is exceeded."""


class ExecutorError(Exception):
    """Raised when an executor operation fails with a stop code."""

    def __init__(self, message: str, stop_code: str) -> None:
        super().__init__(message)
        self.stop_code = stop_code


class Executor:
    """Executes agent tasks in a worktree under budget constraints.

    Supports two modes:
    - Legacy (operations=None): stub that records budget + logs.
    - TaskSpec-driven (operations provided): dispatches to action handlers.
    """

    def __init__(
        self,
        worklog_path: Path,
        budget: ExecutionBudget | None = None,
    ) -> None:
        self._worklog = EventLog(worklog_path)
        self._budget = budget or ExecutionBudget()
        # Optional dependencies for TaskSpec operations
        self._collector: Any | None = None
        self._gate_filter_fn: Callable[[list[GateDef], list[str]], list[GateDef]] | None = None
        self._protected_paths: Any | None = None
        self._pr_manager: Any | None = None

    def configure(
        self,
        collector: Any | None = None,
        gate_filter_fn: Callable[[list[GateDef], list[str]], list[GateDef]] | None = None,
        protected_paths: Any | None = None,
        pr_manager: Any | None = None,
    ) -> None:
        """Inject dependencies for TaskSpec operations."""
        self._collector = collector
        self._gate_filter_fn = gate_filter_fn
        self._protected_paths = protected_paths
        self._pr_manager = pr_manager

    @property
    def budget(self) -> ExecutionBudget:
        return self._budget

    def execute_task(
        self,
        task: RoutedTask,
        worktree: Path,
        timeout: int = 300,
        *,
        operations: list[str] | None = None,
        taskspec: Any | None = None,
        run_id: str = "",
    ) -> ExecutionResult:
        """Execute a single routed task.

        Args:
            task: The routed task to execute.
            worktree: Path to the apply worktree.
            timeout: Maximum seconds for the task.
            operations: Ordered list of operations from TaskSpec. None = legacy mode.
            taskspec: ResolvedTaskSpec (for operations that need it).
            run_id: Current run ID (for branch naming).

        Returns:
            ExecutionResult with outcome details.

        Raises:
            BudgetExceededError: If budget limits are exceeded.
            ExecutorError: If an operation fails with a stop code.
        """
        if self._budget.total_exceeded:
            raise BudgetExceededError(
                f"Total budget exceeded: {self._budget.files_total} files, "
                f"{self._budget.lines_total} lines"
            )

        agent = task.agents[0] if task.agents else "none"

        # Record task start
        self._worklog.append(
            "autopilot.task.start",
            {
                "finding_type": task.finding.finding_type,
                "agent": agent,
                "gate": task.finding.gate_name,
                "priority": task.priority,
                "paths": task.finding.paths,
                "operations": operations,
            },
            actor=agent,
        )

        # Dispatch based on mode
        if operations is None:
            # Legacy stub mode
            result = self._execute_legacy(task, worktree, agent)
        else:
            # TaskSpec-driven mode
            result = self._execute_operations(task, worktree, agent, operations, taskspec, run_id)

        # Record task completion
        self._worklog.append(
            "autopilot.task.complete",
            {
                "finding_type": task.finding.finding_type,
                "agent": agent,
                "success": result.success,
                "exit_code": result.exit_code,
            },
            actor=agent,
        )

        return result

    def _execute_legacy(self, task: RoutedTask, worktree: Path, agent: str) -> ExecutionResult:
        """Legacy stub: count diffs, record budget, return success."""
        files_changed = self._count_changed_files(worktree)
        self._budget.record(files=max(1, files_changed), lines=0)

        if self._budget.iter_exceeded:
            raise BudgetExceededError(
                f"Iteration budget exceeded: {self._budget.files_this_iter} files"
            )

        return ExecutionResult(
            task_finding_type=task.finding.finding_type,
            agent=agent,
            exit_code=0,
            success=True,
            files_touched=task.finding.paths,
        )

    def _execute_operations(
        self,
        task: RoutedTask,
        worktree: Path,
        agent: str,
        operations: list[str],
        taskspec: Any | None,
        run_id: str,
    ) -> ExecutionResult:
        """Dispatch ordered operations from TaskSpec."""
        action_results: list[dict[str, Any]] = []

        for op in operations:
            if op == "run_gates":
                res = self._run_gates(worktree, taskspec)
                action_results.append({"operation": "run_gates", "result": res})
            elif op == "git_pr_upsert":
                res = self._git_pr_upsert(worktree, taskspec, run_id)
                action_results.append({"operation": "git_pr_upsert", "result": res})

        # Check budget after operations
        files_changed = self._count_changed_files(worktree)
        self._budget.record(files=max(1, files_changed), lines=0)

        if self._budget.iter_exceeded:
            raise BudgetExceededError(
                f"Iteration budget exceeded: {self._budget.files_this_iter} files"
            )

        return ExecutionResult(
            task_finding_type=task.finding.finding_type,
            agent=agent,
            exit_code=0,
            success=True,
            files_touched=task.finding.paths,
        )

    def _run_gates(self, worktree: Path, taskspec: Any | None) -> dict[str, Any]:
        """Run gates filtered by TaskSpec acceptance_checks."""
        if self._collector is None:
            return {"status": "skipped", "reason": "no collector configured"}

        if (
            taskspec is not None
            and taskspec.gate_source == "acceptance_checks_only"
            and self._gate_filter_fn is not None
        ):
            from ssidctl.gates.matrix import load_matrix

            matrix = load_matrix()
            filtered = self._gate_filter_fn(matrix.gates, taskspec.acceptance_checks)
            collection = self._collector.collect(worktree, gates=filtered)
        else:
            collection = self._collector.collect(worktree)

        return collection.to_dict()

    def _git_pr_upsert(self, worktree: Path, taskspec: Any | None, run_id: str) -> dict[str, Any]:
        """Create or update a PR for the autopilot changes."""
        if taskspec is None:
            return {"status": "skipped", "reason": "no taskspec"}

        task_id = taskspec.task_id
        branch = f"autopilot/{task_id}/{run_id}"

        # Check for changes
        has_changes = self._has_git_changes(worktree)
        if not has_changes:
            return {"status": "noop", "reason": "no changes to commit"}

        # Check gh availability
        if self._pr_manager is not None and not self._pr_manager.is_gh_available():
            raise ExecutorError(
                f"gh CLI not available — cannot create PR for {task_id}",
                stop_code="STOP_MANUAL_PR_REQUIRED",
            )

        # Create branch, commit, push
        try:
            self._git(worktree, "checkout", "-B", branch)
            self._git(worktree, "add", "-A")
            self._git(
                worktree,
                "commit",
                "-m",
                f"autopilot: {task_id} run {run_id}",
            )
            self._git(worktree, "push", "-u", "origin", branch)
        except subprocess.CalledProcessError as e:
            return {"status": "error", "reason": f"git failed: {e}"}

        # Create or edit PR
        pr_result = self._upsert_pr(worktree, branch, task_id, run_id)
        return {"status": "ok", "branch": branch, "pr": pr_result}

    def _upsert_pr(self, worktree: Path, branch: str, task_id: str, run_id: str) -> dict[str, Any]:
        """Create PR or update existing one."""
        title = f"autopilot: {task_id}"
        body = f"Autopilot run `{run_id}` for task `{task_id}`."

        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--head",
                    branch,
                ],
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return {"action": "created", "url": result.stdout.strip()}

            # PR might already exist — try edit
            if "already exists" in result.stderr:
                edit = subprocess.run(
                    [
                        "gh",
                        "pr",
                        "edit",
                        "--title",
                        title,
                        "--body",
                        body,
                    ],
                    cwd=str(worktree),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if edit.returncode == 0:
                    return {"action": "updated"}
                return {"action": "edit_failed", "error": edit.stderr.strip()}

            return {"action": "create_failed", "error": result.stderr.strip()}
        except (subprocess.TimeoutExpired, OSError) as e:
            return {"action": "error", "error": str(e)}

    def _has_git_changes(self, worktree: Path) -> bool:
        """Check if worktree has uncommitted changes."""
        try:
            proc = subprocess.run(
                ["git", "diff", "--stat", "HEAD"],
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return bool(proc.stdout.strip())
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _count_changed_files(self, worktree: Path) -> int:
        """Count changed files in worktree via git diff."""
        try:
            proc = subprocess.run(
                ["git", "diff", "--stat", "--cached", "HEAD"],
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=30,
            )
            files_changed = proc.stdout.count("\n") - 1
            return max(0, files_changed)
        except (subprocess.TimeoutExpired, OSError):
            return 0

    def _git(self, worktree: Path, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a git command in the worktree."""
        return subprocess.run(
            ["git", *args],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )

    def new_iteration(self) -> None:
        """Reset per-iteration budget counters."""
        self._budget.new_iteration()
