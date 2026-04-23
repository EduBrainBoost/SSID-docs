"""Lifecycle state machine for EMS task/run execution.

States: CREATED -> PLANNING -> PLANNED -> APPROVED -> APPLYING -> VERIFYING -> DONE | FAILED

Transitions are strict — no skipping states.
FAILED can be reached from any active state.
"""

from __future__ import annotations

from enum import StrEnum


class State(StrEnum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    APPLYING = "APPLYING"
    VERIFYING = "VERIFYING"
    DONE = "DONE"
    FAILED = "FAILED"


# Valid forward transitions (non-failure)
_TRANSITIONS: dict[State, tuple[State, ...]] = {
    State.CREATED: (State.PLANNING,),
    State.PLANNING: (State.PLANNED,),
    State.PLANNED: (State.APPROVED,),
    State.APPROVED: (State.APPLYING,),
    State.APPLYING: (State.VERIFYING,),
    State.VERIFYING: (State.DONE,),
    State.DONE: (),
    State.FAILED: (),
}

# States from which FAILED can be reached
_FAILABLE: frozenset[State] = frozenset(s for s in State if s not in (State.DONE, State.FAILED))


class LifecycleError(Exception):
    """Raised on invalid state transitions."""


class Lifecycle:
    """Strict state machine for task/run lifecycle."""

    def __init__(self, initial: State = State.CREATED) -> None:
        self._state = initial
        self._history: list[State] = [initial]

    @property
    def state(self) -> State:
        return self._state

    @property
    def history(self) -> list[State]:
        return list(self._history)

    @property
    def is_terminal(self) -> bool:
        return self._state in (State.DONE, State.FAILED)

    def transition(self, target: State) -> State:
        """Advance to the target state.

        Args:
            target: The desired next state.

        Returns:
            The new state.

        Raises:
            LifecycleError: If the transition is not allowed.
        """
        if self.is_terminal:
            raise LifecycleError(f"Cannot transition from terminal state {self._state.value}")

        if target == State.FAILED:
            if self._state not in _FAILABLE:
                raise LifecycleError(f"Cannot fail from state {self._state.value}")
            self._state = State.FAILED
            self._history.append(State.FAILED)
            return self._state

        allowed = _TRANSITIONS.get(self._state, ())
        if target not in allowed:
            raise LifecycleError(
                f"Invalid transition: {self._state.value} -> {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        self._state = target
        self._history.append(target)
        return self._state

    def fail(self) -> State:
        """Shortcut to transition to FAILED."""
        return self.transition(State.FAILED)

    def next_states(self) -> list[State]:
        """Return valid next states from current state."""
        result = list(_TRANSITIONS.get(self._state, ()))
        if self._state in _FAILABLE:
            result.append(State.FAILED)
        return result
