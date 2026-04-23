"""Parse Claude CLI responses into structured plan/diff/audit YAML."""

from __future__ import annotations

import re
from typing import Any

import yaml


class ParseError(Exception):
    pass


def extract_yaml_blocks(text: str) -> list[dict[str, Any]]:
    """Extract YAML code blocks from Claude response text."""
    pattern = r"```(?:yaml|yml)\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    results = []
    for match in matches:
        try:
            parsed = yaml.safe_load(match)
            if isinstance(parsed, dict):
                results.append(parsed)
        except yaml.YAMLError:
            continue
    return results


def extract_diff_blocks(text: str) -> list[str]:
    """Extract unified diff blocks from Claude response text."""
    pattern = r"```(?:diff|patch)\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches


def parse_plan_response(text: str) -> dict[str, Any]:
    """Parse a planner role response.

    Expects structured YAML with plan steps.
    Returns dict with {steps, summary, ...} or raw text fallback.
    """
    blocks = extract_yaml_blocks(text)
    if blocks:
        return blocks[0]
    return {"raw_summary": text[:500], "structured": False}


def parse_audit_response(text: str) -> dict[str, Any]:
    """Parse an auditor role response.

    Expects PASS/FAIL with structured findings.
    """
    blocks = extract_yaml_blocks(text)
    if blocks:
        return blocks[0]

    # Fallback: detect PASS/FAIL from text
    text_upper = text.upper()
    if "PASS" in text_upper and "FAIL" not in text_upper:
        result = "PASS"
    elif "FAIL" in text_upper:
        result = "FAIL"
    else:
        result = "UNKNOWN"

    return {"result": result, "raw_summary": text[:500], "structured": False}
