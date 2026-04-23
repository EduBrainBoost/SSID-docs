"""Board Deadline Extension — deadline querying and alerting helpers.

Supplements board.py with deadline-specific queries and event emission.
Works on the raw task dicts returned by Board.list_tasks().
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class DeadlineError(Exception):
    pass


def parse_deadline(deadline_str: str) -> datetime:
    """Parse an ISO-8601 UTC deadline string into a timezone-aware datetime."""
    try:
        clean = deadline_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except ValueError as exc:
        raise DeadlineError(f"Invalid deadline format: {deadline_str!r}") from exc


def deadline_status(task: dict[str, Any]) -> str:
    """Return 'OVERDUE', 'DUE_SOON', 'OK', or 'NONE' for a task's deadline.

    DUE_SOON = deadline within the next 48 hours.
    """
    raw = task.get("deadline_utc")
    if not raw:
        return "NONE"
    try:
        dl = parse_deadline(raw)
    except DeadlineError:
        return "NONE"

    now = datetime.now(tz=UTC)
    delta = dl - now
    total_seconds = delta.total_seconds()

    if total_seconds < 0:
        return "OVERDUE"
    if total_seconds < 48 * 3600:
        return "DUE_SOON"
    return "OK"


def filter_overdue(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only tasks whose deadline has passed."""
    return [t for t in tasks if deadline_status(t) == "OVERDUE"]


def filter_due_soon(tasks: list[dict[str, Any]], hours: int = 48) -> list[dict[str, Any]]:
    """Return tasks due within the next *hours* hours (default 48)."""
    now = datetime.now(tz=UTC)
    result: list[dict[str, Any]] = []
    for task in tasks:
        raw = task.get("deadline_utc")
        if not raw:
            continue
        try:
            dl = parse_deadline(raw)
        except DeadlineError:
            continue
        delta = dl - now
        if 0 <= delta.total_seconds() < hours * 3600:
            result.append(task)
    return result


def sort_by_deadline(tasks: list[dict[str, Any]], ascending: bool = True) -> list[dict[str, Any]]:
    """Sort tasks by deadline_utc (tasks without deadline are placed last)."""

    def _key(task: dict[str, Any]) -> tuple[int, datetime]:
        raw = task.get("deadline_utc")
        if not raw:
            return (1, datetime.max.replace(tzinfo=UTC))
        try:
            return (0, parse_deadline(raw))
        except DeadlineError:
            return (1, datetime.max.replace(tzinfo=UTC))

    return sorted(tasks, key=_key, reverse=not ascending)


def deadline_summary(tasks: list[dict[str, Any]]) -> dict[str, int]:
    """Return count of tasks per deadline_status bucket."""
    counts: dict[str, int] = {"OVERDUE": 0, "DUE_SOON": 0, "OK": 0, "NONE": 0}
    for task in tasks:
        status = deadline_status(task)
        counts[status] = counts.get(status, 0) + 1
    return counts


def upcoming_deadlines(tasks: list[dict[str, Any]], days: int = 7) -> list[dict[str, Any]]:
    """Return tasks with deadlines in the next N days, sorted soonest-first."""
    now = datetime.now(tz=UTC)
    upcoming: list[tuple[datetime, dict[str, Any]]] = []
    for task in tasks:
        raw = task.get("deadline_utc")
        if not raw:
            continue
        try:
            dl = parse_deadline(raw)
        except DeadlineError:
            continue
        delta = dl - now
        if 0 <= delta.total_seconds() < days * 86400:
            upcoming.append((dl, task))
    upcoming.sort(key=lambda pair: pair[0])
    return [pair[1] for pair in upcoming]


def render_deadline_report(tasks: list[dict[str, Any]]) -> str:
    """Render a human-readable deadline report for the board."""
    summary = deadline_summary(tasks)
    lines = [
        "Deadline Report",
        "=" * 40,
        f"  OVERDUE:  {summary['OVERDUE']}",
        f"  DUE_SOON: {summary['DUE_SOON']}",
        f"  OK:       {summary['OK']}",
        f"  No DL:    {summary['NONE']}",
        "",
    ]

    overdue = filter_overdue(tasks)
    if overdue:
        lines.append("OVERDUE tasks:")
        for t in sort_by_deadline(overdue):
            lines.append(
                f"  [{t.get('task_id', '?')}] {t.get('title', '')} — {t.get('deadline_utc', '')}"
            )
        lines.append("")

    soon = filter_due_soon(tasks)
    if soon:
        lines.append("DUE SOON tasks (next 48h):")
        for t in sort_by_deadline(soon):
            lines.append(
                f"  [{t.get('task_id', '?')}] {t.get('title', '')} — {t.get('deadline_utc', '')}"
            )

    return "\n".join(lines)
