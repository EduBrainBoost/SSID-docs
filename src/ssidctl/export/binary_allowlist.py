"""Binary Allowlist — controls which binary file types are allowed in exports.

Only explicitly allowed binary extensions pass.  Everything else is denied.
Each allowed type has a max size limit.

Principle: fail-closed — unknown binary types are denied.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class BinaryRule:
    """An allowed binary file type with size limit."""

    extension: str
    max_size_bytes: int
    description: str


@dataclass(frozen=True)
class BinaryVerdict:
    """Result of binary validation."""

    decision: Literal["ALLOW", "DENY"]
    reason: str
    extension: str = ""
    size_bytes: int = 0


# ---------------------------------------------------------------------------
# Allowlist — explicitly allowed binary extensions
# ---------------------------------------------------------------------------

_BINARY_ALLOWLIST: list[BinaryRule] = [
    # Images
    BinaryRule(".png", 2 * 1024 * 1024, "PNG image"),
    BinaryRule(".jpg", 2 * 1024 * 1024, "JPEG image"),
    BinaryRule(".jpeg", 2 * 1024 * 1024, "JPEG image"),
    BinaryRule(".gif", 1 * 1024 * 1024, "GIF image"),
    BinaryRule(".svg", 512 * 1024, "SVG vector image"),
    BinaryRule(".ico", 256 * 1024, "Icon file"),
    BinaryRule(".webp", 2 * 1024 * 1024, "WebP image"),
    # Fonts
    BinaryRule(".woff", 1 * 1024 * 1024, "WOFF font"),
    BinaryRule(".woff2", 1 * 1024 * 1024, "WOFF2 font"),
    BinaryRule(".ttf", 2 * 1024 * 1024, "TrueType font"),
    BinaryRule(".otf", 2 * 1024 * 1024, "OpenType font"),
    BinaryRule(".eot", 1 * 1024 * 1024, "Embedded OpenType font"),
    # Documents (limited)
    BinaryRule(".pdf", 5 * 1024 * 1024, "PDF document"),
]

_ALLOWLIST_MAP: dict[str, BinaryRule] = {r.extension: r for r in _BINARY_ALLOWLIST}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_binary(path: str | Path, size_bytes: int | None = None) -> BinaryVerdict:
    """Validate a binary file against the allowlist.

    Args:
        path: File path (only extension is checked).
        size_bytes: File size in bytes.  If None, only extension is checked.

    Returns:
        BinaryVerdict with ALLOW or DENY.
    """
    p = Path(path)
    ext = p.suffix.lower()

    if not ext:
        return BinaryVerdict("DENY", "No file extension", "", size_bytes or 0)

    rule = _ALLOWLIST_MAP.get(ext)
    if rule is None:
        return BinaryVerdict(
            "DENY", f"Extension {ext} not in binary allowlist", ext, size_bytes or 0
        )

    if size_bytes is not None and size_bytes > rule.max_size_bytes:
        return BinaryVerdict(
            "DENY",
            f"File size {size_bytes} exceeds limit {rule.max_size_bytes} for {ext}",
            ext,
            size_bytes,
        )

    return BinaryVerdict("ALLOW", rule.description, ext, size_bytes or 0)


def get_allowed_extensions() -> list[str]:
    """Return list of all allowed binary extensions."""
    return [r.extension for r in _BINARY_ALLOWLIST]


def get_max_size(extension: str) -> int | None:
    """Return max size for an extension, or None if not allowed."""
    rule = _ALLOWLIST_MAP.get(extension.lower())
    return rule.max_size_bytes if rule else None
