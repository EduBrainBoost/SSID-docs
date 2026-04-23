"""PII/secret/path redaction for findings and output.

All gate findings and evidence must pass through sanitization before
persistence. This module strips:
- Windows/Unix username paths
- API keys / tokens / secrets (delegated to secret_patterns.py)
- Email addresses
- Raw log lines (replaced with structured summaries)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ssidctl.core.secret_patterns import find as _find_secrets
from ssidctl.core.secret_patterns import redact as _redact_secrets

# PII/path patterns (NOT secret tokens — those live in secret_patterns.py)
_PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # Windows user paths: C:\Users\username\... -> C:\Users\<REDACTED>\...
    (
        "user_path_win",
        re.compile(
            r"[A-Za-z]:\\Users\\[^\\\"'\s]+",
            re.IGNORECASE,
        ),
        r"C:\\Users\\<REDACTED>",
    ),
    # Unix home paths: /home/username/... or /Users/username/...
    (
        "user_path_unix",
        re.compile(
            r"(?:/home|/Users)/[^/\"'\s]+",
        ),
        "/home/<REDACTED>",
    ),
    # Email addresses (exclude @version.number patterns like pkg@3.7.1.patch)
    (
        "email",
        re.compile(
            r"[A-Za-z0-9._%+\-]+@(?!\d+\.\d)[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        ),
        "<EMAIL_REDACTED>",
    ),
    # Environment variable references with values
    (
        "env_var",
        re.compile(
            r"(?:export\s+|set\s+)?[A-Z_]{3,}=['\"]?[^'\";\s]+['\"]?",
        ),
        "<ENV_REDACTED>",
    ),
]


@dataclass
class SanitizeResult:
    """Result of sanitization."""

    text: str
    redacted: bool
    redaction_count: int


def sanitize_text(text: str) -> SanitizeResult:
    """Sanitize a text string by redacting sensitive content.

    Applies secret patterns first (from secret_patterns.py),
    then PII patterns (paths, emails, env vars).

    Returns:
        SanitizeResult with redacted text and metadata.
    """
    # Phase 1: secret token redaction (single source of truth)
    result, count = _redact_secrets(text)

    # Phase 2: PII/path redaction
    for _name, pattern, replacement in _PII_PATTERNS:
        new_result, n = pattern.subn(replacement, result)
        count += n
        result = new_result

    return SanitizeResult(
        text=result,
        redacted=count > 0,
        redaction_count=count,
    )


def sanitize_finding(finding: dict) -> dict:
    """Sanitize a structured gate finding.

    Ensures findings follow the format:
    {code, gate, severity, summary, redacted: true}

    Sanitizes the summary field and adds redacted marker.
    """
    result = dict(finding)

    if "summary" in result:
        sr = sanitize_text(str(result["summary"]))
        result["summary"] = sr.text

    result["redacted"] = True
    result["evidence_hash_only"] = True

    return result


def sanitize_findings(findings: list[dict]) -> list[dict]:
    """Sanitize a list of gate findings."""
    return [sanitize_finding(f) for f in findings]


def contains_secrets(text: str) -> bool:
    """Check if text contains potential secrets or PII.

    Used as a pre-flight check before persisting any text.
    Checks both secret patterns and PII patterns.
    """
    # Check secret patterns (from secret_patterns.py)
    if _find_secrets(text):
        return True
    # Check PII patterns
    return any(pattern.search(text) for _name, pattern, _replacement in _PII_PATTERNS)
