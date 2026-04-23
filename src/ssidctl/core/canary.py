"""Canary Verifier — workspace tampering detection.

Takes a hash snapshot of files OUTSIDE the allowed scope paths before
patching begins. After patching, re-hashes and compares. Any change to
a canary file indicates workspace tampering.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_file
from ssidctl.core.timeutil import utcnow_iso


@dataclass
class CanaryReport:
    """Result of canary verification."""

    timestamp: str = ""
    total_canaries: int = 0
    tampered: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.tampered) == 0 and len(self.deleted) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_canaries": self.total_canaries,
            "tampered_count": len(self.tampered),
            "deleted_count": len(self.deleted),
            "is_clean": self.is_clean,
            "tampered": self.tampered,
            "deleted": self.deleted,
        }


class CanaryVerifier:
    """Detects unauthorized file modifications via hash snapshots."""

    # Skip these directories entirely (performance)
    SKIP_DIRS = frozenset({".git", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache"})

    # Max files to snapshot per directory (sampling for performance)
    MAX_FILES_PER_DIR = 50

    def snapshot(
        self,
        worktree: Path,
        scope_paths: list[str],
        max_total: int = 500,
    ) -> dict[str, str]:
        """Hash files OUTSIDE scope_paths as canaries.

        Args:
            worktree: Root of the worktree to snapshot.
            scope_paths: Glob patterns of files that ARE allowed to change.
            max_total: Maximum total canary files to hash.

        Returns:
            Dict of {relative_path: sha256_hash}.
        """
        canaries: dict[str, str] = {}
        count = 0

        for file_path in self._walk(worktree):
            if count >= max_total:
                break

            rel = str(file_path.relative_to(worktree)).replace("\\", "/")

            # Skip files that are IN scope (those are allowed to change)
            if self._matches_any(rel, scope_paths):
                continue

            canaries[rel] = sha256_file(file_path)
            count += 1

        return canaries

    def verify(self, worktree: Path, snapshot: dict[str, str]) -> CanaryReport:
        """Verify canary files haven't been tampered with.

        Args:
            worktree: Root of the worktree.
            snapshot: Previous snapshot from snapshot().

        Returns:
            CanaryReport with tampered/deleted files.
        """
        report = CanaryReport(
            timestamp=utcnow_iso(),
            total_canaries=len(snapshot),
        )

        for rel_path, expected_hash in snapshot.items():
            file_path = worktree / rel_path
            if not file_path.exists():
                report.deleted.append(rel_path)
            else:
                actual_hash = sha256_file(file_path)
                if actual_hash != expected_hash:
                    report.tampered.append(rel_path)

        return report

    def save_snapshot(self, snapshot: dict[str, str], path: Path) -> None:
        """Persist snapshot to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def load_snapshot(self, path: Path) -> dict[str, str]:
        """Load snapshot from JSON file."""
        return json.loads(path.read_text(encoding="utf-8"))

    def _walk(self, root: Path) -> list[Path]:
        """Walk directory tree, skipping non-essential dirs."""
        files: list[Path] = []
        if not root.exists():
            return files

        for item in sorted(root.iterdir()):
            if item.is_dir():
                if item.name in self.SKIP_DIRS:
                    continue
                files.extend(self._walk(item))
            elif item.is_file():
                files.append(item)

        return files

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        """Check if path matches any glob pattern."""
        return any(fnmatch.fnmatch(path, p) for p in patterns)
