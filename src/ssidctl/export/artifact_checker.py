"""Artifact Checker — validates export artifacts for safety.

Checks: file size, type, encoding, forbidden content patterns.
Produces ArtifactVerdict (PASS/FAIL) per file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ssidctl.export.binary_allowlist import validate_binary
from ssidctl.export.deny_glob_registry import validate_path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MiB default
DEFAULT_MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50 MiB total

# Forbidden content patterns (secrets, internal refs)
_FORBIDDEN_CONTENT: list[tuple[str, re.Pattern[str]]] = [
    (
        "hardcoded_password",
        re.compile(r"(?:password|passwd)\s*[:=]\s*['\"][^'\"]{4,}['\"]", re.IGNORECASE),
    ),
    (
        "api_key_value",
        re.compile(r"(?:api[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9]{16,}['\"]", re.IGNORECASE),
    ),
    ("private_key_block", re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----")),
    ("internal_path", re.compile(r"C:\\Users\\[^\\]+\\Documents", re.IGNORECASE)),
    ("internal_path_unix", re.compile(r"/home/[^/]+/Documents", re.IGNORECASE)),
]

# Text file extensions
_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".sh",
        ".ps1",
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".txt",
        ".toml",
        ".rego",
        ".lock",
        ".cfg",
        ".ini",
        ".html",
        ".css",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".mjs",
        ".cjs",
        ".xml",
        ".csv",
    }
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtifactFinding:
    """A single finding from artifact checking."""

    check: str
    severity: Literal["critical", "high", "medium", "info"]
    description: str


@dataclass(frozen=True)
class ArtifactVerdict:
    """Result of artifact validation."""

    decision: Literal["PASS", "FAIL"]
    path: str
    findings: list[ArtifactFinding] = field(default_factory=list)
    size_bytes: int = 0
    file_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "path": self.path,
            "findings": [
                {"check": f.check, "severity": f.severity, "description": f.description}
                for f in self.findings
            ],
            "size_bytes": self.size_bytes,
            "file_type": self.file_type,
        }


# ---------------------------------------------------------------------------
# ArtifactChecker class
# ---------------------------------------------------------------------------


class ArtifactChecker:
    """Validates individual export artifacts."""

    def __init__(
        self,
        *,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        scan_content: bool = True,
    ) -> None:
        self._max_file_size = max_file_size
        self._scan_content = scan_content

    def check_artifact(self, path: Path, *, rel_path: str = "") -> ArtifactVerdict:
        """Check a single artifact file.

        Args:
            path: Absolute path to the file.
            rel_path: Relative path for deny-glob checking.
                Falls back to path.name if empty.

        Returns:
            ArtifactVerdict with PASS or FAIL.
        """
        findings: list[ArtifactFinding] = []
        rp = rel_path or path.name
        ext = path.suffix.lower()

        # 1. Check deny globs
        deny_verdict = validate_path(rp)
        if deny_verdict.decision == "DENY":
            glob_info = deny_verdict.matched_glob
            reason = glob_info.reason if glob_info else "Denied by glob"
            findings.append(
                ArtifactFinding(
                    "deny_glob",
                    "critical",
                    f"Path denied: {reason}",
                )
            )

        # 2. Check file existence and size
        if not path.exists():
            findings.append(
                ArtifactFinding(
                    "existence",
                    "critical",
                    f"File does not exist: {path}",
                )
            )
            decision: Literal["PASS", "FAIL"] = "FAIL" if findings else "PASS"
            return ArtifactVerdict(decision, rp, findings, 0, ext)

        size = path.stat().st_size
        if size > self._max_file_size:
            findings.append(
                ArtifactFinding(
                    "file_size",
                    "high",
                    f"File size {size} exceeds limit {self._max_file_size}",
                )
            )

        # 3. Check binary files
        if ext not in _TEXT_EXTENSIONS:
            bin_verdict = validate_binary(path, size)
            if bin_verdict.decision == "DENY":
                findings.append(
                    ArtifactFinding(
                        "binary_check",
                        "high",
                        f"Binary denied: {bin_verdict.reason}",
                    )
                )

        # 4. Scan text content for forbidden patterns
        if self._scan_content and ext in _TEXT_EXTENSIONS and path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                for name, pattern in _FORBIDDEN_CONTENT:
                    if pattern.search(content):
                        findings.append(
                            ArtifactFinding(
                                f"content_{name}",
                                "critical",
                                f"Forbidden content pattern: {name}",
                            )
                        )
            except OSError:
                findings.append(
                    ArtifactFinding(
                        "read_error",
                        "high",
                        f"Cannot read file: {path}",
                    )
                )

        has_critical = any(f.severity in ("critical", "high") for f in findings)
        decision = "FAIL" if has_critical else "PASS"
        return ArtifactVerdict(decision, rp, findings, size, ext)

    def check_directory(
        self,
        directory: Path,
        *,
        max_total_size: int = DEFAULT_MAX_TOTAL_SIZE,
    ) -> list[ArtifactVerdict]:
        """Check all files in a directory recursively.

        Returns list of ArtifactVerdict, one per file.
        """
        results: list[ArtifactVerdict] = []
        total_size = 0

        if not directory.exists():
            return [
                ArtifactVerdict(
                    "FAIL",
                    str(directory),
                    [
                        ArtifactFinding(
                            "existence", "critical", f"Directory does not exist: {directory}"
                        )
                    ],
                )
            ]

        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(directory)).replace("\\", "/")
            verdict = self.check_artifact(path, rel_path=rel)
            results.append(verdict)
            total_size += verdict.size_bytes

        if total_size > max_total_size:
            results.append(
                ArtifactVerdict(
                    "FAIL",
                    str(directory),
                    [
                        ArtifactFinding(
                            "total_size",
                            "high",
                            f"Total size {total_size} exceeds limit {max_total_size}",
                        )
                    ],
                    total_size,
                )
            )

        return results
