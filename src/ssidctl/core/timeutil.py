"""Shared UTC timestamp helper."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow_iso() -> str:
    """Return current UTC time as ISO 8601 string (e.g. '2026-03-02T12:00:00Z')."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
