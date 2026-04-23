"""Calendar/Cron module — scheduled jobs and ICS export.

Stores cron definitions in cron.yaml and run history in runs.jsonl.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.event_log import EventLog
from ssidctl.core.timeutil import utcnow_iso


class CalendarError(Exception):
    pass


class Calendar:
    def __init__(self, calendar_dir: Path) -> None:
        self._dir = calendar_dir
        self._cron_path = calendar_dir / "cron.yaml"
        self._event_log = EventLog(calendar_dir / "runs.jsonl")

    def _load_jobs(self) -> list[dict[str, Any]]:
        if not self._cron_path.exists():
            return []
        with open(self._cron_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return (data or {}).get("jobs", [])

    def _save_jobs(self, jobs: list[dict[str, Any]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._cron_path, "w", encoding="utf-8") as f:
            yaml.dump({"jobs": jobs}, f, default_flow_style=False)

    @staticmethod
    def _utcnow() -> str:
        return utcnow_iso()

    def _find_job(self, cron_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Load jobs and find the one matching cron_id, or raise."""
        jobs = self._load_jobs()
        for job in jobs:
            if job["cron_id"] == cron_id:
                return jobs, job
        raise CalendarError(f"Cron job not found: {cron_id}")

    def add(
        self,
        cron_id: str,
        schedule: str,
        job: str,
        enabled: bool = True,
    ) -> dict[str, Any]:
        jobs = self._load_jobs()
        if any(j["cron_id"] == cron_id for j in jobs):
            raise CalendarError(f"Cron job already exists: {cron_id}")

        entry = {
            "cron_id": cron_id,
            "schedule": schedule,
            "job": job,
            "enabled": enabled,
            "last_run": None,
            "last_status": None,
            "evidence_hash": None,
        }
        jobs.append(entry)
        self._save_jobs(jobs)
        return entry

    def disable(self, cron_id: str) -> dict[str, Any]:
        jobs, job = self._find_job(cron_id)
        job["enabled"] = False
        self._save_jobs(jobs)
        return job

    def enable(self, cron_id: str) -> dict[str, Any]:
        jobs, job = self._find_job(cron_id)
        job["enabled"] = True
        self._save_jobs(jobs)
        return job

    def trigger(self, cron_id: str) -> dict[str, Any]:
        """Mark a job as triggered (run-now). Records run with status TRIGGERED."""
        jobs, job = self._find_job(cron_id)
        now = self._utcnow()
        job["last_run"] = now
        job["last_status"] = "TRIGGERED"
        self._save_jobs(jobs)
        self._event_log.append(
            "cron.triggered",
            {"cron_id": cron_id, "status": "TRIGGERED"},
        )
        return job

    def record_run(self, cron_id: str, status: str, evidence_hash: str | None = None) -> None:
        jobs, job = self._find_job(cron_id)
        now = self._utcnow()
        job["last_run"] = now
        job["last_status"] = status
        if evidence_hash:
            job["evidence_hash"] = evidence_hash
        self._save_jobs(jobs)
        self._event_log.append(
            "cron.run",
            {"cron_id": cron_id, "status": status},
        )

    def link_content(self, cron_id: str, content_id: str) -> dict[str, Any]:
        """Link a content item to a cron job."""
        jobs, job = self._find_job(cron_id)
        job["linked_content"] = content_id
        self._save_jobs(jobs)
        return job

    def list_jobs(self) -> list[dict[str, Any]]:
        return self._load_jobs()

    def _schedule_to_rrule(self, schedule: str) -> str:
        """Convert cron-like schedule to iCal RRULE (best effort)."""
        s = schedule.strip().lower()
        if s in ("@daily", "0 0 * * *", "0 2 * * *"):
            return "FREQ=DAILY"
        if s in ("@hourly", "0 * * * *"):
            return "FREQ=HOURLY"
        if s in ("@weekly", "0 0 * * 0"):
            return "FREQ=WEEKLY"
        if s in ("@monthly", "0 0 1 * *"):
            return "FREQ=MONTHLY"
        if s.startswith("@yearly") or s == "0 0 1 1 *":
            return "FREQ=YEARLY"
        # Quarterly (every 3 months)
        if "*/3" in s or "1,4,7,10" in s:
            return "FREQ=MONTHLY;INTERVAL=3"
        return "FREQ=DAILY"

    def export_ics(self) -> str:
        """Export jobs as ICS format with schedule-aware RRULE."""
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SSID-EMS//ssidctl//EN"]
        for job in self._load_jobs():
            dtstart = job.get("last_run") or self._utcnow()
            dtstart_ics = dtstart.replace("-", "").replace(":", "").replace("Z", "") + "Z"
            rrule = self._schedule_to_rrule(job["schedule"])
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"SUMMARY:{job['job']}",
                    f"DESCRIPTION:cron_id={job['cron_id']} schedule={job['schedule']}",
                    f"DTSTART:{dtstart_ics}",
                    f"RRULE:{rrule}",
                    "END:VEVENT",
                ]
            )
        lines.append("END:VCALENDAR")
        return "\n".join(lines)
