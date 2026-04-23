"""AutoRunner V2 — Planner: creates run plan artifact from task + scope."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel

from ssidctl.autorunner.models import AutoRunnerRun, RunStatus


class PlanArtifact(BaseModel):
    run_id: str
    task_id: str
    scope: dict
    steps: list[str]
    created_at: str
    artifact_path: str


class Planner:
    def __init__(self, artifact_dir: str | None = None) -> None:
        _default = os.environ.get("SSID_EMS_STATE", "/tmp/ssid_state")  # noqa: S108
        base = Path(artifact_dir or _default + "/autorunner/plans")
        base.mkdir(parents=True, exist_ok=True)
        self._dir = base

    def plan(self, run: AutoRunnerRun) -> PlanArtifact:
        if not run.scope.paths:
            raise ValueError("scope.paths must not be empty — cannot plan without scope")
        steps = [
            "collect: run gate matrix on scope",
            "normalize: deduplicate + classify findings",
            "route: map findings to agents via routing_matrix",
            "execute: apply patches under write-lock + budget",
            "double_verify: reproduce changes in clean worktree",
            "finalize: write evidence manifest + final report",
        ]
        artifact_path = str(self._dir / f"{run.run_id}_plan.yaml")
        artifact = PlanArtifact(
            run_id=run.run_id,
            task_id=run.task_id,
            scope=run.scope.model_dump(mode="json"),
            steps=steps,
            created_at=datetime.now(UTC).isoformat(),
            artifact_path=artifact_path,
        )
        Path(artifact_path).write_text(
            yaml.safe_dump(artifact.model_dump(), sort_keys=True), encoding="utf-8"
        )
        run.plan_artifact = artifact_path
        run.transition(RunStatus.PLANNED)
        return artifact
