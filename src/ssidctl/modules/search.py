"""Unified Search module — queries across all EMS modules.

Searches: tasks (board), runs, content, memory, incidents, team.
Supports optional SQLite FTS5 indexing for faster full-text search.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.event_log import EventLog
from ssidctl.modules.board import Board
from ssidctl.modules.content import ContentPipeline
from ssidctl.modules.memory import MemoryVault


class UnifiedSearch:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._board = Board(state_dir / "board")
        self._content = ContentPipeline(state_dir / "content")
        self._memory = MemoryVault(state_dir / "memory")
        self._runs_log = EventLog(state_dir / "runs" / "runs.jsonl")

    def search(self, query: str, type_filter: str | None = None) -> list[dict[str, Any]]:
        """Search across all EMS modules.

        Args:
            query: Search string (substring match).
            type_filter: Optional — restrict to 'task', 'content', 'memory',
                         'run', 'incident', or 'agent'.
        """
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        # Search board tasks
        if not type_filter or type_filter == "task":
            for task in self._board.list_tasks():
                title = task.get("title", "").lower()
                tid = task.get("task_id", "").lower()
                if query_lower in title or query_lower in tid:
                    results.append(
                        {
                            "type": "task",
                            "id": task["task_id"],
                            "title": task.get("title", ""),
                            "status": task.get("status", ""),
                        }
                    )

        # Search content
        if not type_filter or type_filter == "content":
            for item in self._content.list_items():
                title = item.get("title", "").lower()
                tags = item.get("tags", [])
                if query_lower in title or any(query_lower in t.lower() for t in tags):
                    results.append(
                        {
                            "type": "content",
                            "id": item["content_id"],
                            "title": item.get("title", ""),
                            "stage": item.get("stage", ""),
                        }
                    )

        # Search memory (uses fulltext search over markdown content)
        if not type_filter or type_filter == "memory":
            for doc in self._memory.search(query, fulltext=True):
                results.append(
                    {
                        "type": "memory",
                        "id": doc["doc_id"],
                        "title": doc.get("title", ""),
                    }
                )

        # Search runs
        if not type_filter or type_filter == "run":
            for event in self._runs_log.read_all():
                payload = event.get("payload", {})
                run_id = payload.get("run_id", "")
                task_id = payload.get("task_id", "")
                if query_lower in run_id.lower() or query_lower in task_id.lower():
                    results.append(
                        {
                            "type": "run",
                            "id": run_id,
                            "title": f"task={task_id}",
                            "status": event.get("type", ""),
                        }
                    )

        # Search incidents
        if not type_filter or type_filter == "incident":
            results.extend(self._search_incidents(query_lower))

        # Search team/agents
        if not type_filter or type_filter == "agent":
            results.extend(self._search_agents(query_lower))

        return results

    def _search_incidents(self, query_lower: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        inc_path = self._state_dir / "incidents" / "incidents.jsonl"
        if not inc_path.exists():
            return results
        with open(inc_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    payload = entry.get("payload", {})
                    inc_id = payload.get("incident_id", "")
                    summary = payload.get("summary", "")
                    if query_lower in inc_id.lower() or query_lower in summary.lower():
                        results.append(
                            {
                                "type": "incident",
                                "id": inc_id,
                                "title": summary,
                                "status": payload.get("status", ""),
                            }
                        )
                except (json.JSONDecodeError, KeyError):
                    continue
        return results

    def _search_agents(self, query_lower: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        team_path = self._state_dir / "team" / "team.yaml"
        if not team_path.exists():
            return results
        with open(team_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return results
        for agent in data.get("agents", []):
            name = agent.get("name", "")
            role = agent.get("role", "")
            if query_lower in name.lower() or query_lower in role.lower():
                results.append(
                    {
                        "type": "agent",
                        "id": name,
                        "title": role,
                        "status": agent.get("availability", ""),
                    }
                )
        return results

    def build_fts_index(self) -> sqlite3.Connection:
        """Build an in-memory SQLite FTS5 index over all searchable data."""
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS search_idx USING fts5(type, id, title, status)"
        )
        rows = []
        for task in self._board.list_tasks():
            rows.append(("task", task["task_id"], task.get("title", ""), task.get("status", "")))
        for item in self._content.list_items():
            rows.append(
                ("content", item["content_id"], item.get("title", ""), item.get("stage", ""))
            )
        for doc in self._memory.list_docs():
            rows.append(("memory", doc["doc_id"], doc.get("title", ""), ""))
        conn.executemany("INSERT INTO search_idx VALUES (?,?,?,?)", rows)
        return conn

    def fts_search(self, query: str) -> list[dict[str, Any]]:
        """Search using SQLite FTS5 index."""
        conn = self.build_fts_index()
        results = []
        try:
            cursor = conn.execute(
                "SELECT type, id, title, status FROM search_idx WHERE search_idx MATCH ?",
                (query,),
            )
            for row in cursor:
                results.append({"type": row[0], "id": row[1], "title": row[2], "status": row[3]})
        except sqlite3.OperationalError:
            # FTS query syntax error, fall back to substring
            return self.search(query)
        finally:
            conn.close()
        return results
