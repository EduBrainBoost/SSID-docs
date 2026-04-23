"""Override management — time-limited guard exceptions.

Each override has: override_id, guard_id, reason, approved_by,
valid_from (UTC), valid_until (UTC), status (active|revoked|expired).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml


class OverrideManager:
    def __init__(self, override_dir: Path) -> None:
        self._dir = override_dir
        self._path = override_dir / "overrides.yaml"

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        with open(self._path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return (data or {}).get("overrides", {})

    def _save(self, overrides: dict[str, dict[str, Any]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump({"overrides": overrides}, f, default_flow_style=False)

    def create(
        self,
        guard_id: str,
        reason: str,
        approved_by: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        oid = f"OV-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)
        entry = {
            "override_id": oid,
            "guard_id": guard_id,
            "reason": reason,
            "approved_by": approved_by,
            "valid_from": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "valid_until": (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "active",
        }
        overrides = self._load()
        overrides[oid] = entry
        self._save(overrides)
        return entry

    def active_overrides(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        result = []
        for ov in self._load().values():
            if ov["status"] != "active":
                continue
            until = datetime.strptime(ov["valid_until"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            if now < until:
                result.append(ov)
        return result

    def is_overridden(self, guard_id: str) -> bool:
        return any(ov["guard_id"] == guard_id for ov in self.active_overrides())

    def revoke(self, override_id: str) -> None:
        overrides = self._load()
        if override_id in overrides:
            overrides[override_id]["status"] = "revoked"
            self._save(overrides)

    def list_all(self) -> list[dict[str, Any]]:
        return list(self._load().values())
