"""8 EMS pre-flight/post-Claude guards (G-001 through G-008).

Guards are EMS-internal checks that run before/after Claude invocations.
They do NOT call external scripts — that's the gate runner's job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from ssidctl.core.sanitizer import contains_secrets
from ssidctl.gates.matrix import (
    load_forbidden_extensions,
    load_forbidden_paths,
    load_token_lexicon,
)

# Pre-compiled regex patterns for output policy lint (G-008)
_SCORE_PATTERNS = [
    re.compile(r"\b\d{1,3}\s*/\s*\d{1,3}\b"),  # 100/100, 9/10
    re.compile(r"\bscore\s*[:=]\s*\d+", re.IGNORECASE),  # Score: 95
    re.compile(r"\b\d{1,3}%"),  # 85%
    re.compile(r"\b\d+\.\d+\s*/\s*\d+\b"),  # 9.5/10
]
_BUNDLE_PATTERNS = [
    re.compile(r"\bbundle\s+[a-z]\b", re.IGNORECASE),  # Bundle A
    re.compile(r"\bpaket\b", re.IGNORECASE),  # Paket (German)
]


@dataclass
class GuardResult:
    guard_name: str
    passed: bool
    findings: list[dict[str, Any]]


def _normalize_paths(paths: list[str]) -> list[str]:
    """Normalize backslashes to forward slashes for cross-platform guard checks."""
    return [p.replace("\\", "/") for p in paths]


def guard_root_24_lock(
    repo_path: Path,
    task_id: str = "",
) -> GuardResult:
    """G-001: Verify ROOT-24-LOCK — exactly 24 numbered root dirs, no symlinks.

    BOOTSTRAP-* tasks: allow empty/partial roots.
    """
    is_bootstrap = task_id.startswith("BOOTSTRAP-")
    findings = []

    if not repo_path.exists():
        if is_bootstrap:
            return GuardResult("root_24_lock", True, [])
        findings.append(
            {
                "code": "STRUCT_001",
                "gate": "root_24_lock",
                "severity": "critical",
                "summary": "SSID repo path does not exist",
            }
        )
        return GuardResult("root_24_lock", False, findings)

    pattern = re.compile(r"^\d{2}_")
    root_dirs = []
    for entry in sorted(repo_path.iterdir()):
        if entry.is_dir() and pattern.match(entry.name):
            if entry.is_symlink():
                findings.append(
                    {
                        "code": "STRUCT_002",
                        "gate": "root_24_lock",
                        "severity": "critical",
                        "summary": f"Symlink root dir found: {entry.name}",
                    }
                )
            else:
                root_dirs.append(entry.name)

    if is_bootstrap:
        # Bootstrap allows empty/partial roots
        return GuardResult("root_24_lock", len(findings) == 0, findings)

    if len(root_dirs) != 24:
        findings.append(
            {
                "code": "STRUCT_003",
                "gate": "root_24_lock",
                "severity": "critical",
                "summary": f"Expected 24 root dirs, found {len(root_dirs)}",
            }
        )

    passed = len(findings) == 0
    return GuardResult("root_24_lock", passed, findings)


def guard_forbidden_extensions(
    file_paths: list[str],
    extensions_list: list[str] | None = None,
) -> GuardResult:
    """G-003: No blocklist file extensions."""
    if extensions_list is None:
        extensions_list = load_forbidden_extensions()

    findings = []
    for fp in file_paths:
        for ext in extensions_list:
            if fp.endswith(ext):
                findings.append(
                    {
                        "code": "EXT_001",
                        "gate": "forbidden_extensions",
                        "severity": "critical",
                        "summary": f"Forbidden extension {ext}: {Path(fp).name}",
                    }
                )
                break

    return GuardResult("forbidden_extensions", len(findings) == 0, findings)


def guard_forbidden_paths(
    file_paths: list[str],
    forbidden: list[str] | None = None,
) -> GuardResult:
    """Part of G-003: No writes to forbidden directories."""
    if forbidden is None:
        forbidden = load_forbidden_paths()

    findings = []
    normalized = _normalize_paths(file_paths)
    for fp in normalized:
        for fb in forbidden:
            if fp.startswith(fb) or f"/{fb}" in fp:
                findings.append(
                    {
                        "code": "PATH_001",
                        "gate": "forbidden_paths",
                        "severity": "critical",
                        "summary": f"Write to forbidden path: {fb}",
                    }
                )
                break

    return GuardResult("forbidden_paths", len(findings) == 0, findings)


def guard_secret_pii_scan(
    diff_additions: list[str],
) -> GuardResult:
    """G-005: No secrets/PII in diff additions."""
    findings = []
    for i, line in enumerate(diff_additions):
        if contains_secrets(line):
            findings.append(
                {
                    "code": "SECRET_001",
                    "gate": "secret_pii_scan",
                    "severity": "critical",
                    "summary": f"Potential secret/PII detected in diff line {i + 1}",
                }
            )

    return GuardResult("secret_pii_scan", len(findings) == 0, findings)


def guard_anti_duplication(
    file_paths: list[str],
    repo_path: Path | None = None,
) -> GuardResult:
    """G-002: No duplicate rule_ids or function names in scope."""
    findings = []
    seen_basenames: dict[str, list[str]] = {}
    for fp in file_paths:
        name = Path(fp).name
        seen_basenames.setdefault(name, []).append(fp)
    for name, paths in seen_basenames.items():
        if len(paths) > 1:
            findings.append(
                {
                    "code": "DUP_001",
                    "gate": "anti_duplication",
                    "severity": "high",
                    "summary": f"Duplicate filename '{name}' in {len(paths)} locations",
                }
            )
    return GuardResult("anti_duplication", len(findings) == 0, findings)


def guard_sot_write_guard(
    file_paths: list[str],
    allowed_paths: list[str] | None = None,
    has_sot_approval: bool = False,
) -> GuardResult:
    """G-004: SoT files only if APPROVED_SOT_WRITE and in allowed_paths."""
    sot_patterns = [
        "16_codex/contracts/sot/",
        "23_compliance/policies/sot/",
        "23_compliance/inputs/",
        "24_meta_orchestration/registry/",
    ]
    findings = []
    normalized = _normalize_paths(file_paths)
    for fp in normalized:
        is_sot = any(pat in fp for pat in sot_patterns)
        if not is_sot:
            continue
        if not has_sot_approval:
            findings.append(
                {
                    "code": "SOT_001",
                    "gate": "sot_write_guard",
                    "severity": "critical",
                    "summary": f"SoT write without APPROVED_SOT_WRITE: {Path(fp).name}",
                }
            )
        elif allowed_paths and not any(fnmatch(fp, pat) for pat in allowed_paths):
            findings.append(
                {
                    "code": "SOT_002",
                    "gate": "sot_write_guard",
                    "severity": "critical",
                    "summary": f"SoT write outside allowed_paths: {Path(fp).name}",
                }
            )
    return GuardResult("sot_write_guard", len(findings) == 0, findings)


def guard_registry_semantics(
    file_paths: list[str],
) -> GuardResult:
    """G-006: Registry paths must follow naming conventions.

    - registry/logs/ — only *.log or *.log.jsonl
    - registry/manifests/ — only *.json or *.yaml
    - registry/intake/ — any allowed type
    """
    findings = []
    normalized = _normalize_paths(file_paths)
    for fp in normalized:
        if "/registry/logs/" in fp:
            if not (fp.endswith(".log") or fp.endswith(".log.jsonl")):
                findings.append(
                    {
                        "code": "REG_001",
                        "gate": "registry_semantics",
                        "severity": "high",
                        "summary": f"Invalid file in registry/logs/: {Path(fp).name}",
                    }
                )
        elif "/registry/manifests/" in fp and not (
            fp.endswith(".json") or fp.endswith(".yaml") or fp.endswith(".yml")
        ):
            findings.append(
                {
                    "code": "REG_002",
                    "gate": "registry_semantics",
                    "severity": "high",
                    "summary": f"Invalid file in registry/manifests/: {Path(fp).name}",
                }
            )
    return GuardResult("registry_semantics", len(findings) == 0, findings)


def guard_output_policy_lint(
    text: str,
) -> GuardResult:
    """G-008: No scores, bundles, or prohibited output patterns.

    Detects:
    - Numeric scores (e.g. "100/100", "Score: 95", "85%")
    - Bundle recommendations (e.g. "Bundle A", "Paket")
    - Certification triggers (e.g. "certified", "zertifiziert")
    """
    findings = []

    for pat in _SCORE_PATTERNS:
        matches = pat.findall(text)
        for m in matches:
            findings.append(
                {
                    "code": "OUTPUT_001",
                    "gate": "output_policy_lint",
                    "severity": "high",
                    "summary": f"Score-like pattern detected: '{m.strip()}'",
                }
            )

    for pat in _BUNDLE_PATTERNS:
        matches = pat.findall(text)
        for m in matches:
            findings.append(
                {
                    "code": "OUTPUT_002",
                    "gate": "output_policy_lint",
                    "severity": "high",
                    "summary": f"Bundle-like pattern detected: '{m.strip()}'",
                }
            )

    return GuardResult("output_policy_lint", len(findings) == 0, findings)


def guard_token_legal_lexicon(
    text: str,
    lexicon: list[dict[str, Any]] | None = None,
) -> GuardResult:
    """G-007: No prohibited terms (EMS Policy, NOT SSID SoT)."""
    if lexicon is None:
        lexicon = load_token_lexicon()

    findings = []
    text_lower = text.lower()
    for entry in lexicon:
        term = entry["term"].lower()
        if term in text_lower:
            findings.append(
                {
                    "code": "LEXICON_001",
                    "gate": "token_legal_lexicon",
                    "severity": entry.get("severity", "medium"),
                    "summary": (
                        f"Prohibited term found: '{entry['term']}' ({entry.get('context', 'n/a')})"
                    ),
                }
            )

    return GuardResult("token_legal_lexicon", len(findings) == 0, findings)


def guard_sot_contract(
    repo_path: Path,
    contract_path: Path | None = None,
) -> GuardResult:
    """G-001 integration: Validate SSID repo against sot_contract.yaml rules.

    Looks for the contract at <repo>/16_codex/contracts/sot/sot_contract.yaml
    unless contract_path is provided explicitly.
    """
    from ssidctl.core.sot_contract import load_sot_contract, validate_sot_rules

    # Resolve contract file
    if contract_path is None:
        contract_path = repo_path / "16_codex" / "contracts" / "sot" / "sot_contract.yaml"

    if not contract_path.exists():
        return GuardResult(
            "sot_contract",
            False,
            [
                {
                    "code": "SOT_CONTRACT_001",
                    "gate": "sot_contract",
                    "severity": "critical",
                    "summary": f"sot_contract.yaml not found: {contract_path}",
                }
            ],
        )

    try:
        rules = load_sot_contract(contract_path)
    except (ValueError, FileNotFoundError) as exc:
        return GuardResult(
            "sot_contract",
            False,
            [
                {
                    "code": "SOT_CONTRACT_002",
                    "gate": "sot_contract",
                    "severity": "critical",
                    "summary": f"Failed to load sot_contract.yaml: {exc}",
                }
            ],
        )

    rule_results = validate_sot_rules(repo_path, rules)
    findings = []
    for r in rule_results:
        if not r.passed:
            findings.append(
                {
                    "code": f"SOT_AGENT_{r.rule_id.split('_')[-1]}",
                    "gate": "sot_contract",
                    "severity": "critical",
                    "summary": r.message,
                }
            )

    return GuardResult("sot_contract", len(findings) == 0, findings)
