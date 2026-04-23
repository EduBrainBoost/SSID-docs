"""CLI command: ssidctl guard <subcommand>.

Reads JSON from stdin (Claude Code PreToolUse hook protocol).
Exits 0 (allow) or 2 (block, reason on stderr).

Hard mode (default): guards exit 2 on block.
Softmode: set SSIDCTL_GUARD_SOFT=1 → guards WARN+ALLOW (exit 0).
"""

import argparse
import json
import os
import sys

from ssidctl.core.guard_hooks import (
    guard_bash_allowlist,
    guard_board_scope,
    guard_ems_only,
    guard_gate_scope,
    guard_ops_scope,
    guard_pr_bash_scope,
    guard_pr_scope,
    guard_read_only,
    guard_write_scope,
)

# Softmode flag: when true, blocks are logged as warnings but allowed (exit 0)
# Default is hard mode (exit 2 on block). Set SSIDCTL_GUARD_SOFT=1 to warn-only.
_SOFT_MODE = os.environ.get("SSIDCTL_GUARD_SOFT", "0") == "1"


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("guard", help="Agent enforcement guards (PreToolUse hooks)")
    sub = parser.add_subparsers(dest="guard_action")

    sub.add_parser("read-only", help="Block all write/edit/bash operations")
    sub.add_parser("write-scope", help="Validate write paths against scope")
    sub.add_parser("bash-allowlist", help="Argv-aware bash command filtering")
    sub.add_parser("ems-only", help="Ensure writes target EMS only")
    sub.add_parser("gate-scope", help="Allow only gate commands")
    sub.add_parser("ops-scope", help="Allow only ops/health commands")
    sub.add_parser("board-scope", help="Allow only ssidctl board/calendar/memory")
    sub.add_parser("pr-scope", help="Allow only PR metadata writes")
    sub.add_parser("pr-bash-scope", help="Allow only git push/gh pr")

    parser.set_defaults(func=cmd_guard)


def _read_hook_input() -> dict:
    """Read JSON from stdin (Claude Code hook protocol)."""
    try:
        data = sys.stdin.read()
        if data.strip():
            return json.loads(data)
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _emit_result(result, action_name: str) -> int:
    """Emit guard result: exit 0 (allow) or exit 2 (block)."""
    if result.blocked:
        mode = "WARN" if _SOFT_MODE else "BLOCKED"
        print(f"[ssidctl guard {action_name}] {mode}: {result.reason}", file=sys.stderr)
        if _SOFT_MODE:
            return 0  # Softmode: warn but allow
        return 2
    return 0


def cmd_guard(args: argparse.Namespace, config) -> int:
    action = args.guard_action
    if not action:
        print("Usage: ssidctl guard {read-only|write-scope|bash-allowlist|...}", file=sys.stderr)
        return 1

    input_json = _read_hook_input()

    if action == "read-only":
        result = guard_read_only(input_json)
        return _emit_result(result, action)

    elif action == "write-scope":
        # Scope comes from environment or config
        scope_allow = os.environ.get("SSIDCTL_SCOPE_ALLOW", "**").split(",")
        scope_deny = os.environ.get("SSIDCTL_SCOPE_DENY", "").split(",")
        scope_deny = [d for d in scope_deny if d]
        scope = {"allow": scope_allow, "deny": scope_deny}
        result = guard_write_scope(input_json, scope)
        return _emit_result(result, action)

    elif action == "bash-allowlist":
        result = guard_bash_allowlist(input_json)
        return _emit_result(result, action)

    elif action == "ems-only":
        ems_root = str(config.paths.ems_repo) if hasattr(config, "paths") else ""
        result = guard_ems_only(input_json, ems_root=ems_root)
        return _emit_result(result, action)

    elif action == "gate-scope":
        result = guard_gate_scope(input_json)
        return _emit_result(result, action)

    elif action == "ops-scope":
        result = guard_ops_scope(input_json)
        return _emit_result(result, action)

    elif action == "board-scope":
        result = guard_board_scope(input_json)
        return _emit_result(result, action)

    elif action == "pr-scope":
        result = guard_pr_scope(input_json)
        return _emit_result(result, action)

    elif action == "pr-bash-scope":
        result = guard_pr_bash_scope(input_json)
        return _emit_result(result, action)

    else:
        print(f"Unknown guard action: {action}", file=sys.stderr)
        return 1
