"""Quarantine module — security-only file isolation.

Only for: malware, compromised binaries, active exploit risk, DMCA.
Stores SHA256 hash + metadata; optionally moves file to quarantine storage.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.event_log import EventLog
from ssidctl.core.hashing import sha256_file
from ssidctl.core.timeutil import utcnow_iso


class QuarantineError(Exception):
    pass


class QuarantineStore:
    def __init__(self, quarantine_dir: Path) -> None:
        self._dir = quarantine_dir
        self._store = quarantine_dir / "store"
        self._snapshot = quarantine_dir / "quarantine.yaml"
        self._event_log = EventLog(quarantine_dir / "quarantine.jsonl")

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._snapshot.exists():
            return {}
        with open(self._snapshot, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return (data or {}).get("entries", {})

    def _save(self, entries: dict[str, dict[str, Any]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._snapshot, "w", encoding="utf-8") as f:
            yaml.dump({"entries": entries}, f, default_flow_style=False)

    @staticmethod
    def _utcnow() -> str:
        return utcnow_iso()

    def quarantine(
        self, incident_id: str, file_path: str, reason: str, actor: str = "security"
    ) -> dict[str, Any]:
        source = Path(file_path)
        if not source.exists():
            raise QuarantineError(f"File not found: {file_path}")

        file_hash = sha256_file(source)
        qid = f"Q-{uuid.uuid4().hex[:8]}"

        self._store.mkdir(parents=True, exist_ok=True)
        dest = self._store / qid
        shutil.copy2(source, dest)

        entries = self._load()
        entry = {
            "quarantine_id": qid,
            "incident_id": incident_id,
            "original_path": file_path,
            "file_hash": file_hash,
            "reason": reason,
            "status": "QUARANTINED",
            "quarantined_utc": self._utcnow(),
            "released_utc": None,
            "actor": actor,
        }
        entries[qid] = entry
        self._save(entries)
        self._event_log.append(
            "quarantine.added",
            {"quarantine_id": qid, "incident_id": incident_id, "file_hash": file_hash},
            actor,
        )
        return entry

    def release(self, quarantine_id: str, actor: str = "admin") -> dict[str, Any]:
        entries = self._load()
        if quarantine_id not in entries:
            raise QuarantineError(f"Not found: {quarantine_id}")
        entries[quarantine_id]["status"] = "RELEASED"
        entries[quarantine_id]["released_utc"] = self._utcnow()
        self._save(entries)
        self._event_log.append("quarantine.released", {"quarantine_id": quarantine_id}, actor)
        return entries[quarantine_id]

    def list_quarantined(self) -> list[dict[str, Any]]:
        return [e for e in self._load().values() if e["status"] == "QUARANTINED"]

    def verify(self, quarantine_id: str) -> bool:
        entries = self._load()
        if quarantine_id not in entries:
            raise QuarantineError(f"Not found: {quarantine_id}")
        stored = self._store / quarantine_id
        if not stored.exists():
            return False
        actual = sha256_file(stored)
        return actual == entries[quarantine_id]["file_hash"]
