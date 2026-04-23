"""AutoRunner V2B — Concurrency lock: one run per scope (repo:branch)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel

from ssidctl.autorunner.models import AutoRunnerRun


class ConcurrencyConflictError(Exception):
    def __init__(self, lock_key: str, conflicting_run_id: str) -> None:
        super().__init__(
            f"Scope locked by {conflicting_run_id}: {lock_key}. "
            "Cancel or wait for the conflicting run to finish."
        )
        self.lock_key = lock_key
        self.conflicting_run_id = conflicting_run_id


class ScopeLockKey:
    @staticmethod
    def compute(run: AutoRunnerRun) -> str:
        return f"{run.scope.repo}:{run.scope.branch}"


class LockEntry(BaseModel):
    lock_key: str
    run_id: str
    locked_at: str


class LockStore:
    def __init__(self, base_dir: str | None = None) -> None:
        _default = os.environ.get("SSID_EMS_STATE", "/tmp/ssid_state")  # noqa: S108
        self._dir = Path(base_dir or _default + "/autorunner/locks")
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, lock_key: str) -> Path:
        safe = lock_key.replace(":", "__").replace("/", "_")
        return self._dir / f"{safe}.yaml"

    def acquire(self, run: AutoRunnerRun) -> LockEntry:
        key = ScopeLockKey.compute(run)
        path = self._path(key)
        if path.exists():
            existing = LockEntry.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
            raise ConcurrencyConflictError(lock_key=key, conflicting_run_id=existing.run_id)
        entry = LockEntry(lock_key=key, run_id=run.run_id, locked_at=datetime.now(UTC).isoformat())
        data = yaml.safe_dump(entry.model_dump(mode="json"), sort_keys=True)
        path.write_text(data, encoding="utf-8")
        run.lock_key = key
        return entry

    def release(self, run_id: str, lock_key: str | None) -> None:
        if not lock_key:
            return
        path = self._path(lock_key)
        if not path.exists():
            return
        existing = LockEntry.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        if existing.run_id == run_id:
            path.unlink()

    def is_locked(self, lock_key: str | None) -> LockEntry | None:
        if not lock_key:
            return None
        path = self._path(lock_key)
        if not path.exists():
            return None
        return LockEntry.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

    def list_active(self) -> list[LockEntry]:
        return [
            LockEntry.model_validate(yaml.safe_load(f.read_text(encoding="utf-8")))
            for f in sorted(self._dir.glob("*.yaml"))
        ]
