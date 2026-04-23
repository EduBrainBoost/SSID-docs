"""Secret Pattern Registry — canonical unified secret detection patterns.

Consolidates secret/PII patterns from all SSID repos into a single registry.
Categories: API_KEY, PASSWORD, PRIVATE_KEY, BEARER_TOKEN, GITHUB_TOKEN,
            AWS, STRIPE, OPENAI, GITLAB, SLACK, PII_EMAIL, PII_PHONE, LONG_HEX.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal


class SecretCategory(StrEnum):
    """Categories of secret patterns."""

    API_KEY = "API_KEY"
    PASSWORD = "PASSWORD"  # noqa: S105
    PRIVATE_KEY = "PRIVATE_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"  # noqa: S105
    GITHUB_TOKEN = "GITHUB_TOKEN"  # noqa: S105
    AWS = "AWS"
    STRIPE = "STRIPE"
    OPENAI = "OPENAI"
    GITLAB = "GITLAB"
    SLACK = "SLACK"
    PII_EMAIL = "PII_EMAIL"
    PII_PHONE = "PII_PHONE"
    LONG_HEX = "LONG_HEX"


@dataclass(frozen=True)
class SecretPattern:
    """A single secret detection pattern."""

    name: str
    category: SecretCategory
    pattern: re.Pattern[str]
    severity: Literal["critical", "high", "medium"] = "critical"
    description: str = ""


@dataclass(frozen=True)
class SecretFinding:
    """A detected secret in content."""

    pattern_name: str
    category: SecretCategory
    severity: Literal["critical", "high", "medium"]
    line_number: int
    matched_text_prefix: str  # First 20 chars only (don't log the full secret)
    description: str = ""


# ---------------------------------------------------------------------------
# Canonical pattern registry (union of all repos)
# ---------------------------------------------------------------------------

_PATTERNS: list[SecretPattern] = [
    # API Keys
    SecretPattern(
        "generic_api_key",
        SecretCategory.API_KEY,
        re.compile(
            r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9\-._]{16,}['\"]?", re.IGNORECASE
        ),
        "critical",
        "Generic API key pattern",
    ),
    # Passwords
    SecretPattern(
        "generic_password",
        SecretCategory.PASSWORD,
        re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{4,}['\"]?", re.IGNORECASE),
        "critical",
        "Hardcoded password",
    ),
    # Private Keys
    SecretPattern(
        "private_key_pem",
        SecretCategory.PRIVATE_KEY,
        re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"),
        "critical",
        "PEM-encoded private key",
    ),
    # Bearer Tokens
    SecretPattern(
        "bearer_token",
        SecretCategory.BEARER_TOKEN,
        re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        "critical",
        "Bearer authentication token",
    ),
    # GitHub Tokens
    SecretPattern(
        "github_pat",
        SecretCategory.GITHUB_TOKEN,
        re.compile(r"ghp_[A-Za-z0-9]{36,}"),
        "critical",
        "GitHub Personal Access Token",
    ),
    SecretPattern(
        "github_oauth",
        SecretCategory.GITHUB_TOKEN,
        re.compile(r"gho_[A-Za-z0-9]{36,}"),
        "critical",
        "GitHub OAuth Token",
    ),
    SecretPattern(
        "github_app",
        SecretCategory.GITHUB_TOKEN,
        re.compile(r"ghs_[A-Za-z0-9]{36,}"),
        "high",
        "GitHub App Token",
    ),
    # AWS
    SecretPattern(
        "aws_access_key",
        SecretCategory.AWS,
        re.compile(r"AKIA[0-9A-Z]{16}"),
        "critical",
        "AWS Access Key ID",
    ),
    SecretPattern(
        "aws_secret_key",
        SecretCategory.AWS,
        re.compile(
            r"(?:aws_secret|secret_access_key)\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?",
            re.IGNORECASE,
        ),
        "critical",
        "AWS Secret Access Key",
    ),
    # Stripe
    SecretPattern(
        "stripe_secret",
        SecretCategory.STRIPE,
        re.compile(r"sk_live_[A-Za-z0-9]{24,}"),
        "critical",
        "Stripe Secret Key (live)",
    ),
    SecretPattern(
        "stripe_publishable",
        SecretCategory.STRIPE,
        re.compile(r"pk_live_[A-Za-z0-9]{24,}"),
        "high",
        "Stripe Publishable Key (live)",
    ),
    # OpenAI
    SecretPattern(
        "openai_key",
        SecretCategory.OPENAI,
        re.compile(r"sk-[A-Za-z0-9]{32,}"),
        "critical",
        "OpenAI API Key",
    ),
    # GitLab
    SecretPattern(
        "gitlab_token",
        SecretCategory.GITLAB,
        re.compile(r"glpat-[A-Za-z0-9\-]{20,}"),
        "critical",
        "GitLab Personal Access Token",
    ),
    # Slack
    SecretPattern(
        "slack_token",
        SecretCategory.SLACK,
        re.compile(r"xox[bpsa]-[A-Za-z0-9\-]{10,}"),
        "critical",
        "Slack Token",
    ),
    # PII
    SecretPattern(
        "email_address",
        SecretCategory.PII_EMAIL,
        re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "medium",
        "Email address (PII)",
    ),
    SecretPattern(
        "phone_number",
        SecretCategory.PII_PHONE,
        re.compile(r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
        "medium",
        "Phone number (PII)",
    ),
    # Long hex (potential tokens/hashes exposed as secrets)
    SecretPattern(
        "long_hex_string",
        SecretCategory.LONG_HEX,
        re.compile(
            r"(?:secret|token|key|auth)\s*[:=]\s*['\"]?[0-9a-fA-F]{40,}['\"]?", re.IGNORECASE
        ),
        "high",
        "Long hex string in secret context",
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_content(text: str) -> list[SecretFinding]:
    """Scan text content for secret patterns.

    Returns list of SecretFinding with line numbers.
    """
    findings: list[SecretFinding] = []
    lines = text.splitlines()

    for line_num, line in enumerate(lines, 1):
        for sp in _PATTERNS:
            match = sp.pattern.search(line)
            if match:
                matched = match.group(0)
                prefix = matched[:20] + ("..." if len(matched) > 20 else "")
                findings.append(
                    SecretFinding(
                        pattern_name=sp.name,
                        category=sp.category,
                        severity=sp.severity,
                        line_number=line_num,
                        matched_text_prefix=prefix,
                        description=sp.description,
                    )
                )

    return findings


def scan_file(path: Path) -> list[SecretFinding]:
    """Scan a file for secret patterns.

    Returns empty list if file cannot be read.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return scan_content(text)


def get_patterns_by_category(category: SecretCategory) -> list[SecretPattern]:
    """Get all patterns for a specific category."""
    return [p for p in _PATTERNS if p.category == category]


def get_all_pattern_names() -> list[str]:
    """Get names of all registered patterns."""
    return [p.name for p in _PATTERNS]


def to_export_dict() -> list[dict[str, str]]:
    """Export patterns as list of dicts for use by other repos."""
    return [
        {
            "name": p.name,
            "category": str(p.category),
            "pattern": p.pattern.pattern,
            "severity": p.severity,
            "description": p.description,
        }
        for p in _PATTERNS
    ]
