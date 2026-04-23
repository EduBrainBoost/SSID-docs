"""Supply Chain Manifest — tracks cross-repo export operations.

Append-only manifest of all export operations with SHA256 chain verification.
Records: source_repo, target_repo, exported files, hashes, gate verdicts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportedFile:
    """Record of a single exported file."""

    rel_path: str
    sha256: str
    size_bytes: int


@dataclass
class ExportRecord:
    """Record of a single export operation."""

    export_id: str
    source_repo: str
    target_repo: str
    exported_files: list[ExportedFile] = field(default_factory=list)
    gate_verdict: str = ""  # PASS or BLOCKED
    gate_evidence_hash: str = ""
    operator: str = ""
    timestamp_utc: str = ""
    record_hash: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp_utc:
            self.timestamp_utc = _now_utc()

    def compute_hash(self) -> str:
        """Compute SHA256 hash of this record (excluding record_hash field)."""
        payload = json.dumps(
            {
                "export_id": self.export_id,
                "source_repo": self.source_repo,
                "target_repo": self.target_repo,
                "exported_files": [
                    {"rel_path": f.rel_path, "sha256": f.sha256, "size_bytes": f.size_bytes}
                    for f in self.exported_files
                ],
                "gate_verdict": self.gate_verdict,
                "gate_evidence_hash": self.gate_evidence_hash,
                "operator": self.operator,
                "timestamp_utc": self.timestamp_utc,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "export_id": self.export_id,
            "source_repo": self.source_repo,
            "target_repo": self.target_repo,
            "exported_files": [
                {"rel_path": f.rel_path, "sha256": f.sha256, "size_bytes": f.size_bytes}
                for f in self.exported_files
            ],
            "gate_verdict": self.gate_verdict,
            "gate_evidence_hash": self.gate_evidence_hash,
            "operator": self.operator,
            "timestamp_utc": self.timestamp_utc,
            "record_hash": self.record_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportRecord:
        files = [
            ExportedFile(f["rel_path"], f["sha256"], f["size_bytes"])
            for f in data.get("exported_files", [])
        ]
        return cls(
            export_id=data["export_id"],
            source_repo=data["source_repo"],
            target_repo=data["target_repo"],
            exported_files=files,
            gate_verdict=data.get("gate_verdict", ""),
            gate_evidence_hash=data.get("gate_evidence_hash", ""),
            operator=data.get("operator", ""),
            timestamp_utc=data.get("timestamp_utc", ""),
            record_hash=data.get("record_hash", ""),
        )


# ---------------------------------------------------------------------------
# Supply Chain Manifest
# ---------------------------------------------------------------------------


class SupplyChainManifest:
    """Append-only manifest of export operations with integrity verification."""

    def __init__(self, manifest_path: Path | None = None) -> None:
        """Initialize manifest.

        Args:
            manifest_path: Path to JSONL manifest file.
                If None, operates in-memory only.
        """
        self._path = manifest_path
        self._records: list[ExportRecord] = []
        if manifest_path and manifest_path.exists():
            self._load()

    def _load(self) -> None:
        """Load existing records from JSONL file."""
        if self._path is None or not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            self._records.append(ExportRecord.from_dict(data))

    def append_export_record(self, record: ExportRecord) -> ExportRecord:
        """Append a new export record.  Computes and sets record_hash.

        Args:
            record: The export record to append.

        Returns:
            The record with record_hash set.
        """
        record.record_hash = record.compute_hash()
        self._records.append(record)

        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"))
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        return record

    def verify_manifest_integrity(self) -> tuple[bool, list[str]]:
        """Verify SHA256 hashes of all records.

        Returns:
            (all_valid, list_of_error_descriptions)
        """
        errors: list[str] = []
        for i, record in enumerate(self._records):
            expected = record.compute_hash()
            if record.record_hash and record.record_hash != expected:
                errors.append(
                    f"Record {i} ({record.export_id}): "
                    f"hash mismatch expected={expected} got={record.record_hash}"
                )
        return len(errors) == 0, errors

    @property
    def records(self) -> list[ExportRecord]:
        """Return all records (read-only copy)."""
        return list(self._records)

    def get_latest(self, source_repo: str = "", target_repo: str = "") -> ExportRecord | None:
        """Get the most recent export record, optionally filtered."""
        filtered = self._records
        if source_repo:
            filtered = [r for r in filtered if r.source_repo == source_repo]
        if target_repo:
            filtered = [r for r in filtered if r.target_repo == target_repo]
        return filtered[-1] if filtered else None

    def to_json(self) -> str:
        """Serialize all records as JSON array."""
        return json.dumps([r.to_dict() for r in self._records], indent=2)

    def summary(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "total_records": len(self._records),
            "latest_export": self._records[-1].to_dict() if self._records else None,
            "repos_exported_to": list({r.target_repo for r in self._records}),
            "total_files_exported": sum(len(r.exported_files) for r in self._records),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
