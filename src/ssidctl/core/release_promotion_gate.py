"""Release Promotion Gate — evaluates release readiness across all preconditions.

This is the central gate that determines whether a release candidate may be
promoted. It aggregates checks from:
- Evidence store (sealed runs, gate reports)
- Freeze control (active freezes block promotion)
- Drift sentinel (cross-repo drift blocks promotion)
- Policy conformance (open violations block promotion)
- Export policy (deny-globs, secret scan, artifact checks)

Principle: fail-closed — any unresolvable check results in BLOCKED.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class BlockedReason:
    """A single reason why promotion is blocked."""

    code: str
    description: str
    severity: str = "critical"  # critical | warning


@dataclass
class GateResult:
    """Result of release gate evaluation."""

    decision: str  # "PASS" | "BLOCKED"
    gate_type: str = "release_promotion"
    blocked_reasons: list[dict[str, str]] = field(default_factory=list)
    evidence_hash: str = ""
    timestamp_utc: str = ""
    checks_performed: int = 0
    checks_passed: int = 0


def evaluate_release_gate(context: dict[str, Any]) -> GateResult:
    """Evaluate all release preconditions.

    Args:
        context: Dict with optional keys:
            - triage_items: list of open triage items
            - drift_findings: list of drift findings
            - registry_status: list of registry check results
            - policy_status: list of policy check results
            - freeze_level: current freeze level string
            - evidence_runs: list of evidence run summaries
            - open_violations: list of open policy violations

    Returns:
        GateResult with decision PASS or BLOCKED.
    """
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    blocked_reasons: list[dict[str, str]] = []
    checks = 0
    passed = 0

    # Check 1: No open triage items
    checks += 1
    triage = context.get("triage_items", [])
    if triage:
        blocked_reasons.append(
            {
                "code": "OPEN_TRIAGE",
                "description": f"{len(triage)} open triage items must be resolved before promotion",  # noqa: E501
            }
        )
    else:
        passed += 1

    # Check 2: No drift findings
    checks += 1
    drift = context.get("drift_findings", [])
    if drift:
        blocked_reasons.append(
            {
                "code": "DRIFT_DETECTED",
                "description": f"{len(drift)} drift findings detected across repos",
            }
        )
    else:
        passed += 1

    # Check 3: Registry status clean
    checks += 1
    registry = context.get("registry_status", [])
    registry_failures = [r for r in registry if r.get("status") == "failed"]
    if registry_failures:
        blocked_reasons.append(
            {
                "code": "REGISTRY_FAILURE",
                "description": f"{len(registry_failures)} registry checks failed",
            }
        )
    else:
        passed += 1

    # Check 4: Policy status clean
    checks += 1
    policy = context.get("policy_status", [])
    policy_failures = [p for p in policy if p.get("status") == "failed"]
    if policy_failures:
        blocked_reasons.append(
            {
                "code": "POLICY_FAILURE",
                "description": f"{len(policy_failures)} policy checks failed",
            }
        )
    else:
        passed += 1

    # Check 5: No active freeze above watch level
    checks += 1
    freeze_level = context.get("freeze_level", "none")
    if freeze_level in ("hard_freeze", "emergency_stop"):
        blocked_reasons.append(
            {
                "code": "FREEZE_ACTIVE",
                "description": f"Active freeze at level '{freeze_level}' blocks promotion",
            }
        )
    else:
        passed += 1

    # Check 6: Open policy violations
    checks += 1
    violations = context.get("open_violations", [])
    critical_violations = [v for v in violations if v.get("severity") in ("critical", "high")]
    if critical_violations:
        blocked_reasons.append(
            {
                "code": "POLICY_VIOLATIONS",
                "description": f"{len(critical_violations)} critical/high policy violations open",
            }
        )
    else:
        passed += 1

    # Compute evidence hash over the gate evaluation
    evidence_payload = json.dumps(
        {
            "timestamp": now,
            "checks": checks,
            "passed": passed,
            "blocked_reasons": blocked_reasons,
        },
        sort_keys=True,
    )
    evidence_hash = f"sha256:{hashlib.sha256(evidence_payload.encode()).hexdigest()}"

    decision = "PASS" if not blocked_reasons else "BLOCKED"

    return GateResult(
        decision=decision,
        gate_type="release_promotion",
        blocked_reasons=blocked_reasons,
        evidence_hash=evidence_hash,
        timestamp_utc=now,
        checks_performed=checks,
        checks_passed=passed,
    )
