"""Drift sentinel — local vs remote main comparison.

Git-only, no gh CLI required.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class DriftError(Exception):
    pass


@dataclass(frozen=True)
class DriftReport:
    local_sha: str
    remote_sha: str | None
    is_synced: bool
    ahead: int
    behind: int
    dirty_files: int
    worktrees: list[str]

    @property
    def has_drift(self) -> bool:
        return not self.is_synced or self.ahead > 0 or self.behind > 0


class DriftSentinel:
    """Checks local main vs origin/main and worktree cleanliness."""

    def __init__(self, repo_path: Path) -> None:
        self._repo = repo_path

    def check(self, branch: str = "main") -> DriftReport:
        """Run drift check on the repo."""
        try:
            local_sha = self._git_output("rev-parse", branch)
        except DriftError as err:
            raise DriftError(f"Branch not found: {branch}") from err
        if not local_sha:
            raise DriftError(f"Branch not found: {branch}")

        # Fetch remote (non-fatal if no remote)
        remote_sha = None
        ahead = 0
        behind = 0
        try:
            self._git("fetch", "origin", branch, "--quiet")
            remote_sha = self._git_output("rev-parse", f"origin/{branch}")
            if remote_sha and local_sha:
                ahead = self._count_commits(f"origin/{branch}..{branch}")
                behind = self._count_commits(f"{branch}..origin/{branch}")
        except DriftError:
            pass  # No remote configured

        is_synced = local_sha == remote_sha if remote_sha else True

        # Dirty files
        dirty_output = self._git_output("status", "--porcelain")
        dirty_files = len([line for line in dirty_output.splitlines() if line.strip()])

        # Worktrees
        wt_output = self._git_output("worktree", "list", "--porcelain")
        repo_resolved = self._repo.resolve()
        worktrees = []
        for line in wt_output.splitlines():
            if line.startswith("worktree "):
                wt_path_str = line[len("worktree ") :]
                wt_resolved = Path(wt_path_str).resolve()
                # Skip the main worktree (normalize for cross-platform)
                if wt_resolved != repo_resolved:
                    worktrees.append(wt_path_str)

        return DriftReport(
            local_sha=local_sha,
            remote_sha=remote_sha,
            is_synced=is_synced,
            ahead=ahead,
            behind=behind,
            dirty_files=dirty_files,
            worktrees=worktrees,
        )

    def _count_commits(self, range_spec: str) -> int:
        output = self._git_output("rev-list", "--count", range_spec)
        try:
            return int(output)
        except ValueError:
            return 0

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise DriftError(f"Git failed: {result.stderr.strip()}")
        return result.stdout

    def _git_output(self, *args: str) -> str:
        return self._git(*args).strip()


# ---------------------------------------------------------------------------
# SoT Contract drift (G-016)
# ---------------------------------------------------------------------------


import json as _json  # noqa: E402


@dataclass(frozen=True)
class SoTContractFinding:
    """A single drift finding between EMS and SSID JSON schemas."""

    field: str
    detail: str


@dataclass
class SoTContractReport:
    """Report produced by compare_sot_contracts."""

    ems_path: str
    ssid_path: str
    findings: list[SoTContractFinding] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.findings is None:
            self.findings = []

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0


def _load_json(path: Path) -> tuple[dict | None, str | None]:
    """Load JSON from path. Returns (data, error_detail) pair."""
    try:
        return _json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"{path.name} not found"
    except _json.JSONDecodeError as exc:
        return None, f"parse error: {exc}"


def compare_sot_contracts(
    ems_schema_path: Path,
    ssid_schema_path: Path,
) -> SoTContractReport:
    """Compare EMS and SSID JSON schemas for drift (G-016).

    Checks:
    - Both files must exist and be valid JSON.
    - Required fields in SSID must be present in EMS.
    - Enum values in SSID must be a subset of (or equal to) EMS enums.
    """
    report = SoTContractReport(
        ems_path=str(ems_schema_path),
        ssid_path=str(ssid_schema_path),
    )

    ems_data, ems_err = _load_json(ems_schema_path)
    ssid_data, ssid_err = _load_json(ssid_schema_path)

    if ems_err:
        report.findings.append(SoTContractFinding(field="", detail=f"EMS schema: {ems_err}"))
    if ssid_err:
        report.findings.append(SoTContractFinding(field="", detail=f"SSID schema: {ssid_err}"))

    if report.findings:
        return report

    # --- required field drift ---
    ems_required = set(ems_data.get("required", []))  # type: ignore[union-attr]
    ssid_required = set(ssid_data.get("required", []))  # type: ignore[union-attr]

    for field in ssid_required - ems_required:
        report.findings.append(
            SoTContractFinding(
                field=field, detail=f"required field '{field}' missing from EMS schema"
            )  # noqa: E501
        )

    # --- enum value drift ---
    ems_props = ems_data.get("properties", {})  # type: ignore[union-attr]
    ssid_props = ssid_data.get("properties", {})  # type: ignore[union-attr]

    for prop_name, ssid_prop in ssid_props.items():
        # Navigate into array items if present
        ssid_items = ssid_prop.get("items", ssid_prop)
        ssid_enum = set(ssid_items.get("enum", []))
        if not ssid_enum:
            continue

        ems_prop = ems_props.get(prop_name, {})
        ems_items = ems_prop.get("items", ems_prop)
        ems_enum = set(ems_items.get("enum", []))

        for value in ssid_enum - ems_enum:
            report.findings.append(
                SoTContractFinding(
                    field=prop_name,
                    detail=f"enum value '{value}' present in SSID schema but missing from EMS",
                )
            )

    return report
