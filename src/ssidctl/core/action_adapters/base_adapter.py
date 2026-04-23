"""Base adapter types: AdapterInput and AdapterOutput.

All concrete adapters receive an AdapterInput and return an AdapterOutput.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso


@dataclass
class AdapterInput:
    """Structured input for all action adapters."""

    action_type: str
    target_ref: str
    repo_root: str = ""
    dry_run: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterOutput:
    """Result of adapter execution."""

    outcome: str  # "succeeded" | "blocked" | "failed" | "dry_run"
    stdout_summary: str = ""
    stderr_summary: str = ""
    changed_files: list[str] = field(default_factory=list)
    duration_ms: int = 0
    dry_run: bool = False
    result_hash: str = ""
    error: str | None = None
    started_at: str = field(default_factory=utcnow_iso)
    finished_at: str = field(default_factory=utcnow_iso)

    def compute_result_hash(self) -> str:
        payload = json.dumps(
            {
                "outcome": self.outcome,
                "stdout_summary": self.stdout_summary,
                "stderr_summary": self.stderr_summary,
                "changed_files": sorted(self.changed_files),
            },
            sort_keys=True,
        )
        return sha256_str(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "stdout_summary": self.stdout_summary,
            "stderr_summary": self.stderr_summary,
            "changed_files": self.changed_files,
            "duration_ms": self.duration_ms,
            "dry_run": self.dry_run,
            "result_hash": self.result_hash,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }
