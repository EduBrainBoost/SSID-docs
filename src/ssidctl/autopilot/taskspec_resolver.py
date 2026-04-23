"""TaskSpec Resolver — locates, loads, validates TaskSpec YAML for autopilot runs.

Lookup order:
1. {ems_repo}/templates/taskspec/{task_id}.yaml
2. {state_dir}/tasks/{task_id}.yaml

Stop codes on failure: STOP_TASKSPEC_MISSING, STOP_TASKSPEC_INVALID.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.taskspec_engine import TaskSpecError, validate_taskspec


class TaskSpecResolveError(Exception):
    """Raised when a TaskSpec cannot be resolved."""

    def __init__(self, message: str, stop_code: str) -> None:
        super().__init__(message)
        self.stop_code = stop_code


@dataclass(frozen=True)
class ResolvedTaskSpec:
    """Immutable resolved TaskSpec ready for autopilot consumption."""

    task_id: str
    scope: str
    allowed_paths: list[str]
    acceptance_checks: list[str]
    max_changed_files: int = 12
    max_changed_lines: int = 600
    target_repo_path: str = ""
    gate_source: str = "matrix"
    operations: list[str] = field(default_factory=lambda: ["run_gates"])
    raw: dict[str, Any] = field(default_factory=dict)


class TaskSpecResolver:
    """Resolves task_id to a validated ResolvedTaskSpec."""

    def __init__(self, ems_repo: Path, state_dir: Path) -> None:
        self._templates_dir = ems_repo / "templates" / "taskspec"
        self._tasks_dir = state_dir / "tasks"

    def resolve(self, task_id: str) -> ResolvedTaskSpec:
        """Resolve a task_id to a ResolvedTaskSpec.

        Lookup order:
        1. {ems_repo}/templates/taskspec/{task_id}.yaml
        2. {state_dir}/tasks/{task_id}.yaml

        Raises:
            TaskSpecResolveError: With STOP_TASKSPEC_MISSING or STOP_TASKSPEC_INVALID.
        """
        spec = self._load(task_id)
        self._validate(spec, task_id)
        return self._build(spec)

    def _load(self, task_id: str) -> dict[str, Any]:
        """Load raw YAML from templates or state fallback."""
        template_path = self._templates_dir / f"{task_id}.yaml"
        if template_path.exists():
            return self._read_yaml(template_path, task_id)

        state_path = self._tasks_dir / f"{task_id}.yaml"
        if state_path.exists():
            return self._read_yaml(state_path, task_id)

        raise TaskSpecResolveError(
            f"TaskSpec not found: {task_id} (checked {template_path} and {state_path})",
            stop_code="STOP_TASKSPEC_MISSING",
        )

    def _read_yaml(self, path: Path, task_id: str) -> dict[str, Any]:
        """Read and parse YAML, raising on parse errors."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise TaskSpecResolveError(
                    f"TaskSpec at {path} is not a YAML mapping",
                    stop_code="STOP_TASKSPEC_INVALID",
                )
            return data
        except yaml.YAMLError as e:
            raise TaskSpecResolveError(
                f"TaskSpec YAML parse error at {path}: {e}",
                stop_code="STOP_TASKSPEC_INVALID",
            ) from e

    def _validate(self, spec: dict[str, Any], task_id: str) -> None:
        """Validate against JSON schema and cross-check task_id."""
        # Cross-check: task_id in file must match requested task_id
        file_task_id = spec.get("task_id", "")
        if file_task_id != task_id:
            raise TaskSpecResolveError(
                f"TaskSpec task_id mismatch: file has '{file_task_id}', requested '{task_id}'",
                stop_code="STOP_TASKSPEC_INVALID",
            )

        # Schema validation
        try:
            validate_taskspec(spec)
        except TaskSpecError as e:
            raise TaskSpecResolveError(
                f"TaskSpec schema validation failed: {e}",
                stop_code="STOP_TASKSPEC_INVALID",
            ) from e

    def _build(self, spec: dict[str, Any]) -> ResolvedTaskSpec:
        """Build ResolvedTaskSpec from validated raw dict."""
        target = spec.get("target", {}) or {}
        gate = spec.get("gate", {}) or {}

        return ResolvedTaskSpec(
            task_id=spec["task_id"],
            scope=spec.get("scope", ""),
            allowed_paths=spec.get("allowed_paths", []),
            acceptance_checks=spec.get("acceptance_checks", ["policy", "sot", "qa"]),
            max_changed_files=spec.get("max_changed_files", 12),
            max_changed_lines=spec.get("max_changed_lines", 600),
            target_repo_path=target.get("repo_path", ""),
            gate_source=gate.get("source", "matrix"),
            operations=spec.get("operations", ["run_gates"]),
            raw=spec,
        )
