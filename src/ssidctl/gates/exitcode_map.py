"""Configurable exit code mapping for gate scripts.

Unknown exit codes always map to FAIL.
"""

from __future__ import annotations


def map_exit_code(exit_code: int, mapping: dict[int, str]) -> str:
    """Map a process exit code to PASS/FAIL using the gate's mapping.

    Unknown exit codes = FAIL (invariant).
    """
    return mapping.get(exit_code, "FAIL")
