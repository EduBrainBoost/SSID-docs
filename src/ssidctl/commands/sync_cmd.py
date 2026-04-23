"""ssidctl sync — cross-repo state check."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from ssidctl.config import EMSConfig

_REPOS = ("ssid_repo", "ems_repo")
_EXTRA_REPOS = {
    "ssid-orchestrator": Path(r"C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID-orchestrator"),
}


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("sync", help="Cross-repo state check")
    parser.set_defaults(func=cmd_sync)


def cmd_sync(args: argparse.Namespace, config: EMSConfig) -> int:
    repos: list[tuple[str, Path]] = []
    for name in _REPOS:
        repos.append((name, getattr(config.paths, name)))
    for name, path in _EXTRA_REPOS.items():
        repos.append((name, path))

    all_ok = True

    for name, repo_path in repos:
        print(f"  {name}: {repo_path}")

        if not repo_path.exists():
            print("    SKIP  path not found")
            continue

        # Branch
        branch = _git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if branch is None:
            print("    FAIL  not a git repo")
            all_ok = False
            continue
        print(f"    branch: {branch}")

        # SHA
        sha = _git(repo_path, ["rev-parse", "--short", "HEAD"])
        print(f"    sha:    {sha or '?'}")

        # Dirty files
        dirty = _git(repo_path, ["status", "--porcelain"])
        dirty_count = len([ln for ln in (dirty or "").splitlines() if ln.strip()])
        status = "OK" if dirty_count == 0 else "WARN"
        print(f"    {status:4s}  dirty: {dirty_count} file(s)")
        if dirty_count > 0 and status == "WARN":
            # Not a failure, just a warning
            pass

        # Ahead/behind (only if tracking a remote)
        tracking = _git(repo_path, ["rev-parse", "--abbrev-ref", "@{upstream}"])
        if tracking:
            ab = _git(repo_path, ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
            if ab:
                parts = ab.split()
                if len(parts) == 2:
                    ahead, behind = int(parts[0]), int(parts[1])
                    ab_status = "OK" if ahead == 0 and behind == 0 else "WARN"
                    print(
                        f"    {ab_status:4s}  ahead={ahead} behind={behind} (tracking {tracking})"
                    )
                else:
                    print("    WARN  could not parse ahead/behind")
        else:
            print("    SKIP  no upstream tracking branch")

        print()

    result_str = "PASS" if all_ok else "FAIL"
    print(f"  Result: {result_str}")
    return 0 if all_ok else 1


def _git(repo_path: Path, cmd_args: list[str]) -> str | None:
    """Run a git command in repo_path, return stdout or None on error."""
    try:
        result = subprocess.run(
            ["git"] + cmd_args,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
