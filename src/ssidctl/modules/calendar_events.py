"""Calendar Events module — general events beyond cron jobs.

Event types: TASK_DEADLINE, PIPELINE_SCHEDULE, AUTOMATION_JOB, GOVERNANCE_CYCLE, AGENT_SHIFT, SYSTEM_EVENT
Storage: calendar/events.jsonl (append-only index) + calendar/events/ dir for details
"""  # noqa: E501

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso

_VALID_EVENT_TYPES = frozenset(
    {
        "TASK_DEADLINE",
        "PIPELINE_SCHEDULE",
        "AUTOMATION_JOB",
        "GOVERNANCE_CYCLE",
        "AGENT_SHIFT",
        "SYSTEM_EVENT",
    }
)

_VALID_STATUSES = frozenset({"SCHEDULED", "TRIGGERED", "COMPLETED", "CANCELLED", "OVERDUE"})


class CalendarEventError(Exception):
    pass


class CalendarEventStore:
    def __init__(self, calendar_dir: Path) -> None:
        self._dir = calendar_dir
        self._index_path = calendar_dir / "events.jsonl"

    def _load_events(self) -> list[dict[str, Any]]:
        if not self._index_path.exists():
            return []
        events = []
        with open(self._index_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def _save_events(self, events: list[dict[str, Any]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._index_path, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev, separators=(",", ":")) + "\n")

    def create(
        self,
        title: str,
        event_type: str,
        start_time: str,
        end_time: str | None = None,
        description: str = "",
        owner: str = "user",
        linked_task: str | None = None,
        linked_pipeline_item: str | None = None,
        assigned_agent: str | None = None,
        recurrence: str | None = None,
        reminder_minutes: int | None = None,
    ) -> dict[str, Any]:
        if event_type not in _VALID_EVENT_TYPES:
            raise CalendarEventError(f"Invalid event type: {event_type}")

        event_id = f"EVT-{uuid.uuid4().hex[:8]}"
        now = utcnow_iso()
        event = {
            "event_id": event_id,
            "title": title,
            "description": description,
            "event_type": event_type,
            "start_time": start_time,
            "end_time": end_time,
            "owner": owner,
            "linked_task": linked_task,
            "linked_pipeline_item": linked_pipeline_item,
            "assigned_agent": assigned_agent,
            "recurrence": recurrence,
            "reminder_minutes": reminder_minutes,
            "status": "SCHEDULED",
            "created_at": now,
            "updated_at": now,
        }
        events = self._load_events()
        events.append(event)
        self._save_events(events)
        return event

    def get(self, event_id: str) -> dict[str, Any]:
        for ev in self._load_events():
            if ev["event_id"] == event_id:
                return ev
        raise CalendarEventError(f"Event not found: {event_id}")

    def update(self, event_id: str, **kwargs: Any) -> dict[str, Any]:
        events = self._load_events()
        for ev in events:
            if ev["event_id"] == event_id:
                for k, v in kwargs.items():
                    if v is not None and k in ev:
                        ev[k] = v
                ev["updated_at"] = utcnow_iso()
                self._save_events(events)
                return ev
        raise CalendarEventError(f"Event not found: {event_id}")

    def delete(self, event_id: str) -> dict[str, Any]:
        events = self._load_events()
        for i, ev in enumerate(events):
            if ev["event_id"] == event_id:
                removed = events.pop(i)
                self._save_events(events)
                return removed
        raise CalendarEventError(f"Event not found: {event_id}")

    def transition(self, event_id: str, new_status: str) -> dict[str, Any]:
        if new_status not in _VALID_STATUSES:
            raise CalendarEventError(f"Invalid status: {new_status}")
        return self.update(event_id, status=new_status)

    def list_events(
        self,
        event_type: str | None = None,
        owner: str | None = None,
        status: str | None = None,
        assigned_agent: str | None = None,
    ) -> list[dict[str, Any]]:
        events = self._load_events()
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        if owner:
            events = [e for e in events if e.get("owner") == owner]
        if status:
            events = [e for e in events if e.get("status") == status]
        if assigned_agent:
            events = [e for e in events if e.get("assigned_agent") == assigned_agent]
        return events

    def upcoming(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return upcoming events sorted by start_time."""
        now = utcnow_iso()
        events = [
            e
            for e in self._load_events()
            if e.get("start_time", "") >= now and e.get("status") == "SCHEDULED"
        ]  # noqa: E501
        events.sort(key=lambda e: e.get("start_time", ""))
        return events[:limit]

    def today(self) -> list[dict[str, Any]]:
        """Return events for today."""
        today_prefix = utcnow_iso()[:10]  # "2026-03-15"
        return [e for e in self._load_events() if e.get("start_time", "").startswith(today_prefix)]

    def search(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        return [
            e
            for e in self._load_events()
            if q in e.get("title", "").lower() or q in e.get("description", "").lower()
        ]  # noqa: E501
