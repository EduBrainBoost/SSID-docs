"""Deny Glob Registry — canonical unified deny-glob list across all repos.

Consolidates deny patterns from SSID, SSID-EMS, SSID-open-core, and SSID-docs
into a single authoritative registry.

Categories: SECRETS, PII, BINARY, INTERNAL, BUILD_ARTIFACTS, IDE, QUARANTINE.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class DenyCategory(StrEnum):
    """Categories of denied content."""

    SECRETS = "SECRETS"
    PII = "PII"
    BINARY = "BINARY"
    INTERNAL = "INTERNAL"
    BUILD_ARTIFACTS = "BUILD_ARTIFACTS"
    IDE = "IDE"
    QUARANTINE = "QUARANTINE"
    GIT = "GIT"


@dataclass(frozen=True)
class DenyGlob:
    """A single deny glob pattern with metadata."""

    pattern: str
    category: DenyCategory
    reason: str
    glob_id: str = ""


@dataclass(frozen=True)
class DenyVerdict:
    """Result of validating a path against deny globs."""

    decision: Literal["ALLOW", "DENY"]
    matched_glob: DenyGlob | None = None
    path: str = ""


# ---------------------------------------------------------------------------
# Canonical deny glob list (union of all repos)
# ---------------------------------------------------------------------------

DENY_GLOBS: list[DenyGlob] = [
    # SECRETS
    DenyGlob("*.pem", DenyCategory.SECRETS, "Private key / certificate"),
    DenyGlob("*.key", DenyCategory.SECRETS, "Private key file"),
    DenyGlob("*.p12", DenyCategory.SECRETS, "PKCS12 certificate store"),
    DenyGlob("*.pfx", DenyCategory.SECRETS, "PFX certificate"),
    DenyGlob("*.jks", DenyCategory.SECRETS, "Java keystore"),
    DenyGlob("*.keystore", DenyCategory.SECRETS, "Keystore file"),
    DenyGlob("*.env", DenyCategory.SECRETS, "Environment secrets"),
    DenyGlob(".env*", DenyCategory.SECRETS, "Dotenv variants"),
    DenyGlob("*.secrets", DenyCategory.SECRETS, "Secrets file"),
    DenyGlob("*.secret", DenyCategory.SECRETS, "Secret file"),
    DenyGlob("*.token", DenyCategory.SECRETS, "Token file"),
    DenyGlob("*credentials*", DenyCategory.SECRETS, "Credentials file"),
    DenyGlob("secrets/**", DenyCategory.SECRETS, "Secrets directory"),
    DenyGlob("**/secrets/**", DenyCategory.SECRETS, "Nested secrets directory"),
    # PII
    DenyGlob("**/pii/**", DenyCategory.PII, "PII data directory"),
    DenyGlob("**/personal_data/**", DenyCategory.PII, "Personal data directory"),
    # BINARY (forbidden types)
    DenyGlob("*.exe", DenyCategory.BINARY, "Windows executable"),
    DenyGlob("*.dll", DenyCategory.BINARY, "Windows DLL"),
    DenyGlob("*.so", DenyCategory.BINARY, "Shared object"),
    DenyGlob("*.dylib", DenyCategory.BINARY, "macOS dynamic library"),
    DenyGlob("*.bin", DenyCategory.BINARY, "Binary blob"),
    DenyGlob("*.dat", DenyCategory.BINARY, "Data blob"),
    DenyGlob("*.db", DenyCategory.BINARY, "Database file"),
    DenyGlob("*.sqlite", DenyCategory.BINARY, "SQLite database"),
    DenyGlob("*.sqlite3", DenyCategory.BINARY, "SQLite3 database"),
    DenyGlob("*.ipynb", DenyCategory.BINARY, "Jupyter notebook (may contain outputs)"),
    DenyGlob("*.parquet", DenyCategory.BINARY, "Parquet data file"),
    DenyGlob("*.pkl", DenyCategory.BINARY, "Pickle file (unsafe deserialization)"),
    DenyGlob("*.pickle", DenyCategory.BINARY, "Pickle file"),
    DenyGlob("*.zip", DenyCategory.BINARY, "Archive (may contain anything)"),
    DenyGlob("*.tar", DenyCategory.BINARY, "Tar archive"),
    DenyGlob("*.tar.gz", DenyCategory.BINARY, "Compressed tar"),
    DenyGlob("*.tgz", DenyCategory.BINARY, "Compressed tar"),
    DenyGlob("*.7z", DenyCategory.BINARY, "7-Zip archive"),
    DenyGlob("*.rar", DenyCategory.BINARY, "RAR archive"),
    # INTERNAL
    DenyGlob("internal-only/**", DenyCategory.INTERNAL, "Internal-only directory"),
    DenyGlob("**/internal-only/**", DenyCategory.INTERNAL, "Nested internal-only"),
    DenyGlob(".claude/**", DenyCategory.INTERNAL, "Claude config (internal)"),
    DenyGlob(".devcontainer/**", DenyCategory.INTERNAL, "Devcontainer config"),
    DenyGlob("registry/**/internal*", DenyCategory.INTERNAL, "Internal registry data"),
    # BUILD_ARTIFACTS
    DenyGlob("**/__pycache__/**", DenyCategory.BUILD_ARTIFACTS, "Python bytecode cache"),
    DenyGlob("**/*.pyc", DenyCategory.BUILD_ARTIFACTS, "Python compiled"),
    DenyGlob("**/node_modules/**", DenyCategory.BUILD_ARTIFACTS, "Node modules"),
    DenyGlob("**/dist/**", DenyCategory.BUILD_ARTIFACTS, "Build dist output"),
    DenyGlob("**/.pytest_cache/**", DenyCategory.BUILD_ARTIFACTS, "Pytest cache"),
    DenyGlob("**/.ruff_cache/**", DenyCategory.BUILD_ARTIFACTS, "Ruff cache"),
    DenyGlob("**/.mypy_cache/**", DenyCategory.BUILD_ARTIFACTS, "Mypy cache"),
    DenyGlob("**/.tox/**", DenyCategory.BUILD_ARTIFACTS, "Tox virtualenvs"),
    DenyGlob("**/coverage/**", DenyCategory.BUILD_ARTIFACTS, "Coverage reports"),
    DenyGlob("**/.coverage*", DenyCategory.BUILD_ARTIFACTS, "Coverage data"),
    DenyGlob("*.egg-info/**", DenyCategory.BUILD_ARTIFACTS, "Python egg info"),
    # IDE
    DenyGlob(".vscode/**", DenyCategory.IDE, "VS Code config"),
    DenyGlob(".idea/**", DenyCategory.IDE, "IntelliJ config"),
    DenyGlob("*.swp", DenyCategory.IDE, "Vim swap file"),
    DenyGlob("*.swo", DenyCategory.IDE, "Vim swap file"),
    DenyGlob(".DS_Store", DenyCategory.IDE, "macOS Finder metadata"),
    DenyGlob("Thumbs.db", DenyCategory.IDE, "Windows thumbnail cache"),
    # GIT
    DenyGlob("**/.git/**", DenyCategory.GIT, "Git internals"),
    DenyGlob("**/.gitmodules", DenyCategory.GIT, "Git submodules config"),
    # QUARANTINE
    DenyGlob("**/quarantine/**", DenyCategory.QUARANTINE, "Quarantine data"),
    DenyGlob("02_audit_logging/quarantine/**", DenyCategory.QUARANTINE, "SSID quarantine"),
    DenyGlob("**/malware_quarantine*/**", DenyCategory.QUARANTINE, "Malware quarantine"),
]

# Indexed by category for fast lookup
_BY_CATEGORY: dict[DenyCategory, list[DenyGlob]] = {}
for _g in DENY_GLOBS:
    _BY_CATEGORY.setdefault(_g.category, []).append(_g)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_path(path: str) -> DenyVerdict:
    """Check a path against the canonical deny glob registry.

    Returns ALLOW if no glob matches, DENY with the matching glob otherwise.
    """
    normalized = path.replace("\\", "/").lstrip("/")
    for glob in DENY_GLOBS:
        if fnmatch.fnmatch(normalized, glob.pattern):
            return DenyVerdict("DENY", glob, normalized)
        # Also check basename for simple patterns (no /)
        if "/" not in glob.pattern and fnmatch.fnmatch(
            normalized.rsplit("/", 1)[-1], glob.pattern
        ):
            return DenyVerdict("DENY", glob, normalized)
    return DenyVerdict("ALLOW", None, normalized)


def get_globs_by_category(category: DenyCategory) -> list[DenyGlob]:
    """Get all deny globs for a specific category."""
    return list(_BY_CATEGORY.get(category, []))


def to_json() -> str:
    """Export the full deny glob registry as JSON."""
    return json.dumps(
        [
            {"pattern": g.pattern, "category": str(g.category), "reason": g.reason}
            for g in DENY_GLOBS
        ],
        indent=2,
    )


def to_yaml_dict() -> list[dict[str, str]]:
    """Export as list of dicts suitable for YAML serialization."""
    return [
        {"pattern": g.pattern, "category": str(g.category), "reason": g.reason} for g in DENY_GLOBS
    ]
