"""Lint-fix adapter: runs ruff --fix on an allowlisted path."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ssidctl.core.action_adapters.base_adapter import AdapterInput, AdapterOutput
from ssidctl.core.timeutil import utcnow_iso

# Only paths under these prefixes are allowed
_ALLOWED_PREFIXES = ("src/", "tests/", "portal/")

_ADAPTER_NAME = "lint_fix"


class LintFixAdapter:
    """Runs ruff --fix on a target Python file."""

    @property
    def adapter_name(self) -> str:
        return _ADAPTER_NAME

    @property
    def supported_action_type(self) -> str:
        return "lint_fix"

    @property
    def supports_dry_run(self) -> bool:
        return True

    def validate_input(self, inp: AdapterInput) -> tuple[bool, str]:
        ref = inp.target_ref
        if not any(ref.startswith(p) for p in _ALLOWED_PREFIXES):
            return False, f"target_ref '{ref}' not in allowlist {_ALLOWED_PREFIXES}"
        if inp.repo_root:
            full = Path(inp.repo_root) / ref
            if not full.exists():
                return False, f"File does not exist: {full}"
        return True, ""

    def execute(self, inp: AdapterInput) -> AdapterOutput:
        started = utcnow_iso()
        ok, reason = self.validate_input(inp)
        if not ok:
            return AdapterOutput(
                outcome="blocked",
                stderr_summary=reason,
                dry_run=inp.dry_run,
                started_at=started,
                finished_at=utcnow_iso(),
            )

        if inp.dry_run:
            return AdapterOutput(
                outcome="dry_run",
                stdout_summary=f"[dry_run] would lint-fix {inp.target_ref}",
                dry_run=True,
                started_at=started,
                finished_at=utcnow_iso(),
            )

        full_path = str(Path(inp.repo_root) / inp.target_ref)
        try:
            result = subprocess.run(
                ["python", "-m", "ruff", "check", "--fix", full_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            outcome = "succeeded" if result.returncode == 0 else "failed"
            return AdapterOutput(
                outcome=outcome,
                stdout_summary=result.stdout[:500],
                stderr_summary=result.stderr[:500],
                changed_files=[inp.target_ref] if outcome == "succeeded" else [],
                dry_run=False,
                started_at=started,
                finished_at=utcnow_iso(),
            )
        except Exception as exc:
            return AdapterOutput(
                outcome="failed",
                stderr_summary=str(exc),
                dry_run=False,
                started_at=started,
                finished_at=utcnow_iso(),
            )
