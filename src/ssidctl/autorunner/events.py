"""AutoRunner V2 — append-only JSONL event stream per run."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


class RunEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    type: str
    payload: dict


class RunEventStream:
    def __init__(self, run_id: str, base_dir: str | None = None) -> None:
        self.run_id = run_id
        _default = os.environ.get("SSID_EMS_STATE", "/tmp/ssid_state")  # noqa: S108
        base = Path(base_dir or _default + "/autorunner/events")
        base.mkdir(parents=True, exist_ok=True)
        self._path = base / f"{run_id}.jsonl"

    def append(self, event: RunEvent) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump()) + "\n")

    def read_all(self) -> list[RunEvent]:
        if not self._path.exists():
            return []
        return [
            RunEvent.model_validate(json.loads(line))
            for line in self._path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
