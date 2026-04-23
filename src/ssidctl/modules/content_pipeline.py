"""Content Pipeline module — enhanced pipeline with validated stage transitions.

Stages: IDEA → RESEARCH → OUTLINE → DRAFT → REVIEW → SCHEDULED → PUBLISHED → ARCHIVED
Rework: REVIEW → DRAFT (allowed)
Storage: state_dir/content_pipeline/ with pipeline_index.json
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso

_STAGES = ("IDEA", "RESEARCH", "OUTLINE", "DRAFT", "REVIEW", "SCHEDULED", "PUBLISHED", "ARCHIVED")

_VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "IDEA": ("RESEARCH",),
    "RESEARCH": ("OUTLINE",),
    "OUTLINE": ("DRAFT",),
    "DRAFT": ("REVIEW",),
    "REVIEW": ("SCHEDULED", "DRAFT"),  # DRAFT = rework
    "SCHEDULED": ("PUBLISHED",),
    "PUBLISHED": ("ARCHIVED",),
    "ARCHIVED": (),
}


class PipelineError(Exception):
    pass


class PipelineStore:
    """Enhanced content pipeline with validated stage transitions."""

    def __init__(self, pipeline_dir: Path) -> None:
        self._dir = pipeline_dir
        self._index_path = pipeline_dir / "pipeline_index.json"
        self._artifacts_dir = pipeline_dir / "artifacts"

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._index_path.exists():
            return {}
        with open(self._index_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", {})

    def _save(self, items: dict[str, dict[str, Any]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump({"items": items}, f, indent=2, ensure_ascii=False)

    def create(
        self,
        title: str,
        description: str = "",
        owner: str = "user",
        tags: list[str] | None = None,
        content_body: str = "",
        assigned_agent: str | None = None,
        reviewer: str | None = None,
        scheduled_publish_date: str | None = None,
    ) -> dict[str, Any]:
        item_id = f"PL-{uuid.uuid4().hex[:8]}"
        now = utcnow_iso()
        item = {
            "item_id": item_id,
            "title": title,
            "description": description,
            "stage": "IDEA",
            "owner": owner,
            "created_at": now,
            "updated_at": now,
            "tags": tags or [],
            "attachments": [],
            "content_body": content_body,
            "linked_tasks": [],
            "assigned_agent": assigned_agent,
            "reviewer": reviewer,
            "scheduled_publish_date": scheduled_publish_date,
            "history": [{"stage": "IDEA", "at": now, "by": owner}],
        }
        items = self._load()
        items[item_id] = item
        self._save(items)

        # Persist content body as artifact if provided
        if content_body:
            self._save_artifact(item_id, content_body)

        return item

    def get(self, item_id: str) -> dict[str, Any]:
        items = self._load()
        if item_id not in items:
            raise PipelineError(f"Pipeline item not found: {item_id}")
        item = items[item_id]
        # Load content body from artifact if exists
        artifact = self._load_artifact(item_id)
        if artifact is not None:
            item["content_body"] = artifact
        return item

    def update(self, item_id: str, actor: str = "user", **kwargs: Any) -> dict[str, Any]:
        items = self._load()
        if item_id not in items:
            raise PipelineError(f"Pipeline item not found: {item_id}")

        allowed_fields = {
            "title",
            "description",
            "tags",
            "content_body",
            "assigned_agent",
            "reviewer",
            "scheduled_publish_date",
            "linked_tasks",
        }

        for k, v in kwargs.items():
            if k in allowed_fields and v is not None:
                items[item_id][k] = v

        items[item_id]["updated_at"] = utcnow_iso()
        self._save(items)

        # Persist content body artifact
        if "content_body" in kwargs and kwargs["content_body"]:
            self._save_artifact(item_id, kwargs["content_body"])

        return items[item_id]

    def transition(self, item_id: str, new_stage: str, actor: str = "user") -> dict[str, Any]:
        if new_stage not in _STAGES:
            raise PipelineError(f"Invalid stage: {new_stage}")

        items = self._load()
        if item_id not in items:
            raise PipelineError(f"Pipeline item not found: {item_id}")

        current_stage = items[item_id]["stage"]
        allowed = _VALID_TRANSITIONS.get(current_stage, ())

        if new_stage not in allowed:
            raise PipelineError(
                f"Invalid transition: {current_stage} → {new_stage}. "
                f"Allowed: {', '.join(allowed) if allowed else 'none'}"
            )

        now = utcnow_iso()
        items[item_id]["stage"] = new_stage
        items[item_id]["updated_at"] = now
        items[item_id].setdefault("history", []).append(
            {
                "stage": new_stage,
                "at": now,
                "by": actor,
            }
        )

        self._save(items)
        return items[item_id]

    def assign(self, item_id: str, agent: str, actor: str = "user") -> dict[str, Any]:
        return self.update(item_id, actor=actor, assigned_agent=agent)

    def delete(self, item_id: str) -> dict[str, Any]:
        items = self._load()
        if item_id not in items:
            raise PipelineError(f"Pipeline item not found: {item_id}")
        removed = items.pop(item_id)
        self._save(items)
        return removed

    def list_items(
        self,
        stage: str | None = None,
        owner: str | None = None,
        assigned_agent: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        items = list(self._load().values())
        if stage:
            items = [i for i in items if i.get("stage") == stage]
        if owner:
            items = [i for i in items if i.get("owner") == owner]
        if assigned_agent:
            items = [i for i in items if i.get("assigned_agent") == assigned_agent]
        if tag:
            items = [i for i in items if tag in i.get("tags", [])]
        return items

    def board(self) -> dict[str, list[dict[str, Any]]]:
        """Return items grouped by stage for board view."""
        items = self._load()
        board: dict[str, list[dict[str, Any]]] = {s: [] for s in _STAGES}
        for item in items.values():
            stage = item.get("stage", "IDEA")
            if stage in board:
                board[stage].append(item)
        return board

    def search(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        results = []
        for item in self._load().values():
            if (
                q in item.get("title", "").lower()
                or q in item.get("description", "").lower()
                or any(q in t.lower() for t in item.get("tags", []))
            ):
                results.append(item)
        return results

    def _save_artifact(self, item_id: str, content: str) -> None:
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = self._artifacts_dir / f"{item_id}.md"
        path.write_text(content, encoding="utf-8")

    def _load_artifact(self, item_id: str) -> str | None:
        path = self._artifacts_dir / f"{item_id}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def valid_stages() -> tuple[str, ...]:
        return _STAGES

    @staticmethod
    def valid_transitions() -> dict[str, tuple[str, ...]]:
        return dict(_VALID_TRANSITIONS)
