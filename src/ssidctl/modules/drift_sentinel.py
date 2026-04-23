"""Drift Sentinel — integrity, leakage, and docs-source checks.

Read-only sentinel that validates:
1. Export Integrity: manifest entries match actual file hashes
2. Leakage: no forbidden patterns in public files
3. Docs Source: SSID-docs references only SSID-open-core public sources

Exit codes:
  0 = PASS (all checks green)
  2 = FAIL (integrity/leakage/source violation)
  3 = ERROR (I/O, parse, missing required files)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_file, sha256_str
from ssidctl.core.timeutil import utcnow_iso

# --- Deny patterns for leakage scan ---
DENY_PATTERNS: list[re.Pattern[str]] = [
    # Absolute paths
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"C:/Users/", re.IGNORECASE),
    re.compile(r"/home/\w+", re.IGNORECASE),
    re.compile(r"/mnt/\w+", re.IGNORECASE),
    re.compile(r"Users/bibel", re.IGNORECASE),
    # Credentials / keys
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"sk_live_[A-Za-z0-9]"),
    re.compile(r"sk_test_[A-Za-z0-9]"),
    re.compile(r"ghp_[A-Za-z0-9_]{36}"),
    re.compile(r"gho_[A-Za-z0-9_]{36}"),
    re.compile(r"ssh-rsa\s+AAAA"),
    # Emails (simple)
    re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"),
    # Internal repo paths
    re.compile(r"SSID-EMS[/\\]"),
    re.compile(r"SSID_EMS_STATE"),
    re.compile(r"SSID_EVIDENCE"),
    # UUIDs (board/run IDs)
    re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE),
]

# File extensions allowed in public export
ALLOWED_EXTENSIONS = frozenset(
    {
        ".md",
        ".mdx",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".py",
        ".js",
        ".mjs",
        ".ts",
        ".tsx",
        ".css",
        ".svg",
        ".txt",
        ".html",
        ".sh",
    }
)

# Extensions to scan for leakage (text-readable)
SCANNABLE_EXTENSIONS = frozenset(
    {
        ".md",
        ".mdx",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".py",
        ".js",
        ".mjs",
        ".ts",
        ".tsx",
        ".css",
        ".txt",
        ".html",
        ".svg",
        ".sh",
    }
)


@dataclass
class Finding:
    """A single check finding."""

    check: str
    severity: str  # "FAIL" or "WARN"
    path: str
    detail: str


@dataclass
class DriftReport:
    """Complete drift sentinel report."""

    timestamp: str = ""
    verdict: str = "PASS"
    checks_run: int = 0
    checks_passed: int = 0
    findings: list[Finding] = field(default_factory=list)

    def add_finding(self, check: str, severity: str, path: str, detail: str) -> None:
        self.findings.append(Finding(check=check, severity=severity, path=path, detail=detail))
        if severity == "FAIL":
            self.verdict = "FAIL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "verdict": self.verdict,
            "checks_run": self.checks_run,
            "checks_passed": self.checks_passed,
            "findings_count": len(self.findings),
            "findings": [
                {"check": f.check, "severity": f.severity, "path": f.path, "detail": f.detail}
                for f in self.findings
            ],
        }


def check_integrity(open_core: Path, report: DriftReport) -> None:
    """Check manifest entries match actual file hashes."""
    report.checks_run += 1
    manifest_path = open_core / "public_export" / "manifest.json"

    if not manifest_path.exists():
        report.add_finding("integrity", "FAIL", str(manifest_path), "Manifest not found")
        return

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report.add_finding("integrity", "FAIL", str(manifest_path), f"Parse error: {exc}")
        return

    entries = data.get("entries", [])
    if not entries:
        report.add_finding("integrity", "FAIL", str(manifest_path), "No entries in manifest")
        return

    mismatches = 0
    missing = 0
    for entry in entries:
        rel_path = entry.get("path", "")
        expected_hash = entry.get("sha256", "")
        file_path = open_core / rel_path

        if not file_path.exists():
            report.add_finding("integrity", "FAIL", rel_path, "File missing from disk")
            missing += 1
            continue

        actual_hash = sha256_file(file_path)
        if actual_hash != expected_hash:
            report.add_finding(
                "integrity",
                "FAIL",
                rel_path,
                f"Hash mismatch: expected {expected_hash[:20]}... got {actual_hash[:20]}...",
            )
            mismatches += 1

        # Check extension allowlist
        ext = file_path.suffix.lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            report.add_finding("integrity", "FAIL", rel_path, f"Disallowed extension: {ext}")

    if mismatches == 0 and missing == 0:
        report.checks_passed += 1


def check_leakage(open_core: Path, docs: Path | None, report: DriftReport) -> None:
    """Scan public files for forbidden patterns."""
    report.checks_run += 1
    found_leaks = False

    scan_dirs: list[tuple[str, Path]] = [("open-core", open_core)]
    if docs is not None and docs.exists():
        scan_dirs.append(("docs", docs))

    for label, base_dir in scan_dirs:
        for file_path in base_dir.rglob("*"):
            if not file_path.is_file():
                continue
            # Skip .git, node_modules, dist, __pycache__
            parts = file_path.parts
            if any(p in (".git", "node_modules", "dist", "__pycache__", ".pnpm") for p in parts):
                continue

            ext = file_path.suffix.lower()
            if ext not in SCANNABLE_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            rel = str(file_path.relative_to(base_dir)).replace("\\", "/")

            for pattern in DENY_PATTERNS:
                if pattern.search(content):
                    # Exclude self-referential CI files that contain pattern literals
                    if _is_ci_self_reference(rel):
                        continue
                    report.add_finding(
                        "leakage",
                        "FAIL",
                        f"{label}:{rel}",
                        f"Denied pattern: {pattern.pattern[:40]}",
                    )
                    found_leaks = True

    if not found_leaks:
        report.checks_passed += 1


def _is_ci_self_reference(rel_path: str) -> bool:
    """CI workflow files and test files may contain pattern literals."""
    ci_patterns = [
        ".github/workflows/",
        "tests/",
        "tools/ingest.mjs",
        "tools/changelog-gen.mjs",
    ]
    return any(rel_path.startswith(p) or rel_path.endswith(p.lstrip("/")) for p in ci_patterns)


def check_docs_source(docs: Path, report: DriftReport) -> None:
    """Verify SSID-docs references only public-safe sources."""
    report.checks_run += 1

    if not docs.exists():
        report.add_finding("docs-source", "FAIL", str(docs), "Docs directory not found")
        return

    # Forbidden source references in docs content
    forbidden_refs = [
        re.compile(r"SSID-EMS", re.IGNORECASE),
        re.compile(r"SSID_EMS_STATE"),
        re.compile(r"SSID_EVIDENCE"),
        re.compile(r"C:\\Users\\", re.IGNORECASE),
        re.compile(r"C:/Users/", re.IGNORECASE),
        re.compile(r"/home/\w+/.*SSID", re.IGNORECASE),
    ]

    found_violations = False
    content_dirs = [docs / "src" / "content", docs / "tools"]

    for content_dir in content_dirs:
        if not content_dir.exists():
            continue
        for file_path in content_dir.rglob("*"):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in SCANNABLE_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            rel = str(file_path.relative_to(docs)).replace("\\", "/")

            # Skip CI/test files
            if _is_ci_self_reference(rel):
                continue

            for pattern in forbidden_refs:
                if pattern.search(content):
                    report.add_finding(
                        "docs-source",
                        "FAIL",
                        f"docs:{rel}",
                        f"Forbidden source ref: {pattern.pattern[:40]}",
                    )
                    found_violations = True

    if not found_violations:
        report.checks_passed += 1


def run_sentinel(
    open_core: Path,
    docs: Path | None = None,
    state_dir: Path | None = None,
    evidence_dir: Path | None = None,
) -> DriftReport:
    """Run all drift sentinel checks.

    Returns:
        DriftReport with verdict PASS or FAIL.
    """
    report = DriftReport(timestamp=utcnow_iso())

    check_integrity(open_core, report)
    check_leakage(open_core, docs, report)
    if docs is not None:
        check_docs_source(docs, report)

    return report


def write_report(report: DriftReport, state_dir: Path) -> Path:
    """Write report to state directory. Returns report path."""
    ts = report.timestamp.replace(":", "-")
    report_dir = state_dir / "drift_sentinel" / "reports" / ts
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / "drift_report.json"
    content = json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
    report_path.write_text(content, encoding="utf-8")

    # Write last_report pointer
    last_path = state_dir / "drift_sentinel" / "last_report.json"
    last_path.write_text(content, encoding="utf-8")

    return report_path


def write_evidence(report: DriftReport, evidence_dir: Path) -> str:
    """Write hash-only evidence. Returns content hash."""
    from ssidctl.core.event_log import EventLog

    report_json = json.dumps(report.to_dict(), sort_keys=True, separators=(",", ":"))
    content_hash = sha256_str(report_json)

    log = EventLog(evidence_dir / "index.jsonl")
    log.append(
        "drift_sentinel.run",
        {
            "verdict": report.verdict,
            "checks_run": report.checks_run,
            "checks_passed": report.checks_passed,
            "findings_count": len(report.findings),
            "report_hash": content_hash,
        },
        "ssidctl",
    )
    return content_hash
