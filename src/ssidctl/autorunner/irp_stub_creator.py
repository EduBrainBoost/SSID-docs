"""AR-04 IRP Stub Creator — creates incident_response_plan.md stubs for missing roots.

P3: dry_run=True writes files in place (no git ops) for testing + CI verification.
P4: dry_run=False will create git worktree branch + commit stubs → PR-ready.

Never writes directly to SSID main — always via worktree branch (P4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

IRP_TEMPLATE_PATH_IN_SSID = "05_documentation/templates/TEMPLATE_INCIDENT_RESPONSE.md"
IRP_TARGET_RELATIVE = "docs/incident_response_plan.md"


@dataclass
class IRPStubResult:
    stubs_created: int
    stub_paths: list[str] = field(default_factory=list)
    branch_name: str = ""
    dry_run: bool = True
    errors: list[str] = field(default_factory=list)


class IRPStubCreator:
    def __init__(self, ssid_root: str | Path) -> None:
        self._root = Path(ssid_root)

    def _get_template(self) -> str:
        template_path = self._root / IRP_TEMPLATE_PATH_IN_SSID
        if not template_path.exists():
            raise FileNotFoundError(f"IRP template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")

    def create_stubs(
        self,
        missing_roots: list[str],
        dry_run: bool = True,
        branch_name: str = "",
    ) -> IRPStubResult:
        """Create IRP stub files for missing_roots.

        Args:
            missing_roots: Root directory names (relative to SSID root) missing IRP
            dry_run: If True, write files in place (no git ops). P4 wires False path.
            branch_name: Branch name for git worktree (only when dry_run=False, P4).

        Returns:
            IRPStubResult with count of newly written stubs.
        """
        if not missing_roots:
            return IRPStubResult(stubs_created=0, dry_run=dry_run)

        template = self._get_template()
        stub_paths = []
        errors = []

        for root_name in missing_roots:
            target = self._root / root_name / IRP_TARGET_RELATIVE
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_text(template, encoding="utf-8")
                    stub_paths.append(str(target))
                # If target already exists: idempotent — do not count as created
            except OSError as exc:
                errors.append(f"{root_name}: {exc}")

        return IRPStubResult(
            stubs_created=len(stub_paths),
            stub_paths=stub_paths,
            branch_name=branch_name,
            dry_run=dry_run,
            errors=errors,
        )
