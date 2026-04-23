"""TaskSpec CRUD + validation engine.

TaskSpec has NO raw prompt field — only prompt_vars + prompt_sha256.
State stored at SSID_EMS_STATE/tasks/{task_id}.yaml.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "templates"
    / "taskspec"
    / "taskspec.schema.json"
)


class TaskSpecError(Exception):
    pass


def _load_schema() -> dict[str, Any]:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_taskspec(spec: dict[str, Any]) -> None:
    """Validate a TaskSpec dict against the schema.

    Raises TaskSpecError on validation failure.
    """
    schema = _load_schema()
    try:
        jsonschema.validate(instance=spec, schema=schema)
    except jsonschema.ValidationError as exc:
        raise TaskSpecError(f"TaskSpec validation failed: {exc.message}") from exc

    # Extra invariant: no 'prompt' string field
    if "prompt" in spec:
        raise TaskSpecError(
            "TaskSpec must not contain a 'prompt' string field. Use prompt_vars + prompt_source."
        )


class TaskSpecEngine:
    """CRUD operations for TaskSpecs stored in SSID_EMS_STATE/tasks/."""

    def __init__(self, tasks_dir: Path) -> None:
        self._dir = tasks_dir

    def _task_path(self, task_id: str) -> Path:
        return self._dir / f"{task_id}.yaml"

    def create(self, spec: dict[str, Any]) -> dict[str, Any]:
        validate_taskspec(spec)
        task_id = spec["task_id"]
        path = self._task_path(task_id)
        if path.exists():
            raise TaskSpecError(f"TaskSpec already exists: {task_id}")

        self._dir.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(spec, f, default_flow_style=False)
        return spec

    def get(self, task_id: str) -> dict[str, Any]:
        path = self._task_path(task_id)
        if not path.exists():
            raise TaskSpecError(f"TaskSpec not found: {task_id}")
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def list_tasks(self) -> list[str]:
        if not self._dir.exists():
            return []
        return [p.stem for p in sorted(self._dir.glob("*.yaml"))]

    def update(self, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        spec = self.get(task_id)
        spec.update(updates)
        validate_taskspec(spec)
        with open(self._task_path(task_id), "w", encoding="utf-8") as f:
            yaml.dump(spec, f, default_flow_style=False)
        return spec

    def delete(self, task_id: str) -> None:
        path = self._task_path(task_id)
        if not path.exists():
            raise TaskSpecError(f"TaskSpec not found: {task_id}")
        path.unlink()
