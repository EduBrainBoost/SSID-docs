"""Hash-only WORM evidence store.

Evidence lives at SSID_EVIDENCE/runs/{run_id}/ (external to both repos).
Each run directory contains:
  - manifest.json: Hashes + metadata (no raw text)
  - gate_report.json: PASS/FAIL + sanitized findings
  - SEALED: Immutability sentinel (once written, run is sealed)

An append-only index.jsonl tracks all runs.

FORBIDDEN in evidence: patch.diff, prompt text, response text, stdout/stderr.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_bytes, sha256_file, sha256_str
from ssidctl.core.timeutil import utcnow_iso

# Canonical ID pattern — DO NOT REMOVE (baseline-locked hardening)
_VALID_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class EvidenceError(Exception):
    """Raised on evidence store violations."""


def _validate_id(value: str, label: str = "id") -> str:
    """Validate that an ID is safe for use as a filesystem path component."""
    if not value or not _VALID_ID_RE.match(value):
        raise EvidenceError(f"Invalid {label}: {value!r} — must match {_VALID_ID_RE.pattern}")
    if ".." in value or "/" in value or "\\" in value:
        raise EvidenceError(f"Invalid {label}: {value!r} — path traversal not allowed")
    return value


class EvidenceStore:
    """WORM evidence store with hash-only policy."""

    def __init__(self, evidence_dir: Path) -> None:
        self._base = evidence_dir
        self._runs_dir = evidence_dir / "runs"
        self._index_path = evidence_dir / "index.jsonl"
        self._hash_chain_path = evidence_dir / "hash_chain.json"

    @property
    def base_dir(self) -> Path:
        return self._base

    def _run_dir(self, run_id: str) -> Path:
        _validate_id(run_id, "run_id")
        return self._runs_dir / run_id

    @staticmethod
    def _utcnow() -> str:
        return utcnow_iso()

    def create_run(
        self,
        run_id: str,
        task_id: str,
        ems_version: str,
        worktree_base_commit: str,
        prompt_sha256: str,
        prompt_bytes_len: int,
        toolchain_hash: str,
    ) -> Path:
        """Create a new evidence run directory with initial manifest.

        Returns:
            Path to the run directory.

        Raises:
            EvidenceError: If run already exists.
        """
        run_dir = self._run_dir(run_id)
        if run_dir.exists():
            raise EvidenceError(f"Run already exists: {run_id}")

        run_dir.mkdir(parents=True)

        manifest = {
            "run_id": run_id,
            "task_id": task_id,
            "ems_version": ems_version,
            "timestamp_start": self._utcnow(),
            "timestamp_end": None,
            "lifecycle_status": "APPLYING",
            "worktree_base_commit": worktree_base_commit,
            "result_commit_sha": None,
            "prompt_sha256": prompt_sha256,
            "prompt_bytes_len": prompt_bytes_len,
            "response_sha256": None,
            "response_bytes_len": None,
            "diff_sha256": None,
            "diff_bytes_len": None,
            "toolchain_hash": toolchain_hash,
            "overall_result": None,
        }

        self._write_json(run_dir / "manifest.json", manifest)
        return run_dir

    def finalize_run(
        self,
        run_id: str,
        result_commit_sha: str | None,
        response_sha256: str,
        response_bytes_len: int,
        diff_sha256: str | None,
        diff_bytes_len: int | None,
        overall_result: str,
        lifecycle_status: str = "DONE",
    ) -> None:
        """Finalize a run: update manifest, seal.

        Raises:
            EvidenceError: If run doesn't exist or is already sealed.
        """
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            raise EvidenceError(f"Run not found: {run_id}")
        if self.is_sealed(run_id):
            raise EvidenceError(f"Run already sealed: {run_id}")

        manifest = self._read_json(run_dir / "manifest.json")
        manifest["timestamp_end"] = self._utcnow()
        manifest["lifecycle_status"] = lifecycle_status
        manifest["result_commit_sha"] = result_commit_sha
        manifest["response_sha256"] = response_sha256
        manifest["response_bytes_len"] = response_bytes_len
        manifest["diff_sha256"] = diff_sha256
        manifest["diff_bytes_len"] = diff_bytes_len
        manifest["overall_result"] = overall_result

        self._write_json(run_dir / "manifest.json", manifest)

    def write_gate_report(
        self,
        run_id: str,
        findings: list[dict[str, Any]],
        overall_result: str,
    ) -> None:
        """Write sanitized gate report.

        All findings must already be sanitized (redacted=true).

        Raises:
            EvidenceError: If run doesn't exist or is already sealed.
        """
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            raise EvidenceError(f"Run not found: {run_id}")
        if self.is_sealed(run_id):
            raise EvidenceError(f"Run already sealed: {run_id}")

        # Enforce sanitization
        for f in findings:
            if not f.get("redacted", False):
                raise EvidenceError(
                    f"Finding not sanitized (redacted!=true): {f.get('code', '?')}"
                )

        report = {
            "run_id": run_id,
            "timestamp": self._utcnow(),
            "overall_result": overall_result,
            "findings": findings,
        }
        self._write_json(run_dir / "gate_report.json", report)

    def seal(self, run_id: str) -> None:
        """Seal a run — makes it immutable.

        Writes SEALED sentinel file, appends to index, and extends hash chain.

        Raises:
            EvidenceError: If already sealed or run doesn't exist.
        """
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            raise EvidenceError(f"Run not found: {run_id}")
        if self.is_sealed(run_id):
            raise EvidenceError(f"Run already sealed: {run_id}")

        sentinel = run_dir / "SEALED"
        sentinel.write_text(self._utcnow(), encoding="utf-8")

        # Append to index (read file once, hash + parse)
        raw = (run_dir / "manifest.json").read_bytes()
        manifest_hash = sha256_bytes(raw)
        manifest = json.loads(raw)
        index_entry = {
            "run_id": run_id,
            "task_id": manifest.get("task_id"),
            "sealed_at": self._utcnow(),
            "overall_result": manifest.get("overall_result"),
            "manifest_hash": manifest_hash,
        }
        with open(self._index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(index_entry, separators=(",", ":")) + "\n")

        # Extend hash chain (inter-run cryptographic linking)
        self._append_hash_chain(run_id, manifest_hash)

    def is_sealed(self, run_id: str) -> bool:
        return (self._run_dir(run_id) / "SEALED").exists()

    def get_manifest(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            raise EvidenceError(f"Run not found: {run_id}")
        return self._read_json(run_dir / "manifest.json")

    def get_gate_report(self, run_id: str) -> dict[str, Any] | None:
        path = self._run_dir(run_id) / "gate_report.json"
        if not path.exists():
            return None
        return self._read_json(path)

    def list_runs(self) -> list[dict[str, Any]]:
        """List all runs from the index."""
        if not self._index_path.exists():
            return []
        entries = []
        with open(self._index_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def verify(self, run_id: str) -> dict[str, Any]:
        """Verify integrity of a sealed run.

        Returns dict with {valid: bool, checks: {...}}.
        """
        run_dir = self._run_dir(run_id)
        checks = {}

        checks["exists"] = run_dir.exists()
        if not checks["exists"]:
            return {"valid": False, "checks": checks}

        checks["sealed"] = self.is_sealed(run_id)
        checks["manifest_exists"] = (run_dir / "manifest.json").exists()

        if checks["manifest_exists"]:
            manifest = self._read_json(run_dir / "manifest.json")
            checks["has_overall_result"] = manifest.get("overall_result") is not None
            checks["no_raw_text"] = all(
                key not in manifest
                for key in ("prompt_text", "response_text", "diff_text", "stdout", "stderr")
            )
        else:
            checks["has_overall_result"] = False
            checks["no_raw_text"] = True

        gate_path = run_dir / "gate_report.json"
        checks["gate_report_exists"] = gate_path.exists()
        if checks["gate_report_exists"]:
            report = self._read_json(gate_path)
            findings = report.get("findings", [])
            checks["all_findings_redacted"] = all(f.get("redacted", False) for f in findings)
        else:
            checks["all_findings_redacted"] = True

        valid = all(checks.values())
        return {"valid": valid, "checks": checks}

    def _append_hash_chain(self, run_id: str, manifest_hash: str) -> None:
        """Append a new entry to hash_chain.json linking to previous run."""
        chain = self._read_hash_chain()
        previous_hash = chain[-1]["chain_hash"] if chain else "sha256:genesis"

        # chain_hash = SHA256(previous_chain_hash + manifest_hash)
        combined = f"{previous_hash}|{manifest_hash}"
        chain_hash = sha256_str(combined)

        entry = {
            "seq": len(chain),
            "run_id": run_id,
            "manifest_hash": manifest_hash,
            "previous_chain_hash": previous_hash,
            "chain_hash": chain_hash,
            "sealed_at": self._utcnow(),
        }
        chain.append(entry)
        self._write_json(self._hash_chain_path, chain)

    def _read_hash_chain(self) -> list[dict[str, Any]]:
        """Read hash_chain.json or return empty list."""
        if not self._hash_chain_path.exists():
            return []
        return json.loads(self._hash_chain_path.read_text(encoding="utf-8"))

    def verify_hash_chain(self) -> dict[str, Any]:
        """Verify integrity of the entire hash chain.

        Returns {valid: bool, length: int, errors: [...]}.
        """
        chain = self._read_hash_chain()
        errors = []

        for i, entry in enumerate(chain):
            expected_prev = chain[i - 1]["chain_hash"] if i > 0 else "sha256:genesis"
            if entry["previous_chain_hash"] != expected_prev:
                errors.append(
                    f"seq {i}: previous_chain_hash mismatch "
                    f"(expected {expected_prev[:20]}...,"
                    f" got {entry['previous_chain_hash'][:20]}...)"
                )

            combined = f"{entry['previous_chain_hash']}|{entry['manifest_hash']}"
            expected_hash = sha256_str(combined)
            if entry["chain_hash"] != expected_hash:
                errors.append(f"seq {i}: chain_hash verification failed")

        return {"valid": len(errors) == 0, "length": len(chain), "errors": errors}

    def _write_json(self, path: Path, data: Any) -> None:
        """Write JSON atomically via .tmp → rename to prevent partial writes."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(path)
        except Exception:
            try:  # noqa: SIM105
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _hash_file(path: Path) -> str:
        return sha256_file(path)
