"""EMS write-lock mechanism for Concurrency=1 enforcement.

Lock path: <state_dir>/locks/<repo_name>.lock
Lock format: JSON with holder, PID, TTL, timestamps.
Stale detection: TTL expired + PID dead.
"""

import json
import os
import socket
import uuid
from datetime import UTC, datetime
from pathlib import Path


class LockAcquireError(Exception):
    pass


class LockReleaseError(Exception):
    pass


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with given PID is alive."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _is_lock_stale(data: dict) -> bool:
    """Check if a lock is stale (TTL expired + PID dead)."""
    created = datetime.fromisoformat(data["created_at_utc"].replace("Z", "+00:00"))
    ttl = data.get("ttl_seconds", 300)
    now = datetime.now(UTC)
    elapsed = (now - created).total_seconds()

    ttl_expired = elapsed > ttl
    pid_dead = not _is_pid_alive(data.get("pid", 0))

    return ttl_expired and pid_dead


class WriteLock:
    """Manages a single-flight write lock for a repository."""

    def __init__(self, lock_dir: Path, repo_name: str):
        self.lock_dir = lock_dir
        self.repo_name = repo_name
        self.lockpath = lock_dir / f"{repo_name.lower()}.lock"
        self._lock_id: str | None = None

    def acquire(
        self,
        holder: str,
        repo_git_sha: str,
        ttl_seconds: int = 300,
    ) -> dict:
        """Acquire the write lock.

        Raises LockAcquireError if lock is held by an active process.
        Recovers stale locks (TTL expired + PID dead).
        """
        if self.lockpath.exists():
            existing = json.loads(self.lockpath.read_text(encoding="utf-8"))
            if _is_lock_stale(existing):
                self.lockpath.unlink()
            else:
                raise LockAcquireError(
                    f"Lock already held by '{existing['holder']}' "
                    f"(pid={existing.get('pid')}, ttl={existing.get('ttl_seconds')}s)"
                )

        lock_id = str(uuid.uuid4())
        data = {
            "lock_id": lock_id,
            "holder": holder,
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "cwd_repo": self.repo_name,
            "repo_git_sha": repo_git_sha,
            "mode": "WRITE",
            "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "ttl_seconds": ttl_seconds,
        }
        self.lockpath.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        self._lock_id = lock_id
        return data

    def release(self, force: bool = False) -> None:
        """Release the write lock.

        Args:
            force: If True, remove lock regardless of holder.

        Raises LockReleaseError if lock not held (and force=False).
        """
        if not self.lockpath.exists():
            if force:
                return
            raise LockReleaseError("No lock to release")

        if not force:
            existing = json.loads(self.lockpath.read_text(encoding="utf-8"))
            if self._lock_id and existing.get("lock_id") != self._lock_id:
                raise LockReleaseError(f"Lock held by different process: {existing.get('holder')}")

        self.lockpath.unlink()
        self._lock_id = None

    def status(self) -> dict:
        """Query lock state."""
        if not self.lockpath.exists():
            return {"state": "free", "repo": self.repo_name}

        data = json.loads(self.lockpath.read_text(encoding="utf-8"))

        if _is_lock_stale(data):
            return {
                "state": "stale",
                "repo": self.repo_name,
                "holder": data.get("holder"),
                "pid": data.get("pid"),
                "reason": "TTL expired + PID dead",
            }

        return {
            "state": "held",
            "repo": self.repo_name,
            "holder": data.get("holder"),
            "pid": data.get("pid"),
            "ttl_seconds": data.get("ttl_seconds"),
            "created_at_utc": data.get("created_at_utc"),
        }
