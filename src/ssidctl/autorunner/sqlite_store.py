"""AutoRunner V2 — SQLite-backed run persistence (Phase 4 production hardening).

Drop-in replacement for the YAML-backed RunStore.
Schema: runs(id TEXT PK, status TEXT, created_at TEXT, updated_at TEXT, data TEXT JSON).
Thread-safe via threading.Lock + check_same_thread=False.
DB path: {SSID_EMS_STATE}/autorunner/runs.db  (default: /tmp/ssid_state/autorunner/runs.db).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from ssidctl.autorunner.models import AutoRunnerRun


_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    data        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_updated_at ON runs (updated_at DESC);
"""


class SqliteRunStore:
    """SQLite-backed store for AutoRunner runs.

    Compatible interface with the YAML-backed RunStore:
      save(run)           — upsert
      get(run_id)         — returns AutoRunnerRun | None  (no KeyError)
      load(run_id)        — returns AutoRunnerRun, raises KeyError if missing
      list_runs(limit, offset) — ordered by updated_at DESC
      delete(run_id)      — remove a run by id
    """

    def __init__(self, db_path: str | None = None) -> None:
        _default_state = os.environ.get("SSID_EMS_STATE", "/tmp/ssid_state")  # noqa: S108
        _default_db = str(Path(_default_state) / "autorunner" / "runs.db")
        self.db_path = Path(db_path or _default_db)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # autocommit; we use explicit transactions
        )
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(_DDL)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _serialize(self, run: AutoRunnerRun) -> tuple[str, str, str, str, str]:
        """Return (id, status, created_at, updated_at, data_json)."""
        data = json.dumps(run.model_dump(mode="json"), ensure_ascii=False)
        return (run.run_id, run.status, run.created_at, run.updated_at, data)

    def _deserialize(self, row: tuple) -> AutoRunnerRun:
        data = json.loads(row[4])
        return AutoRunnerRun.model_validate(data)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, run: AutoRunnerRun) -> None:
        """Upsert a run record."""
        row = self._serialize(run)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO runs (id, status, created_at, updated_at, data)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status     = excluded.status,
                    updated_at = excluded.updated_at,
                    data       = excluded.data
                """,
                row,
            )

    def get(self, run_id: str) -> AutoRunnerRun | None:
        """Return the run or None if not found."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, status, created_at, updated_at, data FROM runs WHERE id = ?",
                (run_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._deserialize(row)

    def load(self, run_id: str) -> AutoRunnerRun:
        """Return the run, raising KeyError if not found (compat with YAML store)."""
        run = self.get(run_id)
        if run is None:
            raise KeyError(f"Run not found: {run_id}")
        return run

    def list_runs(self, limit: int = 100, offset: int = 0) -> list[AutoRunnerRun]:
        """Return runs ordered by updated_at DESC."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, status, created_at, updated_at, data "
                "FROM runs ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = cur.fetchall()
        return [self._deserialize(row) for row in rows]

    def list(self) -> list[AutoRunnerRun]:
        """Alias for list_runs() — returns all runs (no pagination)."""
        return self.list_runs(limit=2**31 - 1, offset=0)

    def delete(self, run_id: str) -> None:
        """Remove a run by id. No-op if the run does not exist."""
        with self._lock:
            self._conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> SqliteRunStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
