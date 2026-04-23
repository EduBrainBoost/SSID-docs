"""AutoRunner V2B — Idempotency: RunKey computation + DeduplicationStore."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml

from ssidctl.autorunner.models import RunScope


class RunKey:
    @staticmethod
    def compute(task_id: str, scope: RunScope) -> str:
        key_str = f"{task_id}:{scope.repo}:{scope.branch}:{':'.join(sorted(scope.paths))}"
        digest = hashlib.sha256(key_str.encode()).hexdigest()[:16].upper()
        return f"KEY-{digest}"


class DeduplicationStore:
    """Maps run_key → run_id for non-terminal (active) runs."""

    def __init__(self, base_dir: str | None = None) -> None:
        _default = os.environ.get("SSID_EMS_STATE", "/tmp/ssid_state")  # noqa: S108
        self._path = Path(base_dir or _default + "/autorunner") / "dedup.yaml"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def _save(self, data: dict[str, str]) -> None:
        self._path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")

    def check_active(self, run_key: str) -> str | None:
        return self._load().get(run_key)

    def register(self, run_key: str, run_id: str) -> None:
        data = self._load()
        data[run_key] = run_id
        self._save(data)

    def unregister(self, run_key: str) -> None:
        data = self._load()
        data.pop(run_key, None)
        self._save(data)
