"""Memory Vault module — markdown documents with metadata index.

Stores markdown docs in docs/ and metadata in index.jsonl.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_str
from ssidctl.core.sanitizer import sanitize_text
from ssidctl.core.timeutil import utcnow_iso

CATEGORIES: list[str] = [
    "OPERATIONAL",
    "RESEARCH",
    "ARCHITECTURE",
    "INCIDENT",
    "LESSON",
    "EVIDENCE",
    "NOTE",
]


class MemoryError(Exception):
    pass


class MemoryVault:
    def __init__(self, memory_dir: Path) -> None:
        self._dir = memory_dir
        self._docs_dir = memory_dir / "docs"
        self._index_path = memory_dir / "index.jsonl"

    @staticmethod
    def _utcnow() -> str:
        return utcnow_iso()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_all_entries(self) -> list[dict[str, Any]]:
        """Read all non-deleted entries from the index."""
        if not self._index_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self._index_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def _write_all_entries(self, entries: list[dict[str, Any]]) -> None:
        """Overwrite the entire index with the given entries."""
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._index_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    @staticmethod
    def _apply_defaults(entry: dict[str, Any]) -> dict[str, Any]:
        """Backfill default values for new fields on legacy entries."""
        entry.setdefault("category", "NOTE")
        entry.setdefault("updated_at", entry.get("created", ""))
        entry.setdefault("content", "")
        entry.setdefault("linked_tasks", [])
        entry.setdefault("linked_pipeline_items", [])
        entry.setdefault("attachments", [])
        entry.setdefault("source_agent", None)
        entry.setdefault("confidence_level", 1.0)
        entry.setdefault("deleted", False)
        return entry

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def add(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        owner: str = "user",
        category: str = "NOTE",
        source_agent: str | None = None,
        confidence_level: float = 1.0,
    ) -> dict[str, Any]:
        if category not in CATEGORIES:
            raise MemoryError(f"Invalid category: {category!r}. Must be one of {CATEGORIES}")
        if not 0.0 <= confidence_level <= 1.0:
            raise MemoryError("confidence_level must be between 0.0 and 1.0")

        doc_id = f"M-{uuid.uuid4().hex[:6]}"
        filename = f"{doc_id}-{title.lower().replace(' ', '-')[:40]}.md"
        doc_path = self._docs_dir / filename

        self._docs_dir.mkdir(parents=True, exist_ok=True)
        scrubbed = sanitize_text(content).text
        doc_path.write_text(scrubbed, encoding="utf-8")

        content_hash = sha256_str(scrubbed)
        now = self._utcnow()
        entry: dict[str, Any] = {
            "doc_id": doc_id,
            "title": title,
            "tags": tags or [],
            "path": f"docs/{filename}",
            "hash": content_hash,
            "created": now,
            "updated_at": now,
            "owner": owner,
            "category": category,
            "content": scrubbed,
            "linked_tasks": [],
            "linked_pipeline_items": [],
            "attachments": [],
            "source_agent": source_agent,
            "confidence_level": confidence_level,
            "deleted": False,
        }

        with open(self._index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")

        return entry

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_docs(self) -> list[dict[str, Any]]:
        """Return all non-deleted entries with default fields applied."""
        return [
            self._apply_defaults(e)
            for e in self._read_all_entries()
            if not e.get("deleted", False)
        ]

    def show(self, doc_id: str) -> dict[str, Any]:
        for entry in self.list_docs():
            if entry["doc_id"] == doc_id:
                doc_path = self._dir / entry["path"]
                if doc_path.exists():
                    entry["content"] = doc_path.read_text(encoding="utf-8")
                return entry
        raise MemoryError(f"Document not found: {doc_id}")

    def search(self, query: str, fulltext: bool = True) -> list[dict[str, Any]]:
        """Keyword search across titles, tags, and optionally file content."""
        query_lower = query.lower()
        results = []
        for entry in self.list_docs():
            # Title + tags match
            if query_lower in entry["title"].lower() or any(
                query_lower in t.lower() for t in entry.get("tags", [])
            ):
                results.append(entry)
                continue
            # Fulltext match: read markdown file content
            if fulltext:
                doc_path = self._dir / entry["path"]
                if doc_path.exists():
                    content = doc_path.read_text(encoding="utf-8").lower()
                    if query_lower in content:
                        results.append(entry)
        return results

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        doc_id: str,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Update title, content, tags, or category of an existing entry.

        Recalculates the hash and sets updated_at. Rewrites index.jsonl.
        """
        if category is not None and category not in CATEGORIES:
            raise MemoryError(f"Invalid category: {category!r}. Must be one of {CATEGORIES}")

        all_entries = self._read_all_entries()
        target_idx: int | None = None
        for idx, e in enumerate(all_entries):
            if e.get("doc_id") == doc_id and not e.get("deleted", False):
                target_idx = idx
                break

        if target_idx is None:
            raise MemoryError(f"Document not found: {doc_id}")

        entry = self._apply_defaults(dict(all_entries[target_idx]))

        if title is not None:
            entry["title"] = title
        if tags is not None:
            entry["tags"] = tags
        if category is not None:
            entry["category"] = category

        if content is not None:
            scrubbed = sanitize_text(content).text
            doc_path = self._dir / entry["path"]
            doc_path.write_text(scrubbed, encoding="utf-8")
            entry["hash"] = sha256_str(scrubbed)
            entry["content"] = scrubbed

        entry["updated_at"] = self._utcnow()
        all_entries[target_idx] = entry
        self._write_all_entries(all_entries)
        return entry

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, doc_id: str) -> None:
        """Mark entry as deleted in the index and remove the doc file."""
        all_entries = self._read_all_entries()
        found = False
        for entry in all_entries:
            if entry.get("doc_id") == doc_id and not entry.get("deleted", False):
                entry["deleted"] = True
                entry["updated_at"] = self._utcnow()
                found = True
                # Remove markdown file if it exists
                doc_path = self._dir / entry.get("path", "")
                if doc_path.exists():
                    doc_path.unlink()
                break

        if not found:
            raise MemoryError(f"Document not found: {doc_id}")

        self._write_all_entries(all_entries)

    # ------------------------------------------------------------------
    # Filter helpers
    # ------------------------------------------------------------------

    def list_by_category(self, category: str) -> list[dict[str, Any]]:
        """Return all non-deleted entries matching the given category."""
        if category not in CATEGORIES:
            raise MemoryError(f"Invalid category: {category!r}. Must be one of {CATEGORIES}")
        return [e for e in self.list_docs() if e.get("category") == category]

    def list_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Return all non-deleted entries that include the given tag."""
        tag_lower = tag.lower()
        return [
            e for e in self.list_docs() if any(tag_lower == t.lower() for t in e.get("tags", []))
        ]

    def list_categories(self) -> dict[str, int]:
        """Return a mapping of category -> count of non-deleted entries."""
        counts: Counter[str] = Counter()
        for entry in self.list_docs():
            cat = entry.get("category", "NOTE")
            counts[cat] += 1
        # Include all known categories even if zero
        return {cat: counts.get(cat, 0) for cat in CATEGORIES}

    # ------------------------------------------------------------------
    # Linking
    # ------------------------------------------------------------------

    def link_task(self, doc_id: str, task_id: str) -> dict[str, Any]:
        """Link a task ID to a memory entry (idempotent)."""
        entry = self._get_entry_for_mutation(doc_id)
        if task_id not in entry["linked_tasks"]:
            entry["linked_tasks"].append(task_id)
            self._save_entry(doc_id, entry)
        return entry

    def link_pipeline_item(self, doc_id: str, pipeline_item_id: str) -> dict[str, Any]:
        """Link a pipeline item ID to a memory entry (idempotent)."""
        entry = self._get_entry_for_mutation(doc_id)
        if pipeline_item_id not in entry["linked_pipeline_items"]:
            entry["linked_pipeline_items"].append(pipeline_item_id)
            self._save_entry(doc_id, entry)
        return entry

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def add_attachment(self, doc_id: str, attachment: dict[str, Any]) -> dict[str, Any]:
        """Append an attachment record to a memory entry.

        Expected attachment keys: name, url (or path), mime_type.
        """
        entry = self._get_entry_for_mutation(doc_id)
        entry["attachments"].append(attachment)
        self._save_entry(doc_id, entry)
        return entry

    # ------------------------------------------------------------------
    # Private mutation helpers
    # ------------------------------------------------------------------

    def _get_entry_for_mutation(self, doc_id: str) -> dict[str, Any]:
        """Fetch and default-fill a single non-deleted entry by doc_id."""
        for e in self._read_all_entries():
            if e.get("doc_id") == doc_id and not e.get("deleted", False):
                return self._apply_defaults(dict(e))
        raise MemoryError(f"Document not found: {doc_id}")

    def _save_entry(self, doc_id: str, updated: dict[str, Any]) -> None:
        """Replace the entry for doc_id in the index and rewrite."""
        updated["updated_at"] = self._utcnow()
        all_entries = self._read_all_entries()
        for idx, e in enumerate(all_entries):
            if e.get("doc_id") == doc_id:
                all_entries[idx] = updated
                break
        self._write_all_entries(all_entries)
