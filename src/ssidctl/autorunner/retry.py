"""AutoRunner V2B — FailureClassifier, RetryPolicy, RetryEngine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from ssidctl.autorunner.lock import ConcurrencyConflictError
from ssidctl.autorunner.models import (
    AutoRunnerRun,
    FailureClass,
    RetryState,
    RunScope,
)

if TYPE_CHECKING:
    from ssidctl.autorunner.store import RunStore

_RETRYABLE: frozenset[FailureClass] = frozenset(
    {
        FailureClass.TECHNICAL,
        FailureClass.DEPENDENCY_UNAVAILABLE,
        FailureClass.TIMEOUT,
    }
)

_NON_RETRYABLE: frozenset[FailureClass] = frozenset(
    {
        FailureClass.POLICY_DENY,
        FailureClass.OPERATOR_CANCELLED,
        FailureClass.EVIDENCE_INCOMPLETE,
        FailureClass.CONCURRENCY_CONFLICT,
    }
)


class RetryPolicy(BaseModel):
    max_retries: int = 3
    retryable_classes: list[str] = sorted(_RETRYABLE)  # sorted for deterministic serialization


class FailureClassifier:
    def classify(self, exc: Exception) -> FailureClass:
        if isinstance(exc, ConcurrencyConflictError):
            return FailureClass.CONCURRENCY_CONFLICT
        if isinstance(exc, TimeoutError):
            return FailureClass.TIMEOUT
        msg = str(exc).lower()
        if "policy" in msg or "deny" in msg or "forbidden" in msg:
            return FailureClass.POLICY_DENY
        if "validation" in msg and "failed" in msg:
            return FailureClass.VALIDATION_FAILED
        if "evidence" in msg or "manifest" in msg:
            return FailureClass.EVIDENCE_INCOMPLETE
        if "dependency" in msg or "unavailable" in msg or "connection" in msg:
            return FailureClass.DEPENDENCY_UNAVAILABLE
        if "timeout" in msg or "timed out" in msg:
            return FailureClass.TIMEOUT
        return FailureClass.TECHNICAL


class RetryEngine:
    def can_retry(self, run: AutoRunnerRun) -> bool:
        if run.failure_class is None:
            return False
        if run.failure_class not in _RETRYABLE:
            return False
        if run.retry_state is None:
            return True
        return run.retry_state.attempt < run.retry_state.max_attempts

    def create_retry_run(self, run: AutoRunnerRun, store: RunStore) -> AutoRunnerRun:
        if not self.can_retry(run):
            raise ValueError(
                f"Run {run.run_id} with failure_class={run.failure_class} cannot be retried"
            )
        attempt = (run.retry_state.attempt + 1) if run.retry_state else 2
        max_attempts = run.retry_state.max_attempts if run.retry_state else 3
        child = AutoRunnerRun.create(
            task_id=run.task_id,
            scope=RunScope(
                repo=run.scope.repo,
                branch=run.scope.branch,
                paths=run.scope.paths,
            ),
        )
        child.parent_run_id = run.run_id
        child.retry_state = RetryState(
            attempt=attempt,
            max_attempts=max_attempts,
            last_failure_class=run.failure_class.value if run.failure_class else None,
        )
        store.save(child)
        return child
