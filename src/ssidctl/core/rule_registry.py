"""Rule Registry — manifest of all active rules with integrity verification.

Every policy file, guard, gate, and constraint is registered here.
Before each autopilot run, completeness is verified: all expected rules
must be present and unmodified. Missing or tampered rules trigger STOP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.hashing import sha256_file


@dataclass(frozen=True)
class RuleEntry:
    """A single registered rule."""

    rule_id: str
    path: str
    category: str
    description: str
    expected_hash: str


@dataclass
class CompletenessReport:
    """Result of a completeness check."""

    verified: list[RuleEntry] = field(default_factory=list)
    missing: list[RuleEntry] = field(default_factory=list)
    modified: list[tuple[RuleEntry, str]] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)

    @property
    def verified_count(self) -> int:
        return len(self.verified)

    @property
    def missing_count(self) -> int:
        return len(self.missing)

    @property
    def modified_count(self) -> int:
        return len(self.modified)

    @property
    def unexpected_count(self) -> int:
        return len(self.unexpected)

    @property
    def is_complete(self) -> bool:
        return self.missing_count == 0 and self.modified_count == 0

    def add_verified(self, rule: RuleEntry) -> None:
        self.verified.append(rule)

    def add_missing(self, rule: RuleEntry) -> None:
        self.missing.append(rule)

    def add_modified(self, rule: RuleEntry, actual_hash: str) -> None:
        self.modified.append((rule, actual_hash))

    def add_unexpected(self, path: str) -> None:
        self.unexpected.append(path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified_count": self.verified_count,
            "missing_count": self.missing_count,
            "modified_count": self.modified_count,
            "unexpected_count": self.unexpected_count,
            "is_complete": self.is_complete,
            "missing": [r.rule_id for r in self.missing],
            "modified": [r.rule_id for r, _ in self.modified],
            "unexpected": self.unexpected,
        }


class RuleRegistryError(Exception):
    """Raised on rule registry violations."""


class RuleRegistry:
    """Manifest of all active rules with integrity verification."""

    def __init__(self, registry_path: Path, base_dir: Path) -> None:
        self._registry_path = registry_path
        self._base_dir = base_dir
        self._rules: list[RuleEntry] = []

    def load(self) -> list[RuleEntry]:
        """Load rule registry from YAML manifest."""
        if not self._registry_path.exists():
            raise RuleRegistryError(f"Registry not found: {self._registry_path}")

        data = yaml.safe_load(self._registry_path.read_text(encoding="utf-8"))
        rules_data = data.get("rules", [])

        self._rules = [
            RuleEntry(
                rule_id=r["rule_id"],
                path=r["path"],
                category=r.get("category", "unknown"),
                description=r.get("description", ""),
                expected_hash=r.get("expected_hash", ""),
            )
            for r in rules_data
        ]
        return list(self._rules)

    @property
    def rules(self) -> list[RuleEntry]:
        return list(self._rules)

    def check_completeness(self) -> CompletenessReport:
        """Verify all expected rules are present and unmodified."""
        if not self._rules:
            self.load()

        report = CompletenessReport()
        known_paths: set[str] = set()

        for rule in self._rules:
            known_paths.add(rule.path)
            file_path = self._base_dir / rule.path

            if not file_path.exists():
                report.add_missing(rule)
            elif rule.expected_hash:
                actual_hash = sha256_file(file_path)
                if actual_hash != rule.expected_hash:
                    report.add_modified(rule, actual_hash)
                else:
                    report.add_verified(rule)
            else:
                # No expected hash — just check existence
                report.add_verified(rule)

        # Check for unexpected files in policies/
        policies_dir = self._base_dir / "policies"
        if policies_dir.exists():
            for file_path in sorted(policies_dir.glob("*.yaml")):
                rel = str(file_path.relative_to(self._base_dir)).replace("\\", "/")
                if rel not in known_paths:
                    report.add_unexpected(rel)

        return report

    def generate_registry(self, scan_dirs: list[str] | None = None) -> dict[str, Any]:
        """Scan policy files and generate a registry manifest.

        Useful for bootstrapping: scans all policy files, computes hashes,
        and returns a dict ready to be written as rule_registry.yaml.
        """
        if scan_dirs is None:
            scan_dirs = ["policies"]

        rules: list[dict[str, str]] = []
        for scan_dir in scan_dirs:
            dir_path = self._base_dir / scan_dir
            if not dir_path.exists():
                continue
            for file_path in sorted(dir_path.glob("*.yaml")):
                # Skip the registry itself (circular hash)
                if file_path.name == "rule_registry.yaml":
                    continue
                rel = str(file_path.relative_to(self._base_dir)).replace("\\", "/")
                rules.append(
                    {
                        "rule_id": file_path.stem,
                        "path": rel,
                        "category": "policy",
                        "description": f"Policy file: {file_path.name}",
                        "expected_hash": sha256_file(file_path),
                    }
                )

        return {"version": "1.0.0", "rules": rules}
