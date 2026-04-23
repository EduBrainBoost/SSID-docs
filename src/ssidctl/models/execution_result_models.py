"""Execution result record model for audit-chain persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ssidctl.core.hashing import sha256_str

MAX_OUTPUT_LENGTH = 4096


@dataclass
class ExecutionResultRecord:
    """Complete audit record for a single execution."""

    execution_id: str
    worker_id: str
    action_type: str
    target_ref: str
    adapter_name: str
    started_at: str
    finished_at: str
    duration_ms: int
    outcome_status: str  # succeeded | failed | blocked | expired | abandoned
    exit_code: int
    changed_files: list[str] = field(default_factory=list)
    stdout_summary: str = ""
    stderr_summary: str = ""
    dry_run: bool = False
    approval_snapshot: dict[str, Any] = field(default_factory=dict)
    input_snapshot_hash: str = ""
    result_hash: str = ""
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Truncate outputs
        if len(self.stdout_summary) > MAX_OUTPUT_LENGTH:
            self.stdout_summary = self.stdout_summary[:MAX_OUTPUT_LENGTH]
        if len(self.stderr_summary) > MAX_OUTPUT_LENGTH:
            self.stderr_summary = self.stderr_summary[:MAX_OUTPUT_LENGTH]
        # Compute result hash if not set
        if not self.result_hash:
            self.result_hash = self.compute_result_hash()

    def compute_result_hash(self) -> str:
        """Deterministic SHA-256 hash over sorted canonical fields."""
        canonical = {
            "execution_id": self.execution_id,
            "worker_id": self.worker_id,
            "action_type": self.action_type,
            "target_ref": self.target_ref,
            "adapter_name": self.adapter_name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "outcome_status": self.outcome_status,
            "exit_code": self.exit_code,
            "changed_files": sorted(self.changed_files),
            "dry_run": self.dry_run,
        }
        raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return sha256_str(raw)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "worker_id": self.worker_id,
            "action_type": self.action_type,
            "target_ref": self.target_ref,
            "adapter_name": self.adapter_name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "outcome_status": self.outcome_status,
            "exit_code": self.exit_code,
            "changed_files": self.changed_files,
            "stdout_summary": self.stdout_summary,
            "stderr_summary": self.stderr_summary,
            "dry_run": self.dry_run,
            "approval_snapshot": self.approval_snapshot,
            "input_snapshot_hash": self.input_snapshot_hash,
            "result_hash": self.result_hash,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionResultRecord:
        return cls(
            execution_id=data["execution_id"],
            worker_id=data["worker_id"],
            action_type=data["action_type"],
            target_ref=data["target_ref"],
            adapter_name=data["adapter_name"],
            started_at=data["started_at"],
            finished_at=data["finished_at"],
            duration_ms=data["duration_ms"],
            outcome_status=data["outcome_status"],
            exit_code=data["exit_code"],
            changed_files=data.get("changed_files", []),
            stdout_summary=data.get("stdout_summary", ""),
            stderr_summary=data.get("stderr_summary", ""),
            dry_run=data.get("dry_run", False),
            approval_snapshot=data.get("approval_snapshot", {}),
            input_snapshot_hash=data.get("input_snapshot_hash", ""),
            result_hash=data.get("result_hash", ""),
            evidence_refs=data.get("evidence_refs", []),
        )
