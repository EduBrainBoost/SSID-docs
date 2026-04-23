"""Gate Replay Models — typed data structures for gate replay results.

Provides structured models for gate report serialization, replay
summaries, and comparison between original and replayed results.
Complements gates/runner.py's replay_gates() function.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class ReplayError(Exception):
    pass


@dataclass(frozen=True)
class GateEntry:
    """A single gate result entry in a stored report."""

    gate_id: str
    gate_name: str
    exit_code: int
    result: str  # PASS or FAIL
    stdout: str = ""
    stderr: str = ""

    @property
    def passed(self) -> bool:
        return self.result == "PASS"


@dataclass
class GateReport:
    """A full gate report stored in evidence."""

    run_id: str
    timestamp: str = ""
    gates: list[GateEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, report_path: Path) -> GateReport:
        """Load a gate report from a JSON file."""
        if not report_path.exists():
            raise ReplayError(f"Gate report not found: {report_path}")
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
        gates = [
            GateEntry(
                gate_id=g.get("gate_id", ""),
                gate_name=g.get("gate_name", ""),
                exit_code=g.get("exit_code", -1),
                result=g.get("result", "FAIL"),
                stdout=g.get("stdout", ""),
                stderr=g.get("stderr", ""),
            )
            for g in data.get("gates", [])
        ]
        return cls(
            run_id=data.get("run_id", report_path.parent.name),
            timestamp=data.get("timestamp", ""),
            gates=gates,
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_evidence_dir(cls, evidence_dir: Path, run_id: str) -> GateReport:
        """Load a gate report from the standard evidence path."""
        return cls.from_file(evidence_dir / "runs" / run_id / "gate_report.json")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a dict."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "gates": [asdict(g) for g in self.gates],
            "metadata": self.metadata,
        }

    def save(self, path: Path) -> None:
        """Write the report as JSON to the given path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @property
    def passed(self) -> bool:
        """True if all gates passed."""
        return all(g.passed for g in self.gates)

    @property
    def failed_gates(self) -> list[GateEntry]:
        """Return list of failed gate entries."""
        return [g for g in self.gates if not g.passed]

    @property
    def pass_count(self) -> int:
        return sum(1 for g in self.gates if g.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for g in self.gates if not g.passed)


@dataclass
class ReplayComparison:
    """Compare two gate reports (e.g., original vs replay)."""

    original: GateReport
    replay: GateReport
    diffs: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.diffs = self._compute_diffs()

    def _compute_diffs(self) -> list[dict[str, Any]]:
        """Find gates whose results differ between original and replay."""
        orig_map = {g.gate_id: g for g in self.original.gates}
        replay_map = {g.gate_id: g for g in self.replay.gates}

        diffs: list[dict[str, Any]] = []
        all_ids = sorted(set(orig_map.keys()) | set(replay_map.keys()))
        for gid in all_ids:
            o = orig_map.get(gid)
            r = replay_map.get(gid)
            if o and r:
                if o.result != r.result or o.exit_code != r.exit_code:
                    diffs.append(
                        {
                            "gate_id": gid,
                            "original_result": o.result,
                            "replay_result": r.result,
                            "original_exit": o.exit_code,
                            "replay_exit": r.exit_code,
                        }
                    )
            elif o and not r:
                diffs.append({"gate_id": gid, "status": "missing_in_replay"})
            elif r and not o:
                diffs.append({"gate_id": gid, "status": "new_in_replay"})
        return diffs

    @property
    def is_consistent(self) -> bool:
        """True if original and replay have identical results."""
        return len(self.diffs) == 0

    def render_text(self) -> str:
        """Render comparison as text."""
        lines = [
            f"Replay Comparison: {self.original.run_id}",
            f"  Original: {self.original.pass_count} pass, {self.original.fail_count} fail",
            f"  Replay:   {self.replay.pass_count} pass, {self.replay.fail_count} fail",
            f"  Consistent: {self.is_consistent}",
        ]
        if self.diffs:
            lines.append("  Differences:")
            for d in self.diffs:
                if "status" in d:
                    lines.append(f"    {d['gate_id']}: {d['status']}")
                else:
                    lines.append(
                        f"    {d['gate_id']}: {d['original_result']} -> {d['replay_result']}"
                    )
        return "\n".join(lines)
