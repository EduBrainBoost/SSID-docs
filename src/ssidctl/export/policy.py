"""Export policy module.

Defines export policies governing what can be exported and to where.
Policies evaluate paths using an ordered list of rules; the first match wins.
Built-in deny rules are always checked first and cannot be overridden.
Unmatched paths default to DENY (fail-closed).
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class PolicyDecision(StrEnum):
    """Outcome of a policy evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    SANITIZE = "sanitize"
    SKIP = "skip"


@dataclass(frozen=True)
class PolicyRule:
    """A single policy rule matching a glob pattern."""

    pattern: str
    decision: PolicyDecision
    reason: str = ""
    rule_id: str = ""

    def matches(self, path: str) -> bool:
        return fnmatch.fnmatch(path, self.pattern)


# Built-in deny rules — always evaluated first. Users cannot override these.
_BUILTIN_DENY_RULES: list[PolicyRule] = [
    PolicyRule(
        "**/*.pem", PolicyDecision.DENY, "TLS/PEM certificates must not be exported", "DENY-001"
    ),
    PolicyRule(
        "**/*.key", PolicyDecision.DENY, "Private key files must not be exported", "DENY-002"
    ),
    PolicyRule(
        "**/.env", PolicyDecision.DENY, "Environment files must not be exported", "DENY-003"
    ),
    PolicyRule(
        "**/credentials.json",
        PolicyDecision.DENY,
        "Credential files must not be exported",
        "DENY-004",
    ),
    PolicyRule(
        "**/quarantine/**",
        PolicyDecision.DENY,
        "Quarantine store must not be exported",
        "DENY-005",
    ),
    PolicyRule(
        "**/evidence/**",
        PolicyDecision.DENY,
        "Compliance evidence must not be exported",
        "DENY-006",
    ),
]

# Built-in skip rules — build artifacts and internal directories
_BUILTIN_SKIP_RULES: list[PolicyRule] = [
    PolicyRule(
        "**/__pycache__/**", PolicyDecision.SKIP, "Python cache files excluded", "SKIP-001"
    ),
    PolicyRule("**/*.pyc", PolicyDecision.SKIP, "Compiled Python files excluded", "SKIP-002"),
    PolicyRule("**/node_modules/**", PolicyDecision.SKIP, "Node modules excluded", "SKIP-003"),
    PolicyRule(
        "**/.git/**", PolicyDecision.DENY, "Git internals must not be exported", "SKIP-004"
    ),
]


@dataclass
class ExportPolicy:
    """Export policy: evaluates paths against ordered rules.

    Built-in deny rules are always checked first.
    User rules are checked in order after built-ins.
    Unmatched paths default to DENY (fail-closed).
    """

    rules: list[PolicyRule] = field(default_factory=list)

    def evaluate(self, path: str) -> tuple[PolicyDecision, PolicyRule | None]:
        """Evaluate a path against this policy.

        Returns:
            (decision, matching_rule) — rule is None for the default-deny fallback.
        """
        # 1. Built-in deny rules always win
        for rule in _BUILTIN_DENY_RULES:
            if rule.matches(path):
                return PolicyDecision.DENY, rule

        # 2. Built-in skip rules
        for rule in _BUILTIN_SKIP_RULES:
            if rule.matches(path):
                return rule.decision, rule

        # 3. User-defined rules (first match wins)
        for rule in self.rules:
            if rule.matches(path):
                return rule.decision, rule

        # 4. Default: deny (fail-closed)
        return PolicyDecision.DENY, None

    def to_dict(self) -> dict[str, Any]:
        return {
            "builtin_deny_count": len(_BUILTIN_DENY_RULES),
            "builtin_skip_count": len(_BUILTIN_SKIP_RULES),
            "user_rule_count": len(self.rules),
            "rules": [
                {
                    "pattern": r.pattern,
                    "decision": r.decision.value,
                    "reason": r.reason,
                    "rule_id": r.rule_id,
                }
                for r in self.rules
            ],
        }

    @classmethod
    def from_yaml(cls, path: Path) -> ExportPolicy:
        """Load an ExportPolicy from a YAML file.

        Returns an empty policy if the file does not exist.
        """
        if not path.exists():
            return cls(rules=[])

        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        rules = []
        for entry in data.get("rules", []):
            decision_raw = entry.get("decision", "deny").lower()
            try:
                decision = PolicyDecision(decision_raw)
            except ValueError:
                decision = PolicyDecision.DENY
            rules.append(
                PolicyRule(
                    pattern=entry.get("pattern", "**"),
                    decision=decision,
                    reason=entry.get("reason", ""),
                    rule_id=entry.get("rule_id", ""),
                )
            )
        return cls(rules=rules)
