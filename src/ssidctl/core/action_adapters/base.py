"""Action adapter protocol and result types.

All adapters must conform to the ActionAdapter protocol. No runtime discovery —
adapters are registered statically at import time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ValidationResult:
    """Result of adapter input validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class AdapterResult:
    """Deterministic result from adapter execution."""

    exit_code: int
    stdout_summary: str = ""
    stderr_summary: str = ""
    changed_files: list[str] = field(default_factory=list)
    duration_ms: int = 0
    dry_run: bool = False
    result_hash: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout_summary": self.stdout_summary,
            "stderr_summary": self.stderr_summary,
            "changed_files": self.changed_files,
            "duration_ms": self.duration_ms,
            "dry_run": self.dry_run,
            "result_hash": self.result_hash,
            "error": self.error,
        }


@runtime_checkable
class ActionAdapter(Protocol):
    """Protocol for all action adapters. No runtime discovery."""

    @property
    def name(self) -> str: ...

    @property
    def supported_action_type(self) -> str: ...

    @property
    def supports_dry_run(self) -> bool: ...

    def validate_input(self, payload: dict[str, Any]) -> ValidationResult: ...

    def execute(self, payload: dict[str, Any], dry_run: bool = False) -> AdapterResult: ...
