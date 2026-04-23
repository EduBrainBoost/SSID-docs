"""Content PII Scrubber Extension — PII detection and redaction for content.

Extends core.sanitizer with content-pipeline-specific PII handling:
- Detects PII patterns in content text (emails, phone numbers, IPs, SSNs, etc.)
- Provides redaction with configurable replacement
- Generates PII reports for audit logging
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class PIIScrubError(Exception):
    pass


@dataclass(frozen=True)
class PIIMatch:
    """A detected PII occurrence."""

    pattern_name: str
    matched_text: str
    start: int
    end: int
    replacement: str


@dataclass
class PIIReport:
    """Summary of PII detection/scrubbing on a piece of content."""

    content_id: str
    total_matches: int = 0
    matches_by_type: dict[str, int] = field(default_factory=dict)
    matches: list[PIIMatch] = field(default_factory=list)
    scrubbed: bool = False

    def add_match(self, match: PIIMatch) -> None:
        self.matches.append(match)
        self.total_matches += 1
        self.matches_by_type[match.pattern_name] = (
            self.matches_by_type.get(match.pattern_name, 0) + 1
        )

    @property
    def has_pii(self) -> bool:
        return self.total_matches > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_id": self.content_id,
            "total_matches": self.total_matches,
            "matches_by_type": dict(self.matches_by_type),
            "scrubbed": self.scrubbed,
            "details": [
                {
                    "type": m.pattern_name,
                    "start": m.start,
                    "end": m.end,
                    "replacement": m.replacement,
                }
                for m in self.matches
            ],
        }

    def render_text(self) -> str:
        lines = [
            f"PII Report: {self.content_id}",
            f"  Total matches: {self.total_matches}",
            f"  Scrubbed: {self.scrubbed}",
        ]
        if self.matches_by_type:
            lines.append("  By type:")
            for ptype, count in sorted(self.matches_by_type.items()):
                lines.append(f"    {ptype}: {count}")
        return "\n".join(lines)


# --- PII Pattern Definitions ---

_PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "email",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
        "[EMAIL_REDACTED]",
    ),
    (
        "phone_international",
        re.compile(r"\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{2,4}[\s\-]?\d{2,4}[\s\-]?\d{0,4}"),
        "[PHONE_REDACTED]",
    ),
    (
        "phone_us",
        re.compile(r"\b\d{3}[\-\.]\d{3}[\-\.]\d{4}\b"),
        "[PHONE_REDACTED]",
    ),
    (
        "ssn",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "[SSN_REDACTED]",
    ),
    (
        "credit_card",
        re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
        "[CC_REDACTED]",
    ),
    (
        "ipv4",
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        "[IP_REDACTED]",
    ),
    (
        "iban",
        re.compile(r"\b[A-Z]{2}\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{0,4}\b"),
        "[IBAN_REDACTED]",
    ),
]


def detect_pii(text: str, content_id: str = "") -> PIIReport:
    """Scan text for PII patterns and return a report.

    Does NOT modify the text. Use scrub_pii() for redaction.
    """
    report = PIIReport(content_id=content_id)

    for pattern_name, regex, replacement in _PII_PATTERNS:
        for m in regex.finditer(text):
            report.add_match(
                PIIMatch(
                    pattern_name=pattern_name,
                    matched_text=m.group(),
                    start=m.start(),
                    end=m.end(),
                    replacement=replacement,
                )
            )

    return report


def scrub_pii(text: str, content_id: str = "") -> tuple[str, PIIReport]:
    """Detect and redact PII in text.

    Returns (scrubbed_text, report).
    """
    report = detect_pii(text, content_id)

    if not report.has_pii:
        return text, report

    # Apply replacements in reverse order to preserve positions
    scrubbed = text
    for match in sorted(report.matches, key=lambda m: m.start, reverse=True):
        scrubbed = scrubbed[: match.start] + match.replacement + scrubbed[match.end :]

    report.scrubbed = True
    return scrubbed, report


def scrub_content_item(item: dict[str, Any]) -> tuple[dict[str, Any], PIIReport]:
    """Scrub PII from a content pipeline item's text fields.

    Scans title and tags for PII. Returns updated item dict and report.
    Does NOT mutate the original dict.
    """
    content_id = item.get("content_id", "")
    combined_report = PIIReport(content_id=content_id)

    new_item = dict(item)

    # Scrub title
    title = item.get("title", "")
    if title:
        scrubbed_title, title_report = scrub_pii(title, content_id)
        new_item["title"] = scrubbed_title
        for m in title_report.matches:
            combined_report.add_match(m)

    # Scrub tags
    tags = item.get("tags", [])
    if tags:
        new_tags: list[str] = []
        for tag in tags:
            scrubbed_tag, tag_report = scrub_pii(tag, content_id)
            new_tags.append(scrubbed_tag)
            for m in tag_report.matches:
                combined_report.add_match(m)
        new_item["tags"] = new_tags

    combined_report.scrubbed = combined_report.has_pii
    return new_item, combined_report


def is_safe(text: str) -> bool:
    """Quick check: does this text contain any detectable PII?"""
    report = detect_pii(text)
    return not report.has_pii
