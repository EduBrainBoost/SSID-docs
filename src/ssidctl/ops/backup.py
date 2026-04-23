"""Backup & Recovery — operational backup procedures.

Creates point-in-time backups of EMS state, evidence, and configuration.
Supports full backup mode with SHA-256 integrity verification.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class BackupError(Exception):
    pass


def _safe_extractall(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract tar archive with path traversal protection.

    Blocks:
    - Members with absolute paths
    - Members containing '..' (path traversal)
    - Symlinks and hardlinks pointing outside dest
    """
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        # Block absolute paths
        if member.name.startswith(("/", "\\")):
            raise BackupError(f"Absolute path in archive: {member.name}")
        # Block path traversal
        if ".." in member.name.split("/") or ".." in member.name.split("\\"):
            raise BackupError(f"Path traversal in archive: {member.name}")
        # Verify resolved path stays within dest
        target = (dest / member.name).resolve()
        if not str(target).startswith(str(dest_resolved)):
            raise BackupError(f"Path escape in archive: {member.name}")
        # Block symlinks/hardlinks pointing outside dest
        if member.issym() or member.islnk():
            raise BackupError(f"Symlink/hardlink in archive not allowed: {member.name}")
    tar.extractall(path=dest)  # noqa: S202


@dataclass
class BackupConfig:
    """Backup configuration."""

    source_dirs: list[Path] = field(default_factory=list)
    backup_dir: Path = Path("backups")
    retention_days: int = 90


class BackupManager:
    """Manages backup creation, verification, and lifecycle."""

    def __init__(self, config: BackupConfig) -> None:
        self._config = config
        self._config.backup_dir.mkdir(parents=True, exist_ok=True)

    def _utcnow(self) -> str:
        return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    def _manifest_path(self, backup_id: str) -> Path:
        return self._config.backup_dir / backup_id / "manifest.json"

    def create_backup(self, mode: str = "full") -> dict[str, Any]:
        """Create a timestamped backup of all source directories.

        Args:
            mode: "full" (default) creates a complete backup.

        Returns:
            Backup metadata including ID, paths, and checksums.
        """
        backup_id = f"backup-{self._utcnow()}"
        backup_path = self._config.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        checksums: dict[str, str] = {}
        file_count = 0

        for source_dir in self._config.source_dirs:
            if not source_dir.exists():
                continue
            archive_name = source_dir.name + ".tar.gz"
            archive_path = backup_path / archive_name
            with tarfile.open(archive_path, "w:gz") as tar:
                for item in source_dir.rglob("*"):
                    if item.is_file():
                        tar.add(item, arcname=item.relative_to(source_dir))
                        file_count += 1
            file_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            checksums[archive_name] = f"sha256:{file_hash}"

        manifest = {
            "backup_id": backup_id,
            "mode": mode,
            "created": self._utcnow(),
            "source_dirs": [str(d) for d in self._config.source_dirs],
            "file_count": file_count,
            "checksums": checksums,
        }

        manifest_path = self._manifest_path(backup_id)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return manifest

    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups with metadata."""
        backups: list[dict[str, Any]] = []
        if not self._config.backup_dir.exists():
            return backups
        for entry in sorted(self._config.backup_dir.iterdir()):
            manifest_path = entry / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                backups.append(manifest)
        return backups

    def restore(self, backup_id: str, target_dir: Path) -> dict[str, Any]:
        """Restore from a backup to a target directory.

        Args:
            backup_id: ID of the backup to restore.
            target_dir: Directory to restore into.

        Returns:
            Restore metadata.
        """
        backup_path = self._config.backup_dir / backup_id
        manifest_path = self._manifest_path(backup_id)
        if not manifest_path.exists():
            raise BackupError(f"Backup not found: {backup_id}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        target_dir.mkdir(parents=True, exist_ok=True)
        restored: list[str] = []

        for archive_name in manifest.get("checksums", {}):
            archive_path = backup_path / archive_name
            if not archive_path.exists():
                raise BackupError(f"Archive missing: {archive_path}")
            dest = target_dir / archive_name.replace(".tar.gz", "")
            dest.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive_path, "r:gz") as tar:
                _safe_extractall(tar, dest)
            restored.append(archive_name)

        return {
            "backup_id": backup_id,
            "target_dir": str(target_dir),
            "restored_archives": restored,
            "restored_at": self._utcnow(),
        }

    def verify_backup(self, backup_id: str) -> dict[str, Any]:
        """Verify backup integrity via SHA-256 checksums."""
        manifest_path = self._manifest_path(backup_id)
        if not manifest_path.exists():
            raise BackupError(f"Backup not found: {backup_id}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        results: dict[str, bool] = {}
        all_valid = True

        for archive_name, expected_hash in manifest.get("checksums", {}).items():
            archive_path = self._config.backup_dir / backup_id / archive_name
            if not archive_path.exists():
                results[archive_name] = False
                all_valid = False
                continue
            actual = f"sha256:{hashlib.sha256(archive_path.read_bytes()).hexdigest()}"
            valid = actual == expected_hash
            results[archive_name] = valid
            if not valid:
                all_valid = False

        return {
            "backup_id": backup_id,
            "valid": all_valid,
            "file_checks": results,
        }

    def cleanup_expired(self) -> int:
        """Remove backups older than retention_days. Returns count removed."""
        cutoff = datetime.now(UTC) - timedelta(days=self._config.retention_days)
        removed = 0
        for backup in self.list_backups():
            created_str = backup.get("created", "")
            try:
                created = datetime.strptime(created_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            except ValueError:
                continue
            if created < cutoff:
                backup_path = self._config.backup_dir / backup["backup_id"]
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                    removed += 1
        return removed
