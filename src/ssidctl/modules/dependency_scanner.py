"""Dependency Scanner — static pattern-based dependency risk analysis.

Checks requirements.txt files for known risky patterns such as unpinned
versions, overly broad specifiers, and known-problematic packages.
Uses only stdlib (pathlib, re).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class DependencyScanner:
    """Scan Python dependency files for version-pinning risks."""

    # Packages frequently flagged in supply-chain advisories (static list).
    KNOWN_RISKY_PACKAGES: frozenset[str] = frozenset(
        {
            "requests",
            "urllib3",
            "cryptography",
            "paramiko",
            "pyyaml",
            "jinja2",
            "pillow",
            "setuptools",
            "pip",
            "wheel",
            "numpy",
            "lxml",
        }
    )

    # Version specifier classification ─ ordered by risk (highest first).
    _SPEC_PATTERNS: list[tuple[str, str, str]] = [
        # (regex_for_version_spec, risk_level, recommendation)
        (
            r"^$",
            "high",
            "Pin to an exact version with == to ensure reproducible builds.",
        ),
        (
            r"^>=",
            "medium",
            "Use == for production pins; >= allows untested upgrades.",
        ),
        (
            r"^~=",
            "low",
            "Compatible-release (~=) is acceptable but consider exact pin for prod.",
        ),
        (
            r"^>(?!=)",
            "medium",
            "Open upper bound (>) can pull breaking changes.",
        ),
        (
            r"^<",
            "low",
            "Upper-bound only; combine with >= for a safe range.",
        ),
        (
            r"^!=",
            "medium",
            "Exclusion only; add a positive pin to lock the version.",
        ),
        (
            r"^==",
            "info",
            "Exact pin — good practice.",
        ),
        (
            r"^===",
            "info",
            "Arbitrary equality — acceptable for local builds.",
        ),
    ]

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def scan(self) -> list[dict[str, Any]]:
        """Return a list of finding dicts for every dependency line.

        Each finding contains:
        - package: str
        - version_spec: str
        - risk_level: "high" | "medium" | "low" | "info"
        - recommendation: str
        - source_file: str (relative to repo root)
        """
        findings: list[dict[str, Any]] = []
        for req_file in sorted(self.repo_root.rglob("requirements.txt")):
            findings.extend(self._scan_file(req_file))
        return findings

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _scan_file(self, path: Path) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        if not path.is_file():
            return findings

        relative = str(path.relative_to(self.repo_root))

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            name, version_spec = self._split_requirement(line)
            risk_level, recommendation = self._classify(name, version_spec)

            findings.append(
                {
                    "package": name,
                    "version_spec": version_spec,
                    "risk_level": risk_level,
                    "recommendation": recommendation,
                    "source_file": relative,
                }
            )
        return findings

    def _classify(self, package: str, version_spec: str) -> tuple[str, str]:
        """Return (risk_level, recommendation) for a dependency."""
        base_risk = "info"
        base_rec = "Version specification looks acceptable."

        for pattern, risk, rec in self._SPEC_PATTERNS:
            if re.match(pattern, version_spec):
                base_risk = risk
                base_rec = rec
                break

        # Escalate if the package is in the known-risky set
        if package.lower() in self.KNOWN_RISKY_PACKAGES:
            if base_risk == "info":
                base_risk = "low"
                base_rec += (
                    " This package has a history of security advisories — monitor for updates."
                )
            elif base_risk in ("low", "medium"):
                base_risk = "high"
                base_rec += (
                    " HIGH-RISK: This package has known CVE history and "
                    "the version specifier is not exact-pinned."
                )

        return base_risk, base_rec

    @staticmethod
    def _split_requirement(line: str) -> tuple[str, str]:
        """Return (package_name, version_spec) from a pip requirement line."""
        for sep in ("===", "~=", "==", "!=", ">=", "<=", ">", "<"):
            if sep in line:
                idx = line.index(sep)
                name = line[:idx].strip()
                version = line[idx:].strip()
                if "[" in name:
                    name = name[: name.index("[")]
                return name, version
        name = line.strip()
        if "[" in name:
            name = name[: name.index("[")]
        return name, ""
