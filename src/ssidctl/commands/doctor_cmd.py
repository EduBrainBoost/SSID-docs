"""ssidctl doctor — toolchain health check."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ssidctl.config import EMSConfig

_TOOLS_LOCK = Path(__file__).resolve().parent.parent.parent.parent / "tools.lock.json"


def _parse_version(text: str) -> tuple[int, ...] | None:
    """Extract version tuple from a version string like 'Python 3.11.2' or 'ruff 0.9.10'."""
    match = re.search(r"(\d+(?:\.\d+)+)", text)
    if not match:
        return None
    return tuple(int(x) for x in match.group(1).split("."))


def _version_gte(actual: tuple[int, ...], minimum: tuple[int, ...]) -> bool:
    """Check if actual version >= minimum version."""
    for a, m in zip(actual, minimum, strict=False):
        if a > m:
            return True
        if a < m:
            return False
    return len(actual) >= len(minimum)


def _run_tool_command(cmd: str) -> str:
    """Run a tool command, with python -m fallback for Windows PATH issues."""
    # Try direct command
    try:
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout.strip().split("\n")[0]
        if not out:
            out = result.stderr.strip().split("\n")[0]
        if out:
            return out
    except (FileNotFoundError, OSError):
        pass

    # Fallback: try as python -m module
    tool_name = cmd.split()[0]
    try:
        result = subprocess.run(
            [sys.executable, "-m", tool_name, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout.strip().split("\n")[0]
        if not out:
            out = result.stderr.strip().split("\n")[0]
        if out and "No module named" not in out:
            return out
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass

    return ""


_REQUIRED_PACKAGES = [
    "yaml",
    "jsonschema",
    "httpx",
    "click",
    "pydantic",
]


def _check_dependencies() -> list[str]:
    """Check that required Python packages are importable.

    Returns a list of human-readable strings describing any missing packages.
    An empty list means all dependencies are present.
    Uses builtins.__import__ so monkeypatching in tests works correctly.
    """
    import builtins

    findings: list[str] = []
    for pkg in _REQUIRED_PACKAGES:
        try:
            builtins.__import__(pkg)
        except ImportError:
            findings.append(f"Missing package: {pkg}")
    return findings


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("doctor", help="Toolchain health check")
    parser.set_defaults(func=cmd_doctor)


def cmd_doctor(args: argparse.Namespace, config: EMSConfig) -> int:
    lock_path = _TOOLS_LOCK
    if not lock_path.exists():
        print("tools.lock.json not found", file=sys.stderr)
        return 1

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    tools = lock.get("tools", {})
    all_ok = True

    print("  Tools:")
    for name, spec in tools.items():
        cmd = spec.get("command", "")
        min_ver = spec.get("min_version")
        optional = spec.get("optional", False)

        version_str = _run_tool_command(cmd)

        if not version_str:
            version_str = "not found"
            status = "SKIP" if optional else "FAIL"
            if not optional:
                all_ok = False
        elif min_ver:
            actual_ver = _parse_version(version_str)
            min_ver_tuple = _parse_version(min_ver)
            if actual_ver and min_ver_tuple:
                if _version_gte(actual_ver, min_ver_tuple):
                    status = "OK"
                else:
                    status = "WARN" if optional else "FAIL"
                    if not optional:
                        all_ok = False
            else:
                status = "OK"
        else:
            status = "OK"

        print(f"  {status:4s}  {name}: {version_str} (min: {min_ver})")

    # Check paths
    print()
    print("  Paths:")
    for name in ("ssid_repo", "ems_repo", "state_dir", "evidence_dir", "vault_dir"):
        p = getattr(config.paths, name)
        exists = p.exists()
        status = "OK" if exists else "FAIL"
        if not exists:
            all_ok = False
        print(f"  {status:4s}  {name}: {p}")

    # Check state subdirectories
    print()
    print("  State subdirs:")
    state_dir = config.paths.state_dir
    for sub in [
        "locks",
        "tasks",
        "worktrees",
        "board",
        "content",
        "team",
        "calendar",
        "memory",
        "runs",
        "approvals",
        "incidents",
    ]:
        sub_path = state_dir / sub
        exists = sub_path.exists()
        status = "OK" if exists else "FAIL"
        if not exists:
            all_ok = False
        print(f"  {status:4s}  state_dir/{sub}")

    # Repo health checks
    print()
    print("  Repo health:")
    for repo_name, repo_path in [
        ("ssid_repo", config.paths.ssid_repo),
        ("ems_repo", config.paths.ems_repo),
    ]:
        if not repo_path.exists():
            print(f"  SKIP  {repo_name}: path not found")
            continue

        git_dir = repo_path / ".git"
        if not git_dir.exists() and not (repo_path / "HEAD").exists():
            print(f"  FAIL  {repo_name}: not a git repo")
            all_ok = False
            continue

        # HEAD validity
        head_ok = False
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=10,
            )
            head_ok = result.returncode == 0 and len(result.stdout.strip()) == 40
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        status = "OK" if head_ok else "FAIL"
        if not head_ok:
            all_ok = False
        print(f"  {status:4s}  {repo_name}: HEAD valid")

        # Remote connectivity (just check remote exists)
        remote_ok = False
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=10,
            )
            remote_ok = result.returncode == 0 and "origin" in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        status = "OK" if remote_ok else "WARN"
        print(f"  {status:4s}  {repo_name}: remote configured")

        # Dirty files count
        dirty_count = 0
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                dirty_count = len([line for line in lines if line.strip()])
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        status = "OK" if dirty_count == 0 else "WARN"
        print(f"  {status:4s}  {repo_name}: {dirty_count} dirty file(s)")

    print()
    result_str = "PASS" if all_ok else "FAIL"
    print(f"  Result: {result_str}")
    return 0 if all_ok else 1
