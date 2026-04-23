"""PR module — GitHub PR operations via gh CLI.

Gracefully handles missing gh CLI.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PRError(Exception):
    pass


class GHNotInstalledError(PRError):
    pass


@dataclass(frozen=True)
class PRInfo:
    number: int
    title: str
    state: str
    branch: str
    author: str
    url: str
    mergeable: bool | None = None
    checks_pass: bool | None = None


def _check_gh() -> str:
    """Return gh path or raise GHNotInstalledError."""
    gh = shutil.which("gh")
    if gh is None:
        raise GHNotInstalledError("gh CLI not installed. Install from https://cli.github.com/")
    return gh


class PRManager:
    """Manages GitHub PRs via the gh CLI."""

    def __init__(self, repo_path: Path) -> None:
        self._repo = repo_path

    def list_prs(self, state: str = "open") -> list[PRInfo]:
        """List PRs. state: open|closed|merged|all."""
        _check_gh()
        output = self._gh(
            "pr",
            "list",
            "--state",
            state,
            "--json",
            "number,title,state,headRefName,author,url",
        )
        items = json.loads(output)
        return [
            PRInfo(
                number=item["number"],
                title=item["title"],
                state=item["state"],
                branch=item["headRefName"],
                author=item.get("author", {}).get("login", "unknown"),
                url=item["url"],
            )
            for item in items
        ]

    def status(self, pr_number: int) -> PRInfo:
        """Get status of a specific PR."""
        _check_gh()
        output = self._gh(
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,title,state,headRefName,author,url,mergeable,statusCheckRollup",
        )
        item = json.loads(output)

        checks = item.get("statusCheckRollup") or []
        checks_pass = (
            all(c.get("conclusion") == "SUCCESS" or c.get("status") == "COMPLETED" for c in checks)
            if checks
            else None
        )

        return PRInfo(
            number=item["number"],
            title=item["title"],
            state=item["state"],
            branch=item["headRefName"],
            author=item.get("author", {}).get("login", "unknown"),
            url=item["url"],
            mergeable=item.get("mergeable") == "MERGEABLE",
            checks_pass=checks_pass,
        )

    def comment(self, pr_number: int, body: str) -> None:
        """Add a comment to a PR."""
        _check_gh()
        self._gh("pr", "comment", str(pr_number), "--body", body)

    def ready(self, pr_number: int) -> dict[str, Any]:
        """Mark PR as ready for review (remove draft)."""
        _check_gh()
        self._gh("pr", "ready", str(pr_number))
        return {"pr": pr_number, "action": "marked_ready"}

    def is_gh_available(self) -> bool:
        """Check if gh CLI is available without raising."""
        return shutil.which("gh") is not None

    def _gh(self, *args: str) -> str:
        gh_path = _check_gh()
        result = subprocess.run(
            [gh_path, *args],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise PRError(f"gh failed: {result.stderr.strip()}")
        return result.stdout
