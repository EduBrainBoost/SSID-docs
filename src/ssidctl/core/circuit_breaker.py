"""Circuit Breaker — prevents runaway autopilot retries.

State machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
- CLOSED: normal operation, failures increment counter
- OPEN: too many failures, no new attempts until cooldown expires
- HALF_OPEN: one retry attempt after cooldown; success -> CLOSED, failure -> OPEN

State is persisted to JSON for cross-process recovery.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitSnapshot:
    """Persistent circuit breaker state."""

    state: CircuitState
    failure_count: int
    last_failure_time: float | None
    last_transition: str  # ISO timestamp
    history: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": str(self.state),
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "last_transition": self.last_transition,
            "history": self.history,
        }


class CircuitBreaker:
    """Circuit breaker with cooldown for autopilot failure protection."""

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: int = 300,
    ) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._history: list[dict[str, Any]] = []

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def record_success(self) -> None:
        """Record a successful iteration."""
        old = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._record_event("success", old, self._state)

    def record_failure(self) -> None:
        """Record a failed iteration."""
        old = self._state
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._threshold:
            self._state = CircuitState.OPEN
        self._record_event("failure", old, self._state)

    def can_proceed(self) -> bool:
        """Check if the circuit allows a new attempt."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self._cooldown:
                    old = self._state
                    self._state = CircuitState.HALF_OPEN
                    self._record_event("cooldown_expired", old, self._state)
                    return True
            return False

        # HALF_OPEN: one attempt allowed
        return self._state == CircuitState.HALF_OPEN

    def snapshot(self) -> CircuitSnapshot:
        """Get current state as a snapshot."""
        return CircuitSnapshot(
            state=self._state,
            failure_count=self._failure_count,
            last_failure_time=self._last_failure_time,
            last_transition=utcnow_iso(),
            history=list(self._history),
        )

    def save(self, path: Path) -> None:
        """Persist circuit breaker state to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.snapshot().to_dict(), indent=2),
            encoding="utf-8",
        )

    def load(self, path: Path) -> None:
        """Restore circuit breaker state from JSON."""
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self._state = CircuitState(data.get("state", "CLOSED"))
        self._failure_count = data.get("failure_count", 0)
        self._last_failure_time = data.get("last_failure_time")
        self._history = data.get("history", [])

    def reset(self) -> None:
        """Force-reset the circuit breaker to CLOSED."""
        old = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._record_event("manual_reset", old, self._state)

    def _record_event(self, event: str, old_state: CircuitState, new_state: CircuitState) -> None:
        self._history.append(
            {
                "timestamp": utcnow_iso(),
                "event": event,
                "old_state": str(old_state),
                "new_state": str(new_state),
                "failure_count": self._failure_count,
            }
        )
