"""Team hook validation for Agent Teams quality gates.

These are supplementary quality checks invoked by Claude Code experimental
TeammateIdle and TaskCompleted hooks. Core enforcement is via lock + guard
(independent of these hooks).
"""

import re
from dataclasses import dataclass


@dataclass
class HookResult:
    passed: bool
    reason: str


# Required sections per agent type
_REQUIRED_SECTIONS = {
    "planner": ["PLAN", "APPROVAL", "RISKS"],
    "scope": ["SCOPE_VERDICT", "FINDINGS"],
    "security": ["SECURITY_VERDICT", "FINDINGS"],
    "gate": ["GATE_REPORT", "GATES"],
    "ops": ["OPS_REPORT", "CHECKS"],
    "evidence": ["EVIDENCE_VERDICT", "MANIFEST"],
    "pr": ["PR_VERDICT", "PR_METADATA"],
}

# Forbidden patterns in output (output contract: no scores, no bundles)
_SCORE_PATTERNS = [
    re.compile(r"[Ss]core\s*[:\s]\s*\d+", re.IGNORECASE),
    re.compile(r"\d+\s*/\s*100", re.IGNORECASE),
    re.compile(r"\d+\s*%", re.IGNORECASE),
]

_BUNDLE_PATTERN = re.compile(r"\bbundle\b", re.IGNORECASE)


def check_findings_complete(output: str, agent_type: str) -> HookResult:
    """Validate that agent output contains all required sections.

    Args:
        output: The agent's text output.
        agent_type: One of planner, scope, security, gate, ops, evidence, pr.

    Returns:
        HookResult with passed=True if all sections present.
    """
    required = _REQUIRED_SECTIONS.get(agent_type)
    if not required:
        return HookResult(passed=True, reason="")

    missing = []
    for section in required:
        if f"### {section}" not in output and f"## {section}" not in output:
            missing.append(section)

    if missing:
        return HookResult(
            passed=False,
            reason=f"Missing required sections: {', '.join(missing)}",
        )
    return HookResult(passed=True, reason="")


def validate_output_contract(output: str) -> HookResult:
    """Validate output contract: PASS/FAIL only, no scores, no bundles.

    Returns:
        HookResult with passed=True if contract is satisfied.
    """
    if not output:
        return HookResult(passed=True, reason="")

    # Check for forbidden score patterns
    for pattern in _SCORE_PATTERNS:
        match = pattern.search(output)
        if match:
            return HookResult(
                passed=False,
                reason=f"Output contract violation: score pattern found '{match.group()}'",
            )

    # Check for bundle mentions
    if _BUNDLE_PATTERN.search(output):
        return HookResult(
            passed=False,
            reason="Output contract violation: 'bundle' found (use PASS/FAIL + Findings only)",
        )

    return HookResult(passed=True, reason="")
