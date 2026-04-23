"""SOT_AGENT_039 -- Pydantic <-> TypeScript type mapping consistency check.

Rule: For each Pydantic model exported from the backend, a corresponding
TypeScript interface/type must exist in the frontend type declarations.
Checks for name-level consistency (structural field checking is out of scope).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RULE_ID = "SOT_AGENT_039"
RULE_DESCRIPTION = "Pydantic models must have matching TypeScript interface/type declarations"

# Matches: class Foo(BaseModel): or class Foo(BaseModel, ...):
_PYDANTIC_MODEL = re.compile(
    r"^class\s+([A-Za-z][A-Za-z0-9_]*)\s*\(\s*(?:[A-Za-z0-9_.]*\s*,\s*)*"
    r"(?:BaseModel|pydantic\.BaseModel)[^)]*\)\s*:",
    re.MULTILINE,
)

# Matches: export interface Foo  or  export type Foo =
_TS_INTERFACE = re.compile(r"export\s+(?:interface|type)\s+([A-Za-z][A-Za-z0-9_]*)")

# Models with these suffixes are typically internal helpers, not API contracts
_SKIP_SUFFIXES = ("Config", "Settings", "Meta", "Internal", "Mixin", "Base")


@dataclass
class TypeConsistencyViolation:
    model_name: str
    source_file: str
    reason: str


@dataclass
class TypeConsistencyResult:
    passed: bool
    pydantic_models: list[str] = field(default_factory=list)
    typescript_types: list[str] = field(default_factory=list)
    violations: list[TypeConsistencyViolation] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def to_dict(self) -> dict:
        return {
            "rule_id": RULE_ID,
            "passed": self.passed,
            "pydantic_model_count": len(self.pydantic_models),
            "typescript_type_count": len(self.typescript_types),
            "violation_count": self.violation_count,
            "violations": [
                {
                    "model_name": v.model_name,
                    "source_file": v.source_file,
                    "reason": v.reason,
                }
                for v in self.violations
            ],
        }


def collect_pydantic_models(backend_root: Path) -> dict[str, str]:
    """Return {ModelName: file_path} for all Pydantic models found."""
    models: dict[str, str] = {}
    for py_file in sorted(backend_root.glob("**/*.py")):
        text = py_file.read_text(encoding="utf-8", errors="replace")
        for match in _PYDANTIC_MODEL.finditer(text):
            name = match.group(1)
            if any(name.endswith(s) for s in _SKIP_SUFFIXES):
                continue
            models[name] = str(py_file)
    return models


def collect_typescript_types(frontend_root: Path) -> set[str]:
    """Return set of TypeScript interface/type names found in .ts/.tsx files."""
    names: set[str] = set()
    for ts_file in list(sorted(frontend_root.glob("**/*.ts"))) + list(
        sorted(frontend_root.glob("**/*.tsx"))
    ):
        text = ts_file.read_text(encoding="utf-8", errors="replace")
        for match in _TS_INTERFACE.finditer(text):
            names.add(match.group(1))
    return names


def check_consistency(
    backend_root: Path,
    frontend_root: Path,
    *,
    require_all: bool = False,
) -> TypeConsistencyResult:
    """Check that Pydantic models have matching TypeScript declarations.

    Args:
        backend_root: Root directory of the Python backend.
        frontend_root: Root directory of the TypeScript frontend.
        require_all: If True, every Pydantic model must have a TS equivalent.
                     If False (default), missing TS types are reported but
                     do not fail the check (advisory mode).
    """
    pydantic_models = collect_pydantic_models(backend_root)
    ts_types = collect_typescript_types(frontend_root)

    violations: list[TypeConsistencyViolation] = []

    for model_name, source_file in sorted(pydantic_models.items()):
        if model_name not in ts_types:
            violations.append(
                TypeConsistencyViolation(
                    model_name=model_name,
                    source_file=source_file,
                    reason=(
                        f"Pydantic model '{model_name}' has no matching "
                        "TypeScript interface/type declaration"
                    ),
                )
            )

    passed = len(violations) == 0 if require_all else True

    return TypeConsistencyResult(
        passed=passed,
        pydantic_models=list(pydantic_models.keys()),
        typescript_types=sorted(ts_types),
        violations=violations,
    )
