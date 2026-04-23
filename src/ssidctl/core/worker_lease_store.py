"""Worker lease store: tracks who owns what execution item.

A lease is acquired by a worker when it claims an item.
The lease must be renewed (heartbeat) to remain valid.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ssidctl.core.event_log import EventLog
from ssidctl.core.timeutil import utcnow_iso


def _new_claim_id() -> str:
    return f"CLAIM-{uuid.uuid4().hex[:16]}"


class WorkerLeaseStore:
    """Persistent lease store backed by a JSON file."""

    def __init__(self, store_path: Path, event_log: EventLog | None = None) -> None:
        self._path = store_path
        self._log = event_log
        self._leases: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._leases = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._leases = {}

    def _save(self) -> None:
        """Persist leases atomically via .tmp → rename."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(self._leases, indent=2, ensure_ascii=False), encoding="utf-8"
            )  # noqa: E501
            tmp.replace(self._path)
        except Exception:
            try:  # noqa: SIM105
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def acquire(self, item_id: str, worker_id: str) -> tuple[bool, dict[str, Any]]:
        """Acquire a lease for item_id by worker_id.

        Returns (success, lease_meta).
        """
        if item_id in self._leases:
            existing = self._leases[item_id]
            if existing.get("status") == "active":
                return False, existing

        claim_id = _new_claim_id()
        lease = {
            "item_id": item_id,
            "worker_id": worker_id,
            "claim_id": claim_id,
            "acquired_at": utcnow_iso(),
            "last_heartbeat": utcnow_iso(),
            "status": "active",
        }
        self._leases[item_id] = lease
        self._save()

        if self._log:
            self._log.append(
                "worker.lease_acquired",
                {"item_id": item_id, "worker_id": worker_id, "claim_id": claim_id},
                actor=worker_id,
            )
        return True, lease

    def check_lease(self, item_id: str) -> dict[str, Any] | None:
        """Return the active lease for item_id, or None."""
        lease = self._leases.get(item_id)
        if lease and lease.get("status") == "active":
            return lease
        return None

    def validate_claim(self, item_id: str, claim_id: str, worker_id: str) -> bool:
        """Return True if the claim_id matches the active lease."""
        lease = self._leases.get(item_id)
        if not lease:
            return False
        return (
            lease.get("claim_id") == claim_id
            and lease.get("worker_id") == worker_id
            and lease.get("status") == "active"
        )

    def heartbeat(self, item_id: str, claim_id: str, worker_id: str) -> bool:
        """Renew a lease. Returns False if the claim is invalid or foreign."""
        if not self.validate_claim(item_id, claim_id, worker_id):
            return False
        self._leases[item_id]["last_heartbeat"] = utcnow_iso()
        self._save()
        return True

    def release(self, item_id: str, claim_id: str, worker_id: str) -> bool:
        """Release a lease after execution completes."""
        if not self.validate_claim(item_id, claim_id, worker_id):
            return False
        self._leases[item_id]["status"] = "released"
        self._save()
        return True

    def force_expire(self, item_id: str) -> None:
        """Force-expire a lease (for testing / timeout handling)."""
        if item_id in self._leases:
            self._leases[item_id]["status"] = "expired"
            self._save()
