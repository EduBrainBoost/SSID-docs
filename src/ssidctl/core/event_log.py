"""Append-only JSONL event writer.

All mutations in EMS modules are recorded as events in JSONL files.
Events are immutable once written — the log is the source of truth,
YAML snapshots are derived views.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso


def _make_event_id() -> str:
    return f"EVT-{uuid.uuid4().hex[:12]}"


def _hash_payload(payload: Any) -> str:
    """SHA-256 of the JSON-serialized payload."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_str(raw)


class EventLog:
    """Append-only JSONL event writer for a single log file."""

    def __init__(self, log_path: Path) -> None:
        self._path = log_path

    @property
    def path(self) -> Path:
        return self._path

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        actor: str = "system",
    ) -> dict[str, Any]:
        """Write a single event and return the event dict.

        Args:
            event_type: Event type string (e.g. "task.created", "board.moved").
            payload: Structured payload. Will be hashed, not stored raw in
                     contexts where hash-only policy applies.
            actor: Who triggered the event (user, agent name, system).

        Returns:
            The complete event dict as written.
        """
        event = {
            "event_id": _make_event_id(),
            "timestamp": utcnow_iso(),
            "type": event_type,
            "payload": payload,
            "payload_hash": _hash_payload(payload),
            "actor": actor,
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")

        return event

    def read_all(self) -> list[dict[str, Any]]:
        """Read all events from the log file."""
        if not self._path.exists():
            return []
        events = []
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def read_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Read events filtered by type."""
        return [e for e in self.read_all() if e["type"] == event_type]

    def count(self) -> int:
        """Count total events without loading all into memory."""
        if not self._path.exists():
            return 0
        n = 0
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    n += 1
        return n

    def verify_integrity(self) -> list[str]:
        """Verify payload hashes match for all events.

        Returns:
            List of event_ids with mismatched hashes (empty = all OK).
        """
        failures = []
        for event in self.read_all():
            expected = _hash_payload(event["payload"])
            if event.get("payload_hash") != expected:
                failures.append(event["event_id"])
        return failures
