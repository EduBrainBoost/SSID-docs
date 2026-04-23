"""Write-gate — pre-apply import validation for patch diffs.

Validates:
1. All changed paths within TaskSpec allowed_paths
2. No forbidden file extensions
3. No root-level file creation (ROOT-24-LOCK)
4. TaskSpec must be present
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any


class WriteGateError(Exception):
    """Critical write-gate error (e.g., missing TaskSpec)."""


FORBIDDEN_EXTENSIONS = {".ipynb", ".parquet", ".sqlite", ".db", ".exe", ".dll", ".so"}
_DIFF_PATH_RE = re.compile(r"^[+-]{3} [ab]/(.+)$", re.MULTILINE)


def _extract_paths(diff_text: str) -> set[str]:
    """Extract unique file paths from unified diff."""
    paths = set()
    for match in _DIFF_PATH_RE.finditer(diff_text):
        p = match.group(1)
        if p != "/dev/null":
            paths.add(p)
    return paths


def validate_patch_import(diff_path: Path, taskspec: dict[str, Any] | None) -> dict[str, Any]:
    """Validate a patch diff against TaskSpec constraints.

    Returns: {"status": "PASS"|"FAIL", "findings": [...]}
    """
    if taskspec is None:
        raise WriteGateError("TaskSpec required for write-gate validation")
    if not diff_path.exists():
        raise WriteGateError(f"Diff file not found: {diff_path}")

    diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
    paths = _extract_paths(diff_text)
    allowed = taskspec.get("allowed_paths", [])
    findings: list[dict[str, str]] = []

    for p in sorted(paths):
        suffix = PurePosixPath(p).suffix.lower()
        if suffix in FORBIDDEN_EXTENSIONS:
            findings.append(
                {
                    "type": "forbidden_extension",
                    "detail": f"{p} has forbidden extension {suffix}",
                }
            )
            continue
        if "/" not in p:
            findings.append(
                {
                    "type": "root_level_violation",
                    "detail": f"{p} is at repository root (ROOT-24-LOCK)",
                }
            )
            continue
        in_allowlist = any(p.startswith(a) for a in allowed if a != ".") or "." in allowed
        if not in_allowlist:
            findings.append(
                {
                    "type": "outside_allowlist",
                    "detail": f"{p} not in allowed_paths {allowed}",
                }
            )

    return {"status": "PASS" if not findings else "FAIL", "findings": findings}
