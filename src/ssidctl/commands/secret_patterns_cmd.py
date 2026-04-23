#!/usr/bin/env python3
"""Export secret patterns to SSID repo as generated artifact.

Contract: generates EXACTLY 2 files, no consumer/QA changes.
- 03_core/security/ssid_security/secret_patterns.py
- 03_core/security/ssid_security/__init__.py
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import sys
from pathlib import Path

from ssidctl.core.secret_patterns import PATTERNS

_GENERATED_HEADER_MARKER = "GENERATED FILE"


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "export-secret-patterns",
        help="Export secret patterns to SSID as generated artifact (2 files only)",
    )
    p.add_argument(
        "--target-ssid",
        type=Path,
        required=True,
        help="Path to SSID repo root (or worktree)",
    )
    p.add_argument(
        "--mode",
        choices=["apply", "patch"],
        default="apply",
        help="apply: write files directly. patch: output unified diff to stdout.",
    )
    p.set_defaults(func=cmd_export_secret_patterns)


def _get_ems_commit() -> str:
    """Get current EMS repo HEAD commit (short)."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _compute_pattern_set_sha() -> str:
    """Compute deterministic hash of pattern set (id + regex only)."""
    data = json.dumps(
        [{"id": p["id"], "regex": p["regex"]} for p in PATTERNS],
        sort_keys=True,
    )
    return hashlib.sha256(data.encode()).hexdigest()


def _is_safe_to_overwrite(path: Path) -> bool:
    """SAFE-FIX: only overwrite if file is missing or has generated header."""
    if not path.exists():
        return True
    first_lines = path.read_text(encoding="utf-8", errors="replace")[:500]
    return _GENERATED_HEADER_MARKER in first_lines


def _generate_secret_patterns_py() -> str:
    """Generate the SSID-side secret_patterns.py content from EMS SoT."""
    now_utc = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    ems_commit = _get_ems_commit()
    pattern_set_sha = _compute_pattern_set_sha()

    # Build pattern entries using repr() for proper escaping
    pattern_lines = []
    for p in PATTERNS:
        pattern_lines.append(
            f"    {{\n"
            f'        "id": {repr(p["id"])},\n'
            f'        "name": {repr(p["name"])},\n'
            f'        "regex": {repr(p["regex"])},\n'
            f'        "replacement": {repr(p["replacement"])},\n'
            f"    }},"
        )

    patterns_block = "\n".join(pattern_lines)

    return (
        f"# {'=' * 70}\n"
        f"# GENERATED FILE — DO NOT EDIT MANUALLY\n"
        f"#\n"
        f"# GENERATED_BY=SSID-EMS\n"
        f"# EMS_COMMIT={ems_commit}\n"
        f"# GENERATED_AT={now_utc}\n"
        f"# PATTERN_SET_SHA256={pattern_set_sha}\n"
        f"#\n"
        f"# Source of Truth: SSID-EMS/src/ssidctl/core/secret_patterns.py\n"
        f"# To update: ssidctl export-secret-patterns --target-ssid <path>\n"
        f"# {'=' * 70}\n"
        f'"""Secret pattern definitions — generated from SSID-EMS.\n'
        f"\n"
        f"All secret-detection logic in SSID (redaction_filter, data_minimization)\n"
        f"MUST import from this module. No pattern duplication elsewhere.\n"
        f'"""\n'
        f"from __future__ import annotations\n"
        f"\n"
        f"import re\n"
        f"from typing import Any\n"
        f"\n"
        f'PATTERN_SET_SHA256 = "{pattern_set_sha}"\n'
        f"\n"
        f"PATTERNS: list[dict[str, Any]] = [\n"
        f"{patterns_block}\n"
        f"]\n"
        f"\n"
        f"# Pre-compiled patterns (module-level, no per-call compilation)\n"
        f"COMPILED: list[tuple[str, re.Pattern[str], str]] = [\n"
        f'    (p["id"], re.compile(p["regex"]), p["replacement"])\n'
        f"    for p in PATTERNS\n"
        f"]\n"
        f"\n"
        f"\n"
        f"def find(text: str) -> list[str]:\n"
        f'    """Return list of pattern IDs that match in text.\n'
        f"\n"
        f"    Does NOT return the matched token itself (data-minimization).\n"
        f'    """\n'
        f"    return [\n"
        f"        pattern_id\n"
        f"        for pattern_id, regex, _replacement in COMPILED\n"
        f"        if regex.search(text)\n"
        f"    ]\n"
        f"\n"
        f"\n"
        f"def redact(text: str) -> tuple[str, int]:\n"
        f'    """Redact all secret patterns in text.\n'
        f"\n"
        f"    Returns (redacted_text, redaction_count).\n"
        f"    Replaces entire match — no partial fragments remain.\n"
        f'    """\n'
        f"    count = 0\n"
        f"    result = text\n"
        f"    for _pattern_id, regex, replacement in COMPILED:\n"
        f"        result, n = regex.subn(replacement, result)\n"
        f"        count += n\n"
        f"    return result, count\n"
    )


def _generate_init_py() -> str:
    return (
        "# GENERATED FILE — DO NOT EDIT MANUALLY\n"
        "# Source of Truth: SSID-EMS/src/ssidctl/core/secret_patterns.py\n"
        '"""ssid_security — SSID central secret detection package (generated)."""\n'
        "from .secret_patterns import (\n"
        "    PATTERNS,\n"
        "    COMPILED,\n"
        "    PATTERN_SET_SHA256,\n"
        "    find,\n"
        "    redact,\n"
        ")\n"
        "\n"
        '__all__ = ["PATTERNS", "COMPILED", "PATTERN_SET_SHA256", "find", "redact"]\n'
    )


def _generate_unified_diff(target: Path, rel_path: Path, content: str) -> str:
    """Generate unified diff for a single file."""
    abs_path = target / rel_path
    if abs_path.exists():
        old = abs_path.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        old = []
    new = content.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            old,
            new,
            fromfile=f"a/{rel_path.as_posix()}",
            tofile=f"b/{rel_path.as_posix()}",
        )
    )


def cmd_export_secret_patterns(args, config) -> int:
    target = Path(args.target_ssid).resolve()

    # Validate target is SSID repo
    if not (target / ".git").exists() and not (target / "16_codex").exists():
        print(
            f"ERROR: {target} does not look like SSID repo (no .git or 16_codex)",
            file=sys.stderr,
        )
        return 1

    pkg_dir = target / "03_core" / "security" / "ssid_security"
    sp_path = pkg_dir / "secret_patterns.py"
    init_path = pkg_dir / "__init__.py"

    sp_content = _generate_secret_patterns_py()
    init_content = _generate_init_py()

    # SAFE-FIX: check before writing
    for p in (sp_path, init_path):
        if not _is_safe_to_overwrite(p):
            print(
                f"ERROR: SAFE-FIX blocked — {p} exists without generated header. Manual edit?",
                file=sys.stderr,
            )
            return 1

    if args.mode == "patch":
        rel_sp = Path("03_core") / "security" / "ssid_security" / "secret_patterns.py"
        rel_init = Path("03_core") / "security" / "ssid_security" / "__init__.py"
        diff = _generate_unified_diff(target, rel_sp, sp_content)
        diff += _generate_unified_diff(target, rel_init, init_content)
        if diff:
            print(diff)
        else:
            print("# No changes (files already up to date)")
        return 0

    # mode == "apply": write files directly
    pkg_dir.mkdir(parents=True, exist_ok=True)
    sp_path.write_text(sp_content, encoding="utf-8")
    init_path.write_text(init_content, encoding="utf-8")

    sp_hash = hashlib.sha256(sp_content.encode()).hexdigest()
    print(f"Exported secret_patterns.py to {sp_path}")
    print(f"Exported __init__.py to {init_path}")
    print(f"File SHA256: {sp_hash}")
    return 0
