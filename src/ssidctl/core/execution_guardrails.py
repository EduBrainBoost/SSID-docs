"""Fail-closed execution guardrails — composable validators for worker execution.

Every check returns a GuardrailResult. run_all_guardrails is fail-fast:
first failure stops evaluation and returns blocked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso

# Shell metacharacters that must never appear in any payload field
SHELL_METACHAR_PATTERN = re.compile(r"[;|&`$(){}\[\]<>!#~\n\r]")

# Supported action types (must match action_adapter_registry)
SUPPORTED_ACTION_TYPES = frozenset({"lint_fix", "format_fix", "dependency_update", "test_fix"})

# Required payload fields per action type
REQUIRED_PAYLOAD_FIELDS: dict[str, list[str]] = {
    "lint_fix": ["target_ref", "repo_root"],
    "format_fix": ["target_ref", "repo_root"],
    "dependency_update": ["target_ref", "repo_root"],
    "test_fix": ["target_ref", "repo_root"],
}


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""

    passed: bool
    blocked_reason: str | None
    guardrail_name: str
    checked_at: str
    evidence_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked_reason": self.blocked_reason,
            "guardrail_name": self.guardrail_name,
            "checked_at": self.checked_at,
            "evidence_hash": self.evidence_hash,
        }


def _make_result(
    passed: bool, guardrail_name: str, reason: str | None, evidence_input: str
) -> GuardrailResult:
    return GuardrailResult(
        passed=passed,
        blocked_reason=reason,
        guardrail_name=guardrail_name,
        checked_at=utcnow_iso(),
        evidence_hash=sha256_str(evidence_input),
    )


def _pass(guardrail_name: str, evidence_input: str) -> GuardrailResult:
    return _make_result(True, guardrail_name, None, evidence_input)


def _block(guardrail_name: str, reason: str, evidence_input: str) -> GuardrailResult:
    return _make_result(False, guardrail_name, reason, evidence_input)


# ---------------------------------------------------------------------------
# Individual guardrails
# ---------------------------------------------------------------------------


def validate_action_type(action_type: str) -> GuardrailResult:
    """Unsupported action type => blocked."""
    name = "validate_action_type"
    if action_type in SUPPORTED_ACTION_TYPES:
        return _pass(name, action_type)
    return _block(name, f"Unsupported action type: {action_type}", action_type)


def validate_payload(payload: dict[str, Any], action_type: str) -> GuardrailResult:
    """Invalid or incomplete payload => blocked."""
    name = "validate_payload"
    evidence = f"{action_type}:{sorted(payload.keys())}"
    if not payload:
        return _block(name, "Payload is empty", evidence)
    required = REQUIRED_PAYLOAD_FIELDS.get(action_type, [])
    missing = [f for f in required if f not in payload or not payload[f]]
    if missing:
        return _block(name, f"Missing required fields: {missing}", evidence)
    return _pass(name, evidence)


def validate_target_path(repo: str, path: str, allowlist: list[str]) -> GuardrailResult:
    """Repo/path outside allowlist => blocked. Path traversal => blocked."""
    name = "validate_target_path"
    evidence = f"{repo}:{path}"
    normalized = path.replace("\\", "/")

    # Path traversal check
    if ".." in normalized:
        return _block(name, "Path traversal detected (..)", evidence)

    # Null byte check
    if "\x00" in path or "\x00" in repo:
        return _block(name, "Null byte in path", evidence)

    # Allowlist check
    if not allowlist:
        return _block(name, "Empty allowlist — all paths blocked", evidence)

    if not any(normalized.startswith(prefix) for prefix in allowlist):
        return _block(name, f"Path not in allowlist: {normalized}", evidence)

    return _pass(name, evidence)


def validate_approval(
    action_type: str, approval_status: str, requires_approval: bool
) -> GuardrailResult:
    """Missing approval when required => blocked."""
    name = "validate_approval"
    evidence = f"{action_type}:{approval_status}:{requires_approval}"
    if requires_approval and approval_status != "approved":
        return _block(name, f"Approval required but status is: {approval_status}", evidence)
    return _pass(name, evidence)


def validate_adapter_exists(action_type: str, registered_types: list[str]) -> GuardrailResult:
    """Missing adapter for action type => blocked."""
    name = "validate_adapter_exists"
    evidence = f"{action_type}:{sorted(registered_types)}"
    if action_type not in registered_types:
        return _block(name, f"No adapter registered for: {action_type}", evidence)
    return _pass(name, evidence)


def validate_lease(
    worker_id: str,
    item_id: str,
    lease_owner: str | None,
    lease_expired: bool,
) -> GuardrailResult:
    """Lease conflict or expired => blocked."""
    name = "validate_lease"
    evidence = f"{worker_id}:{item_id}:{lease_owner}:{lease_expired}"
    if lease_owner is None:
        return _block(name, "No active lease for item", evidence)
    if lease_expired:
        return _block(name, "Lease has expired", evidence)
    if lease_owner != worker_id:
        return _block(name, f"Lease owned by different worker: {lease_owner}", evidence)
    return _pass(name, evidence)


def validate_no_shell_injection(payload: dict[str, Any]) -> GuardrailResult:
    """Shell metacharacters in any string field => blocked."""
    name = "validate_no_shell_injection"
    evidence = str(sorted(payload.keys()))
    for key, value in payload.items():
        if isinstance(value, str) and SHELL_METACHAR_PATTERN.search(value):
            return _block(
                name, f"Shell metacharacter in field '{key}': {repr(value[:50])}", evidence
            )
        if isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str) and SHELL_METACHAR_PATTERN.search(item):
                    return _block(name, f"Shell metacharacter in field '{key}[{i}]'", evidence)
    return _pass(name, evidence)


# ---------------------------------------------------------------------------
# Composite guardrail runner
# ---------------------------------------------------------------------------


@dataclass
class GuardrailContext:
    """Input context for running all guardrails."""

    action_type: str
    payload: dict[str, Any]
    repo: str
    target_path: str
    path_allowlist: list[str]
    approval_status: str
    requires_approval: bool
    registered_adapter_types: list[str]
    worker_id: str
    item_id: str
    lease_owner: str | None
    lease_expired: bool


def run_all_guardrails(ctx: GuardrailContext) -> GuardrailResult:
    """Run all guardrails in sequence. Fail-fast on first failure."""
    checks = [
        lambda: validate_action_type(ctx.action_type),
        lambda: validate_payload(ctx.payload, ctx.action_type),
        lambda: validate_no_shell_injection(ctx.payload),
        lambda: validate_target_path(ctx.repo, ctx.target_path, ctx.path_allowlist),
        lambda: validate_approval(ctx.action_type, ctx.approval_status, ctx.requires_approval),
        lambda: validate_adapter_exists(ctx.action_type, ctx.registered_adapter_types),
        lambda: validate_lease(ctx.worker_id, ctx.item_id, ctx.lease_owner, ctx.lease_expired),
    ]

    for check in checks:
        result = check()
        if not result.passed:
            return result

    # All passed
    return _pass("run_all_guardrails", f"all_passed:{ctx.action_type}:{ctx.item_id}")
