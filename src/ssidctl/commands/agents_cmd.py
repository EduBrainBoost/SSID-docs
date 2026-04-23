"""CLI command: ssidctl agents (lock | install | verify | list)."""

import argparse
import subprocess
from pathlib import Path

from ssidctl.core.agent_registry import AgentRegistry


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("agents", help="Manage agent definitions")
    sub = parser.add_subparsers(dest="agents_action")

    sub.add_parser("lock", help="Generate agents.lock.json from .claude/agents/")
    sub.add_parser("verify", help="Verify agents.lock.json against agent files")
    sub.add_parser("list", help="List all registered agents")

    install_p = sub.add_parser("install", help="Install agents to target directory")
    install_p.add_argument(
        "--target",
        choices=["user"],
        default="user",
        help="Install target (default: user-level ~/.claude/agents/)",
    )

    parser.set_defaults(func=cmd_agents)


def _get_ems_git_sha(ems_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(ems_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def cmd_agents(args: argparse.Namespace, config) -> int:
    registry = AgentRegistry(ems_root=Path(config.paths.ems_repo))
    action = args.agents_action

    if action == "lock":
        sha = _get_ems_git_sha(registry.ems_root)
        _lockpath = registry.write_lockfile(ems_git_sha=sha)
        entries = registry.scan()
        print(f"PASS: agents.lock.json written ({len(entries)} agents, ems_sha={sha[:12]})")
        return 0

    elif action == "verify":
        # Verify lockfile hashes
        lock_result = registry.verify_lockfile()
        if lock_result.passed:
            print("PASS: All agent hashes match lockfile")
        else:
            for f in lock_result.findings:
                print(f"FAIL: {f}")

        # Verify canonical definitions
        defs_result = registry.verify_definitions()
        if defs_result.passed:
            print("PASS: All 11 agent definitions present in agents/definitions/")
        else:
            for f in defs_result.findings:
                print(f"FAIL: {f}")

        return 0 if (lock_result.passed and defs_result.passed) else 1

    elif action == "list":
        entries = registry.scan()
        for e in entries:
            print(f"  {e.agent_id:30s}  model={e.model:8s}  category={e.category}")
        return 0

    elif action == "install":
        if args.target == "user":
            target = Path.home() / ".claude" / "agents"
            target.mkdir(parents=True, exist_ok=True)
        else:
            print(f"FAIL: Unknown target {args.target}")
            return 1
        evidences = registry.install(target_dir=target)
        for ev in evidences:
            print(f"  Installed {ev['agent_id']} (sha={ev['agent_sha256'][:12]}...)")
        print(f"PASS: {len(evidences)} agents installed to {target}")
        return 0

    else:
        print("Usage: ssidctl agents {lock|verify|install|list}")
        return 1
