"""Health Check Building Blocks — reusable check primitives for doctor.

Provides composable health check functions that can be used by
doctor_cmd.py and other diagnostic tools. Each check returns a
standardized CheckResult.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class HealthCheckError(Exception):
    pass


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health check."""

    name: str
    status: str  # OK, WARN, FAIL, SKIP
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in ("OK", "SKIP")

    @property
    def is_warning(self) -> bool:
        return self.status == "WARN"

    @property
    def is_failure(self) -> bool:
        return self.status == "FAIL"


@dataclass
class HealthReport:
    """Aggregated report from multiple health checks."""

    checks: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)

    @property
    def all_ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "OK")

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "WARN")

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "FAIL")

    @property
    def skip_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "SKIP")

    def render_text(self) -> str:
        lines = [
            "Health Report",
            "=" * 50,
        ]
        for c in self.checks:
            msg = f": {c.message}" if c.message else ""
            lines.append(f"  {c.status:4s}  {c.name}{msg}")
        lines.append("")
        lines.append(
            f"  Summary: {self.pass_count} OK, {self.warn_count} WARN, "
            f"{self.fail_count} FAIL, {self.skip_count} SKIP"
        )
        result = "PASS" if self.all_ok else "FAIL"
        lines.append(f"  Result: {result}")
        return "\n".join(lines)


# --- Individual Check Functions ---


def check_directory_exists(name: str, path: Path) -> CheckResult:
    """Check that a directory exists."""
    if path.is_dir():
        return CheckResult(name=name, status="OK", message=str(path))
    return CheckResult(name=name, status="FAIL", message=f"Not found: {path}")


def check_file_exists(name: str, path: Path) -> CheckResult:
    """Check that a file exists."""
    if path.is_file():
        return CheckResult(name=name, status="OK", message=str(path))
    return CheckResult(name=name, status="FAIL", message=f"Not found: {path}")


def check_git_repo(name: str, repo_path: Path) -> CheckResult:
    """Check that a path is a valid git repository."""
    if not repo_path.is_dir():
        return CheckResult(name=name, status="FAIL", message=f"Not found: {repo_path}")

    git_dir = repo_path / ".git"
    if not git_dir.exists() and not (repo_path / "HEAD").exists():
        return CheckResult(name=name, status="FAIL", message="Not a git repo")
    return CheckResult(name=name, status="OK", message=str(repo_path))


def check_git_head(name: str, repo_path: Path) -> CheckResult:
    """Check that git HEAD is valid (resolves to a 40-char SHA)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        sha = result.stdout.strip()
        if result.returncode == 0 and len(sha) == 40:
            return CheckResult(name=name, status="OK", message=sha[:12])
        return CheckResult(name=name, status="FAIL", message="HEAD invalid")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CheckResult(name=name, status="FAIL", message="git not available")


def check_git_remote(name: str, repo_path: Path) -> CheckResult:
    """Check that a git remote 'origin' is configured."""
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and "origin" in result.stdout:
            return CheckResult(name=name, status="OK", message="origin configured")
        return CheckResult(name=name, status="WARN", message="No origin remote")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CheckResult(name=name, status="WARN", message="git not available")


def check_git_dirty(name: str, repo_path: Path) -> CheckResult:
    """Check for uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return CheckResult(name=name, status="WARN", message="git status failed")
        lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
        if len(lines) == 0:
            return CheckResult(name=name, status="OK", message="clean")
        return CheckResult(
            name=name,
            status="WARN",
            message=f"{len(lines)} dirty file(s)",
            details={"count": len(lines)},
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CheckResult(name=name, status="WARN", message="git not available")


def check_stale_worktrees(
    name: str, worktrees_dir: Path, max_age_hours: float = 168.0
) -> CheckResult:
    """Check for stale worktree directories (older than max_age_hours)."""
    if not worktrees_dir.is_dir():
        return CheckResult(name=name, status="OK", message="No worktrees dir")

    import time

    stale_count = 0
    for run_dir in worktrees_dir.iterdir():
        if run_dir.is_dir():
            try:
                age_h = (time.time() - run_dir.stat().st_mtime) / 3600.0
                if age_h > max_age_hours:
                    stale_count += 1
            except OSError:
                continue

    if stale_count == 0:
        return CheckResult(name=name, status="OK", message="No stale worktrees")
    return CheckResult(
        name=name,
        status="WARN",
        message=f"{stale_count} stale worktree(s)",
        details={"stale_count": stale_count},
    )


def check_state_subdirs(name: str, state_dir: Path) -> CheckResult:
    """Check that all required EMS state subdirectories exist."""
    required = [
        "board",
        "content",
        "team",
        "calendar",
        "memory",
        "runs",
        "approvals",
        "incidents",
        "locks",
        "tasks",
    ]
    missing = [d for d in required if not (state_dir / d).is_dir()]
    if not missing:
        return CheckResult(name=name, status="OK", message=f"{len(required)} dirs present")
    return CheckResult(
        name=name,
        status="FAIL",
        message=f"Missing: {', '.join(missing)}",
        details={"missing": missing},
    )


def run_health_checks(
    checks: list[Callable[[], CheckResult]],
) -> HealthReport:
    """Run a list of check callables and aggregate results."""
    report = HealthReport()
    for check_fn in checks:
        try:
            result = check_fn()
        except Exception as e:
            result = CheckResult(
                name=check_fn.__name__,
                status="FAIL",
                message=str(e),
            )
        report.add(result)
    return report
