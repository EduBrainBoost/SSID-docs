"""TTL-based purge for FORENSIC evidence — auto-cleanup after expiry."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TTLPolicy:
    max_age_seconds: int = 86400 * 30  # 30 days default


def purge_expired(directory: Path, policy: TTLPolicy) -> list[Path]:
    """Remove files older than policy.max_age_seconds. Returns purged paths."""
    if not directory.exists() or not directory.is_dir():
        return []
    now = time.time()
    purged: list[Path] = []
    for f in directory.rglob("*"):
        if not f.is_file():
            continue
        if now - f.stat().st_mtime > policy.max_age_seconds:
            f.unlink()
            purged.append(f)
    return purged
