"""Gate runner — executes SSID gate scripts in Operate mode.

Gates are external scripts in the SSID repo. Runner invokes them
via subprocess in a worktree context and maps exit codes.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ssidctl.gates.exitcode_map import map_exit_code
from ssidctl.gates.matrix import GateDef


@dataclass
class GateResult:
    gate_id: str
    gate_name: str
    exit_code: int
    result: str  # PASS or FAIL
    stdout: str
    stderr: str


def run_gate(
    gate: GateDef,
    repo_path: Path,
    timeout: int = 120,
    cwd: Path | None = None,
) -> GateResult:
    """Execute a single gate script.

    Args:
        gate: Gate definition from matrix.
        repo_path: Path to SSID repo root.
        timeout: Max seconds for the gate script.
        cwd: Working directory (defaults to repo_path).

    Returns:
        GateResult with exit code and mapped result.
    """
    if gate.skip_reason:
        return GateResult(
            gate_id=gate.id,
            gate_name=gate.name,
            exit_code=0,
            result="PASS",
            stdout=f"SKIP: {gate.skip_reason}",
            stderr="",
        )

    script_path = repo_path / gate.script
    if not script_path.exists():
        return GateResult(
            gate_id=gate.id,
            gate_name=gate.name,
            exit_code=-1,
            result="FAIL",
            stdout="",
            stderr=f"Script not found: {gate.script}",
        )

    cmd = ["python", str(script_path)] + gate.args
    work_dir = cwd or repo_path

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = map_exit_code(proc.returncode, gate.exit_codes)
        return GateResult(
            gate_id=gate.id,
            gate_name=gate.name,
            exit_code=proc.returncode,
            result=result,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired:
        return GateResult(
            gate_id=gate.id,
            gate_name=gate.name,
            exit_code=-2,
            result="FAIL",
            stdout="",
            stderr=f"Gate timed out after {timeout}s",
        )
    except OSError as e:
        return GateResult(
            gate_id=gate.id,
            gate_name=gate.name,
            exit_code=-3,
            result="FAIL",
            stdout="",
            stderr=str(e),
        )


def run_all_gates(
    gates: list[GateDef],
    repo_path: Path,
    timeout: int = 120,
    cwd: Path | None = None,
) -> list[GateResult]:
    """Run all gates sequentially, stopping on first FAIL."""
    results = []
    for gate in gates:
        result = run_gate(gate, repo_path, timeout, cwd)
        results.append(result)
        if result.result == "FAIL":
            break
    return results


def replay_gates(run_id: str, evidence_dir: Path) -> list[GateResult]:
    """Replay gates from a stored gate report.

    Reads {evidence_dir}/runs/{run_id}/gate_report.json and reconstructs
    GateResult list from stored data.
    """
    report_path = evidence_dir / "runs" / run_id / "gate_report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"Gate report not found: {report_path}")

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    results = []
    for entry in report.get("gates", []):
        results.append(
            GateResult(
                gate_id=entry.get("gate_id", ""),
                gate_name=entry.get("gate_name", ""),
                exit_code=entry.get("exit_code", -1),
                result=entry.get("result", "FAIL"),
                stdout=entry.get("stdout", ""),
                stderr=entry.get("stderr", ""),
            )
        )
    return results
