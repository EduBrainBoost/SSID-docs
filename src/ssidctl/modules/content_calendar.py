"""Content Calendar Extension — link content items to calendar and export.

Provides utilities to bridge content.py and calendar_mod.py:
- Link content publish dates into ICS events
- Query content by publish date range
- Generate a unified editorial calendar view
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


class ContentCalendarError(Exception):
    pass


def parse_date(date_str: str) -> datetime:
    """Parse an ISO-8601 date or datetime string."""
    try:
        clean = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except ValueError as exc:
        raise ContentCalendarError(f"Invalid date: {date_str!r}") from exc


def content_with_publish_dates(state_dir: Path) -> list[dict[str, Any]]:
    """Load all content items that have a publish_date set."""
    path = state_dir / "content" / "content.yaml"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or not isinstance(data, dict):
        return []

    return [item for item in data.get("items", {}).values() if item.get("publish_date")]


def content_by_date_range(
    state_dir: Path,
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    """Return content items with publish_date in [start, end] range."""
    start_dt = parse_date(start)
    end_dt = parse_date(end)
    result: list[dict[str, Any]] = []
    for item in content_with_publish_dates(state_dir):
        try:
            pub = parse_date(item["publish_date"])
        except ContentCalendarError:
            continue
        if start_dt <= pub <= end_dt:
            result.append(item)
    result.sort(key=lambda x: x["publish_date"])
    return result


def editorial_calendar(state_dir: Path, weeks_ahead: int = 4) -> list[dict[str, Any]]:
    """Generate an editorial calendar for the next N weeks.

    Returns a list of {week_start, week_end, items: [...]}.
    """
    now = datetime.now(tz=UTC)
    weeks: list[dict[str, Any]] = []

    for i in range(weeks_ahead):
        from datetime import timedelta

        week_start = now + timedelta(weeks=i)
        week_end = week_start + timedelta(days=7)
        start_str = week_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = week_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        items = content_by_date_range(state_dir, start_str, end_str)
        weeks.append(
            {
                "week": i + 1,
                "start": start_str,
                "end": end_str,
                "items": items,
            }
        )
    return weeks


def export_content_ics(state_dir: Path) -> str:
    """Export content publish dates as ICS calendar events.

    Each content item with a publish_date becomes a VEVENT.
    """
    items = content_with_publish_dates(state_dir)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SSID-EMS//content-calendar//EN",
    ]

    for item in items:
        try:
            pub = parse_date(item["publish_date"])
        except ContentCalendarError:
            continue

        dtstart = pub.strftime("%Y%m%dT%H%M%SZ")
        cid = item.get("content_id", "unknown")
        title = item.get("title", "Untitled")
        channel = item.get("channel", "")
        stage = item.get("stage", "")
        tags = ",".join(item.get("tags", []))

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"SUMMARY:Publish: {title}",
                f"DESCRIPTION:content_id={cid} channel={channel} stage={stage} tags={tags}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtstart}",
                f"UID:{cid}@ssid-ems",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\n".join(lines)


def link_content_to_cron(
    state_dir: Path,
    cron_id: str,
    content_id: str,
) -> dict[str, Any]:
    """Link a content item to a cron job in the calendar.

    Updates the cron.yaml entry to include linked_content.
    Returns the updated cron job dict.
    """
    cron_path = state_dir / "calendar" / "cron.yaml"
    if not cron_path.exists():
        raise ContentCalendarError(f"Cron config not found: {cron_path}")

    with open(cron_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or not isinstance(data, dict):
        raise ContentCalendarError("Invalid cron.yaml")

    jobs = data.get("jobs", [])
    for job in jobs:
        if job.get("cron_id") == cron_id:
            job["linked_content"] = content_id
            with open(cron_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False)
            return job

    raise ContentCalendarError(f"Cron job not found: {cron_id}")


def render_editorial_calendar(weeks: list[dict[str, Any]]) -> str:
    """Render an editorial calendar as text."""
    lines = ["Editorial Calendar", "=" * 50]
    for week in weeks:
        lines.append(f"\n  Week {week['week']}: {week['start'][:10]} - {week['end'][:10]}")
        items = week.get("items", [])
        if not items:
            lines.append("    (no content scheduled)")
        else:
            for item in items:
                cid = item.get("content_id", "?")
                title = item.get("title", "Untitled")
                stage = item.get("stage", "?")
                pub = item.get("publish_date", "?")[:10]
                lines.append(f"    [{cid}] {title} ({stage}) — publish: {pub}")
    return "\n".join(lines)
