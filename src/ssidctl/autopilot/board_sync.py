"""Board-Lifecycle Sync Adapter.

Bridges the autopilot Lifecycle state machine with the Board module,
ensuring Board status reflects actual run progress.

Mapping:
    Lifecycle APPLYING   -> Board DOING
    Lifecycle VERIFYING  -> Board REVIEW
    finish("PASS")       -> Board DONE
    finish("STOP_*"/err) -> Board BLOCKED

Unmapped states (CREATED, PLANNING, PLANNED, APPROVED) are ignored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ssidctl.core.event_log import EventLog
from ssidctl.core.lifecycle import State
from ssidctl.core.timeutil import utcnow_iso
from ssidctl.modules.board import Board, BoardError

# Lifecycle state -> Board status mapping
_LIFECYCLE_TO_BOARD: dict[State, str] = {
    State.APPLYING: "DOING",
    State.VERIFYING: "REVIEW",
}


class BoardSyncAdapter:
    """Synchronizes Board status with Lifecycle transitions.

    Idempotent: skips move if Board already has the target status.
    Resilient: logs errors but does not abort the autopilot run.
    """

    def __init__(
        self,
        board: Board,
        task_id: str,
        run_id: str,
        event_log_path: Path,
        lifecycle_state_path: Path | None = None,
    ) -> None:
        self._board = board
        self._task_id = task_id
        self._run_id = run_id
        self._lifecycle_state_path = lifecycle_state_path
        # Lazy-init event log only when needed
        self._event_log_path = event_log_path
        self._event_log: EventLog | None = None

    def _get_event_log(self) -> EventLog:
        if self._event_log is None:
            self._event_log = EventLog(self._event_log_path)
        return self._event_log

    def on_lifecycle_transition(self, state: State) -> None:
        """Called when the autopilot lifecycle transitions to a new state."""
        if not self._task_id:
            return

        board_status = _LIFECYCLE_TO_BOARD.get(state)
        if board_status is None:
            return

        self._sync_board(board_status, reason="lifecycle_transition")
        self._persist_lifecycle(str(state), "lifecycle_transition")

    def on_finish(self, result: str) -> None:
        """Called when the autopilot run finishes."""
        if not self._task_id:
            return

        board_status = "DONE" if result == "PASS" else "BLOCKED"

        self._sync_board(board_status, reason=f"finish:{result}")
        self._persist_lifecycle(board_status, f"finish:{result}")

    def _sync_board(self, target_status: str, reason: str) -> None:
        """Move board task to target_status if not already there."""
        try:
            current = self._board.show(self._task_id)
            if current["status"] == target_status:
                return
            self._board.move(self._task_id, target_status, actor="autopilot")
            self._get_event_log().append(
                "board_sync.moved",
                {
                    "task_id": self._task_id,
                    "run_id": self._run_id,
                    "from_board_status": current["status"],
                    "to_board_status": target_status,
                    "reason": reason,
                },
                actor="autopilot",
            )
        except BoardError as e:
            self._get_event_log().append(
                "board_sync.error",
                {
                    "task_id": self._task_id,
                    "run_id": self._run_id,
                    "target_status": target_status,
                    "error": str(e),
                    "reason": reason,
                },
                actor="autopilot",
            )

    def _persist_lifecycle(self, state_label: str, reason: str) -> None:
        """Write last lifecycle state to JSON file."""
        if self._lifecycle_state_path is None:
            return
        self._lifecycle_state_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "task_id": self._task_id,
            "run_id": self._run_id,
            "last_lifecycle_state": state_label,
            "last_lifecycle_transition_at": utcnow_iso(),
            "last_lifecycle_reason": reason,
        }
        self._lifecycle_state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
