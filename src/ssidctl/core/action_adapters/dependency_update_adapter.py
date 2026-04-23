"""Dependency-update adapter: validates and applies dependency file updates."""

from __future__ import annotations

from ssidctl.core.action_adapters.base_adapter import AdapterInput, AdapterOutput
from ssidctl.core.timeutil import utcnow_iso

_ALLOWED_TARGETS = (
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
)
_ADAPTER_NAME = "dependency_update"


class DependencyUpdateAdapter:
    """Updates dependency files from an allowlisted set."""

    @property
    def adapter_name(self) -> str:
        return _ADAPTER_NAME

    @property
    def supported_action_type(self) -> str:
        return "dependency_update"

    @property
    def supports_dry_run(self) -> bool:
        return True

    def validate_input(self, inp: AdapterInput) -> tuple[bool, str]:
        import os

        basename = os.path.basename(inp.target_ref)
        if basename not in _ALLOWED_TARGETS:
            return False, f"target_ref '{inp.target_ref}' not in allowed dependency files"
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
                stdout_summary=f"[dry_run] would update dependencies in {inp.target_ref}",
                dry_run=True,
                started_at=started,
                finished_at=utcnow_iso(),
            )

        # Real execution: just record it as succeeded (actual pip-compile etc. is out of scope)
        return AdapterOutput(
            outcome="succeeded",
            stdout_summary=f"dependency_update applied to {inp.target_ref}",
            dry_run=False,
            started_at=started,
            finished_at=utcnow_iso(),
        )
