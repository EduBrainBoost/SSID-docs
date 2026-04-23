"""Bootstrap PR — automated PR creation workflow helper.

Provides utilities for creating branches, committing skeleton changes,
and generating PR metadata. Complements bootstrap.py's bootstrap_and_pr()
with more granular control and dry-run support.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class BootstrapPRError(Exception):
    pass


@dataclass
class PRSpec:
    """Specification for a PR to be created."""

    branch: str
    title: str
    body: str
    base: str = "main"
    labels: list[str] = field(default_factory=list)
    draft: bool = False

    def to_gh_args(self) -> list[str]:
        """Generate arguments for `gh pr create`."""
        args = [
            "gh",
            "pr",
            "create",
            "--title",
            self.title,
            "--body",
            self.body,
            "--base",
            self.base,
            "--head",
            self.branch,
        ]
        if self.draft:
            args.append("--draft")
        for label in self.labels:
            args.extend(["--label", label])
        return args


@dataclass
class PRResult:
    """Result of a PR creation attempt."""

    success: bool
    branch: str
    commit_sha: str = ""
    pr_url: str = ""
    error: str = ""
    dry_run: bool = False


def _git(repo_path: Path, *args: str) -> str:
    """Run a git command in the given repo."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise BootstrapPRError(f"Git failed: {result.stderr.strip()}")
    return result.stdout.strip()


def create_branch(repo_path: Path, branch: str, base: str = "HEAD") -> str:
    """Create a new branch from base ref. Returns the SHA of base."""
    sha = _git(repo_path, "rev-parse", base)
    _git(repo_path, "checkout", "-b", branch)
    return sha


def stage_and_commit(
    repo_path: Path,
    paths: list[str] | None = None,
    message: str = "feat: bootstrap skeleton",
) -> str:
    """Stage files and commit. Returns commit SHA.

    If paths is None, stages all changes.
    """
    if paths:
        for p in paths:
            _git(repo_path, "add", p)
    else:
        _git(repo_path, "add", "-A")

    _git(repo_path, "commit", "-m", message)
    return _git(repo_path, "rev-parse", "HEAD")


def prepare_pr(
    repo_path: Path,
    branch: str,
    commit_message: str = "feat: bootstrap skeleton",
    title: str | None = None,
    base: str = "main",
    labels: list[str] | None = None,
    draft: bool = False,
    dry_run: bool = False,
) -> PRResult:
    """Full PR preparation workflow: branch, stage, commit.

    Does NOT push or create the PR on GitHub (caller does that).
    """
    try:
        base_sha = create_branch(repo_path, branch, base)
    except BootstrapPRError as e:
        return PRResult(success=False, branch=branch, error=str(e), dry_run=dry_run)

    if dry_run:
        return PRResult(
            success=True,
            branch=branch,
            commit_sha=base_sha,
            dry_run=True,
        )

    try:
        commit_sha = stage_and_commit(repo_path, message=commit_message)
    except BootstrapPRError as e:
        return PRResult(success=False, branch=branch, error=str(e), dry_run=dry_run)

    return PRResult(
        success=True,
        branch=branch,
        commit_sha=commit_sha,
        dry_run=dry_run,
    )


def generate_pr_body(
    summary: str,
    files_created: int = 0,
    dirs_created: int = 0,
    extra_notes: str = "",
) -> str:
    """Generate a standardized PR body for bootstrap PRs."""
    lines = [
        "## Summary",
        "",
        summary,
        "",
    ]

    if files_created or dirs_created:
        lines.extend(
            [
                "## Changes",
                "",
                f"- Directories created: {dirs_created}",
                f"- Files created: {files_created}",
                "",
            ]
        )

    if extra_notes:
        lines.extend(
            [
                "## Notes",
                "",
                extra_notes,
                "",
            ]
        )

    lines.extend(
        [
            "## Checklist",
            "",
            "- [ ] Structure validation passes (`ssidctl doctor`)",
            "- [ ] All tests pass (`pytest tests/ -v`)",
            "- [ ] No secrets in committed files",
            "",
        ]
    )

    return "\n".join(lines)


def validate_branch_name(branch: str) -> bool:
    """Validate that a branch name follows conventions."""
    if not branch:
        return False
    if branch.startswith("/") or branch.endswith("/"):
        return False
    if ".." in branch:
        return False
    # Must start with a known prefix
    valid_prefixes = ("bootstrap/", "feat/", "fix/", "cms/", "ems/")
    return any(branch.startswith(p) for p in valid_prefixes)
