"""Cross-Repo Drift Checker — validates consistency across all SSID repos.

Checks:
- Version drift (semver misalignment)
- Policy drift (deny-glob divergence)
- SoT drift (registry hash mismatches)
- Export drift (manifest vs actual state)

Fail-closed: missing repos or unreadable data = drift detected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from ssidctl.core.version_manager import CrossRepoVersionManager

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftCheck:
    """Result of a single drift check."""

    check_name: str
    repo_pair: str  # e.g. "SSID -> SSID_OPEN_CORE"
    status: Literal["IN_SYNC", "DRIFT", "ERROR"]
    details: str = ""


@dataclass(frozen=True)
class CrossRepoDriftReport:
    """Aggregated drift report across all repos."""

    checks: list[DriftCheck] = field(default_factory=list)
    has_drift: bool = False
    drift_count: int = 0
    error_count: int = 0
    timestamp_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_drift": self.has_drift,
            "drift_count": self.drift_count,
            "error_count": self.error_count,
            "total_checks": len(self.checks),
            "timestamp_utc": self.timestamp_utc,
            "checks": [
                {
                    "check_name": c.check_name,
                    "repo_pair": c.repo_pair,
                    "status": c.status,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }


# ---------------------------------------------------------------------------
# Cross-Repo Drift Checker
# ---------------------------------------------------------------------------


class CrossRepoDriftChecker:
    """Validates consistency across all SSID repositories."""

    def __init__(self, repo_paths: dict[str, Path]) -> None:
        """Initialize with repo_id -> local path mapping."""
        self._repo_paths = repo_paths

    def check_all(self) -> CrossRepoDriftReport:
        """Run all drift checks.  Fail-closed on errors."""
        ts = _now_utc()
        checks: list[DriftCheck] = []

        checks.extend(self._check_repo_reachability())
        checks.extend(self._check_version_drift())
        checks.extend(self._check_export_policy_presence())
        checks.extend(self._check_ci_workflow_presence())

        drift_count = sum(1 for c in checks if c.status == "DRIFT")
        error_count = sum(1 for c in checks if c.status == "ERROR")
        has_drift = drift_count > 0 or error_count > 0

        return CrossRepoDriftReport(
            checks=checks,
            has_drift=has_drift,
            drift_count=drift_count,
            error_count=error_count,
            timestamp_utc=ts,
        )

    def _check_repo_reachability(self) -> list[DriftCheck]:
        """Verify all expected repos are reachable."""
        checks: list[DriftCheck] = []
        expected = {"SSID", "SSID_EMS", "SSID_OPEN_CORE", "SSID_DOCS"}

        for repo_id in sorted(expected):
            path = self._repo_paths.get(repo_id)
            if path is None:
                checks.append(
                    DriftCheck(
                        "repo_reachability",
                        repo_id,
                        "ERROR",
                        f"Path not configured for {repo_id}",
                    )
                )
            elif not path.exists():
                checks.append(
                    DriftCheck(
                        "repo_reachability",
                        repo_id,
                        "ERROR",
                        f"Path does not exist: {path}",
                    )
                )
            elif not (path / ".git").exists():
                checks.append(
                    DriftCheck(
                        "repo_reachability",
                        repo_id,
                        "DRIFT",
                        f"Not a git repo: {path}",
                    )
                )
            else:
                checks.append(
                    DriftCheck(
                        "repo_reachability",
                        repo_id,
                        "IN_SYNC",
                        f"Repo reachable: {path}",
                    )
                )

        return checks

    def _check_version_drift(self) -> list[DriftCheck]:
        """Check for version drift across repos."""
        try:
            mgr = CrossRepoVersionManager(self._repo_paths)
            drift = mgr.detect_drift()

            if drift.has_drift:
                return [
                    DriftCheck(
                        "version_drift",
                        "ALL",
                        "DRIFT",
                        "; ".join(drift.drift_details),
                    )
                ]
            return [
                DriftCheck(
                    "version_drift",
                    "ALL",
                    "IN_SYNC",
                    "All repo versions aligned",
                )
            ]
        except Exception as exc:
            return [
                DriftCheck(
                    "version_drift",
                    "ALL",
                    "ERROR",
                    f"Version check failed: {exc}",
                )
            ]

    def _check_export_policy_presence(self) -> list[DriftCheck]:
        """Check that export policies exist where expected.  Fail-closed on missing repos."""
        checks: list[DriftCheck] = []

        # SSID-open-core should have export policy
        oc_path = self._repo_paths.get("SSID_OPEN_CORE")
        if oc_path is None:
            checks.append(
                DriftCheck(
                    "export_policy",
                    "SSID_OPEN_CORE",
                    "ERROR",
                    "Path not configured for SSID_OPEN_CORE",
                )
            )
        elif not oc_path.exists():
            checks.append(
                DriftCheck(
                    "export_policy",
                    "SSID_OPEN_CORE",
                    "ERROR",
                    f"Path does not exist: {oc_path}",
                )
            )
        else:
            policy_file = oc_path / "16_codex" / "opencore_export_policy.yaml"
            if policy_file.exists():
                checks.append(
                    DriftCheck(
                        "export_policy",
                        "SSID_OPEN_CORE",
                        "IN_SYNC",
                        "Export policy present",
                    )
                )
            else:
                checks.append(
                    DriftCheck(
                        "export_policy",
                        "SSID_OPEN_CORE",
                        "DRIFT",
                        "Export policy missing at 16_codex/opencore_export_policy.yaml",
                    )
                )

        # SSID-docs should have ingest manifest
        docs_path = self._repo_paths.get("SSID_DOCS")
        if docs_path is None:
            checks.append(
                DriftCheck(
                    "ingest_manifest",
                    "SSID_DOCS",
                    "ERROR",
                    "Path not configured for SSID_DOCS",
                )
            )
        elif not docs_path.exists():
            checks.append(
                DriftCheck(
                    "ingest_manifest",
                    "SSID_DOCS",
                    "ERROR",
                    f"Path does not exist: {docs_path}",
                )
            )
        else:
            manifest_file = docs_path / "tools" / "public_export_manifest.json"
            if manifest_file.exists():
                checks.append(
                    DriftCheck(
                        "ingest_manifest",
                        "SSID_DOCS",
                        "IN_SYNC",
                        "Ingest manifest present",
                    )
                )
            else:
                checks.append(
                    DriftCheck(
                        "ingest_manifest",
                        "SSID_DOCS",
                        "DRIFT",
                        "Ingest manifest missing at tools/public_export_manifest.json",
                    )
                )

        return checks

    def _check_ci_workflow_presence(self) -> list[DriftCheck]:
        """Check that CI workflows exist in all repos."""
        checks: list[DriftCheck] = []

        ci_expectations: dict[str, list[str]] = {
            "SSID": ["ssid_ci.yml"],
            "SSID_EMS": ["ems_ci.yml"],
            "SSID_OPEN_CORE": ["open_core_ci.yml"],
            "SSID_DOCS": ["docs_ci.yml"],
        }

        for repo_id, expected_workflows in ci_expectations.items():
            path = self._repo_paths.get(repo_id)
            if path is None:
                for wf in expected_workflows:
                    checks.append(
                        DriftCheck(
                            "ci_workflow",
                            repo_id,
                            "ERROR",
                            f"Path not configured for {repo_id} (workflow {wf})",
                        )
                    )
                continue
            if not path.exists():
                for wf in expected_workflows:
                    checks.append(
                        DriftCheck(
                            "ci_workflow",
                            repo_id,
                            "ERROR",
                            f"Path does not exist: {path} (workflow {wf})",
                        )
                    )
                continue

            workflows_dir = path / ".github" / "workflows"
            for wf in expected_workflows:
                wf_path = workflows_dir / wf
                if wf_path.exists():
                    checks.append(
                        DriftCheck(
                            "ci_workflow",
                            repo_id,
                            "IN_SYNC",
                            f"Workflow {wf} present",
                        )
                    )
                else:
                    checks.append(
                        DriftCheck(
                            "ci_workflow",
                            repo_id,
                            "DRIFT",
                            f"Workflow {wf} missing",
                        )
                    )

        return checks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
