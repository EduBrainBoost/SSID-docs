"""Rollback Handler — fail-closed rollback with preconditions and evidence.

Manages rollback of releases with mandatory precondition checks.
No rollback without gate approval — all preconditions must PASS.

Principle: fail-closed — missing data or failed checks block rollback.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ssidctl.core.release_state_machine import (
    ReleaseRecord,
    ReleaseState,
    TransitionResult,
    apply_transition,
)

# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------


class RollbackPrecondition(StrEnum):
    """All preconditions that must pass before rollback."""

    RELEASE_EXISTS = "RELEASE_EXISTS"
    STATE_ALLOWS_ROLLBACK = "STATE_ALLOWS_ROLLBACK"
    NO_ACTIVE_CONSUMERS = "NO_ACTIVE_CONSUMERS"
    OPERATOR_AUTHORIZED = "OPERATOR_AUTHORIZED"
    EVIDENCE_CHAIN_VALID = "EVIDENCE_CHAIN_VALID"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreconditionResult:
    """Outcome of a single precondition check."""

    precondition: RollbackPrecondition
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class RollbackEvidence:
    """Evidence record for a rollback operation."""

    release_id: str
    from_version: str
    from_state: str
    reason: str
    operator: str
    precondition_results: list[dict[str, Any]] = field(default_factory=list)
    evidence_hash: str = ""
    timestamp_utc: str = ""


@dataclass(frozen=True)
class RollbackPlan:
    """Plan for executing a rollback."""

    release_id: str
    from_state: str
    to_state: str = str(ReleaseState.ROLLED_BACK)
    preconditions_met: bool = False
    failed_preconditions: list[str] = field(default_factory=list)
    evidence: RollbackEvidence | None = None
    blocked: bool = True
    block_reason: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_evidence(data: dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Rollback Handler
# ---------------------------------------------------------------------------


class RollbackHandler:
    """Manages rollback operations with fail-closed precondition checks."""

    def check_preconditions(
        self,
        record: ReleaseRecord | None,
        *,
        operator: str = "",
        active_consumers: list[str] | None = None,
        evidence_chain_valid: bool | None = None,
    ) -> list[PreconditionResult]:
        """Check all rollback preconditions.  Fail-closed on missing data.

        Args:
            record: The release record to roll back.
            operator: Operator performing the rollback.
            active_consumers: List of active consumers (must be empty).
            evidence_chain_valid: Whether the evidence chain is valid.

        Returns:
            List of PreconditionResult for each check.
        """
        results: list[PreconditionResult] = []

        # 1. Release exists
        if record is None:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.RELEASE_EXISTS,
                    passed=False,
                    detail="Release record is None — fail-closed",
                )
            )
            # Short-circuit: remaining checks cannot run
            for pc in [
                RollbackPrecondition.STATE_ALLOWS_ROLLBACK,
                RollbackPrecondition.NO_ACTIVE_CONSUMERS,
                RollbackPrecondition.OPERATOR_AUTHORIZED,
                RollbackPrecondition.EVIDENCE_CHAIN_VALID,
            ]:
                results.append(
                    PreconditionResult(
                        pc,
                        passed=False,
                        detail="Skipped — release not found",
                    )
                )
            return results

        results.append(
            PreconditionResult(
                RollbackPrecondition.RELEASE_EXISTS,
                passed=True,
                detail=f"Release {record.release_id} exists",
            )
        )

        # 2. State allows rollback (PROMOTED or PUBLISHED)
        rollback_states = {ReleaseState.PROMOTED, ReleaseState.PUBLISHED}
        if record.state in rollback_states:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.STATE_ALLOWS_ROLLBACK,
                    passed=True,
                    detail=f"State {record.state} allows rollback",
                )
            )
        else:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.STATE_ALLOWS_ROLLBACK,
                    passed=False,
                    detail=(
                        f"State {record.state} does not allow rollback"
                        " (must be PROMOTED or PUBLISHED)"
                    ),
                )
            )

        # 3. No active consumers
        if active_consumers is None:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.NO_ACTIVE_CONSUMERS,
                    passed=False,
                    detail="Active consumers data missing — fail-closed",
                )
            )
        elif len(active_consumers) > 0:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.NO_ACTIVE_CONSUMERS,
                    passed=False,
                    detail=f"Active consumers present: {', '.join(active_consumers)}",
                )
            )
        else:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.NO_ACTIVE_CONSUMERS,
                    passed=True,
                    detail="No active consumers",
                )
            )

        # 4. Operator authorized
        if not operator:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.OPERATOR_AUTHORIZED,
                    passed=False,
                    detail="Operator not specified — fail-closed",
                )
            )
        else:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.OPERATOR_AUTHORIZED,
                    passed=True,
                    detail=f"Operator: {operator}",
                )
            )

        # 5. Evidence chain valid
        if evidence_chain_valid is None:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.EVIDENCE_CHAIN_VALID,
                    passed=False,
                    detail="Evidence chain validity unknown — fail-closed",
                )
            )
        elif not evidence_chain_valid:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.EVIDENCE_CHAIN_VALID,
                    passed=False,
                    detail="Evidence chain invalid",
                )
            )
        else:
            results.append(
                PreconditionResult(
                    RollbackPrecondition.EVIDENCE_CHAIN_VALID,
                    passed=True,
                    detail="Evidence chain valid",
                )
            )

        return results

    def prepare_rollback(
        self,
        record: ReleaseRecord | None,
        *,
        reason: str = "",
        operator: str = "",
        active_consumers: list[str] | None = None,
        evidence_chain_valid: bool | None = None,
    ) -> RollbackPlan:
        """Prepare a rollback plan.  Fail-closed if any precondition fails.

        Returns a RollbackPlan — check .blocked before proceeding.
        """
        preconditions = self.check_preconditions(
            record,
            operator=operator,
            active_consumers=active_consumers,
            evidence_chain_valid=evidence_chain_valid,
        )

        failed = [r for r in preconditions if not r.passed]
        all_passed = len(failed) == 0

        if record is None:
            return RollbackPlan(
                release_id="<unknown>",
                from_state="<unknown>",
                blocked=True,
                block_reason="Release record not found",
                failed_preconditions=[r.detail for r in failed],
            )

        ts = _now_utc()
        evidence = RollbackEvidence(
            release_id=record.release_id,
            from_version=str(record.version),
            from_state=str(record.state),
            reason=reason,
            operator=operator,
            precondition_results=[
                {"precondition": str(r.precondition), "passed": r.passed, "detail": r.detail}
                for r in preconditions
            ],
            timestamp_utc=ts,
        )
        # Compute evidence hash
        evidence = RollbackEvidence(
            release_id=evidence.release_id,
            from_version=evidence.from_version,
            from_state=evidence.from_state,
            reason=evidence.reason,
            operator=evidence.operator,
            precondition_results=evidence.precondition_results,
            evidence_hash=_hash_evidence(
                {
                    "release_id": evidence.release_id,
                    "from_version": evidence.from_version,
                    "from_state": evidence.from_state,
                    "reason": evidence.reason,
                    "operator": evidence.operator,
                    "preconditions": evidence.precondition_results,
                    "timestamp_utc": ts,
                }
            ),
            timestamp_utc=ts,
        )

        if not all_passed:
            return RollbackPlan(
                release_id=record.release_id,
                from_state=str(record.state),
                preconditions_met=False,
                failed_preconditions=[r.detail for r in failed],
                evidence=evidence,
                blocked=True,
                block_reason=f"{len(failed)} precondition(s) failed",
            )

        return RollbackPlan(
            release_id=record.release_id,
            from_state=str(record.state),
            preconditions_met=True,
            evidence=evidence,
            blocked=False,
        )

    def execute_rollback(
        self,
        record: ReleaseRecord,
        plan: RollbackPlan,
    ) -> TransitionResult:
        """Execute a rollback via the state machine.

        Requires plan.blocked == False.  Fail-closed otherwise.
        """
        if plan.blocked:
            return TransitionResult(
                allowed=False,
                from_state=record.state,
                to_state=ReleaseState.ROLLED_BACK,
                reason=f"Rollback blocked: {plan.block_reason}",
                timestamp_utc=_now_utc(),
            )

        return apply_transition(
            record,
            ReleaseState.ROLLED_BACK,
            reason=f"Rollback: {plan.evidence.reason if plan.evidence else 'no reason'}",
            operator=plan.evidence.operator if plan.evidence else "",
        )
