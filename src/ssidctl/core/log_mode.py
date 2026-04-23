"""LOG_MODE enforcement — MINIMAL default, FORENSIC explicit only."""

from __future__ import annotations

import re
from enum import Enum

LOG_MODE_ENV = "SSIDCTL_LOG_MODE"


class LogMode(Enum):
    MINIMAL = "MINIMAL"
    FORENSIC = "FORENSIC"


_STRIP_PATTERNS = [
    re.compile(r"^prompt:.*$", re.MULTILINE),
    re.compile(r"^stdout:.*$", re.MULTILINE),
    re.compile(r"^stderr:.*$", re.MULTILINE),
    re.compile(r"^response:.*$", re.MULTILINE),
    re.compile(r"^output:.*$", re.MULTILINE),
]


def get_log_mode(env: dict[str, str] | None = None) -> LogMode:
    """Get log mode from environment. Default: MINIMAL."""
    if env is None:
        import os

        env = dict(os.environ)
    raw = env.get(LOG_MODE_ENV, "MINIMAL")
    if raw == "FORENSIC":
        return LogMode.FORENSIC
    return LogMode.MINIMAL


def filter_output(raw: str, mode: LogMode) -> str:
    """Filter output according to log mode.

    MINIMAL: strip prompts/stdout/responses, keep tool/exit/hash/gate info.
    FORENSIC: keep everything.
    """
    if mode == LogMode.FORENSIC:
        return raw
    lines = raw.split("\n")
    kept = []
    for line in lines:
        stripped = False
        for pattern in _STRIP_PATTERNS:
            if pattern.match(line):
                stripped = True
                break
        if not stripped:
            kept.append(line)
    return "\n".join(kept)
