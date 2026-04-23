"""Release Store — persistent, append-only storage for release lifecycle records.

Stores release records as JSON files in state_dir/releases/{release_id}.json.
All transitions are logged in an append-only JSONL at state_dir/releases/transitions.jsonl.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ssidctl.core.release_state_machine import (
    ReleaseRecord,
    ReleaseState,
    ReleaseVersion,
    apply_transition,
)

logger = logging.getLogger(__name__)


class ReleaseStoreError(Exception):
    """Raised on release store violations."""


class ReleaseStore:
    """Persistent release lifecycle store."""

    def __init__(self, state_dir: Path) -> None:
        self._releases_dir = state_dir / "releases"
        self._transitions_log = self._releases_dir / "transitions.jsonl"

    def _ensure_dir(self) -> None:
        self._releases_dir.mkdir(parents=True, exist_ok=True)

    def _record_path(self, release_id: str) -> Path:
        return self._releases_dir / f"{release_id}.json"

    def create(self, release_id: str, version: str, *, operator: str = "") -> ReleaseRecord:
        """Create a new release in DRAFT state."""
        self._ensure_dir()
        path = self._record_path(release_id)
        if path.exists():
            raise ReleaseStoreError(f"Release already exists: {release_id}")

        record = ReleaseRecord(
            release_id=release_id,
            version=ReleaseVersion.parse(version),
        )
        self._write_record(record)
        self._append_transition_log(
            {
                "release_id": release_id,
                "action": "create",
                "to_state": str(record.state),
                "version": version,
                "operator": operator,
                "timestamp_utc": record.created_utc,
            }
        )
        return record

    def get(self, release_id: str) -> ReleaseRecord | None:
        """Load a release record by ID."""
        path = self._record_path(release_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return ReleaseRecord.from_dict(data)
        except Exception as e:
            logger.warning("Failed to load release %s: %s", release_id, e)
            return None

    def list_releases(self) -> list[dict[str, Any]]:
        """List all releases."""
        if not self._releases_dir.is_dir():
            return []
        releases = []
        for f in sorted(self._releases_dir.glob("*.json")):
            if f.name == "transitions.jsonl":
                continue
            try:
                data = json.loads(f.read_text())
                releases.append(data)
            except Exception:  # noqa: S112
                continue
        return releases

    def transition(
        self,
        release_id: str,
        to_state: str,
        *,
        gate_passed: bool | None = None,
        operator: str = "",
        reason: str = "",
        evidence_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute a state transition on a release."""
        record = self.get(release_id)
        if record is None:
            raise ReleaseStoreError(f"Release not found: {release_id}")

        target = ReleaseState(to_state)
        result = apply_transition(
            record,
            target,
            gate_passed=gate_passed,
            operator=operator,
            reason=reason,
        )

        if result.allowed:
            self._write_record(record)
            self._append_transition_log(
                {
                    "release_id": release_id,
                    "action": "transition",
                    "from_state": str(result.from_state),
                    "to_state": str(result.to_state),
                    "operator": operator,
                    "reason": reason or result.reason,
                    "evidence_hash": result.evidence_hash,
                    "evidence_refs": evidence_refs or [],
                    "timestamp_utc": result.timestamp_utc,
                }
            )

        return {
            "allowed": result.allowed,
            "from_state": str(result.from_state),
            "to_state": str(result.to_state),
            "reason": result.reason,
            "evidence_hash": result.evidence_hash,
            "timestamp_utc": result.timestamp_utc,
        }

    def get_transition_log(self) -> list[dict[str, Any]]:
        """Read the full transition log."""
        if not self._transitions_log.exists():
            return []
        entries = []
        for line in self._transitions_log.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def _write_record(self, record: ReleaseRecord) -> None:
        """Write record to disk atomically."""
        self._ensure_dir()
        path = self._record_path(record.release_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record.to_dict(), indent=2))
        tmp.replace(path)

    def _append_transition_log(self, entry: dict[str, Any]) -> None:
        """Append entry to transitions JSONL."""
        self._ensure_dir()
        with self._transitions_log.open("a") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
