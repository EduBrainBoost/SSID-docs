"""SOT_AGENT_041: Change Budget enforcement.

Per-PR/run limits:
- Max 25 files changed (configurable)
- Max 2000 lines added/removed
- Max 3 SSID roots touched
- Max 10 new files
- Max 5 deleted files (requires justification)
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BudgetLimits:
    """Configurable budget limits."""

    max_files: int = 25
    max_lines: int = 2000
    max_roots: int = 3
    max_new_files: int = 10
    max_deleted_files: int = 5


@dataclass
class BudgetUsage:
    """Current budget usage."""

    files_changed: int = 0
    lines_changed: int = 0
    roots_touched: set[str] = field(default_factory=set)
    new_files: int = 0
    deleted_files: int = 0


@dataclass
class BudgetViolation:
    category: str
    limit: int
    used: int
    message: str


@dataclass
class ChangeBudgetResult:
    rule_id: str = "SOT_AGENT_041"
    passed: bool = True
    usage: BudgetUsage = field(default_factory=BudgetUsage)
    limits: BudgetLimits = field(default_factory=BudgetLimits)
    violations: list[BudgetViolation] = field(default_factory=list)
    status: str = "WITHIN_BUDGET"

    def add_violation(self, category: str, limit: int, used: int, message: str) -> None:
        self.violations.append(
            BudgetViolation(category=category, limit=limit, used=used, message=message)
        )
        self.passed = False
        self.status = "OVER_BUDGET"

    def to_tracking_dict(self) -> dict[str, Any]:
        return {
            "budget": {
                "files_changed": {
                    "limit": self.limits.max_files,
                    "used": self.usage.files_changed,
                    "remaining": max(0, self.limits.max_files - self.usage.files_changed),
                },
                "lines_changed": {
                    "limit": self.limits.max_lines,
                    "used": self.usage.lines_changed,
                    "remaining": max(0, self.limits.max_lines - self.usage.lines_changed),
                },
                "roots_touched": {
                    "limit": self.limits.max_roots,
                    "used": len(self.usage.roots_touched),
                    "remaining": max(0, self.limits.max_roots - len(self.usage.roots_touched)),
                },
                "new_files": {
                    "limit": self.limits.max_new_files,
                    "used": self.usage.new_files,
                    "remaining": max(0, self.limits.max_new_files - self.usage.new_files),
                },
                "deleted_files": {
                    "limit": self.limits.max_deleted_files,
                    "used": self.usage.deleted_files,
                    "remaining": max(0, self.limits.max_deleted_files - self.usage.deleted_files),
                },
            },
            "status": self.status,
        }


# 24 SSID root prefixes
SSID_ROOTS = {f"{i:02d}_" for i in range(1, 25)}


class ChangeBudgetRule:
    """Validates PR/run change budget constraints."""

    rule_id = "SOT_AGENT_041"
    description = "Change Budget"
    category = "scope"

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def check(
        self,
        limits: BudgetLimits | None = None,
        base_ref: str = "main",
        **kwargs: Any,
    ) -> ChangeBudgetResult:
        """Check change budget against git diff from base_ref."""
        result = ChangeBudgetResult(limits=limits or BudgetLimits())
        diff_stats = self._get_diff_stats(base_ref)
        if diff_stats is None:
            return result
        self._compute_usage(diff_stats, result)
        self._enforce_limits(result)
        return result

    def _get_diff_stats(self, base_ref: str) -> list[str] | None:
        """Get git diff --stat lines."""
        try:
            output = subprocess.run(
                ["git", "diff", "--stat", "--diff-filter=ACDMR", f"{base_ref}...HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_root),
            )
            if output.returncode != 0:
                return None
            return output.stdout.strip().splitlines()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _compute_usage(self, stat_lines: list[str], result: ChangeBudgetResult) -> None:
        """Parse diff stats into budget usage."""
        new_files = self._get_new_files()
        deleted_files = self._get_deleted_files()

        for line in stat_lines:
            if " | " not in line:
                continue
            parts = line.split(" | ")
            filepath = parts[0].strip()
            result.usage.files_changed += 1

            # Detect root
            for root_prefix in SSID_ROOTS:
                if filepath.startswith(root_prefix):
                    result.usage.roots_touched.add(root_prefix.rstrip("_"))
                    break

            # Parse line changes
            change_part = parts[1].strip() if len(parts) > 1 else ""
            import re

            nums = re.findall(r"\d+", change_part)
            if nums:
                result.usage.lines_changed += sum(int(n) for n in nums)

        result.usage.new_files = len(new_files)
        result.usage.deleted_files = len(deleted_files)

    def _get_new_files(self) -> list[str]:
        try:
            output = subprocess.run(
                ["git", "diff", "--diff-filter=A", "--name-only", "main...HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_root),
            )
            return [f for f in output.stdout.strip().splitlines() if f]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _get_deleted_files(self) -> list[str]:
        try:
            output = subprocess.run(
                ["git", "diff", "--diff-filter=D", "--name-only", "main...HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_root),
            )
            return [f for f in output.stdout.strip().splitlines() if f]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _enforce_limits(self, result: ChangeBudgetResult) -> None:
        """Check usage against limits."""
        u, lim = result.usage, result.limits

        if u.files_changed > lim.max_files:
            result.add_violation(
                "files_changed",
                lim.max_files,
                u.files_changed,
                f"{u.files_changed} files exceed limit of {lim.max_files}",
            )

        if u.lines_changed > lim.max_lines:
            result.add_violation(
                "lines_changed",
                lim.max_lines,
                u.lines_changed,
                f"{u.lines_changed} lines exceed limit of {lim.max_lines}",
            )

        if len(u.roots_touched) > lim.max_roots:
            result.add_violation(
                "roots_touched",
                lim.max_roots,
                len(u.roots_touched),
                f"{len(u.roots_touched)} roots exceed limit of {lim.max_roots}",
            )

        if u.new_files > lim.max_new_files:
            result.add_violation(
                "new_files",
                lim.max_new_files,
                u.new_files,
                f"{u.new_files} new files exceed limit of {lim.max_new_files}",
            )

        if u.deleted_files > lim.max_deleted_files:
            result.add_violation(
                "deleted_files",
                lim.max_deleted_files,
                u.deleted_files,
                f"{u.deleted_files} deleted files exceed limit of {lim.max_deleted_files}",
            )
