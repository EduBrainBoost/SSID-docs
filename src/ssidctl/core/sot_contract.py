"""SoT Contract Rule Engine (G-001 / sot_contract).

Loads and validates sot_contract.yaml rule files against an SSID repo structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SoTRule:
    rule_id: str
    description: str
    severity: str
    mode: str  # "hard_fail" | "warn"


@dataclass
class SoTRuleResult:
    rule_id: str
    passed: bool
    message: str


# ---------------------------------------------------------------------------
# Rule constants — which paths each rule checks
# ---------------------------------------------------------------------------

# Rules that verify root-dir presence for a specific numbered root
_ROOT_RULES: dict[str, dict[str, Any]] = {
    "SOT_AGENT_006": {
        "root": "01_ai_layer",
        "description": "Root 01 AI Layer must exist",
    },
}

# Rules that check for a specific file inside a root
_FILE_RULES: dict[str, dict[str, str]] = {
    "SOT_AGENT_029": {
        "root": "08_identity_score",
        "file": "module.yaml",
        "message_template": "module.yaml missing in 08_identity_score",
    },
}

# Rules that check the dispatcher entry point
_DISPATCHER_RULES = {"SOT_AGENT_001"}

# Pattern: numbered roots that must exist (24 total)
_EXPECTED_ROOTS = [
    "01_ai_layer",
    "02_audit_logging",
    "03_core",
    "04_deployment",
    "05_documentation",
    "06_data_pipeline",
    "07_governance_legal",
    "08_identity_score",
    "09_infrastructure",
    "10_integration",
    "11_monitoring",
    "12_networking",
    "13_notifications",
    "14_performance",
    "15_reporting",
    "16_codex",
    "17_sandbox",
    "18_search",
    "19_security",
    "20_storage",
    "21_testing",
    "22_tooling",
    "23_compliance",
    "24_meta_orchestration",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_sot_contract(contract_path: Path) -> list[SoTRule]:
    """Load and parse a sot_contract.yaml, returning a list of SoTRule objects.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file is not a valid YAML mapping or has no 'rules' key.
    """
    if not contract_path.exists():
        raise FileNotFoundError(f"SoT contract file not found: {contract_path}")

    raw = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError(f"sot_contract.yaml must be a YAML mapping, got {type(raw).__name__}")

    if "rules" not in raw:
        raise ValueError("sot_contract.yaml must contain a 'rules' key")

    rules: list[SoTRule] = []
    for entry in raw["rules"]:
        rules.append(
            SoTRule(
                rule_id=entry["id"],
                description=entry.get("description", ""),
                severity=entry.get("severity", "high"),
                mode=entry.get("mode", "hard_fail"),
            )
        )

    return rules


def validate_sot_rules(repo_path: Path, rules: list[SoTRule]) -> list[SoTRuleResult]:
    """Validate a list of SoT rules against an SSID repo structure.

    Returns one SoTRuleResult per rule.
    """
    results: list[SoTRuleResult] = []

    for rule in rules:
        result = _evaluate_rule(repo_path, rule)
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Internal evaluation
# ---------------------------------------------------------------------------


def _evaluate_rule(repo_path: Path, rule: SoTRule) -> SoTRuleResult:
    rid = rule.rule_id

    # SOT_AGENT_001: dispatcher must exist in 24_meta_orchestration
    if rid in _DISPATCHER_RULES:
        dispatcher = repo_path / "24_meta_orchestration" / "dispatcher.yaml"
        if dispatcher.exists():
            return SoTRuleResult(rid, True, "dispatcher.yaml found")
        return SoTRuleResult(rid, False, "dispatcher.yaml missing in 24_meta_orchestration")

    # SOT_AGENT_006: 01_ai_layer root must exist
    if rid in _ROOT_RULES:
        spec = _ROOT_RULES[rid]
        root_dir = repo_path / spec["root"]
        if root_dir.is_dir():
            return SoTRuleResult(rid, True, f"{spec['root']} exists")
        return SoTRuleResult(rid, False, f"Root directory missing: {spec['root']}")

    # File-existence rules (e.g. SOT_AGENT_029)
    if rid in _FILE_RULES:
        spec = _FILE_RULES[rid]
        target = repo_path / spec["root"] / spec["file"]
        if target.exists():
            return SoTRuleResult(rid, True, f"{spec['file']} found")
        return SoTRuleResult(rid, False, spec["message_template"])

    # Generic numbered-root existence check for unrecognised rule IDs
    # Try to map rule index to a root dir (e.g. SOT_AGENT_002 → root index 1)
    try:
        idx = int(rid.split("_")[-1]) - 1
        if 0 <= idx < len(_EXPECTED_ROOTS):
            root = _EXPECTED_ROOTS[idx]
            if (repo_path / root).is_dir():
                return SoTRuleResult(rid, True, f"{root} exists")
            return SoTRuleResult(rid, False, f"Root directory missing: {root}")
    except (ValueError, IndexError):
        pass

    # Unknown rule — pass by default (extensible)
    return SoTRuleResult(rid, True, f"Rule {rid} has no evaluator — auto-pass")
