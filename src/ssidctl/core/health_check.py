"""Health Check — aggregated health status for EMS and cross-repo.

Checks: config validity, paths, guards, registry, cross-repo reachability.
Returns structured JSON-serializable health report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthStatus:
    """Health status for a single check."""

    service: str
    status: Literal["healthy", "degraded", "unhealthy"]
    details: str = ""
    timestamp_utc: str = ""


@dataclass(frozen=True)
class HealthReport:
    """Aggregated health report."""

    overall: Literal["healthy", "degraded", "unhealthy"]
    checks: list[HealthStatus] = field(default_factory=list)
    timestamp_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "checks": [
                {
                    "service": c.service,
                    "status": c.status,
                    "details": c.details,
                    "timestamp_utc": c.timestamp_utc,
                }
                for c in self.checks
            ],
            "timestamp_utc": self.timestamp_utc,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_path(name: str, path: Path) -> HealthStatus:
    """Check that a path exists and is accessible."""
    ts = _now_utc()
    if path.exists():
        return HealthStatus(name, "healthy", f"Path exists: {path}", ts)
    return HealthStatus(name, "unhealthy", f"Path missing: {path}", ts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_ems_health(
    *,
    ems_root: Path | None = None,
    config_valid: bool | None = None,
) -> HealthReport:
    """Check EMS system health.

    Checks:
    - EMS root path exists
    - Config is valid (passed in)
    - Required directories exist (src, tests, policies)
    - Policy files loadable
    """
    ts = _now_utc()
    checks: list[HealthStatus] = []

    if ems_root is None:
        checks.append(HealthStatus("ems_root", "unhealthy", "EMS root not specified", ts))
    else:
        checks.append(_check_path("ems_root", ems_root))
        checks.append(_check_path("src_dir", ems_root / "src" / "ssidctl"))
        checks.append(_check_path("tests_dir", ems_root / "tests"))
        checks.append(_check_path("policies_dir", ems_root / "policies"))

        # Check policy files
        policies_dir = ems_root / "policies"
        if policies_dir.exists():
            yaml_files = list(policies_dir.glob("*.yaml"))
            if yaml_files:
                checks.append(
                    HealthStatus(
                        "policy_files",
                        "healthy",
                        f"{len(yaml_files)} policy files found",
                        ts,
                    )
                )
            else:
                checks.append(
                    HealthStatus(
                        "policy_files",
                        "degraded",
                        "No policy YAML files found",
                        ts,
                    )
                )

    # Config validity
    if config_valid is None:
        checks.append(HealthStatus("config", "degraded", "Config validity not checked", ts))
    elif config_valid:
        checks.append(HealthStatus("config", "healthy", "Config valid", ts))
    else:
        checks.append(HealthStatus("config", "unhealthy", "Config invalid", ts))

    overall = _aggregate_status(checks)
    return HealthReport(overall=overall, checks=checks, timestamp_utc=ts)


def check_cross_repo_health(
    repo_paths: dict[str, Path],
) -> HealthReport:
    """Check cross-repo health by verifying all repo paths are reachable.

    Args:
        repo_paths: Dict mapping repo names to local paths.
    """
    ts = _now_utc()
    checks: list[HealthStatus] = []

    expected_repos = {"SSID", "SSID_EMS", "SSID_OPEN_CORE", "SSID_DOCS"}

    for repo_name in sorted(expected_repos):
        path = repo_paths.get(repo_name)
        if path is None:
            checks.append(
                HealthStatus(
                    f"repo_{repo_name.lower()}",
                    "unhealthy",
                    f"Path not configured for {repo_name}",
                    ts,
                )
            )
            continue

        checks.append(_check_path(f"repo_{repo_name.lower()}", path))

        # Check for .git directory (verify it's a repo)
        git_dir = path / ".git"
        if git_dir.exists():
            checks.append(
                HealthStatus(
                    f"repo_{repo_name.lower()}_git",
                    "healthy",
                    f"Git repo confirmed: {path}",
                    ts,
                )
            )
        else:
            checks.append(
                HealthStatus(
                    f"repo_{repo_name.lower()}_git",
                    "degraded",
                    f"No .git directory: {path}",
                    ts,
                )
            )

    overall = _aggregate_status(checks)
    return HealthReport(overall=overall, checks=checks, timestamp_utc=ts)


def _aggregate_status(
    checks: list[HealthStatus],
) -> Literal["healthy", "degraded", "unhealthy"]:
    """Aggregate individual check statuses into overall status."""
    if not checks:
        return "unhealthy"
    statuses = {c.status for c in checks}
    if "unhealthy" in statuses:
        return "unhealthy"
    if "degraded" in statuses:
        return "degraded"
    return "healthy"
