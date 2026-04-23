"""Convergence Detector — determines if the autopilot loop is making progress.

Analyzes iteration history to detect:
- CONVERGED: all findings resolved
- DIVERGING: findings increasing over iterations
- OSCILLATING: same findings appearing/disappearing cyclically
- STALLED: no progress for N consecutive iterations
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ConvergenceVerdict(StrEnum):
    CONTINUE = "CONTINUE"
    CONVERGED = "CONVERGED"
    STOP_DIVERGING = "STOP_DIVERGING"
    STOP_OSCILLATING = "STOP_OSCILLATING"
    STOP_STALLED = "STOP_STALLED"


@dataclass(frozen=True)
class IterationSnapshot:
    """Summary of one autopilot iteration for convergence tracking."""

    iteration: int
    findings_count: int
    finding_types: frozenset[str]
    all_pass: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "findings_count": self.findings_count,
            "finding_types": sorted(self.finding_types),
            "all_pass": self.all_pass,
        }


class ConvergenceDetector:
    """Analyzes iteration history to detect convergence or divergence."""

    def __init__(
        self,
        stall_threshold: int = 2,
        oscillation_window: int = 3,
    ) -> None:
        self._stall_threshold = stall_threshold
        self._oscillation_window = oscillation_window

    def check(self, history: list[IterationSnapshot]) -> ConvergenceVerdict:
        """Determine convergence verdict from iteration history.

        Args:
            history: Ordered list of iteration snapshots (oldest first).

        Returns:
            ConvergenceVerdict indicating whether to continue, stop, or declare success.
        """
        if not history:
            return ConvergenceVerdict.CONTINUE

        latest = history[-1]

        # All pass = converged
        if latest.all_pass:
            return ConvergenceVerdict.CONVERGED

        if len(history) < 2:
            return ConvergenceVerdict.CONTINUE

        # Check: Are findings decreasing?
        counts = [s.findings_count for s in history]
        deltas = [counts[i] - counts[i + 1] for i in range(len(counts) - 1)]

        # Recent deltas all non-positive = stalled or diverging
        recent = deltas[-self._stall_threshold :]
        if len(recent) >= self._stall_threshold and all(d <= 0 for d in recent):
            if any(d < 0 for d in recent):
                return ConvergenceVerdict.STOP_DIVERGING
            return ConvergenceVerdict.STOP_STALLED

        # Oscillation detection: A-B-A pattern in finding types
        if len(history) >= self._oscillation_window:
            window = history[-self._oscillation_window :]
            type_sets = [s.finding_types for s in window]
            # Check if first and last match but middle differs
            if type_sets[0] == type_sets[-1] and type_sets[0] != type_sets[1]:
                return ConvergenceVerdict.STOP_OSCILLATING

        return ConvergenceVerdict.CONTINUE

    def summary(self, history: list[IterationSnapshot]) -> dict[str, Any]:
        """Generate convergence summary for reporting."""
        verdict = self.check(history)
        counts = [s.findings_count for s in history]
        return {
            "verdict": str(verdict),
            "iterations": len(history),
            "findings_trend": counts,
            "latest_findings": counts[-1] if counts else 0,
            "is_improving": (len(counts) >= 2 and counts[-1] < counts[-2] if counts else False),
        }
