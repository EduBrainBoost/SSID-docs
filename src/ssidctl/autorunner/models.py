"""AutoRunner V2 — Run model and state machine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel


class RunStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


# --- Plan B enums and sub-models ---


class FailureClass(StrEnum):
    TECHNICAL = "technical"
    POLICY_DENY = "policy_deny"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    OPERATOR_CANCELLED = "operator_cancelled"
    VALIDATION_FAILED = "validation_failed"
    CONCURRENCY_CONFLICT = "concurrency_conflict"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    QUOTA_EXCEEDED = "quota_exceeded"


class Provenance(BaseModel):
    repo: str
    branch: str
    commit_sha: str
    ref_type: str = "branch"
    resolved_at: str


class RetryState(BaseModel):
    attempt: int = 1
    max_attempts: int = 3
    last_failure_class: str | None = None


class EvidenceSeal(BaseModel):
    run_id: str
    provenance: Provenance
    manifest_hash: str  # "sha256:<hex>" or "sha256:none"
    sealed_at: str
    seal_path: str


# --- FSM ---

_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.DRAFT: {RunStatus.PLANNED, RunStatus.CANCELLED},
    RunStatus.PLANNED: {RunStatus.QUEUED, RunStatus.CANCELLED},
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.SUCCEEDED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
}

_TERMINAL = {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}


class RunScope(BaseModel):
    repo: str
    branch: str
    paths: list[str]
    worktree_lock: str | None = None  # populated on RUNNING


class ProviderAttempt(BaseModel):
    provider_id: str
    started_at: str
    finished_at: str | None = None
    success: bool = False
    error_class: str | None = None
    error_message: str | None = None


class AutoRunnerRun(BaseModel):
    run_id: str
    task_id: str
    autorunner_id: str | None = None
    scope: RunScope
    status: RunStatus = RunStatus.DRAFT
    plan_artifact: str | None = None
    evidence_manifest: str | None = None
    final_report: str | None = None
    created_at: str
    updated_at: str
    error: str | None = None
    failure_class: FailureClass | None = None
    lock_key: str | None = None
    run_key: str | None = None
    parent_run_id: str | None = None
    retry_state: RetryState | None = None
    provenance: Provenance | None = None
    evidence_seal: EvidenceSeal | None = None
    worker_type: str | None = None
    resolved_worker: str | None = None
    selected_provider: str | None = None
    provider_attempts: list[ProviderAttempt] = []
    final_provider: str | None = None

    @classmethod
    def create(cls, task_id: str, scope: RunScope | None) -> AutoRunnerRun:
        if scope is None:
            raise ValueError("scope is required — no Run without scope")
        now = datetime.now(UTC).isoformat()
        return cls(
            run_id=f"RUN-{uuid.uuid4().hex[:12].upper()}",
            task_id=task_id,
            scope=scope,
            created_at=now,
            updated_at=now,
        )

    def transition(self, target: RunStatus) -> None:
        allowed = _TRANSITIONS[self.status]
        if target not in allowed:
            raise ValueError(
                f"Invalid transition: {self.status} → {target}. "
                f"Allowed: {sorted(s.value for s in allowed) or 'none (terminal)'}"
            )
        # Guard: QUEUED requires plan_artifact
        if target == RunStatus.QUEUED and not self.plan_artifact:
            raise ValueError("plan_artifact must be set before transitioning to QUEUED")
        self.status = target
        self.updated_at = datetime.now(UTC).isoformat()

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL
