"""AutoRunner V2B — EvidenceSealer: immutable SHA256 seal of evidence manifest."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ssidctl.autorunner.models import AutoRunnerRun, EvidenceSeal, Provenance


class EvidenceSealer:
    def __init__(self, seal_dir: str | None = None) -> None:
        _default = os.environ.get("SSID_EMS_STATE", "/tmp/ssid_state")  # noqa: S108
        self._dir = Path(seal_dir or _default + "/autorunner/seals")
        self._dir.mkdir(parents=True, exist_ok=True)

    def seal(self, run: AutoRunnerRun, provenance: Provenance) -> EvidenceSeal:
        manifest_hash = self._hash_manifest(run.evidence_manifest)
        seal_path = str(self._dir / f"{run.run_id}_seal.yaml")
        seal = EvidenceSeal(
            run_id=run.run_id,
            provenance=provenance,
            manifest_hash=manifest_hash,
            sealed_at=datetime.now(UTC).isoformat(),
            seal_path=seal_path,
        )
        Path(seal_path).write_text(
            yaml.safe_dump(seal.model_dump(mode="json"), sort_keys=True),
            encoding="utf-8",
        )
        run.evidence_seal = seal
        run.provenance = provenance
        return seal

    @staticmethod
    def _hash_manifest(manifest_path: str | None) -> str:
        if not manifest_path:
            return "sha256:none"
        p = Path(manifest_path)
        if not p.exists():
            return "sha256:none"
        return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
