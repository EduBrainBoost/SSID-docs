"""Cross-Repo Version Manager — multi-repo version coordination.

Reads versions from SSID, SSID-EMS, SSID-open-core, SSID-docs and detects
drift between them.  Proposes coordinated version bumps.

Principle: fail-closed — missing repos or unreadable versions = drift blocker.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path
from typing import Any, Literal

from ssidctl.core.release_state_machine import ReleaseVersion

# ---------------------------------------------------------------------------
# Repo identifiers and version sources
# ---------------------------------------------------------------------------

REPO_VERSION_SOURCES: dict[str, list[str]] = {
    "SSID": ["pyproject.toml"],
    "SSID_EMS": ["pyproject.toml"],
    "SSID_OPEN_CORE": ["pyproject.toml"],
    "SSID_DOCS": ["package.json"],
}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RepoVersion:
    """Version information for a single repo."""

    repo_id: str
    version: ReleaseVersion | None
    source_file: str
    error: str = ""


@dataclass(frozen=True)
class VersionDriftReport:
    """Drift report across all repos."""

    repo_versions: list[RepoVersion]
    has_drift: bool
    drift_details: list[str] = field(default_factory=list)
    timestamp_utc: str = ""


@dataclass(frozen=True)
class BumpProposal:
    """Proposed coordinated version bump."""

    bump_type: Literal["major", "minor", "patch"]
    current_versions: dict[str, str]
    proposed_version: str
    affected_repos: list[str]
    blocked: bool = False
    block_reason: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def _read_pyproject_version(path: Path) -> str | None:
    """Extract version from pyproject.toml."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    m = _PYPROJECT_VERSION_RE.search(text)
    return m.group(1) if m else None


def _read_package_json_version(path: Path) -> str | None:
    """Extract version from package.json."""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("version")


def _read_version(repo_path: Path, source_file: str) -> tuple[str | None, str]:
    """Read version from a source file.  Returns (version_str, error)."""
    full_path = repo_path / source_file
    if not full_path.exists():
        return None, f"File not found: {full_path}"

    if source_file == "pyproject.toml":
        v = _read_pyproject_version(full_path)
    elif source_file == "package.json":
        v = _read_package_json_version(full_path)
    else:
        return None, f"Unknown source file type: {source_file}"

    if v is None:
        return None, f"No version field found in {full_path}"
    return v, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class CrossRepoVersionManager:
    """Manages version coordination across multiple SSID repositories."""

    def __init__(self, repo_paths: dict[str, Path]) -> None:
        """Initialize with repo_id -> local path mapping.

        Args:
            repo_paths: Dict mapping repo IDs (SSID, SSID_EMS, etc.)
                to their local filesystem paths.
        """
        self._repo_paths = repo_paths

    def read_all_versions(self) -> list[RepoVersion]:
        """Read versions from all configured repos.  Fail-closed on errors."""
        results: list[RepoVersion] = []
        for repo_id, sources in REPO_VERSION_SOURCES.items():
            repo_path = self._repo_paths.get(repo_id)
            if repo_path is None:
                results.append(
                    RepoVersion(
                        repo_id=repo_id,
                        version=None,
                        source_file="",
                        error=f"Repo path not configured for {repo_id}",
                    )
                )
                continue

            for source_file in sources:
                v_str, err = _read_version(repo_path, source_file)
                if err:
                    results.append(
                        RepoVersion(
                            repo_id=repo_id,
                            version=None,
                            source_file=source_file,
                            error=err,
                        )
                    )
                    continue

                try:
                    version = ReleaseVersion.parse(v_str)  # type: ignore[arg-type]
                except ValueError as exc:
                    results.append(
                        RepoVersion(
                            repo_id=repo_id,
                            version=None,
                            source_file=source_file,
                            error=f"Invalid semver: {exc}",
                        )
                    )
                    continue

                results.append(
                    RepoVersion(
                        repo_id=repo_id,
                        version=version,
                        source_file=source_file,
                    )
                )

        return results

    def detect_drift(self) -> VersionDriftReport:
        """Detect version drift across all repos.

        Drift is detected when:
        - Any repo has an unreadable version (error)
        - Major/minor versions differ across repos
        """
        from datetime import datetime as _dt

        versions = self.read_all_versions()
        drift_details: list[str] = []

        # Check for errors (fail-closed: errors = drift)
        for rv in versions:
            if rv.error:
                drift_details.append(f"{rv.repo_id}: {rv.error}")

        # Check for version differences
        valid_versions = {rv.repo_id: rv.version for rv in versions if rv.version is not None}
        if len(valid_versions) > 1:
            majors = {r: v.major for r, v in valid_versions.items()}
            minors = {r: v.minor for r, v in valid_versions.items()}

            if len(set(majors.values())) > 1:
                drift_details.append(f"Major version drift: {majors}")
            elif len(set(minors.values())) > 1:
                drift_details.append(f"Minor version drift: {minors}")

        has_drift = len(drift_details) > 0
        ts = _dt.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return VersionDriftReport(
            repo_versions=versions,
            has_drift=has_drift,
            drift_details=drift_details,
            timestamp_utc=ts,
        )

    def propose_bump(
        self,
        bump_type: Literal["major", "minor", "patch"],
    ) -> BumpProposal:
        """Propose a coordinated version bump across all repos.

        Fail-closed: if drift exists, the proposal is blocked.
        """
        drift = self.detect_drift()
        current = {
            rv.repo_id: str(rv.version) for rv in drift.repo_versions if rv.version is not None
        }

        if drift.has_drift:
            return BumpProposal(
                bump_type=bump_type,
                current_versions=current,
                proposed_version="",
                affected_repos=list(current.keys()),
                blocked=True,
                block_reason=f"Version drift detected: {'; '.join(drift.drift_details)}",
            )

        if not current:
            return BumpProposal(
                bump_type=bump_type,
                current_versions={},
                proposed_version="",
                affected_repos=[],
                blocked=True,
                block_reason="No readable versions found",
            )

        # Use the highest version as baseline
        baseline = max(
            (ReleaseVersion.parse(v) for v in current.values()),
        )

        if bump_type == "major":
            proposed = baseline.bump_major()
        elif bump_type == "minor":
            proposed = baseline.bump_minor()
        else:
            proposed = baseline.bump_patch()

        return BumpProposal(
            bump_type=bump_type,
            current_versions=current,
            proposed_version=str(proposed),
            affected_repos=list(current.keys()),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize current state for reporting."""
        drift = self.detect_drift()
        return {
            "repo_versions": [
                {
                    "repo_id": rv.repo_id,
                    "version": str(rv.version) if rv.version else None,
                    "source_file": rv.source_file,
                    "error": rv.error,
                }
                for rv in drift.repo_versions
            ],
            "has_drift": drift.has_drift,
            "drift_details": drift.drift_details,
            "timestamp_utc": drift.timestamp_utc,
        }
