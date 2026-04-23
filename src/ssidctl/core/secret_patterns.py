"""Single source of truth for secret/token detection patterns.

All secret-detection logic (sanitizer, guards, data-minimization) MUST
import patterns from this module. No pattern duplication elsewhere.

Patterns detect:
- AWS access keys (AKIA/ASIA)
- GitHub tokens (ghp_, gho_, ghs_, ghu_, github_pat_)
- GitLab PATs (glpat-)
- Slack tokens (xox[baprs]-)
- Stripe keys (sk_live_, sk_test_, pk_live_, pk_test_)
- Private key headers (PEM format)
- Generic API keys (sk-, pk-, bearer, api_key)
- Long hex strings (40+ chars, likely tokens/SHAs)
"""

from __future__ import annotations

import re
from typing import Any

# --- Pattern Definitions ---
# Each entry: (id, name, compiled_regex, replacement)
# Patterns are ordered: specific first, generic last (to avoid over-matching).

PATTERNS: list[dict[str, Any]] = [
    {
        "id": "SEC-AWS-001",
        "name": "aws_access_key",
        "regex": r"(?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}",
        "replacement": "<AWS_KEY_REDACTED>",
    },
    {
        "id": "SEC-GH-001",
        "name": "github_token",
        "regex": r"(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9_]{36,}",
        "replacement": "<GITHUB_TOKEN_REDACTED>",
    },
    {
        "id": "SEC-GH-002",
        "name": "github_pat",
        "regex": r"github_pat_[A-Za-z0-9_]{22,}",
        "replacement": "<GITHUB_PAT_REDACTED>",
    },
    {
        "id": "SEC-GL-001",
        "name": "gitlab_pat",
        "regex": r"glpat-[A-Za-z0-9\-_]{20,}",
        "replacement": "<GITLAB_PAT_REDACTED>",
    },
    {
        "id": "SEC-SLACK-001",
        "name": "slack_token",
        "regex": r"xox[baprs]-[A-Za-z0-9\-]{10,}",
        "replacement": "<SLACK_TOKEN_REDACTED>",
    },
    {
        "id": "SEC-STRIPE-001",
        "name": "stripe_key",
        "regex": r"[sr]k_(?:live|test)_[A-Za-z0-9]{10,}",
        "replacement": "<STRIPE_KEY_REDACTED>",
    },
    {
        "id": "SEC-PK-001",
        "name": "private_key_header",
        "regex": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
        "replacement": "<PRIVATE_KEY_REDACTED>",
    },
    {
        "id": "SEC-API-001",
        "name": "generic_api_key",
        "regex": (
            r"(?i)"
            r"(?:(?:sk-|pk-)[A-Za-z0-9_\-]{20,}"
            r"|bearer\s+[A-Za-z0-9_\-]{20,}"
            r"|api[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,})"
        ),
        "replacement": "<API_KEY_REDACTED>",
    },
    {
        "id": "SEC-HEX-001",
        "name": "long_hex_token",
        "regex": (
            r"(?<!sha256:)(?<!sha384:)(?<!sha512:)"
            r"(?<!sha1:)(?<!commit )(?<!merkle:)"
            r"(?<!digest:)(?<!integrity:)(?<!checksum:)"
            r"\b[0-9a-fA-F]{40,}\b"
        ),
        "replacement": "<HEX_REDACTED>",
    },
]

# Pre-compiled patterns (module-level, no per-call compilation)
COMPILED: list[tuple[str, re.Pattern[str], str]] = [
    (p["id"], re.compile(p["regex"]), p["replacement"]) for p in PATTERNS
]


def find(text: str) -> list[str]:
    """Return list of pattern IDs that match in text.

    Does NOT return the matched token itself (data-minimization).
    """
    return [pattern_id for pattern_id, regex, _replacement in COMPILED if regex.search(text)]


def redact(text: str) -> tuple[str, int]:
    """Redact all secret patterns in text.

    Returns (redacted_text, redaction_count).
    Replaces entire match — no partial fragments remain.
    """
    count = 0
    result = text
    for _pattern_id, regex, replacement in COMPILED:
        result, n = regex.subn(replacement, result)
        count += n
    return result, count
