"""Startup Validator — fail-closed startup checks.

Validates critical preconditions before the EMS system starts.
Blocks startup if any critical check fails.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StartupCheck:
    """Result of a single startup check."""

    name: str
    passed: bool
    critical: bool
    detail: str = ""


@dataclass(frozen=True)
class StartupReport:
    """Aggregated startup validation report."""

    can_start: bool
    checks: list[StartupCheck] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    timestamp_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_start": self.can_start,
            "checks": [
                {"name": c.name, "passed": c.passed, "critical": c.critical, "detail": c.detail}
                for c in self.checks
            ],
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "timestamp_utc": self.timestamp_utc,
        }


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_startup(
    *,
    ems_root: Path | None = None,
    required_env_vars: list[str] | None = None,
    required_paths: list[Path] | None = None,
    min_python: tuple[int, int] = (3, 11),
) -> StartupReport:
    """Validate all startup preconditions.

    Fail-closed: any critical failure blocks startup.

    Args:
        ems_root: Path to EMS repository root.
        required_env_vars: Environment variables that must be set.
        required_paths: Filesystem paths that must exist.
        min_python: Minimum Python version (major, minor).

    Returns:
        StartupReport with can_start=True/False.
    """
    import os

    checks: list[StartupCheck] = []
    critical_failures: list[str] = []
    warnings: list[str] = []

    # 1. Python version
    py_ver = sys.version_info[:2]
    if py_ver >= min_python:
        checks.append(
            StartupCheck(
                "python_version",
                True,
                True,
                f"Python {py_ver[0]}.{py_ver[1]} >= {min_python[0]}.{min_python[1]}",
            )
        )
    else:
        detail = f"Python {py_ver[0]}.{py_ver[1]} < {min_python[0]}.{min_python[1]}"
        checks.append(StartupCheck("python_version", False, True, detail))
        critical_failures.append(detail)

    # 2. EMS root
    if ems_root is None:
        checks.append(
            StartupCheck(
                "ems_root",
                False,
                True,
                "EMS root not specified",
            )
        )
        critical_failures.append("EMS root not specified")
    elif not ems_root.exists():
        detail = f"EMS root does not exist: {ems_root}"
        checks.append(StartupCheck("ems_root", False, True, detail))
        critical_failures.append(detail)
    else:
        checks.append(
            StartupCheck(
                "ems_root",
                True,
                True,
                f"EMS root exists: {ems_root}",
            )
        )

    # 3. Required env vars
    if required_env_vars:
        for var in required_env_vars:
            val = os.environ.get(var)
            if val:
                checks.append(
                    StartupCheck(
                        f"env_{var}",
                        True,
                        False,
                        f"{var} is set",
                    )
                )
            else:
                detail = f"Environment variable {var} not set"
                checks.append(StartupCheck(f"env_{var}", False, False, detail))
                warnings.append(detail)

    # 4. Required paths
    if required_paths:
        for p in required_paths:
            if p.exists():
                checks.append(
                    StartupCheck(
                        f"path_{p.name}",
                        True,
                        True,
                        f"Path exists: {p}",
                    )
                )
            else:
                detail = f"Required path missing: {p}"
                checks.append(StartupCheck(f"path_{p.name}", False, True, detail))
                critical_failures.append(detail)

    # 5. Policy directory
    if ems_root and ems_root.exists():
        policies = ems_root / "policies"
        if policies.exists() and any(policies.glob("*.yaml")):
            checks.append(
                StartupCheck(
                    "policies",
                    True,
                    True,
                    "Policy directory with YAML files found",
                )
            )
        else:
            detail = "No policy YAML files found"
            checks.append(StartupCheck("policies", False, True, detail))
            critical_failures.append(detail)

    can_start = len(critical_failures) == 0
    return StartupReport(
        can_start=can_start,
        checks=checks,
        critical_failures=critical_failures,
        warnings=warnings,
        timestamp_utc=_now_utc(),
    )
