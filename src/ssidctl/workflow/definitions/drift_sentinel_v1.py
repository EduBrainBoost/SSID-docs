"""Drift Sentinel v1 — 9-step durable workflow definition.

Workflow name : drift_sentinel_v1
Version       : 1.0.0

Step sequence
-------------
0  collect_state_snapshot  — snapshot open_core path existence + timestamp
1  compute_drift           — run full drift sentinel (integrity/leakage/docs-source)
2  classify_drift          — classify verdict into clean / drift_detected
3  emit_evidence           — hash-only evidence payload (no raw PII)
4  propose_remediation     — build allowlisted remediation proposals
5  await_operator_decision — BLOCKS until operator approves (requires_approval=True)
6  execute_remediation     — fail-closed execution of allowlisted actions (proposal-only)
7  post_verify             — re-run drift check to confirm state post-remediation
8  close_run               — seal the run record with final verdict

SAFE-FIX / ROOT-24-LOCK constraints
-------------------------------------
- No side effects in execute_remediation for this version (proposals only).
- All hashes use canonical ``sha256:<hex>`` prefix (ssidctl.core.hashing).
- Timestamps are UTC ISO 8601 from ssidctl.core.timeutil.
- Evidence payloads are hash-only; no raw findings text, no PII.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso
from ssidctl.modules.drift_sentinel import run_sentinel
from ssidctl.workflow.registry import (
    StepDefinition,
    WorkflowDefinition,
    register_workflow,
)

# ---------------------------------------------------------------------------
# Fail-closed action allowlist for execute_remediation
# ---------------------------------------------------------------------------

_REMEDIATION_ACTION_ALLOWLIST: frozenset[str] = frozenset(
    {
        "regenerate_manifest",
        "redact_and_report",
        "update_docs_refs",
    }
)

# Mapping: finding type -> proposal entry
_FINDING_TYPE_TO_PROPOSAL: dict[str, dict[str, str]] = {
    "integrity": {
        "type": "integrity_repair",
        "action": "regenerate_manifest",
    },
    "leakage": {
        "type": "leakage_fix",
        "action": "redact_and_report",
    },
    "docs-source": {
        "type": "docs_source_fix",
        "action": "update_docs_refs",
    },
}


# ---------------------------------------------------------------------------
# Step 0 — collect_state_snapshot
# ---------------------------------------------------------------------------


def step_collect_state_snapshot(ctx: dict[str, Any]) -> dict[str, Any]:
    """Collect a snapshot of open_core/docs path state.

    Input keys
    ----------
    open_core_path : str
    docs_path      : str  (optional)

    Output keys
    -----------
    snapshot_hash    : str  — sha256:<hex> of the snapshot JSON
    open_core_exists : bool
    docs_exists      : bool
    timestamp        : str
    open_core_path   : str  — echoed back
    docs_path        : str  — echoed back
    """
    open_core_path: str = ctx.get("open_core_path", "")
    docs_path: str = ctx.get("docs_path", "")

    open_core_exists = Path(open_core_path).exists() if open_core_path else False
    docs_exists = Path(docs_path).exists() if docs_path else False
    timestamp = utcnow_iso()

    snapshot: dict[str, Any] = {
        "open_core_path": open_core_path,
        "docs_path": docs_path,
        "open_core_exists": open_core_exists,
        "docs_exists": docs_exists,
        "timestamp": timestamp,
    }
    snapshot_hash = sha256_str(json.dumps(snapshot, sort_keys=True, separators=(",", ":")))

    return {
        "snapshot_hash": snapshot_hash,
        "open_core_exists": open_core_exists,
        "docs_exists": docs_exists,
        "timestamp": timestamp,
        "open_core_path": open_core_path,
        "docs_path": docs_path,
    }


# ---------------------------------------------------------------------------
# Step 1 — compute_drift
# ---------------------------------------------------------------------------


def step_compute_drift(ctx: dict[str, Any]) -> dict[str, Any]:
    """Run the full drift sentinel and return the report dict.

    Input keys
    ----------
    open_core_path : str
    docs_path      : str  (optional)

    Output keys
    -----------
    verdict       : str  — "PASS" | "FAIL" | "ERROR"
    checks_run    : int
    checks_passed : int
    findings      : list[dict]
    findings_count: int
    timestamp     : str
    error         : str  (only when verdict == "ERROR")
    """
    open_core_path: str = ctx.get("open_core_path", "")
    docs_path: str = ctx.get("docs_path", "")

    open_core = Path(open_core_path) if open_core_path else None

    if open_core is None or not open_core.exists():
        return {
            "verdict": "ERROR",
            "checks_run": 0,
            "checks_passed": 0,
            "findings": [],
            "findings_count": 0,
            "timestamp": utcnow_iso(),
            "error": f"open_core_path does not exist or was not provided: '{open_core_path}'",
        }

    docs = Path(docs_path) if docs_path else None

    report = run_sentinel(open_core, docs=docs)
    result = report.to_dict()
    # Ensure findings_count is present (to_dict includes it already, but be explicit)
    result.setdefault("findings_count", len(report.findings))
    return result


# ---------------------------------------------------------------------------
# Step 2 — classify_drift
# ---------------------------------------------------------------------------


def step_classify_drift(ctx: dict[str, Any]) -> dict[str, Any]:
    """Classify the drift verdict into a human-readable category.

    Input keys
    ----------
    verdict  : str  — "PASS" | "FAIL" | "ERROR"
    findings : list[dict]

    Output keys
    -----------
    classification     : str   — "clean" | "drift_detected" | "error"
    remediation_needed : bool
    findings_count     : int
    finding_types      : list[str]  (only present when drift_detected)
    """
    verdict: str = ctx.get("verdict", "")
    findings: list[dict[str, Any]] = ctx.get("findings", [])

    if verdict == "PASS":
        return {
            "classification": "clean",
            "remediation_needed": False,
            "findings_count": 0,
            "finding_types": [],
        }

    # FAIL or ERROR
    finding_types: list[str] = sorted({f.get("check", "") for f in findings if f.get("check")})
    return {
        "classification": "drift_detected" if verdict == "FAIL" else "error",
        "remediation_needed": verdict == "FAIL",
        "findings_count": len(findings),
        "finding_types": finding_types,
    }


# ---------------------------------------------------------------------------
# Step 3 — emit_evidence
# ---------------------------------------------------------------------------


def step_emit_evidence(ctx: dict[str, Any]) -> dict[str, Any]:
    """Produce a hash-only evidence payload.

    Input keys
    ----------
    classification     : str
    remediation_needed : bool
    findings_count     : int

    Output keys
    -----------
    evidence_hash    : str  — sha256:<hex>
    evidence_payload : dict — hash-only, no raw PII
    """
    classification: str = ctx.get("classification", "")
    remediation_needed: bool = bool(ctx.get("remediation_needed", False))
    findings_count: int = int(ctx.get("findings_count", 0))
    timestamp = utcnow_iso()

    evidence_payload: dict[str, Any] = {
        "timestamp": timestamp,
        "classification": classification,
        "remediation_needed": remediation_needed,
        "findings_count": findings_count,
    }

    evidence_hash = sha256_str(json.dumps(evidence_payload, sort_keys=True, separators=(",", ":")))
    evidence_payload_with_hash = dict(evidence_payload)
    evidence_payload_with_hash["self_hash"] = evidence_hash

    return {
        "evidence_hash": evidence_hash,
        "evidence_payload": evidence_payload_with_hash,
    }


# ---------------------------------------------------------------------------
# Step 4 — propose_remediation
# ---------------------------------------------------------------------------


def step_propose_remediation(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build an allowlisted remediation proposal list.

    Input keys
    ----------
    remediation_needed : bool
    finding_types      : list[str]

    Output keys
    -----------
    proposal      : list[dict] | None
    action        : str  — "none" | "requires_approval"
    proposal_hash : str  (only when proposal is not None)
    """
    remediation_needed: bool = bool(ctx.get("remediation_needed", False))
    finding_types: list[str] = ctx.get("finding_types", []) or []

    if not remediation_needed:
        return {
            "proposal": None,
            "action": "none",
        }

    proposal: list[dict[str, str]] = []
    for ftype in finding_types:
        entry = _FINDING_TYPE_TO_PROPOSAL.get(ftype)
        if entry:
            proposal.append(dict(entry))

    proposal_hash = sha256_str(json.dumps(proposal, sort_keys=True, separators=(",", ":")))

    return {
        "proposal": proposal,
        "action": "requires_approval",
        "proposal_hash": proposal_hash,
    }


# ---------------------------------------------------------------------------
# Step 5 — await_operator_decision
# ---------------------------------------------------------------------------


def step_await_operator_decision(ctx: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    """Gate step: the engine blocks here until an operator approves.

    When the engine resumes (after external approval), this function
    runs and simply acknowledges the decision.

    Output keys
    -----------
    decision  : str  — "approved"
    timestamp : str
    """
    return {
        "decision": "approved",
        "timestamp": utcnow_iso(),
    }


# ---------------------------------------------------------------------------
# Step 6 — execute_remediation
# ---------------------------------------------------------------------------


def step_execute_remediation(ctx: dict[str, Any]) -> dict[str, Any]:
    """Execute approved remediation proposals (fail-closed, proposal-only).

    Input keys
    ----------
    proposal : list[dict] | None

    Output keys
    -----------
    executed : bool
    actions  : list[dict]  (when executed=True)
    reason   : str         (when executed=False)

    Raises
    ------
    RuntimeError
        If any proposal action is not in ``_REMEDIATION_ACTION_ALLOWLIST``
        (fail-closed guard).
    """
    proposal: list[dict[str, str]] | None = ctx.get("proposal")

    if not proposal:
        return {
            "executed": False,
            "reason": "no_proposal",
        }

    # Fail-closed: validate all actions before executing any
    for entry in proposal:
        action = entry.get("action", "")
        if action not in _REMEDIATION_ACTION_ALLOWLIST:
            raise RuntimeError(
                f"execute_remediation: action '{action}' is not in the allowlist "
                f"{sorted(_REMEDIATION_ACTION_ALLOWLIST)}. Aborting (fail-closed)."
            )

    actions_result = [
        {"action": entry.get("action", ""), "status": "proposed_only"} for entry in proposal
    ]

    return {
        "executed": True,
        "actions": actions_result,
    }


# ---------------------------------------------------------------------------
# Step 7 — post_verify
# ---------------------------------------------------------------------------


def step_post_verify(ctx: dict[str, Any]) -> dict[str, Any]:
    """Re-run drift computation to confirm state post-remediation.

    Delegates entirely to step_compute_drift (same input/output contract).
    """
    return step_compute_drift(ctx)


# ---------------------------------------------------------------------------
# Step 8 — close_run
# ---------------------------------------------------------------------------


def step_close_run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Seal the run record.

    Input keys
    ----------
    verdict : str  (from post_verify or earlier compute_drift)

    Output keys
    -----------
    closed_at     : str
    final_verdict : str
    """
    return {
        "closed_at": utcnow_iso(),
        "final_verdict": ctx.get("verdict", "UNKNOWN"),
    }


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_drift_sentinel_workflow() -> WorkflowDefinition:
    """Construct, register, and return the drift_sentinel_v1 WorkflowDefinition.

    Builds a :class:`~ssidctl.workflow.registry.WorkflowDefinition` with 9
    ordered :class:`~ssidctl.workflow.registry.StepDefinition` objects, calls
    :func:`~ssidctl.workflow.registry.register_workflow`, and returns the
    definition.

    Returns
    -------
    WorkflowDefinition
        The registered ``drift_sentinel_v1`` workflow definition.
    """
    defn = WorkflowDefinition(name="drift_sentinel_v1", version="1.0.0")

    defn.add_step(
        StepDefinition(
            step_type="collect_state_snapshot",
            function=step_collect_state_snapshot,
            retryable=True,
            max_attempts=3,
            requires_approval=False,
        )
    )
    defn.add_step(
        StepDefinition(
            step_type="compute_drift",
            function=step_compute_drift,
            retryable=True,
            max_attempts=3,
            requires_approval=False,
        )
    )
    defn.add_step(
        StepDefinition(
            step_type="classify_drift",
            function=step_classify_drift,
            retryable=True,
            max_attempts=3,
            requires_approval=False,
        )
    )
    defn.add_step(
        StepDefinition(
            step_type="emit_evidence",
            function=step_emit_evidence,
            retryable=True,
            max_attempts=3,
            requires_approval=False,
        )
    )
    defn.add_step(
        StepDefinition(
            step_type="propose_remediation",
            function=step_propose_remediation,
            retryable=True,
            max_attempts=3,
            requires_approval=False,
        )
    )
    defn.add_step(
        StepDefinition(
            step_type="await_operator_decision",
            function=step_await_operator_decision,
            retryable=False,
            max_attempts=1,
            requires_approval=True,  # REQUIRED — registry enforces this
        )
    )
    defn.add_step(
        StepDefinition(
            step_type="execute_remediation",
            function=step_execute_remediation,
            retryable=False,
            max_attempts=1,
            requires_approval=False,
        )
    )
    defn.add_step(
        StepDefinition(
            step_type="post_verify",
            function=step_post_verify,
            retryable=True,
            max_attempts=3,
            requires_approval=False,
        )
    )
    defn.add_step(
        StepDefinition(
            step_type="close_run",
            function=step_close_run,
            retryable=True,
            max_attempts=3,
            requires_approval=False,
        )
    )

    register_workflow(defn)
    return defn
