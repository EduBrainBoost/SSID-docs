"""Collector — gathers gate/CI outputs for the autopilot loop.

Runs all gates in the apply worktree and collects results.
Also gathers repo status (dirty files, branch info).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso
from ssidctl.gates.matrix import GateDef, load_matrix
from ssidctl.gates.runner import GateResult, run_all_gates


@dataclass
class CollectionResult:
    """Result of collecting gate outputs and repo status."""

    timestamp: str = ""
    gate_results: list[GateResult] = field(default_factory=list)
    all_pass: bool = False
    failed_gates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "all_pass": self.all_pass,
            "total_gates": len(self.gate_results),
            "failed_gates": self.failed_gates,
            "gate_results": [
                {
                    "gate_id": gr.gate_id,
                    "gate_name": gr.gate_name,
                    "result": gr.result,
                    "exit_code": gr.exit_code,
                }
                for gr in self.gate_results
            ],
        }


class Collector:
    """Collects gate outputs for autopilot analysis."""

    def __init__(self, ssid_repo: Path, timeout: int = 120) -> None:
        self._repo = ssid_repo
        self._timeout = timeout

    def collect(
        self,
        worktree_path: Path,
        gates: list[GateDef] | None = None,
    ) -> CollectionResult:
        """Run all gates and collect results.

        Args:
            worktree_path: Path to the worktree to run gates in.
            gates: Optional list of gates. If None, loads from matrix.

        Returns:
            CollectionResult with all gate outputs.
        """
        if gates is None:
            matrix = load_matrix()
            gates = matrix.gates

        gate_results = run_all_gates(gates, self._repo, timeout=self._timeout, cwd=worktree_path)

        failed = [gr.gate_name for gr in gate_results if gr.result == "FAIL"]

        return CollectionResult(
            timestamp=utcnow_iso(),
            gate_results=gate_results,
            all_pass=len(failed) == 0,
            failed_gates=failed,
        )

    def save_collection(self, result: CollectionResult, path: Path) -> None:
        """Persist collection result to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result.to_dict(), indent=2),
            encoding="utf-8",
        )
