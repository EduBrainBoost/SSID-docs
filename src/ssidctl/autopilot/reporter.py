"""Reporter — generates handoff reports and evidence for autopilot runs.

Produces:
- handoff.md: human-readable run summary
- findings.json: normalized findings from all iterations
- convergence.json: convergence history
- evidence manifest (via EvidenceStore)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ssidctl.core.convergence import ConvergenceDetector, IterationSnapshot
from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso


class Reporter:
    """Generates autopilot run reports and evidence."""

    def __init__(self, runs_dir: Path) -> None:
        self._runs_dir = runs_dir

    def _run_dir(self, run_id: str) -> Path:
        d = self._runs_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_handoff(
        self,
        run_id: str,
        result: str,
        history: list[IterationSnapshot],
        tasks_executed: list[dict[str, Any]] | None = None,
        pr_url: str = "",
    ) -> Path:
        """Write handoff.md — human-readable run summary."""
        run_dir = self._run_dir(run_id)
        path = run_dir / "handoff.md"

        lines = [
            f"# Autopilot Run: {run_id}",
            "",
            f"**Result:** {result}",
            f"**Timestamp:** {utcnow_iso()}",
            f"**Iterations:** {len(history)}",
            "",
        ]

        if pr_url:
            lines.append(f"**PR:** {pr_url}")
            lines.append("")

        # Convergence summary
        lines.append("## Convergence")
        detector = ConvergenceDetector()
        summary = detector.summary(history)
        lines.append(f"- Verdict: {summary['verdict']}")
        lines.append(f"- Findings trend: {summary['findings_trend']}")
        lines.append(f"- Improving: {summary['is_improving']}")
        lines.append("")

        # Iteration details
        lines.append("## Iterations")
        for snap in history:
            status = "PASS" if snap.all_pass else "FAIL"
            lines.append(
                f"- Iteration {snap.iteration}: "
                f"{snap.findings_count} findings [{status}] "
                f"types={sorted(snap.finding_types)}"
            )
        lines.append("")

        # Tasks executed
        if tasks_executed:
            lines.append("## Tasks Executed")
            for task in tasks_executed:
                lines.append(
                    f"- [{task.get('finding_type', '?')}] "
                    f"agent={task.get('agent', '?')} "
                    f"success={task.get('success', '?')}"
                )
            lines.append("")

        # Stop details
        if result.startswith("STOP_"):
            lines.append("## Stop Reason")
            lines.append(f"The autopilot stopped with code: **{result}**")
            lines.append("")
            lines.append("Manual intervention required.")
            lines.append("")

        content = "\n".join(lines)
        path.write_text(content, encoding="utf-8")
        return path

    def write_findings(
        self,
        run_id: str,
        findings: list[dict[str, Any]],
    ) -> Path:
        """Write findings.json — all normalized findings."""
        run_dir = self._run_dir(run_id)
        path = run_dir / "findings.json"
        path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "timestamp": utcnow_iso(),
                    "findings": findings,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def write_convergence(
        self,
        run_id: str,
        history: list[IterationSnapshot],
    ) -> Path:
        """Write convergence.json — iteration history."""
        run_dir = self._run_dir(run_id)
        path = run_dir / "convergence.json"
        detector = ConvergenceDetector()
        path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "timestamp": utcnow_iso(),
                    "summary": detector.summary(history),
                    "iterations": [s.to_dict() for s in history],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def write_routing_decisions(
        self,
        run_id: str,
        decisions: list[dict[str, Any]],
    ) -> Path:
        """Write routing_decisions.json."""
        run_dir = self._run_dir(run_id)
        path = run_dir / "routing_decisions.json"
        path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "timestamp": utcnow_iso(),
                    "decisions": decisions,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def content_hash(self, run_id: str) -> str:
        """Compute aggregate hash of all run artifacts."""
        run_dir = self._run_dir(run_id)
        parts: list[str] = []
        for path in sorted(run_dir.glob("*")):
            if path.is_file():
                parts.append(sha256_str(path.read_text(encoding="utf-8")))
        return sha256_str("|".join(parts))
