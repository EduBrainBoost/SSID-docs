"""SOT_AGENT_037 -- API naming convention enforcement.

Rule: All API routes must follow the pattern /api/{module}/{resource}
(optionally followed by /{id} or sub-paths).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RULE_ID = "SOT_AGENT_037"
RULE_DESCRIPTION = "API routes must follow /api/{module}/{resource}[/{id}] convention"

# Pattern: /api/<module>/<resource> with optional trailing path segments
_ROUTE_PATTERN = re.compile(
    r"""@(?:app|router)\.(get|post|put|patch|delete|head|options)\(\s*["']"""
    r"""(/[^"']+)["']""",
    re.VERBOSE,
)
_VALID_API_PATH = re.compile(r"^/api/[a-z][a-z0-9_-]*/[a-z][a-z0-9_-]*(/.*)?$")
_EXEMPT_PATHS = frozenset({"/api/health", "/api/ready", "/api/metrics", "/api/docs"})


@dataclass
class ApiNamingViolation:
    file: str
    line: int
    route: str
    reason: str


@dataclass
class ApiNamingResult:
    passed: bool
    violations: list[ApiNamingViolation] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def to_dict(self) -> dict:
        return {
            "rule_id": RULE_ID,
            "passed": self.passed,
            "violation_count": self.violation_count,
            "violations": [
                {
                    "file": v.file,
                    "line": v.line,
                    "route": v.route,
                    "reason": v.reason,
                }
                for v in self.violations
            ],
        }


def check_file(path: Path) -> ApiNamingResult:
    """Check a single Python source file for API naming violations."""
    violations: list[ApiNamingViolation] = []

    if not path.exists() or path.suffix != ".py":
        return ApiNamingResult(passed=True)

    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = _ROUTE_PATTERN.search(line)
        if not match:
            continue
        route = match.group(2)
        if route in _EXEMPT_PATHS:
            continue
        if not route.startswith("/api/"):
            violations.append(
                ApiNamingViolation(
                    file=str(path),
                    line=lineno,
                    route=route,
                    reason=f"Route '{route}' does not start with /api/",
                )
            )
        elif not _VALID_API_PATH.match(route):
            violations.append(
                ApiNamingViolation(
                    file=str(path),
                    line=lineno,
                    route=route,
                    reason=(
                        f"Route '{route}' does not match "
                        "/api/{module}/{resource}[/{id}] pattern"
                    ),
                )
            )

    return ApiNamingResult(passed=len(violations) == 0, violations=violations)


def check_directory(root: Path, glob: str = "**/*.py") -> ApiNamingResult:
    """Recursively check all Python files in a directory."""
    all_violations: list[ApiNamingViolation] = []
    for path in sorted(root.glob(glob)):
        result = check_file(path)
        all_violations.extend(result.violations)
    return ApiNamingResult(passed=len(all_violations) == 0, violations=all_violations)
