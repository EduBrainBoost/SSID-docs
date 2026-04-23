"""Public export pipeline — sanitized SSID → open-core.

Walks the SSID repo, filters through export policy (deny globs, secret scan),
sanitizes text files, computes integrity manifest, and optionally creates
a PR to SSID-open-core.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import yaml

from ssidctl.core.hashing import sha256_file
from ssidctl.core.sanitizer import sanitize_text
from ssidctl.core.secret_patterns import find as find_secrets
from ssidctl.core.timeutil import utcnow_iso

# Text file extensions that should be sanitized
_TEXT_EXTENSIONS = frozenset(
    {
        ".py",
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".txt",
        ".toml",
        ".cfg",
        ".ini",
        ".rst",
        ".csv",
        ".html",
        ".css",
        ".js",
        ".sh",
        ".bash",
        ".ps1",
        ".bat",
        ".cmd",
    }
)

# Allowed binary extensions for pass-through (images, docs)
_ALLOWED_BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".pdf",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
    }
)

# Explicitly denied binary extensions (dangerous / opaque)
_DENIED_BINARY_EXTENSIONS = frozenset(
    {
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".msi",
        ".zip",
        ".tar",
        ".gz",
        ".7z",
        ".rar",
        ".bz2",
        ".xz",
        ".p12",
        ".jks",
        ".pfx",
        ".pem",
        ".key",
        ".class",
        ".jar",
        ".war",
        ".pyc",
        ".pyo",
        ".o",
        ".a",
        ".lib",
        ".obj",
    }
)

# Maximum file size for export (10 MB)
_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


@dataclass
class ExportPolicy:
    """Parsed export policy from opencore_export_policy.yaml."""

    version: str
    source_repo: str
    target_repo: str
    deny_globs: list[str]
    secret_scan_regex: list[str]

    @classmethod
    def from_file(cls, path: Path) -> ExportPolicy:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return cls(
            version=raw.get("version", "1.0.0"),
            source_repo=raw.get("source_repo", "SSID"),
            target_repo=raw.get("target_repo", "SSID-open-core"),
            deny_globs=raw.get("deny_globs", []),
            secret_scan_regex=raw.get("secret_scan_regex", []),
        )


@dataclass
class ExportEntry:
    """A single file in the export manifest."""

    rel_path: str
    sha256: str
    sanitized: bool
    size_bytes: int


@dataclass
class ExportResult:
    """Result of an export run."""

    timestamp: str
    policy_version: str
    entries: list[ExportEntry] = field(default_factory=list)
    denied: list[str] = field(default_factory=list)
    secret_blocked: list[str] = field(default_factory=list)
    binary_blocked: list[str] = field(default_factory=list)
    oversized: list[str] = field(default_factory=list)
    total_files: int = 0
    exported_files: int = 0


class ExportPipeline:
    """Orchestrates sanitized export from SSID to open-core."""

    def __init__(
        self,
        source_repo: Path,
        policy_path: Path,
        staging_dir: Path,
    ) -> None:
        self._source = source_repo
        self._policy = ExportPolicy.from_file(policy_path)
        self._staging = staging_dir

    def _is_denied(self, rel_path: str) -> bool:
        """Check if a relative path matches any deny glob."""
        normalized = rel_path.replace("\\", "/")
        return any(fnmatch(normalized, g) for g in self._policy.deny_globs)

    def _is_text_file(self, path: Path) -> bool:
        return path.suffix.lower() in _TEXT_EXTENSIONS

    def run(self, dry_run: bool = False) -> ExportResult:
        """Execute the export pipeline.

        Args:
            dry_run: If True, only compute what would be exported without copying.

        Returns:
            ExportResult with manifest of exported/denied files.
        """
        result = ExportResult(
            timestamp=utcnow_iso(),
            policy_version=self._policy.version,
        )

        # Walk source repo (skip .git and hidden dirs)
        all_files = self._collect_files()
        result.total_files = len(all_files)

        if not dry_run:
            self._staging.mkdir(parents=True, exist_ok=True)

        for rel_path in all_files:
            source_path = self._source / rel_path

            # Check deny globs
            if self._is_denied(rel_path):
                result.denied.append(rel_path)
                continue

            # Check file size cap
            try:
                file_stat_size = source_path.stat().st_size
            except OSError:
                continue
            if file_stat_size > _MAX_FILE_SIZE_BYTES:
                result.oversized.append(rel_path)
                continue

            # For text files: check secrets and sanitize
            if self._is_text_file(source_path):
                try:
                    content = source_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    # Skip files that can't be read as text
                    continue

                # Hard-block on actual secrets (tokens/keys).
                # PII (paths, emails) passes through — sanitize_text handles it.
                secret_hits = find_secrets(content)
                if secret_hits:
                    result.secret_blocked.append(rel_path)
                    continue

                sanitized = sanitize_text(content)
                was_sanitized = sanitized.redacted

                if not dry_run:
                    dest = self._staging / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(sanitized.text, encoding="utf-8")
            else:
                # Binary file — enforce extension allowlist
                ext = source_path.suffix.lower()
                if ext in _DENIED_BINARY_EXTENSIONS:
                    result.binary_blocked.append(rel_path)
                    continue
                if ext not in _ALLOWED_BINARY_EXTENSIONS:
                    result.binary_blocked.append(rel_path)
                    continue

                was_sanitized = False
                if not dry_run:
                    dest = self._staging / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest)

            # Compute hash from staged file (or source if dry-run)
            if dry_run:
                file_hash = sha256_file(source_path)
                file_size = source_path.stat().st_size
            else:
                dest = self._staging / rel_path
                file_hash = sha256_file(dest)
                file_size = dest.stat().st_size

            result.entries.append(
                ExportEntry(
                    rel_path=rel_path,
                    sha256=file_hash,
                    sanitized=was_sanitized,
                    size_bytes=file_size,
                )
            )

        result.exported_files = len(result.entries)
        return result

    def _collect_files(self) -> list[str]:
        """Collect all non-hidden files from source repo."""
        files: list[str] = []
        for path in sorted(self._source.rglob("*")):
            if not path.is_file():
                continue
            # Skip .git directory and other hidden paths
            parts = path.relative_to(self._source).parts
            if any(p.startswith(".") for p in parts):
                continue
            files.append(str(path.relative_to(self._source)).replace("\\", "/"))
        return files

    def write_manifest(self, result: ExportResult, output_path: Path) -> None:
        """Write export manifest to JSON file."""
        manifest = {
            "timestamp": result.timestamp,
            "policy_version": result.policy_version,
            "total_files_scanned": result.total_files,
            "exported_files": result.exported_files,
            "denied_count": len(result.denied),
            "secret_blocked_count": len(result.secret_blocked),
            "binary_blocked_count": len(result.binary_blocked),
            "oversized_count": len(result.oversized),
            "max_file_size_bytes": _MAX_FILE_SIZE_BYTES,
            "entries": [
                {
                    "path": e.rel_path,
                    "sha256": e.sha256,
                    "sanitized": e.sanitized,
                    "size_bytes": e.size_bytes,
                }
                for e in result.entries
            ],
            "denied_paths": result.denied,
            "secret_blocked_paths": result.secret_blocked,
            "binary_blocked_paths": result.binary_blocked,
            "oversized_paths": result.oversized,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
