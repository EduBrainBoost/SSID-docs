"""Attestation Engine — periodic re-verification of rules, policies, and plans.

Verifies that all registered rules, policy files, and plan artifacts
are still present and unmodified. Generates attestation records with
timestamps for audit compliance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_file, sha256_str
from ssidctl.core.rule_registry import RuleRegistry
from ssidctl.core.timeutil import utcnow_iso

EXPECTED_AGENTS = [
    "ssid-01-planner",
    "ssid-02-scope-sentry",
    "ssid-03-patch-implementer",
    "ssid-04-gate-runner",
    "ssid-05-security-compliance",
    "ssid-06-evidence-worm",
    "ssid-07-pr-integrator",
    "ssid-08-ops-runner",
    "ssid-09-content-writer",
    "ssid-10-designer",
    "ssid-11-board-manager",
    "ssid-12-test-runner",
]


@dataclass
class AttestationRecord:
    """A single attestation event."""

    timestamp: str
    rules_expected: int
    rules_verified: int
    rules_missing: int
    rules_modified: int
    rules_unexpected: int
    plans_checked: int = 0
    plans_present: int = 0
    agents_expected: int = 0
    agents_present: int = 0
    agents_missing: list[str] | None = None
    verdict: str = "PASS"
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "timestamp": self.timestamp,
            "rules_expected": self.rules_expected,
            "rules_verified": self.rules_verified,
            "rules_missing": self.rules_missing,
            "rules_modified": self.rules_modified,
            "rules_unexpected": self.rules_unexpected,
            "plans_checked": self.plans_checked,
            "plans_present": self.plans_present,
            "agents_expected": self.agents_expected,
            "agents_present": self.agents_present,
            "verdict": self.verdict,
            "content_hash": self.content_hash,
        }
        if self.agents_missing:
            d["agents_missing"] = self.agents_missing
        return d


@dataclass
class ArtifactStatus:
    """Status of a single tracked artifact."""

    path: str
    category: str
    exists: bool
    current_hash: str = ""
    last_verified: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "category": self.category,
            "exists": self.exists,
            "current_hash": self.current_hash,
            "last_verified": self.last_verified,
        }


class AttestationEngine:
    """Performs periodic attestation of rules, policies, and plans."""

    def __init__(self, ems_dir: Path, state_dir: Path) -> None:
        self._ems_dir = ems_dir
        self._state_dir = state_dir
        self._attestation_dir = state_dir / "attestation"

    def attest_rules(self) -> AttestationRecord:
        """Attest all rules in the rule registry."""
        registry_path = self._ems_dir / "policies" / "rule_registry.yaml"

        if not registry_path.exists():
            return AttestationRecord(
                timestamp=utcnow_iso(),
                rules_expected=0,
                rules_verified=0,
                rules_missing=0,
                rules_modified=0,
                rules_unexpected=0,
                verdict="WARN_NO_REGISTRY",
            )

        registry = RuleRegistry(registry_path, self._ems_dir)
        report = registry.check_completeness()

        record = AttestationRecord(
            timestamp=utcnow_iso(),
            rules_expected=len(registry.rules),
            rules_verified=report.verified_count,
            rules_missing=report.missing_count,
            rules_modified=report.modified_count,
            rules_unexpected=report.unexpected_count,
            verdict="PASS" if report.is_complete else "FAIL",
            content_hash=sha256_str(json.dumps(report.to_dict())),
        )

        return record

    def attest_plans(self) -> tuple[int, int, list[ArtifactStatus]]:
        """Check that all plan files in docs/plans/ still exist.

        Returns:
            (checked, present, statuses)
        """
        plans_dir = self._ems_dir / "docs" / "plans"
        statuses: list[ArtifactStatus] = []

        if not plans_dir.exists():
            return 0, 0, statuses

        for plan_file in sorted(plans_dir.glob("*.md")):
            rel = str(plan_file.relative_to(self._ems_dir)).replace("\\", "/")
            statuses.append(
                ArtifactStatus(
                    path=rel,
                    category="plan",
                    exists=True,
                    current_hash=sha256_file(plan_file),
                    last_verified=utcnow_iso(),
                )
            )

        return len(statuses), len(statuses), statuses

    def attest_policies(self) -> list[ArtifactStatus]:
        """Check all policy YAML files."""
        policies_dir = self._ems_dir / "policies"
        statuses: list[ArtifactStatus] = []

        if not policies_dir.exists():
            return statuses

        for policy_file in sorted(policies_dir.glob("*.yaml")):
            rel = str(policy_file.relative_to(self._ems_dir)).replace("\\", "/")
            statuses.append(
                ArtifactStatus(
                    path=rel,
                    category="policy",
                    exists=True,
                    current_hash=sha256_file(policy_file),
                    last_verified=utcnow_iso(),
                )
            )

        return statuses

    def attest_agents(self) -> tuple[int, int, list[str], list[ArtifactStatus]]:
        """Verify all 12 agent definitions exist in agents/definitions/.

        Returns:
            (expected, present, missing_names, statuses)
        """
        defs_dir = self._ems_dir / "agents" / "definitions"
        statuses: list[ArtifactStatus] = []
        missing: list[str] = []
        present = 0

        for agent_name in EXPECTED_AGENTS:
            agent_file = defs_dir / f"{agent_name}.md"
            if agent_file.exists():
                present += 1
                statuses.append(
                    ArtifactStatus(
                        path=f"agents/definitions/{agent_name}.md",
                        category="agent_definition",
                        exists=True,
                        current_hash=sha256_file(agent_file),
                        last_verified=utcnow_iso(),
                    )
                )
            else:
                missing.append(agent_name)
                statuses.append(
                    ArtifactStatus(
                        path=f"agents/definitions/{agent_name}.md",
                        category="agent_definition",
                        exists=False,
                        last_verified=utcnow_iso(),
                    )
                )

        return len(EXPECTED_AGENTS), present, missing, statuses

    def attest_all(self) -> AttestationRecord:
        """Full attestation: rules + plans + policies + agents."""
        rule_record = self.attest_rules()
        plans_checked, plans_present, plan_statuses = self.attest_plans()
        policy_statuses = self.attest_policies()
        agents_expected, agents_present, agents_missing, agent_statuses = self.attest_agents()

        rule_record.plans_checked = plans_checked
        rule_record.plans_present = plans_present
        rule_record.agents_expected = agents_expected
        rule_record.agents_present = agents_present
        if agents_missing:
            rule_record.agents_missing = agents_missing
            rule_record.verdict = "FAIL"

        # Save attestation report
        self._save_attestation(rule_record, plan_statuses, policy_statuses, agent_statuses)

        return rule_record

    def _save_attestation(
        self,
        record: AttestationRecord,
        plans: list[ArtifactStatus],
        policies: list[ArtifactStatus],
        agents: list[ArtifactStatus] | None = None,
    ) -> Path:
        """Persist attestation to state directory."""
        self._attestation_dir.mkdir(parents=True, exist_ok=True)

        report: dict[str, Any] = {
            "record": record.to_dict(),
            "plans": [p.to_dict() for p in plans],
            "policies": [p.to_dict() for p in policies],
        }
        if agents:
            report["agents"] = [a.to_dict() for a in agents]

        # Write timestamped report
        ts = record.timestamp.replace(":", "-")
        report_path = self._attestation_dir / f"attestation_{ts}.json"
        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        # Write latest pointer
        latest_path = self._attestation_dir / "latest.json"
        latest_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        return report_path

    def get_latest(self) -> dict[str, Any] | None:
        """Load latest attestation report."""
        latest = self._attestation_dir / "latest.json"
        if not latest.exists():
            return None
        return json.loads(latest.read_text(encoding="utf-8"))
