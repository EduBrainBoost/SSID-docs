"""Task Board module — Kanban-style task management.

Event-sourced: tasks.yaml (snapshot) + tasks.jsonl (event log).
Statuses: BACKLOG | READY | DOING | BLOCKED | REVIEW | DONE | CANCELLED
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.event_log import EventLog
from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso

_VALID_STATUSES = frozenset(
    {
        "BACKLOG",
        "READY",
        "DOING",
        "BLOCKED",
        "REVIEW",
        "DONE",
        "CANCELLED",
    }
)
_VALID_PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})
_VALID_MODULES = frozenset({"EMS", "SSID", "Content", "Infra"})


class BoardError(Exception):
    pass


class Board:
    """Event-sourced task board."""

    def __init__(self, board_dir: Path) -> None:
        self._dir = board_dir
        self._snapshot_path = board_dir / "tasks.yaml"
        self._event_log = EventLog(board_dir / "tasks.jsonl")

    def _load_tasks(self) -> dict[str, dict[str, Any]]:
        if not self._snapshot_path.exists():
            return {}
        with open(self._snapshot_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return {}
        return data.get("tasks", {})

    def _save_tasks(self, tasks: dict[str, dict[str, Any]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._snapshot_path, "w", encoding="utf-8") as f:
            yaml.dump({"tasks": tasks}, f, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def _utcnow() -> str:
        return utcnow_iso()

    @staticmethod
    def _hash_notes(notes: str) -> str:
        return sha256_str(notes)

    def add(
        self,
        task_id: str,
        title: str,
        module: str = "EMS",
        owner: str = "user",
        priority: str = "P1",
        notes: str = "",
        deadline: str | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        tasks = self._load_tasks()
        if task_id in tasks:
            raise BoardError(f"Task already exists: {task_id}")
        if module not in _VALID_MODULES:
            raise BoardError(f"Invalid module: {module}")
        if priority not in _VALID_PRIORITIES:
            raise BoardError(f"Invalid priority: {priority}")

        now = self._utcnow()
        task = {
            "task_id": task_id,
            "title": title,
            "module": module,
            "owner": owner,
            "status": "BACKLOG",
            "priority": priority,
            "links": {"pr": None, "run_id": None, "evidence": None},
            "created_utc": now,
            "updated_utc": now,
            "deadline_utc": deadline,
            "notes_hash": self._hash_notes(notes) if notes else None,
        }

        tasks[task_id] = task
        self._save_tasks(tasks)
        self._event_log.append("board.task_added", {"task_id": task_id, "title": title}, actor)
        return task

    def move(self, task_id: str, status: str, actor: str = "user") -> dict[str, Any]:
        if status not in _VALID_STATUSES:
            raise BoardError(f"Invalid status: {status}")

        tasks = self._load_tasks()
        if task_id not in tasks:
            raise BoardError(f"Task not found: {task_id}")

        old_status = tasks[task_id]["status"]
        tasks[task_id]["status"] = status
        tasks[task_id]["updated_utc"] = self._utcnow()

        self._save_tasks(tasks)
        self._event_log.append(
            "board.task_moved",
            {"task_id": task_id, "from": old_status, "to": status},
            actor,
        )
        return tasks[task_id]

    def assign(self, task_id: str, owner: str, actor: str = "user") -> dict[str, Any]:
        tasks = self._load_tasks()
        if task_id not in tasks:
            raise BoardError(f"Task not found: {task_id}")

        old_owner = tasks[task_id]["owner"]
        tasks[task_id]["owner"] = owner
        tasks[task_id]["updated_utc"] = self._utcnow()

        self._save_tasks(tasks)
        self._event_log.append(
            "board.task_assigned",
            {"task_id": task_id, "from": old_owner, "to": owner},
            actor,
        )
        return tasks[task_id]

    def link(
        self,
        task_id: str,
        pr: str | None = None,
        run_id: str | None = None,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        tasks = self._load_tasks()
        if task_id not in tasks:
            raise BoardError(f"Task not found: {task_id}")

        if pr is not None:
            tasks[task_id]["links"]["pr"] = pr
        if run_id is not None:
            tasks[task_id]["links"]["run_id"] = run_id
        if evidence is not None:
            tasks[task_id]["links"]["evidence"] = evidence
        tasks[task_id]["updated_utc"] = self._utcnow()

        self._save_tasks(tasks)
        return tasks[task_id]

    def show(self, task_id: str) -> dict[str, Any]:
        tasks = self._load_tasks()
        if task_id not in tasks:
            raise BoardError(f"Task not found: {task_id}")
        return tasks[task_id]

    def update(
        self,
        task_id: str,
        title: str | None = None,
        priority: str | None = None,
        module: str | None = None,
        notes: str | None = None,
        deadline: str | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        tasks = self._load_tasks()
        if task_id not in tasks:
            raise BoardError(f"Task not found: {task_id}")
        if priority and priority not in _VALID_PRIORITIES:
            raise BoardError(f"Invalid priority: {priority}")
        if module and module not in _VALID_MODULES:
            raise BoardError(f"Invalid module: {module}")

        changes: dict[str, Any] = {}
        if title is not None:
            changes["title"] = (tasks[task_id]["title"], title)
            tasks[task_id]["title"] = title
        if priority is not None:
            changes["priority"] = (tasks[task_id]["priority"], priority)
            tasks[task_id]["priority"] = priority
        if module is not None:
            changes["module"] = (tasks[task_id]["module"], module)
            tasks[task_id]["module"] = module
        if notes is not None:
            tasks[task_id]["notes_hash"] = self._hash_notes(notes)
        if deadline is not None:
            changes["deadline_utc"] = (tasks[task_id].get("deadline_utc"), deadline)
            tasks[task_id]["deadline_utc"] = deadline

        tasks[task_id]["updated_utc"] = self._utcnow()
        self._save_tasks(tasks)
        self._event_log.append(
            "board.task_updated",
            {
                "task_id": task_id,
                "changes": {k: {"from": v[0], "to": v[1]} for k, v in changes.items()},
            },
            actor,
        )
        return tasks[task_id]

    def delete(self, task_id: str, actor: str = "user") -> dict[str, Any]:
        tasks = self._load_tasks()
        if task_id not in tasks:
            raise BoardError(f"Task not found: {task_id}")

        removed = tasks.pop(task_id)
        self._save_tasks(tasks)
        self._event_log.append(
            "board.task_deleted",
            {"task_id": task_id, "title": removed.get("title", "")},
            actor,
        )
        return removed

    def list_tasks(
        self,
        status: str | None = None,
        owner: str | None = None,
    ) -> list[dict[str, Any]]:
        tasks = self._load_tasks()
        result = list(tasks.values())
        if status:
            result = [t for t in result if t["status"] == status]
        if owner:
            result = [t for t in result if t["owner"] == owner]
        return result
