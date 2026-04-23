"""Content Pipeline module — IDEA to POSTMORTEM stages.

Event-sourced: content.yaml + content.jsonl.
Stages: IDEA | OUTLINE | BRIEF | SCRIPT | ASSETS | REVIEW | PUBLISH | ARCHIVE | POSTMORTEM
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.event_log import EventLog
from ssidctl.core.timeutil import utcnow_iso

_VALID_STAGES = (
    "IDEA",
    "OUTLINE",
    "BRIEF",
    "SCRIPT",
    "ASSETS",
    "REVIEW",
    "PUBLISH",
    "ARCHIVE",
    "POSTMORTEM",
)


class ContentError(Exception):
    pass


class ContentPipeline:
    def __init__(self, content_dir: Path) -> None:
        self._dir = content_dir
        self._snapshot = content_dir / "content.yaml"
        self._event_log = EventLog(content_dir / "content.jsonl")

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._snapshot.exists():
            return {}
        with open(self._snapshot, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return (data or {}).get("items", {})

    def _save(self, items: dict[str, dict[str, Any]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._snapshot, "w", encoding="utf-8") as f:
            yaml.dump({"items": items}, f, default_flow_style=False)

    @staticmethod
    def _utcnow() -> str:
        return utcnow_iso()

    def new(
        self,
        content_id: str,
        title: str,
        channel: str = "blog",
        tags: list[str] | None = None,
        owner: str = "user",
        actor: str = "user",
    ) -> dict[str, Any]:
        items = self._load()
        if content_id in items:
            raise ContentError(f"Content already exists: {content_id}")

        now = self._utcnow()
        item = {
            "content_id": content_id,
            "stage": "IDEA",
            "title": title,
            "channel": channel,
            "tags": tags or [],
            "script_ref": None,
            "attachments": [],
            "owner": owner,
            "created_utc": now,
            "updated_utc": now,
            "script_hash": None,
            "assets_hash": None,
            "publish_date": None,
            "checklist": [],
        }
        items[content_id] = item
        self._save(items)
        self._event_log.append(
            "content.created",
            {"content_id": content_id, "title": title},
            actor,
        )
        return item

    def stage(self, content_id: str, new_stage: str, actor: str = "user") -> dict[str, Any]:
        if new_stage not in _VALID_STAGES:
            raise ContentError(f"Invalid stage: {new_stage}")
        items = self._load()
        if content_id not in items:
            raise ContentError(f"Content not found: {content_id}")

        old_stage = items[content_id]["stage"]
        items[content_id]["stage"] = new_stage
        items[content_id]["updated_utc"] = self._utcnow()
        self._save(items)
        self._event_log.append(
            "content.staged",
            {"content_id": content_id, "from": old_stage, "to": new_stage},
            actor,
        )
        return items[content_id]

    def attach(self, content_id: str, path: str, hash_val: str, mime: str) -> dict[str, Any]:
        items = self._load()
        if content_id not in items:
            raise ContentError(f"Content not found: {content_id}")
        items[content_id]["attachments"].append({"path": path, "hash": hash_val, "mime": mime})
        items[content_id]["updated_utc"] = self._utcnow()
        self._save(items)
        return items[content_id]

    def edit(
        self,
        content_id: str,
        title: str | None = None,
        channel: str | None = None,
        tags: list[str] | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        items = self._load()
        if content_id not in items:
            raise ContentError(f"Content not found: {content_id}")
        changes: dict[str, Any] = {}
        if title is not None:
            items[content_id]["title"] = title
            changes["title"] = title
        if channel is not None:
            items[content_id]["channel"] = channel
            changes["channel"] = channel
        if tags is not None:
            items[content_id]["tags"] = tags
            changes["tags"] = tags
        items[content_id]["updated_utc"] = self._utcnow()
        self._save(items)
        self._event_log.append("content.edited", {"content_id": content_id, **changes}, actor)
        return items[content_id]

    def _update_field(self, content_id: str, field: str, value: Any) -> dict[str, Any]:
        """Load, set a single field, save, and return the updated item."""
        items = self._load()
        if content_id not in items:
            raise ContentError(f"Content not found: {content_id}")
        items[content_id][field] = value
        items[content_id]["updated_utc"] = self._utcnow()
        self._save(items)
        return items[content_id]

    def set_script_hash(self, content_id: str, script_hash: str) -> dict[str, Any]:
        return self._update_field(content_id, "script_hash", script_hash)

    def set_assets_hash(self, content_id: str, assets_hash: str) -> dict[str, Any]:
        return self._update_field(content_id, "assets_hash", assets_hash)

    def show(self, content_id: str) -> dict[str, Any]:
        items = self._load()
        if content_id not in items:
            raise ContentError(f"Content not found: {content_id}")
        return items[content_id]

    def set_publish_date(self, content_id: str, date_str: str) -> dict[str, Any]:
        return self._update_field(content_id, "publish_date", date_str)

    def set_checklist(self, content_id: str, checklist: list[str]) -> dict[str, Any]:
        return self._update_field(content_id, "checklist", checklist)

    def list_items(self, stage: str | None = None) -> list[dict[str, Any]]:
        items = self._load()
        result = list(items.values())
        if stage:
            result = [i for i in result if i["stage"] == stage]
        return result
