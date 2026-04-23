"""ssidctl gates — run guards (Bootstrap) or full chain (Operate)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ssidctl.config import EMSConfig
from ssidctl.core.sanitizer import sanitize_findings
from ssidctl.gates.guards import (
    GuardResult,
    guard_anti_duplication,
    guard_forbidden_extensions,
    guard_forbidden_paths,
    guard_output_policy_lint,
    guard_registry_semantics,
    guard_root_24_lock,
    guard_secret_pii_scan,
    guard_sot_write_guard,
    guard_token_legal_lexicon,
)
from ssidctl.gates.matrix import load_matrix
from ssidctl.gates.runner import replay_gates, run_all_gates


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("gates", help="Run guards/gates")
    parser.add_argument("--guard", type=str, help="Run a specific guard by name")
    parser.add_argument("--all", action="store_true", help="Run all guards")
    parser.add_argument("--task-id", type=str, default="", help="Task ID for bootstrap exception")
    parser.add_argument("--replay", type=str, default=None, help="Replay gates from stored run ID")
    parser.set_defaults(func=cmd_gates)


def cmd_gates(args: argparse.Namespace, config: EMSConfig) -> int:
    if args.replay:
        return _replay_run(args.replay, config)

    if args.guard:
        return _run_single_guard(args.guard, args.task_id, config)

    if args.all:
        return _run_all_guards(args.task_id, config)

    # Default: run all guards
    return _run_all_guards(args.task_id, config)


def _replay_run(run_id: str, config: EMSConfig) -> int:
    try:
        results = replay_gates(run_id, config.paths.evidence_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    all_pass = True
    for gr in results:
        status = "PASS" if gr.result == "PASS" else "FAIL"
        print(f"  {status}  {gr.gate_name} (exit={gr.exit_code})")
        if gr.result != "PASS":
            all_pass = False
    return 0 if all_pass else 1


def _run_single_guard(name: str, task_id: str, config: EMSConfig) -> int:
    files = _collect_repo_files(config.paths.ssid_repo)
    result = _execute_guard(name, task_id, config, files)
    if result is None:
        print(f"Unknown guard: {name}", file=sys.stderr)
        return 1
    _print_guard_result(result)
    return 0 if result.passed else 1


def _run_all_guards(task_id: str, config: EMSConfig) -> int:
    matrix = load_matrix()
    is_bootstrap = config.mode == "bootstrap"
    all_pass = True
    files = _collect_repo_files(config.paths.ssid_repo)

    for guard_def in matrix.guards:
        if is_bootstrap and guard_def.bootstrap == "skipped":
            print(f"  SKIP  {guard_def.name} (bootstrap mode)")
            continue

        is_token_guard = guard_def.name == "token_legal_lexicon"
        if is_token_guard and not config.guards.token_legal_lexicon_enabled:
            print(f"  SKIP  {guard_def.name} (disabled)")
            continue

        result = _execute_guard(guard_def.name, task_id, config, files)
        if result:
            _print_guard_result(result)
            if not result.passed:
                all_pass = False

    if config.mode == "operate":
        print("\n--- Gates (Operate mode) ---")
        gate_results = run_all_gates(
            matrix.gates,
            config.paths.ssid_repo,
        )
        for gr in gate_results:
            status = "PASS" if gr.result == "PASS" else "FAIL"
            print(f"  {status}  {gr.gate_name} (exit={gr.exit_code})")
            if gr.result != "PASS":
                all_pass = False

    return 0 if all_pass else 1


def _collect_repo_files(repo_path: Path) -> list[str]:
    """Collect tracked AND untracked file paths from SSID repo for guard context.

    Uses --cached (tracked) + --others --exclude-standard (untracked but not
    gitignored) so that guards can detect newly created forbidden files that
    are not yet staged.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().splitlines() if f]
    except Exception:  # noqa: S110
        return []
    return []


def _execute_guard(
    name: str,
    task_id: str,
    config: EMSConfig,
    files: list[str] | None = None,
) -> GuardResult | None:
    if name == "root_24_lock":
        return guard_root_24_lock(config.paths.ssid_repo, task_id)
    elif name == "anti_duplication":
        return guard_anti_duplication(files or [], config.paths.ssid_repo)
    elif name == "forbidden_extensions":
        return guard_forbidden_extensions(files or [])
    elif name == "sot_write_guard":
        return guard_sot_write_guard(files or [])
    elif name == "secret_pii_scan":
        return guard_secret_pii_scan(files or [])
    elif name == "registry_semantics":
        return guard_registry_semantics(files or [])
    elif name == "token_legal_lexicon":
        return guard_token_legal_lexicon("")
    elif name == "forbidden_paths":
        return guard_forbidden_paths(files or [])
    elif name == "output_policy_lint":
        return guard_output_policy_lint("")
    else:
        return None


def _print_guard_result(result: GuardResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"  {status}  {result.guard_name}")
    if result.findings:
        sanitized = sanitize_findings(result.findings)
        for f in sanitized:
            print(f"         [{f['severity']}] {f['code']}: {f['summary']}")
