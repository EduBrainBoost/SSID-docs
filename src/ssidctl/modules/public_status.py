"""Public Status module — sanitized Now/Next/Later aggregation.

Reads board tasks and produces a sanitized JSON with:
- Counts per category (now/next/later/done)
- Topic tags from an allowlist (no IDs, no raw text, no URLs)
- No internal identifiers, no file paths, no usernames

Status mapping:
  now   = DOING, REVIEW, BLOCKED
  next  = READY
  later = BACKLOG
  done  = DONE, CANCELLED
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso

# Only these topic tags are allowed in public output.
ALLOWED_TOPICS = frozenset(
    {
        "architecture",
        "compliance",
        "crypto",
        "data-pipeline",
        "documentation",
        "export",
        "governance",
        "identity",
        "infrastructure",
        "observability",
        "security",
        "testing",
        "tooling",
        "ux",
    }
)

# Board status → public category mapping
_STATUS_MAP: dict[str, str] = {
    "DOING": "now",
    "REVIEW": "now",
    "BLOCKED": "now",
    "READY": "next",
    "BACKLOG": "later",
    "DONE": "done",
    "CANCELLED": "done",
}

# Deny patterns — if any of these appear in a string, it is stripped.
_DENY_PATTERNS = [
    "http://",
    "https://",
    "C:\\Users",
    "C:/Users",
    "/home/",
    "/mnt/",
    "@",
    "ghp_",
    "gho_",
    "sk_live_",
    "sk_test_",
]


def _sanitize_tag(tag: str) -> str | None:
    """Return tag only if it's in the allowlist, else None."""
    normalized = tag.strip().lower().replace(" ", "-").replace("_", "-")
    if normalized in ALLOWED_TOPICS:
        return normalized
    return None


def _contains_deny_pattern(text: str) -> bool:
    """Return True if text contains any denied pattern."""
    lower = text.lower()
    return any(p.lower() in lower for p in _DENY_PATTERNS)


def aggregate_board(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate board tasks into sanitized public status.

    Returns a dict suitable for JSON serialization with:
    - counts: {now, next, later, done}
    - topics: {now: [...], next: [...], later: [...]}
    - generated_utc: timestamp
    """
    counts: dict[str, int] = {"now": 0, "next": 0, "later": 0, "done": 0}
    topics: dict[str, set[str]] = {"now": set(), "next": set(), "later": set()}

    for task in tasks:
        status = task.get("status", "BACKLOG")
        category = _STATUS_MAP.get(status, "later")
        counts[category] = counts.get(category, 0) + 1

        # Extract topic from module field (sanitized via allowlist)
        module = task.get("module", "")
        tag = _sanitize_tag(module)
        if tag and category in topics:
            topics[category].add(tag)

        # Extract topic from title (first word, sanitized)
        title = task.get("title", "")
        if not _contains_deny_pattern(title):
            for word in title.split():
                tag = _sanitize_tag(word)
                if tag and category in topics:
                    topics[category].add(tag)

    return {
        "schema_version": "1.0.0",
        "generated_utc": utcnow_iso(),
        "counts": counts,
        "topics": {
            "now": sorted(topics["now"]),
            "next": sorted(topics["next"]),
            "later": sorted(topics["later"]),
        },
    }


def write_public_status(data: dict[str, Any], output_path: Path) -> str:
    """Write public_status.json and return its SHA-256 hash."""
    content = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return sha256_str(content)
