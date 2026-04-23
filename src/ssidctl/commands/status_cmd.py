"""ssidctl status — agent heartbeats and system overview."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ssidctl.config import EMSConfig


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("status", help="Agent heartbeats and system overview")
    sub = parser.add_subparsers(dest="status_action")

    sub.add_parser("agents", help="Show agent heartbeat status")
    sub.add_parser("overview", help="System summary (repos, services, runs)")

    parser.set_defaults(func=cmd_status)


def cmd_status(args: argparse.Namespace, config: EMSConfig) -> int:
    if args.status_action == "agents":
        return _status_agents(config)
    elif args.status_action == "overview":
        return _status_overview(config)
    else:
        print("Usage: ssidctl status {agents|overview}", file=sys.stderr)
        return 1


def _status_agents(config: EMSConfig) -> int:
    """Show agent heartbeat status from state directory."""
    agents_dir = config.paths.state_dir / "agents"
    if not agents_dir.exists():
        # Fall back to reading agent definitions
        agents_dir_alt = config.paths.ems_repo / ".claude" / "agents"
        if agents_dir_alt.exists():
            print("  Registered agents (no heartbeat data):")
            for f in sorted(agents_dir_alt.glob("*.md")):
                print(f"    {f.stem:30s}  status=unknown")
            return 0
        print("  No agent state directory found.")
        return 0

    heartbeat_files = sorted(agents_dir.glob("*.json"))
    if not heartbeat_files:
        print("  No agent heartbeats found.")
        return 0

    print("  Agent heartbeats:")
    for hb_path in heartbeat_files:
        try:
            data = json.loads(hb_path.read_text(encoding="utf-8"))
            agent_id = data.get("agent_id", hb_path.stem)
            status = data.get("status", "unknown")
            last_seen = data.get("last_seen", "?")
            task = data.get("current_task", None)
            task_str = f"  task={task}" if task else ""
            print(f"    {agent_id:30s}  status={status:10s}  last_seen={last_seen}{task_str}")
        except (json.JSONDecodeError, OSError):
            print(f"    {hb_path.stem:30s}  status=error (corrupt heartbeat)")

    return 0


def _status_overview(config: EMSConfig) -> int:
    """System summary: repos, services, active runs."""
    print("  Repos:")
    for name in ("ssid_repo", "ems_repo"):
        repo_path = getattr(config.paths, name)
        exists = repo_path.exists()
        if exists:
            branch = _git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"]) or "?"
            sha = _git(repo_path, ["rev-parse", "--short", "HEAD"]) or "?"
            print(f"    {name:15s}  branch={branch:30s}  sha={sha}")
        else:
            print(f"    {name:15s}  NOT FOUND")

    # State directory summary
    print()
    print("  State:")
    state_dir = config.paths.state_dir
    if state_dir.exists():
        subdirs = sorted(d.name for d in state_dir.iterdir() if d.is_dir())
        print(f"    dir:    {state_dir}")
        print(f"    subdirs: {', '.join(subdirs) if subdirs else '(empty)'}")
    else:
        print(f"    FAIL  state_dir not found: {state_dir}")

    # Active runs
    print()
    print("  Runs:")
    runs_dir = config.paths.state_dir / "runs"
    if runs_dir.exists():
        run_dirs = sorted(d.name for d in runs_dir.iterdir() if d.is_dir())
        print(f"    total: {len(run_dirs)}")
        for rd in run_dirs[-5:]:
            status_path = runs_dir / rd / "status.json"
            if status_path.exists():
                try:
                    status_data = json.loads(status_path.read_text(encoding="utf-8"))
                    st = status_data.get("status", "?")
                    print(f"    {rd}  status={st}")
                except (json.JSONDecodeError, OSError):
                    print(f"    {rd}  status=unknown")
            else:
                print(f"    {rd}  status=no-status-file")
    else:
        print("    (no runs directory)")

    # Evidence summary
    print()
    print("  Evidence:")
    evidence_dir = config.paths.evidence_dir
    if evidence_dir.exists():
        evidence_runs = evidence_dir / "runs"
        if evidence_runs.exists():
            count = len([d for d in evidence_runs.iterdir() if d.is_dir()])
            print(f"    sealed runs: {count}")
        else:
            print("    sealed runs: 0")

        chain_path = evidence_dir / "hash_chain.json"
        if chain_path.exists():
            try:
                chain = json.loads(chain_path.read_text(encoding="utf-8"))
                print(f"    chain length: {len(chain)}")
            except (json.JSONDecodeError, OSError):
                print("    chain length: error")
        else:
            print("    chain length: 0 (no chain file)")
    else:
        print(f"    NOT FOUND: {evidence_dir}")

    # Orchestrator health (best-effort)
    print()
    print("  Services:")
    _check_service("orchestrator", "http://127.0.0.1:3210/api/health")
    _check_service("ems-backend", "http://127.0.0.1:8000/api/health")

    return 0


def _check_service(name: str, url: str) -> None:
    """Best-effort HTTP health check via curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "2", url],
            capture_output=True,
            text=True,
            timeout=5,
        )
        code = result.stdout.strip()
        status = "reachable" if code in ("200", "204") else f"http={code}"
        print(f"    {name:20s}  {status}")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        print(f"    {name:20s}  unreachable")


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
