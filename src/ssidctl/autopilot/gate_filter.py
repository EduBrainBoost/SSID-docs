"""Gate Filter — maps TaskSpec acceptance_checks to gate subsets from the matrix.

Mapping:
  "structure" -> structure_guard, duplicate_guard, repo_separation
  "policy"    -> policy_check
  "sot"       -> sot_validation, sanctions_freshness, dora_ir_presence, critical_paths_presence
  "qa"        -> qa_check

Always included: secret_scan (mandatory, non-negotiable).
"""

from __future__ import annotations

from ssidctl.gates.matrix import GateDef

# Maps acceptance_check category to gate names
_CHECK_TO_GATES: dict[str, list[str]] = {
    "structure": ["structure_guard", "duplicate_guard", "repo_separation"],
    "policy": ["policy_check", "workflow_lint"],
    "sot": [
        "sot_validation",
        "sanctions_freshness",
        "dora_ir_presence",
        "critical_paths_presence",
    ],
    "qa": ["qa_check"],
}

# Always included regardless of acceptance_checks
_MANDATORY_GATES = {"secret_scan"}


def filter_gates(
    all_gates: list[GateDef],
    acceptance_checks: list[str],
) -> list[GateDef]:
    """Filter gates based on TaskSpec acceptance_checks.

    Args:
        all_gates: Full list of gates from the matrix.
        acceptance_checks: List of check categories (e.g. ["policy", "sot", "structure"]).

    Returns:
        Filtered list preserving original gate order.
        Always includes secret_scan (mandatory).
    """
    # Build set of allowed gate names
    allowed_names: set[str] = set(_MANDATORY_GATES)
    for check in acceptance_checks:
        gate_names = _CHECK_TO_GATES.get(check, [])
        allowed_names.update(gate_names)

    # Filter preserving order
    return [g for g in all_gates if g.name in allowed_names]
