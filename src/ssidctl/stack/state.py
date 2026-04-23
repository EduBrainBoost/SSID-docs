"""Stack state persistence (external, no repo writes)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class StackState:
    stack_id: str
    components: dict[str, dict[str, Any]]
    started_at: str
    stopped_at: str | None = None


def load_state(path: Path) -> StackState | None:
    """Load stack state from JSON file. Returns None if missing or corrupt."""
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return StackState(
            stack_id=raw["stack_id"],
            components=raw["components"],
            started_at=raw["started_at"],
            stopped_at=raw.get("stopped_at"),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def save_state(state: StackState, path: Path) -> None:
    """Save stack state to JSON file. Creates parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(state), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
