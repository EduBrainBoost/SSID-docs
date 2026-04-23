"""Attachment Vault module — raw assets with hash + metadata.

Stores files in SSID_VAULT with hash tracking in index.jsonl.
NOT hash-only WORM — this stores actual files.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_file
from ssidctl.core.timeutil import utcnow_iso


class VaultError(Exception):
    pass


class AttachmentVault:
    def __init__(self, vault_dir: Path) -> None:
        self._dir = vault_dir
        self._index_path = vault_dir / "index.jsonl"

    @staticmethod
    def _utcnow() -> str:
        return utcnow_iso()

    @staticmethod
    def _hash_file(path: Path) -> str:
        return sha256_file(path)

    def add(
        self,
        source_path: Path,
        category: str = "attachments",
        mime: str = "application/octet-stream",
    ) -> dict[str, Any]:
        if not source_path.exists():
            raise VaultError(f"Source file not found: {source_path}")

        dest_dir = self._dir / category
        dest_dir.mkdir(parents=True, exist_ok=True)

        asset_id = f"V-{uuid.uuid4().hex[:8]}"
        dest_name = f"{asset_id}-{source_path.name}"
        dest_path = dest_dir / dest_name
        shutil.copy2(str(source_path), str(dest_path))

        file_hash = self._hash_file(dest_path)
        entry = {
            "asset_id": asset_id,
            "original_name": source_path.name,
            "path": f"vault://{category}/{dest_name}",
            "hash": file_hash,
            "mime": mime,
            "size_bytes": dest_path.stat().st_size,
            "created": self._utcnow(),
        }

        with open(self._index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")

        return entry

    def list_assets(self) -> list[dict[str, Any]]:
        if not self._index_path.exists():
            return []
        entries = []
        with open(self._index_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def retrieve(self, asset_id: str) -> tuple[Path, dict[str, Any]]:
        """Look up an asset by ID and return (file_path, metadata).

        Raises VaultError if asset not found or file missing on disk.
        """
        for entry in self.list_assets():
            if entry["asset_id"] == asset_id:
                # vault://category/filename -> category/filename
                rel = entry["path"].removeprefix("vault://")
                file_path = self._dir / rel
                if not file_path.exists():
                    raise VaultError(f"Asset file missing on disk: {file_path}")
                return file_path, entry
        raise VaultError(f"Asset not found: {asset_id}")

    def link(
        self,
        asset_id: str,
        task_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Link an asset to a task and/or run."""
        for entry in self.list_assets():
            if entry["asset_id"] == asset_id:
                link_entry = {
                    "asset_id": asset_id,
                    "task_id": task_id,
                    "run_id": run_id,
                    "linked_at": self._utcnow(),
                }
                links_path = self._dir / "links.jsonl"
                with open(links_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(link_entry, separators=(",", ":")) + "\n")
                return link_entry
        raise VaultError(f"Asset not found: {asset_id}")
