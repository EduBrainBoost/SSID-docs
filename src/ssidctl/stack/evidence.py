"""Stack evidence ledger (append-only JSONL, external)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso


def append_ledger(
    path: Path,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Append a single entry to the stack ledger (JSONL format).

    Creates the file and parent directories if they do not exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": utcnow_iso(),
        "action": action,
        "details": details or {},
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
