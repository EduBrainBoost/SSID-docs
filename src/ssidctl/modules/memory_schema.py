"""Memory schema models — typed dataclasses with validation.

Provides MemoryEntry, MemoryCreate, MemoryUpdate, and MemorySearchResult
with field-level validation.  No external dependencies (uses stdlib only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ssidctl.modules.memory import CATEGORIES


class MemorySchemaError(ValueError):
    """Raised when schema validation fails."""


# ---------------------------------------------------------------------------
# Validators (shared)
# ---------------------------------------------------------------------------


def _validate_category(category: str) -> None:
    if category not in CATEGORIES:
        raise MemorySchemaError(f"Invalid category: {category!r}. Must be one of {CATEGORIES}")


def _validate_confidence(value: float) -> None:
    if not isinstance(value, (int, float)):
        raise MemorySchemaError("confidence_level must be a number")
    if not 0.0 <= float(value) <= 1.0:
        raise MemorySchemaError(f"confidence_level must be between 0.0 and 1.0, got {value}")


# ---------------------------------------------------------------------------
# MemoryEntry — full stored record
# ---------------------------------------------------------------------------


@dataclass
class MemoryEntry:
    """Full memory entry as stored in the index."""

    doc_id: str
    title: str
    tags: list[str]
    path: str
    hash: str
    created: str
    updated_at: str
    owner: str
    category: str
    content: str
    linked_tasks: list[str]
    linked_pipeline_items: list[str]
    attachments: list[dict[str, Any]]
    source_agent: str | None
    confidence_level: float
    deleted: bool = False

    def __post_init__(self) -> None:
        _validate_category(self.category)
        _validate_confidence(self.confidence_level)
        if not self.doc_id:
            raise MemorySchemaError("doc_id must not be empty")
        if not self.title:
            raise MemorySchemaError("title must not be empty")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        """Construct from a raw index dict, applying defaults for missing fields."""
        return cls(
            doc_id=data["doc_id"],
            title=data["title"],
            tags=data.get("tags", []),
            path=data["path"],
            hash=data.get("hash", ""),
            created=data.get("created", ""),
            updated_at=data.get("updated_at", data.get("created", "")),
            owner=data.get("owner", "user"),
            category=data.get("category", "NOTE"),
            content=data.get("content", ""),
            linked_tasks=data.get("linked_tasks", []),
            linked_pipeline_items=data.get("linked_pipeline_items", []),
            attachments=data.get("attachments", []),
            source_agent=data.get("source_agent"),
            confidence_level=float(data.get("confidence_level", 1.0)),
            deleted=data.get("deleted", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "tags": self.tags,
            "path": self.path,
            "hash": self.hash,
            "created": self.created,
            "updated_at": self.updated_at,
            "owner": self.owner,
            "category": self.category,
            "content": self.content,
            "linked_tasks": self.linked_tasks,
            "linked_pipeline_items": self.linked_pipeline_items,
            "attachments": self.attachments,
            "source_agent": self.source_agent,
            "confidence_level": self.confidence_level,
            "deleted": self.deleted,
        }


# ---------------------------------------------------------------------------
# MemoryCreate — input for add()
# ---------------------------------------------------------------------------


@dataclass
class MemoryCreate:
    """Validated input for creating a new memory entry."""

    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    owner: str = "user"
    category: str = "NOTE"
    source_agent: str | None = None
    confidence_level: float = 1.0

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise MemorySchemaError("title must not be empty")
        if not self.content or not self.content.strip():
            raise MemorySchemaError("content must not be empty")
        _validate_category(self.category)
        _validate_confidence(self.confidence_level)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryCreate:
        return cls(
            title=data["title"],
            content=data["content"],
            tags=data.get("tags", []),
            owner=data.get("owner", "user"),
            category=data.get("category", "NOTE"),
            source_agent=data.get("source_agent"),
            confidence_level=float(data.get("confidence_level", 1.0)),
        )


# ---------------------------------------------------------------------------
# MemoryUpdate — input for update()
# ---------------------------------------------------------------------------


@dataclass
class MemoryUpdate:
    """Validated input for updating an existing memory entry.

    All fields are optional; only provided (non-None) fields are applied.
    """

    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    category: str | None = None

    def __post_init__(self) -> None:
        if self.title is not None and not self.title.strip():
            raise MemorySchemaError("title must not be empty if provided")
        if self.content is not None and not self.content.strip():
            raise MemorySchemaError("content must not be empty if provided")
        if self.category is not None:
            _validate_category(self.category)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryUpdate:
        return cls(
            title=data.get("title"),
            content=data.get("content"),
            tags=data.get("tags"),
            category=data.get("category"),
        )

    def has_changes(self) -> bool:
        """Return True if at least one field is being updated."""
        return any(v is not None for v in (self.title, self.content, self.tags, self.category))


# ---------------------------------------------------------------------------
# MemorySearchResult — lightweight result record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemorySearchResult:
    """A single search hit returned by MemoryVault.search()."""

    doc_id: str
    title: str
    category: str
    tags: list[str]
    score: float  # 0.0–1.0 relevance hint; 1.0 = exact title/tag match
    snippet: str  # short excerpt from content, may be empty

    def __post_init__(self) -> None:
        _validate_category(self.category)
        _validate_confidence(self.score)

    @classmethod
    def from_entry(
        cls,
        entry: dict[str, Any],
        score: float = 1.0,
        snippet: str = "",
    ) -> MemorySearchResult:
        return cls(
            doc_id=entry["doc_id"],
            title=entry["title"],
            category=entry.get("category", "NOTE"),
            tags=entry.get("tags", []),
            score=score,
            snippet=snippet,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "category": self.category,
            "tags": self.tags,
            "score": self.score,
            "snippet": self.snippet,
        }
