"""SOT_AGENT_038 -- PascalCase component naming enforcement.

Rule: React/TypeScript components exported from .tsx/.ts files must use
PascalCase naming. Default exports must also be PascalCase identifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RULE_ID = "SOT_AGENT_038"
RULE_DESCRIPTION = "React/TypeScript components must use PascalCase naming"

_PASCAL_CASE = re.compile(r"^[A-Z][A-Za-z0-9]*$")

# Matches: export function/const/class Foo, export default Foo
_EXPORT_NAMED = re.compile(
    r"^export\s+(?:default\s+)?(?:function|const|class|abstract\s+class)"
    r"\s+([A-Za-z_][A-Za-z0-9_]*)"
)
_EXPORT_DEFAULT_IDENT = re.compile(r"^export\s+default\s+([A-Za-z_][A-Za-z0-9_]*)\s*;?$")

# Component heuristics: files that contain JSX return or React.FC annotation
_JSX_RETURN = re.compile(r"return\s*\(?\s*<[A-Z/]")
_REACT_FC = re.compile(r":\s*React\.FC|:\s*FC<|:\s*React\.ReactElement|:\s*JSX\.Element")

COMPONENT_EXTENSIONS = frozenset({".tsx", ".jsx"})
SKIP_PATTERNS = frozenset({"index", "main", "app", "types", "constants", "utils"})


@dataclass
class ComponentNamingViolation:
    file: str
    line: int
    name: str
    reason: str


@dataclass
class ComponentNamingResult:
    passed: bool
    violations: list[ComponentNamingViolation] = field(default_factory=list)

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
                    "name": v.name,
                    "reason": v.reason,
                }
                for v in self.violations
            ],
        }


def _is_component_file(text: str) -> bool:
    """Heuristic: does the file contain JSX or React.FC annotations?"""
    return bool(_JSX_RETURN.search(text) or _REACT_FC.search(text))


def check_file(path: Path) -> ComponentNamingResult:
    """Check a single TypeScript/React file for PascalCase violations."""
    violations: list[ComponentNamingViolation] = []

    if not path.exists() or path.suffix not in COMPONENT_EXTENSIONS:
        return ComponentNamingResult(passed=True)

    text = path.read_text(encoding="utf-8", errors="replace")

    if not _is_component_file(text):
        return ComponentNamingResult(passed=True)

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        for pattern in (_EXPORT_NAMED, _EXPORT_DEFAULT_IDENT):
            match = pattern.match(stripped)
            if not match:
                continue
            name = match.group(1)
            if name in SKIP_PATTERNS:
                continue
            if not _PASCAL_CASE.match(name):
                violations.append(
                    ComponentNamingViolation(
                        file=str(path),
                        line=lineno,
                        name=name,
                        reason=(
                            f"Component '{name}' does not use PascalCase; "
                            "rename to start with an uppercase letter"
                        ),
                    )
                )

    return ComponentNamingResult(passed=len(violations) == 0, violations=violations)


def check_directory(root: Path, glob: str = "**/*.tsx") -> ComponentNamingResult:
    """Recursively check all TSX files in a directory."""
    all_violations: list[ComponentNamingViolation] = []
    for path in sorted(root.glob(glob)):
        result = check_file(path)
        all_violations.extend(result.violations)
    return ComponentNamingResult(passed=len(all_violations) == 0, violations=all_violations)
