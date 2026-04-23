"""Protected Paths — core logic registry that blocks autopilot modification.

Files matching protected path patterns trigger STOP_CORE_CHANGE when
the autopilot attempts to modify them. This is a safety net to prevent
automated fixes from touching security-critical code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


def _glob_match(path: str, pattern: str) -> bool:
    """Match path against a glob pattern supporting ** for directory recursion."""
    # Normalize: ** can match zero or more path segments
    # Split on ** first, then handle * within segments
    parts = pattern.split("**")
    regex_parts = []
    for part in parts:
        escaped = re.escape(part)
        escaped = escaped.replace(r"\*", "[^/]*")
        escaped = escaped.replace(r"\?", "[^/]")
        regex_parts.append(escaped)
    # Join with .* but also allow zero-length match (strip redundant slashes)
    regex = ".*".join(regex_parts)
    # Handle patterns like **/X or X/** where ** at boundary matches zero segments
    regex = regex.replace("/.*", "(/.*)?")
    regex = regex.replace(".*/", "(.*/)?")
    return bool(re.fullmatch(regex, path))


@dataclass(frozen=True)
class ProtectedPathViolation:
    """A single protected path violation."""

    path: str
    matched_pattern: str


class ProtectedPathsError(Exception):
    """Raised on protected paths configuration errors."""


class ProtectedPaths:
    """Checks file paths against protected patterns."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._patterns: list[str] = []

    def load(self) -> list[str]:
        """Load protected path patterns from YAML."""
        if not self._config_path.exists():
            raise ProtectedPathsError(f"Config not found: {self._config_path}")

        data = yaml.safe_load(self._config_path.read_text(encoding="utf-8"))
        self._patterns = data.get("protected_paths", [])
        return list(self._patterns)

    @property
    def patterns(self) -> list[str]:
        return list(self._patterns)

    def check(self, paths: list[str]) -> list[ProtectedPathViolation]:
        """Check if any paths match protected patterns.

        Args:
            paths: List of file paths (relative to repo root).

        Returns:
            List of violations (empty = all OK).
        """
        if not self._patterns:
            self.load()

        violations: list[ProtectedPathViolation] = []
        for path in paths:
            normalized = path.replace("\\", "/")
            for pattern in self._patterns:
                if _glob_match(normalized, pattern):
                    violations.append(
                        ProtectedPathViolation(path=normalized, matched_pattern=pattern)
                    )
                    break  # One match per path is enough

        return violations

    def is_protected(self, path: str) -> bool:
        """Check if a single path is protected."""
        return len(self.check([path])) > 0
