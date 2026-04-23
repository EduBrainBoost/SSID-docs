"""Hash-only Approval Ledger.

Records explicit approval artifacts in append-only JSONL.
APPLY requires an approval record — no approval = no apply.

Fields: approval_id, task_id, run_id, approver, approved_utc,
        diff_hash, toolchain_hash, scope_hash.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso


class ApprovalError(Exception):
    """Raised on approval violations."""


def _make_approval_id() -> str:
    return f"A-{uuid.uuid4().hex[:8]}"


class ApprovalLedger:
    """Append-only approval ledger (hash-only)."""

    def __init__(self, ledger_path: Path) -> None:
        self._path = ledger_path

    @property
    def path(self) -> Path:
        return self._path

    def record(
        self,
        task_id: str,
        run_id: str,
        approver: str,
        diff_hash: str,
        toolchain_hash: str,
        scope_hash: str,
    ) -> dict[str, Any]:
        """Record an approval.

        Args:
            task_id: The task being approved.
            run_id: The run being approved.
            approver: Who approved (e.g. "user", "agent:Agent-AUD").
            diff_hash: SHA-256 of the diff.
            toolchain_hash: SHA-256 of toolchain state.
            scope_hash: SHA-256 of scope spec.

        Returns:
            The approval record.
        """
        if not approver:
            raise ApprovalError("Approver is required")
        if not diff_hash.startswith("sha256:"):
            raise ApprovalError(f"diff_hash must be sha256: prefixed, got: {diff_hash}")

        record = {
            "approval_id": _make_approval_id(),
            "task_id": task_id,
            "run_id": run_id,
            "approver": approver,
            "approved_utc": utcnow_iso(),
            "diff_hash": diff_hash,
            "toolchain_hash": toolchain_hash,
            "scope_hash": scope_hash,
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

        return record

    def find_approval(self, task_id: str, diff_hash: str) -> dict[str, Any] | None:
        """Find an approval matching task_id and diff_hash.

        Returns the approval record or None.
        """
        for entry in self.read_all():
            if entry["task_id"] == task_id and entry["diff_hash"] == diff_hash:
                return entry
        return None

    def has_approval(self, task_id: str, diff_hash: str) -> bool:
        """Check if an approval exists for the given task and diff."""
        return self.find_approval(task_id, diff_hash) is not None

    def read_all(self) -> list[dict[str, Any]]:
        """Read all approval records."""
        if not self._path.exists():
            return []
        entries = []
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def read_by_task(self, task_id: str) -> list[dict[str, Any]]:
        """Read approvals for a specific task."""
        return [e for e in self.read_all() if e["task_id"] == task_id]

    def count(self) -> int:
        """Count total approvals."""
        if not self._path.exists():
            return 0
        n = 0
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    n += 1
        return n
