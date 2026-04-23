"""Watchdog — monitors autopilot process for hangs and timeouts.

Tracks phase durations and enforces per-phase timeouts.
If the autopilot exceeds a phase timeout, the watchdog records the
timeout event and signals that the loop should abort.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso


@dataclass
class PhaseTimer:
    """Timer for a single autopilot phase."""

    phase: str
    timeout_seconds: int
    start_time: float | None = None
    end_time: float | None = None

    @property
    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.monotonic()
        return end - self.start_time

    @property
    def is_timed_out(self) -> bool:
        return self.elapsed > self.timeout_seconds

    @property
    def is_running(self) -> bool:
        return self.start_time is not None and self.end_time is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "timeout_seconds": self.timeout_seconds,
            "elapsed": round(self.elapsed, 2),
            "timed_out": self.is_timed_out,
        }


class WatchdogTimeoutError(Exception):
    """Raised when a phase exceeds its timeout."""


class Watchdog:
    """Monitors phase durations and enforces timeouts."""

    DEFAULT_TIMEOUTS: dict[str, int] = {
        "collect": 60,
        "triage": 30,
        "route": 10,
        "patch": 300,
        "verify": 300,
        "pr_update": 120,
        "report": 60,
    }

    def __init__(
        self,
        timeouts: dict[str, int] | None = None,
        total_timeout: int = 1800,
    ) -> None:
        self._timeouts = timeouts or dict(self.DEFAULT_TIMEOUTS)
        self._total_timeout = total_timeout
        self._phases: list[PhaseTimer] = []
        self._current: PhaseTimer | None = None
        self._run_start: float | None = None

    @property
    def total_elapsed(self) -> float:
        if self._run_start is None:
            return 0.0
        return time.monotonic() - self._run_start

    @property
    def is_total_timed_out(self) -> bool:
        return self.total_elapsed > self._total_timeout

    def start_run(self) -> None:
        """Mark the start of an autopilot run."""
        self._run_start = time.monotonic()
        self._phases = []
        self._current = None

    def start_phase(self, phase: str) -> None:
        """Start timing a phase.

        Raises:
            WatchdogTimeoutError: If total run timeout exceeded.
        """
        if self.is_total_timed_out:
            raise WatchdogTimeoutError(
                f"Total run timeout ({self._total_timeout}s) exceeded "
                f"after {self.total_elapsed:.1f}s"
            )

        # End previous phase if running
        if self._current and self._current.is_running:
            self._current.end_time = time.monotonic()

        timeout = self._timeouts.get(phase, 300)
        timer = PhaseTimer(
            phase=phase,
            timeout_seconds=timeout,
            start_time=time.monotonic(),
        )
        self._phases.append(timer)
        self._current = timer

    def end_phase(self) -> None:
        """End timing the current phase."""
        if self._current and self._current.is_running:
            self._current.end_time = time.monotonic()

    def check(self) -> None:
        """Check if current phase or total run has timed out.

        Raises:
            WatchdogTimeoutError: If any timeout is exceeded.
        """
        if self.is_total_timed_out:
            raise WatchdogTimeoutError(f"Total run timeout ({self._total_timeout}s) exceeded")

        if self._current and self._current.is_timed_out:
            raise WatchdogTimeoutError(
                f"Phase '{self._current.phase}' timeout "
                f"({self._current.timeout_seconds}s) exceeded "
                f"after {self._current.elapsed:.1f}s"
            )

    def report(self) -> dict[str, Any]:
        """Generate watchdog timing report."""
        return {
            "timestamp": utcnow_iso(),
            "total_elapsed": round(self.total_elapsed, 2),
            "total_timeout": self._total_timeout,
            "total_timed_out": self.is_total_timed_out,
            "phases": [p.to_dict() for p in self._phases],
        }

    def save_report(self, path: Path) -> None:
        """Persist watchdog report to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.report(), indent=2),
            encoding="utf-8",
        )
