"""AutoRunner V2 — YAML-backed run persistence."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from ssidctl.autorunner.models import AutoRunnerRun


class RunStore:
    def __init__(self, base_dir: str | None = None) -> None:
        _default = os.environ.get("SSID_EMS_STATE", "/tmp/ssid_state")  # noqa: S108
        self.base_dir = Path(base_dir or _default + "/autorunner/runs")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.base_dir / f"{run_id}.yaml"

    def save(self, run: AutoRunnerRun) -> None:
        self._path(run.run_id).write_text(
            yaml.safe_dump(run.model_dump(mode="json"), sort_keys=True), encoding="utf-8"
        )

    def load(self, run_id: str) -> AutoRunnerRun:
        path = self._path(run_id)
        if not path.exists():
            raise KeyError(f"Run not found: {run_id}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return AutoRunnerRun.model_validate(data)

    def list_runs(self, limit: int = 100, offset: int = 0) -> list[AutoRunnerRun]:
        files = sorted(
            self.base_dir.glob("RUN-*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        return [
            AutoRunnerRun.model_validate(yaml.safe_load(f.read_text(encoding="utf-8")))
            for f in files[offset : offset + limit]
        ]
