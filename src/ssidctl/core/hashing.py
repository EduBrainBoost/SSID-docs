"""Shared SHA-256 hashing helpers.

All hashes use the canonical 'sha256:<hex>' prefix format.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    """SHA-256 hash of raw bytes with 'sha256:' prefix."""
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def sha256_str(text: str) -> str:
    """SHA-256 hash of a UTF-8 string with 'sha256:' prefix."""
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    """SHA-256 hash of a file's contents with 'sha256:' prefix."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"
