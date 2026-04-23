"""Content Review Checklist Extension — checklist validation and tracking.

Provides structured checklist management for content items:
- Template-based checklist generation
- Item checking/unchecking with audit trail
- Completion percentage and blocking detection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ssidctl.core.timeutil import utcnow_iso


class ChecklistError(Exception):
    pass


@dataclass
class ChecklistItem:
    """A single checklist item."""

    text: str
    checked: bool = False
    checked_by: str | None = None
    checked_at: str | None = None

    def check(self, actor: str = "user") -> None:
        self.checked = True
        self.checked_by = actor
        self.checked_at = utcnow_iso()

    def uncheck(self) -> None:
        self.checked = False
        self.checked_by = None
        self.checked_at = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "checked": self.checked,
            "checked_by": self.checked_by,
            "checked_at": self.checked_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChecklistItem:
        return cls(
            text=data["text"],
            checked=data.get("checked", False),
            checked_by=data.get("checked_by"),
            checked_at=data.get("checked_at"),
        )

    @classmethod
    def from_string(cls, text: str) -> ChecklistItem:
        """Parse a checklist item from a simple string (legacy format)."""
        return cls(text=text.strip())


@dataclass
class ReviewChecklist:
    """Manages a review checklist for a content item."""

    content_id: str
    items: list[ChecklistItem] = field(default_factory=list)

    @classmethod
    def from_content(cls, content_item: dict[str, Any]) -> ReviewChecklist:
        """Build a ReviewChecklist from a content pipeline item dict."""
        content_id = content_item.get("content_id", "")
        raw_list = content_item.get("checklist", [])
        items: list[ChecklistItem] = []
        for entry in raw_list:
            if isinstance(entry, str):
                items.append(ChecklistItem.from_string(entry))
            elif isinstance(entry, dict):
                items.append(ChecklistItem.from_dict(entry))
        return cls(content_id=content_id, items=items)

    def add_item(self, text: str) -> ChecklistItem:
        """Add a new checklist item."""
        item = ChecklistItem(text=text.strip())
        self.items.append(item)
        return item

    def remove_item(self, index: int) -> ChecklistItem:
        """Remove a checklist item by index."""
        if index < 0 or index >= len(self.items):
            raise ChecklistError(f"Index out of range: {index} (0-{len(self.items) - 1})")
        return self.items.pop(index)

    def check_item(self, index: int, actor: str = "user") -> ChecklistItem:
        """Check a checklist item by index."""
        if index < 0 or index >= len(self.items):
            raise ChecklistError(f"Index out of range: {index} (0-{len(self.items) - 1})")
        self.items[index].check(actor)
        return self.items[index]

    def uncheck_item(self, index: int) -> ChecklistItem:
        """Uncheck a checklist item by index."""
        if index < 0 or index >= len(self.items):
            raise ChecklistError(f"Index out of range: {index} (0-{len(self.items) - 1})")
        self.items[index].uncheck()
        return self.items[index]

    def check_by_text(self, text: str, actor: str = "user") -> ChecklistItem | None:
        """Check the first item matching the given text."""
        for item in self.items:
            if item.text == text:
                item.check(actor)
                return item
        return None

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def checked_count(self) -> int:
        return sum(1 for i in self.items if i.checked)

    @property
    def unchecked_count(self) -> int:
        return self.total - self.checked_count

    @property
    def completion_pct(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.checked_count / self.total) * 100.0

    @property
    def is_complete(self) -> bool:
        return self.total > 0 and self.checked_count == self.total

    @property
    def is_blocking(self) -> bool:
        """A checklist is blocking if it has unchecked items."""
        return self.total > 0 and not self.is_complete

    def to_string_list(self) -> list[str]:
        """Export as simple string list (for content.set_checklist compatibility)."""
        return [item.text for item in self.items]

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Export as list of dicts with full state."""
        return [item.to_dict() for item in self.items]

    def render_text(self) -> str:
        """Render checklist as text with checkboxes."""
        lines = [
            f"Review Checklist: {self.content_id}",
            f"  Progress: {self.checked_count}/{self.total} ({self.completion_pct:.0f}%)",
            "",
        ]
        for i, item in enumerate(self.items):
            mark = "x" if item.checked else " "
            by = f" (by {item.checked_by})" if item.checked_by else ""
            lines.append(f"  [{mark}] {i}. {item.text}{by}")
        return "\n".join(lines)


# --- Template-based checklist generation ---

REVIEW_TEMPLATES: dict[str, list[str]] = {
    "blog": [
        "Title and headline reviewed",
        "Content accuracy verified",
        "SEO metadata set",
        "Images and media checked",
        "Internal links validated",
        "Grammar and spell check done",
        "Publish date confirmed",
    ],
    "video": [
        "Script reviewed and approved",
        "Audio quality checked",
        "Visual quality checked",
        "Captions/subtitles added",
        "Thumbnail created",
        "Publish date confirmed",
    ],
    "social": [
        "Copy reviewed",
        "Hashtags and mentions verified",
        "Media attached",
        "Scheduling confirmed",
    ],
    "default": [
        "Content reviewed",
        "Quality check passed",
        "Metadata complete",
        "Ready for publish",
    ],
}


def generate_checklist(channel: str) -> list[str]:
    """Generate a checklist template based on the content channel."""
    return list(REVIEW_TEMPLATES.get(channel, REVIEW_TEMPLATES["default"]))
