"""SoT Validation Service — file-based persistence for validation events.

Stores events as individual JSON files and maintains an append-only audit log.
Storage layout:
    runs/sot_validations/<run_id>.json   — full event payload
    runs/sot_validations/audit_log.jsonl  — one JSON line per ingested event
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SoTValidationService:
    """File-based store for SoT validation events."""

    REQUIRED_FIELDS = ("event_type", "ts", "run_id", "source", "status", "summary", "findings")

    def __init__(self, runs_dir: Path) -> None:
        self._base = runs_dir / "sot_validations"
        self._base.mkdir(parents=True, exist_ok=True)
        self._audit_log = self._base / "audit_log.jsonl"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store_event(self, event_data: dict[str, Any]) -> Path:
        """Persist a validated event to disk.

        Writes:
            1. Full event as ``<run_id>.json``
            2. Append-only line to ``audit_log.jsonl``

        Returns:
            Path to the created JSON file.
        """
        run_id: str = event_data["run_id"]
        event_file = self._base / f"{run_id}.json"

        # Write individual event file
        event_file.write_text(
            json.dumps(event_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Append to audit log (one compact JSON line)
        with self._audit_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event_data, ensure_ascii=False) + "\n")

        return event_file

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        decision: str | None = None,
        repo: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        finding_class: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return stored events sorted by ``ts`` descending with optional filters.

        Args:
            limit: Maximum number of events to return.
            offset: Number of events to skip (pagination).
            decision: Filter by decision (pass/warn/fail).
            repo: Filter by repository name.
            date_from: ISO-8601 lower bound (inclusive).
            date_to: ISO-8601 upper bound (inclusive).
            finding_class: Filter to events containing this finding class.

        Returns:
            Tuple of (filtered events page, total matching count).
        """
        events: list[dict[str, Any]] = []
        for path in self._base.glob("*.json"):
            if path.name == "audit_log.jsonl":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                events.append(data)
            except (json.JSONDecodeError, OSError):
                continue

        # Apply filters
        if decision:
            events = [
                e
                for e in events
                if e.get("status") == decision
                or (e.get("summary") or {}).get("decision") == decision
            ]
        if repo:
            events = [
                e
                for e in events
                if e.get("repo", "").lower() == repo.lower()
                or e.get("source", "").lower() == repo.lower()
            ]
        if date_from:
            events = [e for e in events if e.get("ts", "") >= date_from]
        if date_to:
            events = [e for e in events if e.get("ts", "") <= date_to]
        if finding_class:
            events = [
                e
                for e in events
                if any(f.get("class") == finding_class for f in e.get("findings", []))
            ]

        # Sort by ts descending
        events.sort(key=lambda e: e.get("ts", ""), reverse=True)
        total = len(events)
        return events[offset : offset + limit], total

    def summary(self) -> dict[str, Any]:
        """Return aggregated summary across all stored events."""
        events, total = self.list_events(limit=10000)
        by_decision: dict[str, int] = {}
        by_repo: dict[str, int] = {}
        for e in events:
            d = e.get("status", (e.get("summary") or {}).get("decision", "unknown"))
            by_decision[d] = by_decision.get(d, 0) + 1
            r = e.get("repo", "unknown")
            by_repo[r] = by_repo.get(r, 0) + 1
        latest = events[0] if events else None
        return {
            "total_runs": total,
            "by_decision": by_decision,
            "by_repo": by_repo,
            "latest_run_id": latest.get("run_id") if latest else None,
            "latest_ts": latest.get("ts") if latest else None,
            "latest_decision": latest.get("status", (latest.get("summary") or {}).get("decision"))
            if latest
            else None,
        }

    def get_event(self, run_id: str) -> dict[str, Any] | None:
        """Load a single event by *run_id*.

        Returns:
            Event dict or ``None`` if not found.
        """
        event_file = self._base / f"{run_id}.json"
        if not event_file.is_file():
            return None
        try:
            return json.loads(event_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def event_exists(self, run_id: str) -> bool:
        """Check whether an event with *run_id* is already stored."""
        return (self._base / f"{run_id}.json").is_file()
