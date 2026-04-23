"""Durable workflow storage layer.

Provides an append-only JSONL-based persistence layer for WorkflowRun state,
Checkpoint journals, and idempotency key indexing.

Storage layout under base_dir::

    runs/{run_id}.json         — latest run snapshot (overwritten on update)
    checkpoints/{run_id}.jsonl — append-only checkpoint log per run
    idempotency.jsonl          — append-only idempotency key index
    event_log.jsonl            — append-only mutation event log

Key invariants:
- Checkpoint files are APPEND-ONLY; lines are never overwritten or deleted.
- Run snapshot files (runs/*.json) always hold the latest state.
- All event_log entries carry a payload_hash for integrity verification.
- Directory parents are created automatically on first write.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso
from ssidctl.workflow.models import Checkpoint, WorkflowRun


def _make_event_id() -> str:
    return f"EVT-{uuid.uuid4().hex[:12]}"


def _hash_payload(payload: Any) -> str:
    """Return SHA-256 of the JSON-serialized payload."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_str(raw)


class WorkflowStore:
    """Filesystem-backed storage for durable workflow runs.

    Args:
        base_dir: Root directory for all store files. Created automatically
            if it does not exist.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)
        self._runs_dir = self._base / "runs"
        self._checkpoints_dir = self._base / "checkpoints"
        self._idempotency_path = self._base / "idempotency.jsonl"
        self._event_log_path = self._base / "event_log.jsonl"

    # ------------------------------------------------------------------
    # Run persistence
    # ------------------------------------------------------------------

    def save_run(self, run: WorkflowRun) -> None:
        """Persist the latest run snapshot atomically.

        Writes ``run.to_dict()`` to a ``.tmp`` file then renames to
        ``runs/{run_id}.json`` to prevent partial writes.  Also appends a
        ``run.saved`` event to the event log.

        Args:
            run: The :class:`~ssidctl.workflow.models.WorkflowRun` to persist.
        """
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        run_path = self._runs_dir / f"{run.run_id}.json"
        tmp_path = run_path.with_suffix(".tmp")
        run_dict = run.to_dict()
        try:
            tmp_path.write_text(
                json.dumps(run_dict, separators=(",", ":"), ensure_ascii=False),
                encoding="utf-8",
            )
            tmp_path.replace(run_path)
        except Exception:
            try:  # noqa: SIM105
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        self._append_event("run.saved", {"run_id": run.run_id, "status": run.status.value})

    def load_run(self, run_id: str) -> WorkflowRun | None:
        """Load a run snapshot by ID.

        Args:
            run_id: The run UUID string.

        Returns:
            A :class:`~ssidctl.workflow.models.WorkflowRun` instance, or
            ``None`` if no snapshot exists for *run_id* or the file is corrupt.
        """
        run_path = self._runs_dir / f"{run_id}.json"
        if not run_path.exists():
            return None
        try:
            data = json.loads(run_path.read_text(encoding="utf-8"))
            return WorkflowRun.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError, ValueError):
            return None

    def list_runs(self) -> list[WorkflowRun]:
        """Return all persisted run snapshots, sorted by filename.

        Returns:
            A list of :class:`~ssidctl.workflow.models.WorkflowRun` objects.
        """
        if not self._runs_dir.exists():
            return []
        runs: list[WorkflowRun] = []
        for path in sorted(self._runs_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            runs.append(WorkflowRun.from_dict(data))
        return runs

    # ------------------------------------------------------------------
    # Checkpoint persistence
    # ------------------------------------------------------------------

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Append a checkpoint record to the per-run JSONL journal.

        Checkpoint files are APPEND-ONLY; previously written lines are
        never modified or removed.  Also appends a ``checkpoint.saved``
        event to the event log.

        Args:
            checkpoint: The :class:`~ssidctl.workflow.models.Checkpoint` to
                persist.
        """
        self._checkpoints_dir.mkdir(parents=True, exist_ok=True)
        cp_path = self._checkpoints_dir / f"{checkpoint.run_id}.jsonl"
        line = json.dumps(checkpoint.to_dict(), separators=(",", ":")) + "\n"
        with open(cp_path, "a", encoding="utf-8") as fh:
            fh.write(line)
        self._append_event(
            "checkpoint.saved",
            {
                "run_id": checkpoint.run_id,
                "step_id": checkpoint.step_id,
                "status": checkpoint.status.value,
            },
        )

    def load_checkpoints(self, run_id: str) -> list[Checkpoint]:
        """Load all checkpoints for a run, in append order.

        Args:
            run_id: The run UUID string.

        Returns:
            A list of :class:`~ssidctl.workflow.models.Checkpoint` objects,
            oldest first.  Returns an empty list if no checkpoint file exists.
        """
        cp_path = self._checkpoints_dir / f"{run_id}.jsonl"
        if not cp_path.exists():
            return []
        checkpoints: list[Checkpoint] = []
        for line in cp_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                checkpoints.append(Checkpoint.from_dict(json.loads(line)))
        return checkpoints

    # ------------------------------------------------------------------
    # Idempotency key index
    # ------------------------------------------------------------------

    def record_idempotency_key(self, key: str, run_id: str, step_id: str) -> None:
        """Append an idempotency key entry to the index.

        Args:
            key: The idempotency key (typically a ``sha256:`` string).
            run_id: The associated run UUID string.
            step_id: The associated step UUID string.
        """
        self._idempotency_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "key": key,
            "run_id": run_id,
            "step_id": step_id,
            "timestamp": utcnow_iso(),
        }
        line = json.dumps(entry, separators=(",", ":")) + "\n"
        with open(self._idempotency_path, "a", encoding="utf-8") as fh:
            fh.write(line)

    def has_idempotency_key(self, key: str) -> bool:
        """Return True if the key exists in the idempotency index.

        Performs a full linear scan of ``idempotency.jsonl``.

        Args:
            key: The idempotency key to look up.
        """
        return self.get_idempotency_entry(key) is not None

    def get_idempotency_entry(self, key: str) -> dict[str, Any] | None:
        """Return the first matching idempotency entry, or None.

        Args:
            key: The idempotency key to look up.

        Returns:
            The entry dict (with ``key``, ``run_id``, ``step_id``,
            ``timestamp`` fields), or ``None`` if the key is not found.
        """
        if not self._idempotency_path.exists():
            return None
        for line in self._idempotency_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("key") == key:
                return entry
        return None

    # ------------------------------------------------------------------
    # Internal event log
    # ------------------------------------------------------------------

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append a single structured event to ``event_log.jsonl``.

        Args:
            event_type: Dot-separated event type string (e.g. ``"run.saved"``).
            payload: Structured payload dict. Must not contain secrets or PII.
        """
        self._event_log_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "event_id": _make_event_id(),
            "timestamp": utcnow_iso(),
            "type": event_type,
            "payload": payload,
            "payload_hash": _hash_payload(payload),
        }
        line = json.dumps(event, separators=(",", ":")) + "\n"
        with open(self._event_log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
