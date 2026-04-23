"""Worktree Garbage Collection — standalone GC utilities.

Provides fine-grained GC helpers that can be used independently
of the WorktreeOrchestrator. Handles orphan detection, age-based
cleanup, and dry-run reporting.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

WORKTREE_ROLES = ("plan", "apply", "verify")


class GCError(Exception):
    pass


@dataclass
class GCCandidate:
    """A directory that is a candidate for garbage collection."""

    path: Path
    run_id: str
    task_id: str | None
    reason: str
    age_hours: float


@dataclass
class GCReport:
    """Summary of a GC run."""

    scanned: int = 0
    removed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    candidates: list[GCCandidate] = field(default_factory=list)


def _dir_age_hours(path: Path) -> float:
    """Return age of a directory in hours based on mtime."""
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) / 3600.0
    except OSError:
        return 0.0


def _has_worktree_roles(directory: Path) -> bool:
    """Check if a directory contains any worktree role subdirs."""
    return any((directory / role).is_dir() for role in WORKTREE_ROLES)


def find_orphan_dirs(
    worktrees_dir: Path,
    registered_paths: set[str],
) -> list[GCCandidate]:
    """Find worktree directories that are not registered with git.

    Args:
        worktrees_dir: Base worktrees directory.
        registered_paths: Set of absolute POSIX paths from `git worktree list`.
    """
    if not worktrees_dir.is_dir():
        return []

    candidates: list[GCCandidate] = []
    for run_dir in sorted(worktrees_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name

        # Check flat layout (run_dir/role)
        for role in WORKTREE_ROLES:
            role_path = run_dir / role
            if role_path.is_dir():
                resolved = role_path.resolve().as_posix()
                if resolved not in registered_paths:
                    candidates.append(
                        GCCandidate(
                            path=role_path,
                            run_id=run_id,
                            task_id=None,
                            reason="orphan",
                            age_hours=_dir_age_hours(role_path),
                        )
                    )

        # Check nested layout (run_dir/task_id/role)
        for child in sorted(run_dir.iterdir()):
            if child.is_dir() and child.name not in WORKTREE_ROLES:
                task_id = child.name
                for role in WORKTREE_ROLES:
                    role_path = child / role
                    if role_path.is_dir():
                        resolved = role_path.resolve().as_posix()
                        if resolved not in registered_paths:
                            candidates.append(
                                GCCandidate(
                                    path=role_path,
                                    run_id=run_id,
                                    task_id=task_id,
                                    reason="orphan",
                                    age_hours=_dir_age_hours(role_path),
                                )
                            )

    return candidates


def find_stale_dirs(
    worktrees_dir: Path,
    max_age_hours: float = 168.0,  # 7 days
) -> list[GCCandidate]:
    """Find worktree run directories older than max_age_hours."""
    if not worktrees_dir.is_dir():
        return []

    candidates: list[GCCandidate] = []
    for run_dir in sorted(worktrees_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        age = _dir_age_hours(run_dir)
        if age >= max_age_hours:
            candidates.append(
                GCCandidate(
                    path=run_dir,
                    run_id=run_dir.name,
                    task_id=None,
                    reason=f"stale (>{max_age_hours:.0f}h)",
                    age_hours=age,
                )
            )
    return candidates


def gc_remove(
    candidates: list[GCCandidate],
    dry_run: bool = False,
) -> GCReport:
    """Remove GC candidate directories.

    Args:
        candidates: Directories to remove.
        dry_run: If True, only report but don't remove.
    """
    report = GCReport(scanned=len(candidates))
    report.candidates = list(candidates)

    for candidate in candidates:
        if dry_run:
            report.skipped += 1
            continue
        try:
            if candidate.path.is_dir():
                shutil.rmtree(candidate.path, ignore_errors=True)
                report.removed += 1
            else:
                report.skipped += 1
        except OSError as e:
            report.errors.append(f"Failed to remove {candidate.path}: {e}")
            report.skipped += 1

    return report


def render_gc_report(report: GCReport) -> str:
    """Render a GC report as text."""
    lines = [
        "Worktree GC Report",
        "=" * 40,
        f"  Scanned:  {report.scanned}",
        f"  Removed:  {report.removed}",
        f"  Skipped:  {report.skipped}",
    ]
    if report.errors:
        lines.append(f"  Errors:   {len(report.errors)}")
        for err in report.errors:
            lines.append(f"    - {err}")
    if report.candidates:
        lines.append("")
        lines.append("  Candidates:")
        for c in report.candidates:
            task_str = f"/{c.task_id}" if c.task_id else ""
            lines.append(f"    {c.run_id}{task_str}: {c.reason} ({c.age_hours:.1f}h old)")
    return "\n".join(lines)
