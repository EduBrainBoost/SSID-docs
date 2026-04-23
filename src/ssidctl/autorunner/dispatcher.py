"""AutoRunner V2B — Dispatcher: validates plan, acquires concurrency lock, transitions QUEUED."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from ssidctl.autorunner.lock import LockStore
from ssidctl.autorunner.models import AutoRunnerRun, RunStatus


class DispatchResult(BaseModel):
    run_id: str
    queue_position: int = 0
    worktree_lock: str
    lock_key: str


class Dispatcher:
    def __init__(self, lock_store: LockStore | None = None) -> None:
        self._lock_store = lock_store or LockStore()

    def dispatch(self, run: AutoRunnerRun) -> DispatchResult:
        if run.status != RunStatus.PLANNED:
            raise ValueError(
                f"Can only dispatch a PLANNED run, got: {run.status}. Ensure Planner ran first."
            )
        # Acquire concurrency lock — raises ConcurrencyConflictError if scope is taken
        self._lock_store.acquire(run)  # sets run.lock_key
        lock = f"lock-{run.run_id}-{uuid.uuid4().hex[:8]}"
        run.scope.worktree_lock = lock
        run.transition(RunStatus.QUEUED)
        return DispatchResult(
            run_id=run.run_id,
            worktree_lock=lock,
            lock_key=run.lock_key or "",
        )
