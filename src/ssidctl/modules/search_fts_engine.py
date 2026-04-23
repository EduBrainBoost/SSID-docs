"""Search FTS5 Engine — persistent SQLite FTS5 index for full-text search.

Extends search.py's in-memory FTS with a persistent on-disk index,
incremental updates, and richer query support (prefix, phrase, boolean).
"""
# ruff: noqa: S608  — table name is a fixed class constant, not user input

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class FTSError(Exception):
    pass


class FTS5Engine:
    """Persistent SQLite FTS5 search engine.

    Stores the index at {state_dir}/search/fts_index.db.
    Schema: (type TEXT, id TEXT, title TEXT, body TEXT, status TEXT, updated REAL)
    """

    _TABLE = "search_fts"
    _META_TABLE = "search_meta"

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._db_dir = state_dir / "search"
        self._db_path = self._db_dir / "fts_index.db"
        self._conn: sqlite3.Connection | None = None

    def _ensure_db(self) -> sqlite3.Connection:
        """Open or create the SQLite database with FTS5 table."""
        if self._conn is not None:
            return self._conn

        self._db_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {self._TABLE} "
            f"USING fts5(type, id, title, body, status, updated UNINDEXED)"
        )
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {self._META_TABLE} (key TEXT PRIMARY KEY, value TEXT)"
        )
        conn.commit()
        self._conn = conn
        return conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def upsert(self, doc_type: str, doc_id: str, title: str, body: str, status: str = "") -> None:
        """Insert or replace a document in the FTS index."""
        conn = self._ensure_db()
        conn.execute(f"DELETE FROM {self._TABLE} WHERE id = ?", (doc_id,))
        conn.execute(
            f"INSERT INTO {self._TABLE} (type, id, title, body, status, updated) "
            f"VALUES (?, ?, ?, ?, ?, ?)",
            (doc_type, doc_id, title, body, status, time.time()),
        )
        conn.commit()

    def upsert_batch(self, docs: list[dict[str, Any]]) -> int:
        """Batch upsert documents. Each dict needs: type, id, title, body, status.

        Returns number of documents indexed.
        """
        conn = self._ensure_db()
        count = 0
        for doc in docs:
            doc_id = doc["id"]
            conn.execute(f"DELETE FROM {self._TABLE} WHERE id = ?", (doc_id,))
            conn.execute(
                f"INSERT INTO {self._TABLE} (type, id, title, body, status, updated) "
                f"VALUES (?, ?, ?, ?, ?, ?)",
                (
                    doc.get("type", ""),
                    doc_id,
                    doc.get("title", ""),
                    doc.get("body", ""),
                    doc.get("status", ""),
                    time.time(),
                ),
            )
            count += 1
        conn.commit()
        self._set_meta("last_indexed", str(time.time()))
        return count

    def delete(self, doc_id: str) -> None:
        """Remove a document from the FTS index."""
        conn = self._ensure_db()
        conn.execute(f"DELETE FROM {self._TABLE} WHERE id = ?", (doc_id,))
        conn.commit()

    def search(
        self,
        query: str,
        type_filter: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search the FTS5 index.

        Supports FTS5 query syntax: prefix*, "exact phrase", AND/OR/NOT.
        Falls back to substring search if FTS5 query syntax fails.
        """
        conn = self._ensure_db()
        results: list[dict[str, Any]] = []

        try:
            if type_filter:
                cursor = conn.execute(
                    f"SELECT type, id, title, snippet({self._TABLE}, 3, '>>','<<', '...', 32), "
                    f"status FROM {self._TABLE} "
                    f"WHERE {self._TABLE} MATCH ? AND type = ? LIMIT ?",
                    (query, type_filter, limit),
                )
            else:
                cursor = conn.execute(
                    f"SELECT type, id, title, snippet({self._TABLE}, 3, '>>','<<', '...', 32), "
                    f"status FROM {self._TABLE} "
                    f"WHERE {self._TABLE} MATCH ? LIMIT ?",
                    (query, limit),
                )
            for row in cursor:
                results.append(
                    {
                        "type": row[0],
                        "id": row[1],
                        "title": row[2],
                        "snippet": row[3],
                        "status": row[4],
                    }
                )
        except sqlite3.OperationalError:
            results = self._fallback_search(query, type_filter, limit)

        return results

    def _fallback_search(
        self, query: str, type_filter: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Fallback substring search when FTS5 MATCH fails."""
        conn = self._ensure_db()
        like_q = f"%{query}%"

        if type_filter:
            cursor = conn.execute(
                f"SELECT type, id, title, body, status FROM {self._TABLE} "
                f"WHERE (title LIKE ? OR body LIKE ?) AND type = ? LIMIT ?",
                (like_q, like_q, type_filter, limit),
            )
        else:
            cursor = conn.execute(
                f"SELECT type, id, title, body, status FROM {self._TABLE} "
                f"WHERE title LIKE ? OR body LIKE ? LIMIT ?",
                (like_q, like_q, limit),
            )

        results: list[dict[str, Any]] = []
        for row in cursor:
            results.append(
                {
                    "type": row[0],
                    "id": row[1],
                    "title": row[2],
                    "snippet": row[3][:100] if row[3] else "",
                    "status": row[4],
                }
            )
        return results

    def rebuild_from_state(self) -> int:
        """Rebuild the full index from EMS state files.

        Scans board/tasks.yaml, content/content.yaml, team/team.yaml,
        incidents/incidents.jsonl, and memory/index.jsonl.
        Returns total document count indexed.
        """
        docs: list[dict[str, Any]] = []

        docs.extend(self._scan_board())
        docs.extend(self._scan_content())
        docs.extend(self._scan_team())
        docs.extend(self._scan_incidents())
        docs.extend(self._scan_memory())

        if docs:
            conn = self._ensure_db()
            conn.execute(f"DELETE FROM {self._TABLE}")
            conn.commit()
            return self.upsert_batch(docs)
        return 0

    def _scan_board(self) -> list[dict[str, Any]]:
        """Scan board/tasks.yaml for indexable documents."""
        import yaml

        path = self._state_dir / "board" / "tasks.yaml"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return []
        docs: list[dict[str, Any]] = []
        for task in data.get("tasks", {}).values():
            docs.append(
                {
                    "type": "task",
                    "id": task.get("task_id", ""),
                    "title": task.get("title", ""),
                    "body": f"module={task.get('module', '')} owner={task.get('owner', '')}",
                    "status": task.get("status", ""),
                }
            )
        return docs

    def _scan_content(self) -> list[dict[str, Any]]:
        """Scan content/content.yaml for indexable documents."""
        import yaml

        path = self._state_dir / "content" / "content.yaml"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return []
        docs: list[dict[str, Any]] = []
        for item in data.get("items", {}).values():
            tags = " ".join(item.get("tags", []))
            docs.append(
                {
                    "type": "content",
                    "id": item.get("content_id", ""),
                    "title": item.get("title", ""),
                    "body": f"channel={item.get('channel', '')} tags={tags}",
                    "status": item.get("stage", ""),
                }
            )
        return docs

    def _scan_team(self) -> list[dict[str, Any]]:
        """Scan team/team.yaml for indexable documents."""
        import yaml

        path = self._state_dir / "team" / "team.yaml"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return []
        docs: list[dict[str, Any]] = []
        for agent in data.get("agents", []):
            docs.append(
                {
                    "type": "agent",
                    "id": agent.get("name", ""),
                    "title": agent.get("role", ""),
                    "body": " ".join(agent.get("responsibilities", [])),
                    "status": agent.get("availability", ""),
                }
            )
        return docs

    def _scan_incidents(self) -> list[dict[str, Any]]:
        """Scan incidents/incidents.jsonl for indexable entries."""
        path = self._state_dir / "incidents" / "incidents.jsonl"
        if not path.exists():
            return []
        docs: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    payload = entry.get("payload", {})
                    docs.append(
                        {
                            "type": "incident",
                            "id": payload.get("incident_id", ""),
                            "title": payload.get("summary", ""),
                            "body": payload.get("description", ""),
                            "status": payload.get("status", ""),
                        }
                    )
                except (json.JSONDecodeError, KeyError):
                    continue
        return docs

    def _scan_memory(self) -> list[dict[str, Any]]:
        """Scan memory/index.jsonl for indexable documents."""
        path = self._state_dir / "memory" / "index.jsonl"
        if not path.exists():
            return []
        docs: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    body = ""
                    doc_path = self._state_dir / "memory" / entry.get("path", "")
                    if doc_path.exists():
                        body = doc_path.read_text(encoding="utf-8")[:2000]
                    tags = " ".join(entry.get("tags", []))
                    docs.append(
                        {
                            "type": "memory",
                            "id": entry.get("doc_id", ""),
                            "title": entry.get("title", ""),
                            "body": f"{tags} {body}".strip(),
                            "status": "",
                        }
                    )
                except (json.JSONDecodeError, KeyError):
                    continue
        return docs

    def _set_meta(self, key: str, value: str) -> None:
        conn = self._ensure_db()
        conn.execute(
            f"INSERT OR REPLACE INTO {self._META_TABLE} (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def get_meta(self, key: str) -> str | None:
        """Read a metadata value from the search_meta table."""
        conn = self._ensure_db()
        cursor = conn.execute(f"SELECT value FROM {self._META_TABLE} WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def stats(self) -> dict[str, Any]:
        """Return index statistics."""
        conn = self._ensure_db()
        total = conn.execute(f"SELECT COUNT(*) FROM {self._TABLE}").fetchone()[0]
        by_type: dict[str, int] = {}
        for row in conn.execute(f"SELECT type, COUNT(*) FROM {self._TABLE} GROUP BY type"):
            by_type[row[0]] = row[1]
        return {
            "total_docs": total,
            "by_type": by_type,
            "db_path": str(self._db_path),
            "last_indexed": self.get_meta("last_indexed"),
        }
