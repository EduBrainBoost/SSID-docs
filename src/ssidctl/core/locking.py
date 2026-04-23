"""PID-based global lock for concurrency=1 enforcement.

Lock file lives at SSID_EMS_STATE/locks/ems.lock (external to both repos).
Contains JSON with PID, timestamp, holder name.
Stale lock detection via PID liveness check.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso


class LockError(Exception):
    """Raised when lock cannot be acquired."""


class EMSLock:
    """PID-based file lock for EMS global concurrency control."""

    def __init__(self, lock_dir: Path) -> None:
        self._lock_file = lock_dir / "ems.lock"

    @property
    def lock_file(self) -> Path:
        return self._lock_file

    def _read_lock(self) -> dict[str, Any] | None:
        """Read current lock state, or None if no lock."""
        if not self._lock_file.exists():
            return None
        try:
            data = json.loads(self._lock_file.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def _is_pid_alive(self, pid: int) -> bool:
        """Check if a process with the given PID is still running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _is_stale(self, lock_data: dict[str, Any]) -> bool:
        """Check if lock is stale (holder process is dead)."""
        pid = lock_data.get("pid")
        if pid is None:
            return True
        return not self._is_pid_alive(pid)

    def acquire(self, holder: str = "ssidctl") -> dict[str, Any]:
        """Acquire the global lock.

        Args:
            holder: Name of the lock holder (for diagnostics).

        Returns:
            Lock data dict.

        Raises:
            LockError: If lock is already held by a live process.
        """
        existing = self._read_lock()
        if existing is not None and not self._is_stale(existing):
            raise LockError(
                f"Lock held by PID {existing['pid']} "
                f"(holder={existing.get('holder', '?')}, "
                f"since={existing.get('acquired_at', '?')}). "
                f"Concurrency=1 enforced."
            )

        lock_data = {
            "pid": os.getpid(),
            "holder": holder,
            "acquired_at": utcnow_iso(),
        }

        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file.write_text(
            json.dumps(lock_data, indent=2),
            encoding="utf-8",
        )
        return lock_data

    def release(self) -> bool:
        """Release the lock.

        Returns:
            True if lock was released, False if no lock existed.
        """
        if not self._lock_file.exists():
            return False
        existing = self._read_lock()
        if existing and existing.get("pid") != os.getpid():
            # Don't release someone else's lock
            return False
        self._lock_file.unlink(missing_ok=True)
        return True

    def force_release(self) -> bool:
        """Force-release the lock regardless of PID.

        Use only for manual recovery.
        """
        if not self._lock_file.exists():
            return False
        self._lock_file.unlink(missing_ok=True)
        return True

    def status(self) -> dict[str, Any]:
        """Get lock status information."""
        existing = self._read_lock()
        if existing is None:
            return {"locked": False}
        stale = self._is_stale(existing)
        return {
            "locked": True,
            "stale": stale,
            "pid": existing.get("pid"),
            "holder": existing.get("holder"),
            "acquired_at": existing.get("acquired_at"),
        }

    def __enter__(self) -> EMSLock:
        self.acquire()
        return self

    def __exit__(self, *args: Any) -> None:
        self.release()
