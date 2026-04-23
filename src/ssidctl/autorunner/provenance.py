"""AutoRunner V2B — ProvenanceResolver: git sha + branch binding."""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime

from ssidctl.autorunner.models import Provenance, RunScope


class ProvenanceResolver:
    def __init__(self, repo_root: str | None = None) -> None:
        self._root = repo_root or os.environ.get("GIT_REPO_ROOT", ".")

    def resolve(self, scope: RunScope) -> Provenance:
        return Provenance(
            repo=scope.repo,
            branch=scope.branch,
            commit_sha=self._git_sha(),
            ref_type="branch",
            resolved_at=datetime.now(UTC).isoformat(),
        )

    def _git_sha(self) -> str:
        try:
            result = subprocess.run(  # noqa: S603
                ["git", "-C", self._root, "rev-parse", "HEAD"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()[:40]
        except Exception:  # noqa: BLE001, S110
            pass
        return "unknown"
