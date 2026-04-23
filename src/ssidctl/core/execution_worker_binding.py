"""Execution worker binding: wires together queue, leases, dispatcher, results.

This is the top-level coordinator for the worker execution flow:
  register -> claim -> heartbeat -> execute -> store result
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ssidctl.core.action_adapter_registry import get_adapter, get_dispatch_entry
from ssidctl.core.audited_action_dispatcher import AuditedActionDispatcher
from ssidctl.core.event_log import EventLog
from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso
from ssidctl.core.worker_lease_store import WorkerLeaseStore


def _new_exec_id() -> str:
    return f"EXEC-{uuid.uuid4().hex[:16]}"


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass
class ExecutionItem:
    """An item in the execution queue."""

    item_id: str
    action_type: str
    target_ref: str
    repo_root: str = ""
    status: str = "pending"  # pending | claimed | succeeded | failed | blocked | expired
    claim_id: str = ""
    worker_id: str = ""
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "action_type": self.action_type,
            "target_ref": self.target_ref,
            "repo_root": self.repo_root,
            "status": self.status,
            "claim_id": self.claim_id,
            "worker_id": self.worker_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionItem:
        return cls(
            item_id=d["item_id"],
            action_type=d["action_type"],
            target_ref=d["target_ref"],
            repo_root=d.get("repo_root", ""),
            status=d.get("status", "pending"),
            claim_id=d.get("claim_id", ""),
            worker_id=d.get("worker_id", ""),
            created_at=d.get("created_at", utcnow_iso()),
            updated_at=d.get("updated_at", utcnow_iso()),
            extra=d.get("extra", {}),
        )


@dataclass
class ExecutionResult:
    """Result of executing a single queue item."""

    execution_id: str
    item_id: str
    worker_id: str
    action_type: str
    outcome_status: str  # succeeded | failed | blocked | dry_run
    stdout_summary: str = ""
    stderr_summary: str = ""
    changed_files: list[str] = field(default_factory=list)
    dry_run: bool = False
    result_hash: str = ""
    started_at: str = field(default_factory=utcnow_iso)
    finished_at: str = field(default_factory=utcnow_iso)

    def compute_result_hash(self) -> str:
        payload = json.dumps(
            {
                "execution_id": self.execution_id,
                "item_id": self.item_id,
                "outcome_status": self.outcome_status,
                "stdout_summary": self.stdout_summary,
                "changed_files": sorted(self.changed_files),
            },
            sort_keys=True,
        )
        return sha256_str(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "item_id": self.item_id,
            "worker_id": self.worker_id,
            "action_type": self.action_type,
            "outcome_status": self.outcome_status,
            "stdout_summary": self.stdout_summary,
            "stderr_summary": self.stderr_summary,
            "changed_files": self.changed_files,
            "dry_run": self.dry_run,
            "result_hash": self.result_hash,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionResult:
        return cls(
            execution_id=d["execution_id"],
            item_id=d["item_id"],
            worker_id=d["worker_id"],
            action_type=d["action_type"],
            outcome_status=d["outcome_status"],
            stdout_summary=d.get("stdout_summary", ""),
            stderr_summary=d.get("stderr_summary", ""),
            changed_files=d.get("changed_files", []),
            dry_run=d.get("dry_run", False),
            result_hash=d.get("result_hash", ""),
            started_at=d.get("started_at", utcnow_iso()),
            finished_at=d.get("finished_at", utcnow_iso()),
        )


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------


class ExecutionQueue:
    """Persistent FIFO queue backed by a JSON file."""

    def __init__(self, queue_path: Path) -> None:
        self._path = queue_path
        self._items: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._items = {item["item_id"]: item for item in data.get("items", [])}
                self._order = data.get("order", list(self._items.keys()))
            except Exception:
                self._items = {}
                self._order = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {
                    "items": [self._items[k] for k in self._order if k in self._items],
                    "order": self._order,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def enqueue(self, item: ExecutionItem) -> None:
        self._items[item.item_id] = item.to_dict()
        if item.item_id not in self._order:
            self._order.append(item.item_id)
        self._save()

    def get(self, item_id: str) -> ExecutionItem | None:
        d = self._items.get(item_id)
        return ExecutionItem.from_dict(d) if d else None

    def next_pending(self, allowed_types: set[str] | None = None) -> ExecutionItem | None:
        """Return the first pending item that has an allowed action type."""
        for item_id in self._order:
            d = self._items.get(item_id)
            if not d:
                continue
            if d.get("status") != "pending":
                continue
            if allowed_types is not None and d["action_type"] not in allowed_types:
                continue
            return ExecutionItem.from_dict(d)
        return None

    def update_status(self, item_id: str, status: str, **kwargs: Any) -> None:
        if item_id in self._items:
            self._items[item_id]["status"] = status
            self._items[item_id]["updated_at"] = utcnow_iso()
            for k, v in kwargs.items():
                self._items[item_id][k] = v
            self._save()


# ---------------------------------------------------------------------------
# Result store
# ---------------------------------------------------------------------------


class ExecutionResultStore:
    """Persistent store for execution results backed by a JSON file."""

    def __init__(self, store_path: Path, event_log: EventLog | None = None) -> None:
        self._path = store_path
        self._log = event_log
        self._results: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._results = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._results = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._results, indent=2), encoding="utf-8")

    def store(self, result: ExecutionResult) -> None:
        self._results[result.execution_id] = result.to_dict()
        self._save()

    def get(self, execution_id: str) -> ExecutionResult | None:
        d = self._results.get(execution_id)
        return ExecutionResult.from_dict(d) if d else None

    def list_all(self) -> list[ExecutionResult]:
        return [ExecutionResult.from_dict(d) for d in self._results.values()]


# ---------------------------------------------------------------------------
# Worker binding
# ---------------------------------------------------------------------------

_KNOWN_ACTION_TYPES = set(["lint_fix", "format_fix", "dependency_update", "test_fix"])


class ExecutionWorkerBinding:
    """Top-level coordinator for the worker execution lifecycle."""

    def __init__(
        self,
        queue: ExecutionQueue,
        lease_store: WorkerLeaseStore,
        dispatcher: AuditedActionDispatcher,
        result_store: ExecutionResultStore,
        event_log: EventLog,
    ) -> None:
        self._queue = queue
        self._leases = lease_store
        self._dispatcher = dispatcher
        self._results = result_store
        self._log = event_log
        self._workers: dict[str, dict[str, Any]] = {}

    def register_worker(
        self, worker_id: str, capabilities: list[str] | None = None
    ) -> dict[str, Any]:
        entry = {
            "worker_id": worker_id,
            "capabilities": capabilities or list(_KNOWN_ACTION_TYPES),
            "registered_at": utcnow_iso(),
        }
        self._workers[worker_id] = entry
        self._log.append("worker.registered", entry, actor=worker_id)
        return entry

    def claim_next(self, worker_id: str) -> ExecutionItem | None:
        """Claim the next executable item for this worker."""
        worker = self._workers.get(worker_id)
        capabilities = set(worker["capabilities"]) if worker else _KNOWN_ACTION_TYPES

        # Only items whose action_type is in the dispatch matrix AND in capabilities
        allowed = {t for t in capabilities if get_dispatch_entry(t) is not None}
        item = self._queue.next_pending(allowed_types=allowed)
        if item is None:
            return None

        ok, lease = self._leases.acquire(item.item_id, worker_id)
        if not ok:
            return None

        self._queue.update_status(
            item.item_id, "claimed", claim_id=lease["claim_id"], worker_id=worker_id
        )
        item.status = "claimed"
        item.claim_id = lease["claim_id"]
        item.worker_id = worker_id

        self._log.append(
            "worker.claimed",
            {"item_id": item.item_id, "worker_id": worker_id, "claim_id": lease["claim_id"]},
            actor=worker_id,
        )
        return item

    def heartbeat(self, item_id: str, claim_id: str, worker_id: str) -> bool:
        """Renew a lease. Returns False if claim is invalid or foreign."""
        return self._leases.heartbeat(item_id, claim_id, worker_id)

    def mark_timeout(self, item_id: str) -> None:
        """Mark an item as expired (lease timeout)."""
        self._queue.update_status(item_id, "expired")
        self._leases.force_expire(item_id)

    def execute(
        self,
        item: ExecutionItem,
        worker_id: str,
        dry_run: bool = False,
        approval_token: str | None = None,
    ) -> ExecutionResult:
        """Execute an item via the audited dispatcher.

        Returns an ExecutionResult regardless of outcome.
        """
        execution_id = _new_exec_id()
        started = utcnow_iso()

        # Gate: action_type must be in dispatch matrix
        entry = get_dispatch_entry(item.action_type)
        if entry is None:
            result = ExecutionResult(
                execution_id=execution_id,
                item_id=item.item_id,
                worker_id=worker_id,
                action_type=item.action_type,
                outcome_status="blocked",
                stderr_summary=f"'{item.action_type}' not in dispatch matrix",
                dry_run=dry_run,
                started_at=started,
                finished_at=utcnow_iso(),
            )
            self._results.store(result)
            self._log.append(
                "worker.execution_complete",
                result.to_dict(),
                actor=worker_id,
            )
            self._queue.update_status(item.item_id, "blocked")
            return result

        # Gate: adapter must exist
        adapter = get_adapter(item.action_type)
        if adapter is None:
            result = ExecutionResult(
                execution_id=execution_id,
                item_id=item.item_id,
                worker_id=worker_id,
                action_type=item.action_type,
                outcome_status="blocked",
                stderr_summary=f"No adapter registered for '{item.action_type}'",
                dry_run=dry_run,
                started_at=started,
                finished_at=utcnow_iso(),
            )
            self._results.store(result)
            self._log.append("worker.execution_complete", result.to_dict(), actor=worker_id)
            self._queue.update_status(item.item_id, "blocked")
            return result

        # Dispatch
        adapter_output = self._dispatcher.dispatch(
            action_type=item.action_type,
            target_ref=item.target_ref,
            repo_root=item.repo_root,
            worker_id=worker_id,
            claim_id=item.claim_id,
            item_id=item.item_id,
            dry_run=dry_run,
            approval_token=approval_token,
            extra=item.extra,
        )

        # Map adapter outcome to execution result
        if adapter_output.outcome == "dry_run":
            outcome_status = "succeeded"
        else:
            outcome_status = adapter_output.outcome  # succeeded | blocked | failed

        result = ExecutionResult(
            execution_id=execution_id,
            item_id=item.item_id,
            worker_id=worker_id,
            action_type=item.action_type,
            outcome_status=outcome_status,
            stdout_summary=adapter_output.stdout_summary,
            stderr_summary=adapter_output.stderr_summary,
            changed_files=adapter_output.changed_files,
            dry_run=dry_run,
            started_at=started,
            finished_at=utcnow_iso(),
        )
        result.result_hash = result.compute_result_hash()

        self._results.store(result)
        self._log.append("worker.execution_complete", result.to_dict(), actor=worker_id)
        self._queue.update_status(item.item_id, outcome_status)

        return result
