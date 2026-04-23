"""AutoRunner V2B — Runner: executes pipeline, manages RUNNING state, classifies failures."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel

from ssidctl.autorunner.ar_script_matrix import ARScriptMatrix, UnknownARIdError
from ssidctl.autorunner.events import RunEvent, RunEventStream
from ssidctl.autorunner.models import AutoRunnerRun, RunStatus
from ssidctl.autorunner.retry import FailureClassifier

# SSID repo root — override in tests via patch or env var
SSID_REPO_ROOT: str = os.environ.get(
    "SSID_REPO_ROOT",
    str(Path(__file__).parent.parent.parent.parent.parent / "SSID"),
)


class RunResult(BaseModel):
    run_id: str
    success: bool
    summary: str
    evidence_manifest: str | None = None
    final_report: str | None = None


_CLASSIFIER = FailureClassifier()
_MATRIX = ARScriptMatrix()


class Runner:
    def run(self, run: AutoRunnerRun, events: RunEventStream) -> RunResult:
        if run.status != RunStatus.QUEUED:
            raise ValueError(f"Can only run a QUEUED run, got: {run.status}")
        run.transition(RunStatus.RUNNING)
        events.append(RunEvent(type="run_started", payload={"run_id": run.run_id}))
        try:
            result = self._execute_pipeline(run, events)
            run.transition(RunStatus.SUCCEEDED)
            run.evidence_manifest = result.evidence_manifest
            run.final_report = result.final_report
            events.append(RunEvent(type="run_succeeded", payload={"summary": result.summary}))
            return result
        except Exception as exc:
            run.failure_class = _CLASSIFIER.classify(exc)
            run.transition(RunStatus.FAILED)
            run.error = str(exc)
            events.append(
                RunEvent(
                    type="run_failed",
                    payload={"error": str(exc), "failure_class": str(run.failure_class)},
                )
            )
            return RunResult(run_id=run.run_id, success=False, summary=f"FAILED: {exc}")

    def _execute_pipeline(self, run: AutoRunnerRun, events: RunEventStream) -> RunResult:
        """Execute the AR pipeline for this run.

        If autorunner_id is set, invokes the corresponding SSID AR script.
        Falls back to stub pipeline for runs without autorunner_id.
        """
        if not run.autorunner_id:
            # Stub pipeline — backward compatible for non-AR runs
            for phase in ("collect", "route", "execute", "verify", "finalize"):
                events.append(RunEvent(type="phase_started", payload={"phase": phase}))
            return RunResult(
                run_id=run.run_id,
                success=True,
                summary="Pipeline completed (stub)",
                evidence_manifest=f"evidence://{run.run_id}/manifest.yaml",
            )

        try:
            defn = _MATRIX.get(run.autorunner_id)
        except UnknownARIdError as exc:
            raise ValueError(str(exc)) from exc

        repo_root = Path(SSID_REPO_ROOT)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "ar_result.json"
            args = [
                a.replace("{out}", str(out_path)).replace("{repo_root}", str(repo_root))
                for a in defn.args_template
            ]
            cmd = ["python", str(repo_root / defn.script_path)] + args
            events.append(
                RunEvent(
                    type="phase_started",
                    payload={"phase": "execute", "script": defn.script_path},
                )
            )
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(repo_root),
            )
            events.append(RunEvent(
                type="phase_completed",
                payload={"phase": "execute", "exit_code": proc.returncode, "stdout": proc.stdout[:500]},
            ))

            ar_result: dict = {}
            if out_path.exists():
                try:
                    ar_result = json.loads(out_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    ar_result = {"status": "ERROR", "detail": "invalid JSON output"}
            else:
                ar_result = {"status": "ERROR", "detail": "no output file produced"}

            # AR scripts may not return a status field. If missing and exit_code is 0, treat as success.
            status = ar_result.get("status")
            success = proc.returncode == 0 and (status == "PASS" or status is None)

            if not success:
                # TODO P4: call agent_invoker.invoke_on_fail(run.autorunner_id, ar_result)
                # AgentInvoker is wired and tested (Task 3); call site deferred to P4.
                status_str = status or "SUCCESS"
                raise RuntimeError(
                    f"{run.autorunner_id} failed: exit_code={proc.returncode}, status={status_str}"
                )

            return RunResult(
                run_id=run.run_id,
                success=True,
                summary=f"{run.autorunner_id}: {status or 'SUCCESS'} (exit={proc.returncode})",
                evidence_manifest=ar_result.get("evidence_manifest"),
                final_report=ar_result.get("final_report"),
            )
