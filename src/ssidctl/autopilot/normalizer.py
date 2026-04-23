"""Finding Normalizer — converts gate results into structured findings.

Takes raw GateResult objects and failure_taxonomy.yaml to produce
normalized Finding objects with type, path, severity, and summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ssidctl.gates.runner import GateResult


@dataclass(frozen=True)
class Finding:
    """A normalized finding from a gate or guard check."""

    finding_type: str  # From failure_taxonomy (e.g. SECRET_FAIL)
    gate_id: str
    gate_name: str
    severity: str  # FAIL or WARN
    summary: str
    paths: list[str] = field(default_factory=list)
    raw_exit_code: int = -1

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_type": self.finding_type,
            "gate_id": self.gate_id,
            "gate_name": self.gate_name,
            "severity": self.severity,
            "summary": self.summary,
            "paths": self.paths,
            "raw_exit_code": self.raw_exit_code,
        }


# Gate name -> failure taxonomy code mapping
_GATE_TO_TYPE: dict[str, str] = {
    "root_24_lock": "STRUCTURE_FAIL",
    "structure_guard": "STRUCTURE_FAIL",
    "anti_duplication": "STRUCTURE_FAIL",
    "forbidden_extensions": "SCOPE_FAIL",
    "sot_write_guard": "SOT_FAIL",
    "sot_validation": "SOT_FAIL",
    "secret_pii_scan": "SECRET_FAIL",
    "secret_scan": "SECRET_FAIL",
    "registry_semantics": "STRUCTURE_FAIL",
    "token_legal_lexicon": "SCOPE_FAIL",
    "output_policy_lint": "SCOPE_FAIL",
    "duplicate_guard": "STRUCTURE_FAIL",
    "repo_separation": "STRUCTURE_FAIL",
    "policy_check": "SOT_FAIL",
    "qa_check": "TEST_FAIL",
    "workflow_lint": "TOOLCHAIN_FAIL",
    "sanctions_freshness": "SOT_FAIL",
    "dora_ir_presence": "SOT_FAIL",
    "critical_paths_presence": "SOT_FAIL",
}


class FindingNormalizer:
    """Converts gate results into normalized findings."""

    def __init__(self, taxonomy_path: Path | None = None) -> None:
        self._taxonomy: dict[str, Any] = {}
        if taxonomy_path and taxonomy_path.exists():
            data = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
            self._taxonomy = data.get("codes", {})

    def normalize(self, gate_results: list[GateResult]) -> list[Finding]:
        """Convert gate results to normalized findings.

        Only FAIL results are converted to findings.
        PASS results are filtered out.
        """
        findings: list[Finding] = []

        for gr in gate_results:
            if gr.result == "PASS":
                continue

            finding_type = _GATE_TO_TYPE.get(gr.gate_name, "UNKNOWN")

            # Extract affected paths from stderr/stdout (best-effort)
            paths = self._extract_paths(gr.stderr + gr.stdout)

            # Build summary
            summary = self._build_summary(gr)

            findings.append(
                Finding(
                    finding_type=finding_type,
                    gate_id=gr.gate_id,
                    gate_name=gr.gate_name,
                    severity="FAIL",
                    summary=summary,
                    paths=paths,
                    raw_exit_code=gr.exit_code,
                )
            )

        return findings

    def deduplicate(self, findings: list[Finding]) -> list[Finding]:
        """Remove duplicate findings (same type + gate + paths)."""
        seen: set[str] = set()
        unique: list[Finding] = []

        for f in findings:
            key = f"{f.finding_type}:{f.gate_id}:{','.join(sorted(f.paths))}"
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    @staticmethod
    def _extract_paths(output: str) -> list[str]:
        """Best-effort path extraction from gate output."""
        paths: list[str] = []
        for line in output.splitlines():
            stripped = line.strip()
            # Look for lines that look like file paths
            if "/" in stripped and not stripped.startswith("#"):
                # Simple heuristic: lines containing common path separators
                for word in stripped.split():
                    if "/" in word and "." in word and len(word) < 200:
                        clean = word.strip("'\"(),;:")
                        if clean:
                            paths.append(clean)
        return paths[:20]  # Cap at 20 paths

    @staticmethod
    def _build_summary(gr: GateResult) -> str:
        """Build a human-readable summary from gate result."""
        if gr.exit_code == -1:
            return f"Gate script not found: {gr.gate_name}"
        if gr.exit_code == -2:
            return f"Gate timed out: {gr.gate_name}"
        if gr.exit_code == -3:
            return f"Gate execution error: {gr.gate_name}"

        # Use first non-empty line of stderr, then stdout
        for output in (gr.stderr, gr.stdout):
            for line in output.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("="):
                    return stripped[:200]

        return f"Gate {gr.gate_name} failed with exit code {gr.exit_code}"
