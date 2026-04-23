"""AutoRunner V2B — Finalizer: writes evidence manifest + final report + evidence seal."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel

from ssidctl.autorunner.models import AutoRunnerRun
from ssidctl.autorunner.provenance import ProvenanceResolver
from ssidctl.autorunner.sealer import EvidenceSealer


class FinalReport(BaseModel):
    run_id: str
    task_id: str
    status: str  # succeeded | failed
    summary: str
    evidence_manifest: str | None
    report_path: str
    finalized_at: str


class Finalizer:
    def __init__(
        self,
        report_dir: str | None = None,
        sealer: EvidenceSealer | None = None,
        resolver: ProvenanceResolver | None = None,
    ) -> None:
        _default = os.environ.get("SSID_EMS_STATE", "/tmp/ssid_state")  # noqa: S108
        base = Path(report_dir or _default + "/autorunner/reports")
        base.mkdir(parents=True, exist_ok=True)
        self._dir = base
        self._sealer = sealer or EvidenceSealer()
        self._resolver = resolver or ProvenanceResolver()

    def finalize(self, run: AutoRunnerRun, success: bool, summary: str) -> FinalReport:
        if success and not run.evidence_manifest:
            raise ValueError("evidence_manifest must be set — no 'green' without evidence")
        report_path = str(self._dir / f"{run.run_id}_report.yaml")
        report = FinalReport(
            run_id=run.run_id,
            task_id=run.task_id,
            status="succeeded" if success else "failed",
            summary=summary,
            evidence_manifest=run.evidence_manifest,
            report_path=report_path,
            finalized_at=datetime.now(UTC).isoformat(),
        )
        Path(report_path).write_text(
            yaml.safe_dump(report.model_dump(), sort_keys=True),
            encoding="utf-8",
        )
        run.final_report = report_path
        # Seal evidence on success
        if success:
            prov = self._resolver.resolve(run.scope)
            self._sealer.seal(run, prov)
        return report
