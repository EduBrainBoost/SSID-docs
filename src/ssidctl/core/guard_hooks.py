"""Guard hooks for agent enforcement (PreToolUse protocol).

Each guard function receives a JSON dict (from Claude Code hook stdin)
and returns a GuardResult indicating whether the action is blocked.

Softmode: In the initial deployment, the CLI wrapper exits 0 (WARN+ALLOW)
instead of exit 2. After PR5 (lock hardening), the wrapper switches to exit 2.
"""

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import PurePosixPath, PureWindowsPath


@dataclass
class GuardResult:
    blocked: bool
    reason: str


# Shell operators that indicate command chaining or redirection
_BLOCKED_OPERATORS = {">", ">>", "|", "&", ";", "&&", "||"}

# Patterns always blocked regardless of allowlist
_BLOCKED_PATTERNS = [
    "Invoke-WebRequest",
    "-EncodedCommand",
]

# Read-only tools (no mutation)
_SAFE_TOOLS = {"Read", "Grep", "Glob"}

# Hard-deny paths (write-scope, Hardening B)
_HARD_DENY_PREFIXES = ["16_codex/", ".git/", ".github/"]


def _extract_binary(command: str) -> str:
    """Extract the first token (binary name) from a command string."""
    parts = command.strip().split()
    if not parts:
        return ""
    binary = parts[0]
    # Strip path prefix to get just the binary name
    binary = PurePosixPath(binary).name
    binary = PureWindowsPath(binary).name
    return binary


def _has_blocked_operator(command: str) -> str | None:
    """Check if command contains blocked shell operators. Returns operator or None."""
    # Check for double-char operators first
    for op in ("&&", "||", ">>"):
        if op in command:
            return op
    # Then single-char
    for op in ("|", ";", ">", "&"):
        # Skip & at end (background) or inside &&
        if op == "&" and "&&" in command:
            continue
        if op == ">" and ">>" in command:
            continue
        if op in command:
            return op
    return None


def _has_blocked_pattern(command: str) -> str | None:
    """Check if command contains explicitly blocked patterns."""
    for pattern in _BLOCKED_PATTERNS:
        if pattern.lower() in command.lower():
            return pattern
    return None


def _normalize_path(file_path: str) -> str:
    """Normalize a file path to forward-slash relative form."""
    p = file_path.replace("\\", "/")
    # Strip common repo prefixes to get relative path
    for prefix in [
        "C:/Users/bibel/SSID-Workspace/SSID-Arbeitsbereich/Github/SSID/",
        "C:/Users/bibel/SSID-Workspace/SSID-Arbeitsbereich/Github/SSID-EMS/",
    ]:
        if p.startswith(prefix):
            p = p[len(prefix) :]
            break
    return p


# === Guard Functions ===


def guard_read_only(input_json: dict) -> GuardResult:
    """Block all write/edit/bash-write operations. For read-only agents."""
    tool = input_json.get("tool_name", "")

    if tool in _SAFE_TOOLS:
        return GuardResult(blocked=False, reason="")

    if tool in ("Write", "Edit"):
        return GuardResult(blocked=True, reason=f"BLOCKED: read-only agent cannot use {tool}")

    if tool == "Bash":
        command = input_json.get("tool_input", {}).get("command", "")
        # Block any bash for read-only agents (they shouldn't have bash at all)
        return GuardResult(
            blocked=True, reason=f"BLOCKED: read-only agent cannot use Bash: {command[:60]}"
        )

    return GuardResult(blocked=False, reason="")


def guard_bash_allowlist(
    input_json: dict,
    allowed_binaries: list[str] | None = None,
) -> GuardResult:
    """Argv-aware bash guard. Checks binary, operators, blocked patterns."""
    if allowed_binaries is None:
        allowed_binaries = [
            "python",
            "git",
            "gh",
            "pytest",
            "opa",
            "conftest",
            "ruff",
            "mypy",
            "pnpm",
            "gitleaks",
            "semgrep",
            "ssidctl",
        ]

    command = input_json.get("tool_input", {}).get("command", "")

    # Check blocked patterns first
    blocked_pattern = _has_blocked_pattern(command)
    if blocked_pattern:
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: forbidden pattern '{blocked_pattern}' in command",
        )

    # Check blocked operators
    blocked_op = _has_blocked_operator(command)
    if blocked_op:
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: shell operator '{blocked_op}' not allowed (redirect/pipe/chain)",
        )

    # Check binary against allowlist
    binary = _extract_binary(command)
    if binary and binary not in allowed_binaries:
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: binary '{binary}' not in allowlist {allowed_binaries}",
        )

    return GuardResult(blocked=False, reason="")


def guard_write_scope(input_json: dict, scope: dict) -> GuardResult:
    """Validate write target path against TaskSpec scope.

    scope: {"allow": ["pattern/**"], "deny": ["pattern/**"]}
    Hard-deny: 16_codex/**, .git/**, .github/**
    """
    file_path = input_json.get("tool_input", {}).get("file_path", "")
    rel_path = _normalize_path(file_path)

    # Hard-deny paths (Hardening B)
    for prefix in _HARD_DENY_PREFIXES:
        if rel_path.startswith(prefix):
            return GuardResult(
                blocked=True,
                reason=f"BLOCKED: hard-deny path '{prefix}' (SoT/git protected)",
            )

    # Check explicit deny patterns
    for pattern in scope.get("deny", []):
        if fnmatch(rel_path, pattern):
            return GuardResult(
                blocked=True,
                reason=f"BLOCKED: path '{rel_path}' matches deny pattern '{pattern}'",
            )

    # Check allow patterns
    allow_patterns = scope.get("allow", [])
    if allow_patterns:
        for pattern in allow_patterns:
            if fnmatch(rel_path, pattern):
                return GuardResult(blocked=False, reason="")
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: path '{rel_path}' not in allowed scope",
        )

    return GuardResult(blocked=False, reason="")


def guard_ems_only(input_json: dict, ems_root: str = "") -> GuardResult:
    """Ensure writes only target SSID-EMS paths."""
    tool = input_json.get("tool_name", "")

    if tool in ("Write", "Edit"):
        file_path = input_json.get("tool_input", {}).get("file_path", "")
        normalized = file_path.replace("\\", "/")
        ems_normalized = ems_root.replace("\\", "/")
        if not normalized.startswith(ems_normalized):
            return GuardResult(
                blocked=True,
                reason=f"BLOCKED: write target not in EMS ({file_path[:60]})",
            )

    if tool == "Bash":
        command = input_json.get("tool_input", {}).get("command", "")
        # For bash in EMS-only mode, check for blocked operators
        blocked_op = _has_blocked_operator(command)
        if blocked_op:
            return GuardResult(
                blocked=True,
                reason=f"BLOCKED: shell operator '{blocked_op}' not allowed in EMS-only mode",
            )

    return GuardResult(blocked=False, reason="")


def guard_gate_scope(input_json: dict) -> GuardResult:
    """Allow only gate commands (pytest, sot_validator, gitleaks, etc.)."""
    command = input_json.get("tool_input", {}).get("command", "")

    # Check for blocked operators first
    blocked_op = _has_blocked_operator(command)
    if blocked_op:
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: shell operator '{blocked_op}' not allowed in gate-scope",
        )

    # Allowed gate binaries
    gate_binaries = [
        "python",
        "pytest",
        "git",
        "gitleaks",
        "semgrep",
        "opa",
        "conftest",
        "ruff",
        "mypy",
        "ssidctl",
        "where.exe",
        "pwsh",
    ]
    binary = _extract_binary(command)
    if binary and binary not in gate_binaries:
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: '{binary}' not allowed in gate-scope",
        )

    return GuardResult(blocked=False, reason="")


def guard_ops_scope(input_json: dict) -> GuardResult:
    """Allow only health-check commands (where, pwsh, ssidctl doctor, etc.)."""
    command = input_json.get("tool_input", {}).get("command", "")

    # Check for blocked operators first
    blocked_op = _has_blocked_operator(command)
    if blocked_op:
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: shell operator '{blocked_op}' not allowed in ops-scope",
        )

    # Allowed ops binaries
    ops_binaries = [
        "where.exe",
        "pwsh",
        "python",
        "git",
        "ssidctl",
        "gh",
        "node",
        "npm",
        "pnpm",
    ]
    binary = _extract_binary(command)
    if binary and binary not in ops_binaries:
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: '{binary}' not allowed in ops-scope",
        )

    return GuardResult(blocked=False, reason="")


def guard_board_scope(input_json: dict) -> GuardResult:
    """Allow only ssidctl board/calendar/memory commands."""
    command = input_json.get("tool_input", {}).get("command", "").strip()

    allowed_prefixes = [
        "ssidctl board",
        "ssidctl calendar",
        "ssidctl memory",
    ]
    if any(command.startswith(p) for p in allowed_prefixes):
        return GuardResult(blocked=False, reason="")

    return GuardResult(
        blocked=True,
        reason=f"BLOCKED: only ssidctl board/calendar/memory allowed, got: {command[:60]}",
    )


def guard_pr_scope(input_json: dict) -> GuardResult:
    """Allow only PR metadata file writes (not repo source files)."""
    file_path = input_json.get("tool_input", {}).get("file_path", "")
    rel_path = _normalize_path(file_path)

    # Block writes to repo source paths (anything that looks like a numbered root dir)
    if re.match(r"^\d{2}_", rel_path):
        return GuardResult(
            blocked=True,
            reason=f"BLOCKED: PR agent cannot write to repo source: {rel_path}",
        )

    # Hard-deny paths
    for prefix in _HARD_DENY_PREFIXES:
        if rel_path.startswith(prefix):
            return GuardResult(
                blocked=True,
                reason=f"BLOCKED: PR agent cannot write to {prefix}",
            )

    return GuardResult(blocked=False, reason="")


def guard_pr_bash_scope(input_json: dict) -> GuardResult:
    """Allow only git push and gh pr commands."""
    command = input_json.get("tool_input", {}).get("command", "").strip()

    allowed_prefixes = [
        "git push",
        "git checkout",
        "git branch",
        "git status",
        "git log",
        "git diff",
        "gh pr",
        "gh api",
    ]
    if any(command.startswith(p) for p in allowed_prefixes):
        return GuardResult(blocked=False, reason="")

    return GuardResult(
        blocked=True,
        reason=f"BLOCKED: only git push/gh pr allowed in pr-bash-scope, got: {command[:60]}",
    )
