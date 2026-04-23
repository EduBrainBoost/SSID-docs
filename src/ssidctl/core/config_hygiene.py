"""Config Hygiene Checker — scans config files for hardcoded secrets.

Validates .yaml, .json, .toml, .env files for plaintext passwords,
API keys, private keys, and other secrets that should not be in config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ssidctl.core.secret_pattern_registry import SecretFinding, scan_file

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileHygieneResult:
    """Hygiene check result for a single file."""

    path: str
    findings: list[SecretFinding] = field(default_factory=list)
    passed: bool = True


@dataclass(frozen=True)
class HygieneReport:
    """Aggregated hygiene report for a directory."""

    directory: str
    file_results: list[FileHygieneResult] = field(default_factory=list)
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory": self.directory,
            "passed": self.passed,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "files_checked": len(self.file_results),
            "files_with_findings": sum(1 for f in self.file_results if not f.passed),
            "findings": [
                {
                    "file": fr.path,
                    "findings": [
                        {
                            "pattern": f.pattern_name,
                            "category": str(f.category),
                            "severity": f.severity,
                            "line": f.line_number,
                        }
                        for f in fr.findings
                    ],
                }
                for fr in self.file_results
                if not fr.passed
            ],
        }


# ---------------------------------------------------------------------------
# Config file extensions to scan
# ---------------------------------------------------------------------------

_CONFIG_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".env",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
    }
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ConfigHygieneChecker:
    """Scans configuration files for hardcoded secrets."""

    def __init__(
        self,
        *,
        extensions: frozenset[str] | None = None,
        min_severity: Literal["critical", "high", "medium"] = "high",
    ) -> None:
        """Initialize checker.

        Args:
            extensions: File extensions to scan. Defaults to config file types.
            min_severity: Minimum severity to report. Default "high".
        """
        self._extensions = extensions or _CONFIG_EXTENSIONS
        self._min_severity = min_severity
        self._severity_order = {"critical": 0, "high": 1, "medium": 2}

    def _severity_passes(self, severity: str) -> bool:
        """Check if a finding's severity meets minimum threshold."""
        s_order = self._severity_order.get(severity, 99)
        min_order = self._severity_order.get(self._min_severity, 1)
        return s_order <= min_order

    def check_file(self, path: Path) -> FileHygieneResult:
        """Check a single config file for secrets."""
        if not path.exists():
            return FileHygieneResult(str(path), [], True)

        findings = scan_file(path)
        filtered = [f for f in findings if self._severity_passes(f.severity)]
        passed = len(filtered) == 0
        return FileHygieneResult(str(path), filtered, passed)

    def check_config_dir(self, directory: Path) -> HygieneReport:
        """Check all config files in a directory recursively.

        Args:
            directory: Directory to scan.

        Returns:
            HygieneReport with aggregated findings.
        """
        if not directory.exists():
            return HygieneReport(
                directory=str(directory),
                passed=False,
                total_findings=1,
                critical_count=1,
            )

        results: list[FileHygieneResult] = []
        total = 0
        critical = 0
        high = 0

        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self._extensions:
                continue

            result = self.check_file(path)
            results.append(result)

            for f in result.findings:
                total += 1
                if f.severity == "critical":
                    critical += 1
                elif f.severity == "high":
                    high += 1

        passed = critical == 0 and high == 0
        return HygieneReport(
            directory=str(directory),
            file_results=results,
            total_findings=total,
            critical_count=critical,
            high_count=high,
            passed=passed,
        )
