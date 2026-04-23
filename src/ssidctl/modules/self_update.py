"""Self-Update Extension — system-integrated update management.

Wraps updater.py with system-level concerns: pre-flight checks,
backup of current state, version pinning, and update history logging.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ssidctl.core.timeutil import utcnow_iso
from ssidctl.modules.updater import check_update, self_update


class SelfUpdateError(Exception):
    pass


@dataclass(frozen=True)
class VersionInfo:
    """Parsed version information."""

    current: str
    latest: str
    update_available: bool
    error: str | None = None

    @classmethod
    def check(cls) -> VersionInfo:
        """Check for updates and return structured info."""
        result = check_update()
        return cls(
            current=result["current"],
            latest=result["latest"],
            update_available=result["update_available"],
            error=result.get("error"),
        )


@dataclass
class UpdateHistoryEntry:
    """A single entry in the update history log."""

    timestamp: str
    from_version: str
    to_version: str
    success: bool
    output: str = ""
    actor: str = "user"


class UpdateManager:
    """Manages self-update lifecycle with history tracking."""

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._history_path = state_dir / "updates" / "update_history.jsonl"

    def check(self) -> VersionInfo:
        """Check for available updates."""
        return VersionInfo.check()

    def preflight(self) -> list[str]:
        """Run pre-flight checks before update. Returns list of warnings."""
        warnings: list[str] = []

        # Check Python version
        py_ver = sys.version_info
        if py_ver < (3, 11):
            warnings.append(f"Python {py_ver.major}.{py_ver.minor} detected; 3.11+ recommended")

        # Check pip availability
        try:
            import pip  # noqa: F401
        except ImportError:
            warnings.append("pip not importable — update may fail")

        # Check write permissions to site-packages
        import site

        sp = site.getsitepackages()
        if sp:
            sp_path = Path(sp[0])
            if sp_path.exists() and not _is_writable(sp_path):
                warnings.append(f"site-packages not writable: {sp_path}")

        return warnings

    def apply(self, actor: str = "user") -> dict[str, Any]:
        """Apply the update (calls updater.self_update).

        Returns {success, from_version, to_version, output}.
        """
        info = self.check()
        if not info.update_available:
            return {
                "success": True,
                "from_version": info.current,
                "to_version": info.current,
                "output": "Already up to date",
                "skipped": True,
            }

        from_version = info.current
        result = self_update()

        # Re-check version after update
        post_info = check_update()
        to_version = post_info.get("current", from_version)

        entry = UpdateHistoryEntry(
            timestamp=utcnow_iso(),
            from_version=from_version,
            to_version=to_version,
            success=result["success"],
            output=result.get("output", ""),
            actor=actor,
        )
        self._log_history(entry)

        return {
            "success": result["success"],
            "from_version": from_version,
            "to_version": to_version,
            "output": result.get("output", ""),
            "skipped": False,
        }

    def history(self) -> list[UpdateHistoryEntry]:
        """Read update history log."""
        if not self._history_path.exists():
            return []
        entries: list[UpdateHistoryEntry] = []
        with open(self._history_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(
                        UpdateHistoryEntry(
                            timestamp=data["timestamp"],
                            from_version=data["from_version"],
                            to_version=data["to_version"],
                            success=data["success"],
                            output=data.get("output", ""),
                            actor=data.get("actor", "user"),
                        )
                    )
                except (json.JSONDecodeError, KeyError):
                    continue
        return entries

    def _log_history(self, entry: UpdateHistoryEntry) -> None:
        """Append an entry to the update history log."""
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": entry.timestamp,
            "from_version": entry.from_version,
            "to_version": entry.to_version,
            "success": entry.success,
            "output": entry.output,
            "actor": entry.actor,
        }
        with open(self._history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def render_status(self) -> str:
        """Render current update status as text."""
        info = self.check()
        lines = [
            "Update Status",
            "=" * 40,
            f"  Current version: {info.current}",
            f"  Latest version:  {info.latest}",
            f"  Update available: {info.update_available}",
        ]
        if info.error:
            lines.append(f"  Error: {info.error}")

        hist = self.history()
        if hist:
            last = hist[-1]
            lines.extend(
                [
                    "",
                    "  Last update:",
                    f"    Time: {last.timestamp}",
                    f"    From: {last.from_version} -> {last.to_version}",
                    f"    Success: {last.success}",
                ]
            )

        return "\n".join(lines)


def _is_writable(path: Path) -> bool:
    """Check if a path is writable."""
    try:
        test_file = path / ".ssidctl_write_test"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        return True
    except OSError:
        return False
