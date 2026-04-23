"""Double Verification Protocol (DVP) — anti-manipulation gate verification.

Runs gates in BOTH the apply and verify worktrees and compares results.
Any mismatch indicates potential manipulation or non-determinism.

Also verifies gate script integrity before execution by checking SHA-256
hashes against known values.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_file, sha256_str
from ssidctl.gates.runner import run_all_gates


@dataclass(frozen=True)
class DVPResult:
    """Comparison of a single gate run in apply vs verify worktrees."""

    gate_id: str
    gate_name: str
    apply_result: str
    verify_result: str
    apply_stdout_hash: str
    verify_stdout_hash: str
    match: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "gate_name": self.gate_name,
            "apply_result": self.apply_result,
            "verify_result": self.verify_result,
            "apply_stdout_hash": self.apply_stdout_hash,
            "verify_stdout_hash": self.verify_stdout_hash,
            "match": self.match,
        }


@dataclass
class DVPReport:
    """Complete DVP report for one verification pass."""

    results: list[DVPResult]
    script_integrity: list[dict[str, Any]]
    all_match: bool
    all_scripts_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_match": self.all_match,
            "all_scripts_verified": self.all_scripts_verified,
            "results": [r.to_dict() for r in self.results],
            "script_integrity": self.script_integrity,
        }


class ManipulationError(Exception):
    """Raised when gate script manipulation is detected."""


class DoubleVerifier:
    """Runs gates in both worktrees and compares results."""

    def __init__(self, known_script_hashes: dict[str, str] | None = None) -> None:
        self._known_hashes = known_script_hashes or {}

    def verify_script_integrity(self, gates: list[Any], repo_path: Path) -> list[dict[str, Any]]:
        """Verify gate script hashes before execution.

        Returns list of check results. Raises ManipulationError on mismatch
        when known hashes are configured.
        """
        checks: list[dict[str, Any]] = []
        for gate in gates:
            script_path = repo_path / gate.script
            if not script_path.exists():
                checks.append(
                    {
                        "gate_id": gate.id,
                        "script": gate.script,
                        "status": "MISSING",
                        "hash": None,
                    }
                )
                continue

            actual_hash = sha256_file(script_path)
            expected = self._known_hashes.get(gate.id)

            if expected and actual_hash != expected:
                checks.append(
                    {
                        "gate_id": gate.id,
                        "script": gate.script,
                        "status": "TAMPERED",
                        "expected": expected,
                        "actual": actual_hash,
                    }
                )
                raise ManipulationError(
                    f"Gate script tampered: {gate.script} "
                    f"(expected {expected[:20]}..., got {actual_hash[:20]}...)"
                )

            checks.append(
                {
                    "gate_id": gate.id,
                    "script": gate.script,
                    "status": "VERIFIED",
                    "hash": actual_hash,
                }
            )

        return checks

    def run_double_verification(
        self,
        gates: list[Any],
        apply_wt: Path,
        verify_wt: Path,
        repo_path: Path,
        timeout: int = 120,
    ) -> DVPReport:
        """Run gates in both worktrees and compare.

        Args:
            gates: List of GateDef objects from the gate matrix.
            apply_wt: Path to the apply worktree.
            verify_wt: Path to the verify worktree.
            repo_path: Path to SSID repo (for script resolution).
            timeout: Gate timeout in seconds.

        Returns:
            DVPReport with comparison results.
        """
        # 1. Verify script integrity
        script_checks = self.verify_script_integrity(gates, repo_path)

        # 2. Run in apply worktree
        apply_results = run_all_gates(gates, repo_path, timeout=timeout, cwd=apply_wt)

        # 3. Run in verify worktree (independent)
        verify_results = run_all_gates(gates, repo_path, timeout=timeout, cwd=verify_wt)

        # 4. Compare results
        dvp_results: list[DVPResult] = []

        # Pad shorter list if gates differ
        max_len = max(len(apply_results), len(verify_results))
        for i in range(max_len):
            a = apply_results[i] if i < len(apply_results) else None
            v = verify_results[i] if i < len(verify_results) else None

            if a is None or v is None:
                dvp_results.append(
                    DVPResult(
                        gate_id=a.gate_id if a else (v.gate_id if v else "?"),
                        gate_name=a.gate_name if a else (v.gate_name if v else "?"),
                        apply_result=a.result if a else "MISSING",
                        verify_result=v.result if v else "MISSING",
                        apply_stdout_hash=sha256_str(a.stdout) if a else "",
                        verify_stdout_hash=sha256_str(v.stdout) if v else "",
                        match=False,
                    )
                )
                continue

            a_hash = sha256_str(a.stdout)
            v_hash = sha256_str(v.stdout)

            dvp_results.append(
                DVPResult(
                    gate_id=a.gate_id,
                    gate_name=a.gate_name,
                    apply_result=a.result,
                    verify_result=v.result,
                    apply_stdout_hash=a_hash,
                    verify_stdout_hash=v_hash,
                    match=(a.result == v.result),
                )
            )

        return DVPReport(
            results=dvp_results,
            script_integrity=script_checks,
            all_match=all(r.match for r in dvp_results),
            all_scripts_verified=all(c["status"] == "VERIFIED" for c in script_checks),
        )

    def save_report(self, report: DVPReport, path: Path) -> None:
        """Persist DVP report to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report.to_dict(), indent=2),
            encoding="utf-8",
        )
