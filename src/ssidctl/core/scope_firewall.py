"""Scope Firewall — validates diffs against TaskSpec scope limits.

Enforces:
- allowed_paths: glob patterns for permitted file modifications
- max_changed_files: upper bound on modified files
- max_changed_lines: upper bound on changed lines (adds + deletes)
- allowed_file_types: extension allowlist

Diff rejected if any constraint is violated.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass(frozen=True)
class ScopeSpec:
    """Scope constraints for a task."""

    allowed_paths: list[str] = field(default_factory=lambda: ["*"])
    max_changed_files: int = 12
    max_changed_lines: int = 600
    allowed_file_types: list[str] = field(
        default_factory=lambda: [".py", ".yaml", ".yml", ".json", ".md", ".txt", ".toml"]
    )


@dataclass(frozen=True)
class DiffEntry:
    """A single changed file in a diff."""

    path: str
    added_lines: int = 0
    deleted_lines: int = 0


@dataclass
class ScopeViolation:
    """A single scope violation."""

    code: str
    message: str


class ScopeFirewall:
    """Validates diffs against scope constraints."""

    def __init__(self, scope: ScopeSpec) -> None:
        self._scope = scope

    def validate(self, entries: list[DiffEntry]) -> list[ScopeViolation]:
        """Validate a list of diff entries against scope.

        Returns:
            List of violations (empty = all OK).
        """
        violations: list[ScopeViolation] = []

        # Check file count
        if len(entries) > self._scope.max_changed_files:
            violations.append(
                ScopeViolation(
                    code="SCOPE_FILE_COUNT",
                    message=(
                        f"Changed {len(entries)} files, "
                        f"max allowed: {self._scope.max_changed_files}"
                    ),
                )
            )

        # Check total line count
        total_lines = sum(e.added_lines + e.deleted_lines for e in entries)
        if total_lines > self._scope.max_changed_lines:
            violations.append(
                ScopeViolation(
                    code="SCOPE_LINE_COUNT",
                    message=(
                        f"Changed {total_lines} lines, "
                        f"max allowed: {self._scope.max_changed_lines}"
                    ),
                )
            )

        for entry in entries:
            # Check path against allowed patterns
            if not self._path_allowed(entry.path):
                violations.append(
                    ScopeViolation(
                        code="SCOPE_PATH",
                        message=f"Path not in allowed_paths: {entry.path}",
                    )
                )

            # Check file extension
            ext = PurePosixPath(entry.path).suffix
            if ext and ext not in self._scope.allowed_file_types:
                violations.append(
                    ScopeViolation(
                        code="SCOPE_FILE_TYPE",
                        message=f"File type not allowed: {ext} ({entry.path})",
                    )
                )

        return violations

    def _path_allowed(self, path: str) -> bool:
        """Check if a path matches any allowed_paths pattern."""
        normalized = path.replace("\\", "/")
        return any(fnmatch.fnmatch(normalized, p) for p in self._scope.allowed_paths)
