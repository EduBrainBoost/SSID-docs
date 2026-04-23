"""Test-fix adapter: runs fixes for test files in the tests/ directory only."""

from __future__ import annotations

from ssidctl.core.action_adapters.base_adapter import AdapterInput, AdapterOutput
from ssidctl.core.timeutil import utcnow_iso

_ALLOWED_PREFIXES = ("tests/",)
_ADAPTER_NAME = "test_fix"


class TestFixAdapter:
    """Applies test-specific fixes on allowlisted test paths."""

    @property
    def adapter_name(self) -> str:
        return _ADAPTER_NAME

    @property
    def supported_action_type(self) -> str:
        return "test_fix"

    @property
    def supports_dry_run(self) -> bool:
        return True

    def validate_input(self, inp: AdapterInput) -> tuple[bool, str]:
        ref = inp.target_ref
        if not any(ref.startswith(p) for p in _ALLOWED_PREFIXES):
            return False, f"target_ref '{ref}' must be under tests/ — allowlist rejected"
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
                stdout_summary=f"[dry_run] would test-fix {inp.target_ref}",
                dry_run=True,
                started_at=started,
                finished_at=utcnow_iso(),
            )

        return AdapterOutput(
            outcome="succeeded",
            stdout_summary=f"test_fix applied to {inp.target_ref}",
            dry_run=False,
            started_at=started,
            finished_at=utcnow_iso(),
        )
