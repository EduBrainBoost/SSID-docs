"""Run management module — query and replay runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ssidctl.core.event_log import EventLog
from ssidctl.core.evidence_store import EvidenceError, EvidenceStore


class RunError(Exception):
    pass


class RunManager:
    """Query and replay EMS runs."""

    def __init__(self, state_dir: Path, evidence_dir: Path) -> None:
        self._event_log = EventLog(state_dir / "runs" / "runs.jsonl")
        self._evidence = EvidenceStore(evidence_dir)

    def list_runs(self) -> list[dict[str, Any]]:
        """List all run events from event log."""
        return self._event_log.read_all()

    def show(self, run_id: str) -> dict[str, Any]:
        """Show run details from event log + evidence."""
        events = [
            e for e in self._event_log.read_all() if e.get("payload", {}).get("run_id") == run_id
        ]
        manifest = None
        gate_report = None
        sealed = False
        try:
            manifest = self._evidence.get_manifest(run_id)
            gate_report = self._evidence.get_gate_report(run_id)
            sealed = self._evidence.is_sealed(run_id)
        except EvidenceError:
            pass
        if not events and manifest is None:
            raise RunError(f"Run not found: {run_id}")
        return {
            "run_id": run_id,
            "events": events,
            "manifest": manifest,
            "gate_report": gate_report,
            "sealed": sealed,
        }

    def replay_gates(self, run_id: str, ssid_repo: Path) -> dict[str, Any]:
        """Re-run gates (no Claude). Deterministic verification."""
        try:
            manifest = self._evidence.get_manifest(run_id)
        except EvidenceError as e:
            raise RunError(f"Cannot replay: {e}") from e
        from ssidctl.gates.matrix import load_matrix
        from ssidctl.gates.runner import run_all_gates

        matrix = load_matrix()
        gate_results = run_all_gates(matrix.gates, ssid_repo)
        return {
            "run_id": run_id,
            "original_result": manifest.get("overall_result"),
            "replay_gates": [
                {"gate": gr.gate_name, "result": gr.result, "exit_code": gr.exit_code}
                for gr in gate_results
            ],
            "replay_overall": (
                "PASS" if all(gr.result == "PASS" for gr in gate_results) else "FAIL"
            ),
        }
