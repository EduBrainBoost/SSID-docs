"""Autopilot Loop — the main feedback loop orchestrator.

Orchestrates: Collect -> Triage -> Route -> Patch -> Verify -> PR -> Report -> Repeat
with bounded autonomy, convergence detection, circuit breaking, and DVP.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ssidctl.autopilot.collector import Collector
from ssidctl.autopilot.double_verify import DoubleVerifier
from ssidctl.autopilot.executor import (
    BudgetExceededError,
    ExecutionBudget,
    Executor,
    ExecutorError,
)
from ssidctl.autopilot.gate_filter import filter_gates
from ssidctl.autopilot.normalizer import FindingNormalizer
from ssidctl.autopilot.reporter import Reporter
from ssidctl.autopilot.router import RoutingEngine
from ssidctl.autopilot.taskspec_resolver import TaskSpecResolveError, TaskSpecResolver
from ssidctl.autopilot.watchdog import Watchdog, WatchdogTimeoutError
from ssidctl.core.canary import CanaryVerifier
from ssidctl.core.circuit_breaker import CircuitBreaker
from ssidctl.core.convergence import (
    ConvergenceDetector,
    ConvergenceVerdict,
    IterationSnapshot,
)
from ssidctl.core.event_log import EventLog
from ssidctl.core.evidence_store import EvidenceError, EvidenceStore
from ssidctl.core.hashing import sha256_str
from ssidctl.core.lifecycle import Lifecycle, State
from ssidctl.core.locking import EMSLock
from ssidctl.core.protected_paths import ProtectedPaths
from ssidctl.core.rule_registry import RuleRegistry
from ssidctl.core.worktree_orchestrator import WorktreeOrchestrator
from ssidctl.modules.pr import PRManager

if TYPE_CHECKING:
    from ssidctl.autopilot.board_sync import BoardSyncAdapter


@dataclass
class AutopilotConfig:
    """Configuration for an autopilot run."""

    task_id: str = ""
    scope_paths: list[str] = field(default_factory=lambda: ["*"])
    max_iterations: int = 5
    max_total_time_seconds: int = 1800
    budget: ExecutionBudget = field(default_factory=ExecutionBudget)
    phase_timeouts: dict[str, int] | None = None

    @staticmethod
    def from_yaml(path: Path) -> AutopilotConfig:
        """Load autopilot config from YAML."""
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        iteration = data.get("iteration", {})
        budget_data = data.get("budget", {})
        timeouts = data.get("phase_timeouts")

        return AutopilotConfig(
            max_iterations=iteration.get("max_iterations", 5),
            max_total_time_seconds=iteration.get("max_total_time_seconds", 1800),
            budget=ExecutionBudget(
                max_files_per_iter=budget_data.get("max_files_per_iteration", 8),
                max_lines_per_iter=budget_data.get("max_lines_per_iteration", 400),
                max_total_files=budget_data.get("max_total_files", 20),
                max_total_lines=budget_data.get("max_total_lines", 1200),
            ),
            phase_timeouts=timeouts,
        )


@dataclass
class AutopilotResult:
    """Result of a complete autopilot run."""

    run_id: str
    result: str
    iterations: int
    history: list[IterationSnapshot] = field(default_factory=list)
    handoff_path: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "result": self.result,
            "iterations": self.iterations,
            "history": [s.to_dict() for s in self.history],
            "handoff_path": self.handoff_path,
            "error": self.error,
        }


class AutopilotLoop:
    """Main autopilot feedback loop orchestrator."""

    def __init__(
        self,
        ssid_repo: Path,
        ems_repo: Path,
        state_dir: Path,
        evidence_dir: Path,
        config: AutopilotConfig | None = None,
        board_sync: BoardSyncAdapter | None = None,
    ) -> None:
        self._ssid_repo = ssid_repo
        self._ems_repo = ems_repo
        self._state_dir = state_dir
        self._evidence_dir = evidence_dir
        self._config = config or AutopilotConfig()
        self._board_sync = board_sync

        # Initialize components
        policies_dir = ems_repo / "policies"
        self._lock = EMSLock(state_dir / "locks")
        self._worktrees = WorktreeOrchestrator(ssid_repo, state_dir / "worktrees")
        self._collector = Collector(ssid_repo)
        self._resolver = TaskSpecResolver(ems_repo, state_dir)
        self._normalizer = FindingNormalizer(policies_dir / "failure_taxonomy.yaml")
        self._protected = ProtectedPaths(policies_dir / "protected_paths.yaml")
        self._router = RoutingEngine(
            policies_dir / "routing_matrix.yaml",
            self._protected,
        )
        self._canary = CanaryVerifier()
        self._dvp = DoubleVerifier()
        self._convergence = ConvergenceDetector()
        self._circuit = CircuitBreaker()
        self._watchdog = Watchdog(
            timeouts=self._config.phase_timeouts,
            total_timeout=self._config.max_total_time_seconds,
        )
        self._reporter = Reporter(state_dir / "runs")
        self._event_log = EventLog(state_dir / "runs" / "autopilot.jsonl")
        self._evidence = EvidenceStore(evidence_dir)
        # Accumulates all findings for gate report (populated during run)
        self._pending_findings: list[dict[str, Any]] = []

    def run(self, run_id: str) -> AutopilotResult:
        """Execute the full autopilot feedback loop.

        Args:
            run_id: Unique run identifier (ISO8601 format).

        Returns:
            AutopilotResult with outcome and history.
        """
        history: list[IterationSnapshot] = []
        all_findings: list[dict[str, Any]] = []
        all_routing: list[dict[str, Any]] = []

        # Lifecycle state machine tracks run phases
        lifecycle = Lifecycle(State.CREATED)

        try:
            # === CREATED -> PLANNING ===
            lifecycle.transition(State.PLANNING)

            self._event_log.append(
                "autopilot.run.start",
                {
                    "run_id": run_id,
                    "config": {
                        "max_iter": self._config.max_iterations,
                        "task_id": self._config.task_id,
                    },
                },
            )

            # Acquire lock
            self._lock.acquire("autopilot")

            # Resolve TaskSpec (if task_id provided)
            resolved_spec = None
            if self._config.task_id:
                try:
                    resolved_spec = self._resolver.resolve(self._config.task_id)
                except TaskSpecResolveError as e:
                    lifecycle.fail()
                    return self._finish(run_id, e.stop_code, history, error=str(e))
                # Override budget from TaskSpec limits
                self._config.budget.max_total_files = resolved_spec.max_changed_files
                self._config.budget.max_total_lines = resolved_spec.max_changed_lines

            # Rule registry completeness check
            registry_path = self._ems_repo / "policies" / "rule_registry.yaml"
            if registry_path.exists():
                registry = RuleRegistry(registry_path, self._ems_repo)
                report = registry.check_completeness()
                if not report.is_complete:
                    lifecycle.fail()
                    return self._finish(
                        run_id,
                        "STOP_RULE_MISSING",
                        history,
                        error=f"Missing rules: {report.missing_count}, "
                        f"Modified: {report.modified_count}",
                    )

            # === PLANNING -> PLANNED ===
            lifecycle.transition(State.PLANNED)

            # === PLANNED -> APPROVED ===
            # Check approval ledger if task_id is set
            if resolved_spec:
                from ssidctl.core.approval_ledger import ApprovalLedger
                from ssidctl.core.hashing import sha256_str

                ledger = ApprovalLedger(self._state_dir / "approvals" / "approvals.jsonl")
                # Deterministic hash of task scope for approval check
                scope_key = f"{resolved_spec.task_id}:{','.join(resolved_spec.allowed_paths)}"
                scope_hash = f"sha256:{sha256_str(scope_key)}"

                if not ledger.has_approval(resolved_spec.task_id, scope_hash):
                    lifecycle.fail()
                    return self._finish(
                        run_id,
                        "STOP_NOT_APPROVED",
                        history,
                        error=f"No approval found for task {resolved_spec.task_id}. "
                        f"Run: ssidctl approve record --task {resolved_spec.task_id} "
                        f"--run {run_id} --diff-hash {scope_hash}",
                    )

            lifecycle.transition(State.APPROVED)

            # === APPROVED -> APPLYING ===
            lifecycle.transition(State.APPLYING)
            self._notify_board(state=State.APPLYING)

            # Create worktrees
            wt_info = self._worktrees.create(run_id, self._config.task_id)
            apply_wt = wt_info["worktrees"]["apply"]["path"]
            verify_wt = wt_info["worktrees"]["verify"]["path"]

            # Create evidence run (OI-03/OI-05: register run in WORM store)
            base_commit = wt_info.get("base_commit", "")
            task_id_for_evidence = self._config.task_id or run_id
            toolchain_hash = sha256_str(f"autopilot:{self._config.max_iterations}:{base_commit}")
            with contextlib.suppress(EvidenceError):
                self._evidence.create_run(
                    run_id=run_id,
                    task_id=task_id_for_evidence,
                    ems_version="autopilot",
                    worktree_base_commit=base_commit,
                    prompt_sha256=sha256_str(""),
                    prompt_bytes_len=0,
                    toolchain_hash=toolchain_hash,
                )
            # Canary snapshot
            canary_snap = self._canary.snapshot(apply_wt, self._config.scope_paths)

            # Start watchdog
            self._watchdog.start_run()

            # Load circuit breaker state
            cb_path = self._state_dir / "runs" / run_id / "circuit_breaker.json"
            self._circuit.load(cb_path)

            # === LOOP ===
            executor = Executor(
                worklog_path=self._state_dir / "runs" / run_id / "worklog.jsonl",
                budget=self._config.budget,
            )
            # Configure executor with dependencies for TaskSpec operations
            executor.configure(
                collector=self._collector,
                gate_filter_fn=filter_gates,
                protected_paths=self._protected,
                pr_manager=PRManager(self._ssid_repo),
            )

            for iteration in range(1, self._config.max_iterations + 1):
                # Circuit breaker check
                if not self._circuit.can_proceed():
                    return self._finish(run_id, "STOP_CIRCUIT_OPEN", history)

                try:
                    self._watchdog.check()

                    # 1. COLLECT (with gate filtering if TaskSpec specifies it)
                    self._watchdog.start_phase("collect")
                    if resolved_spec and resolved_spec.gate_source == "acceptance_checks_only":
                        from ssidctl.gates.matrix import load_matrix

                        matrix = load_matrix()
                        filtered = filter_gates(matrix.gates, resolved_spec.acceptance_checks)
                        collection = self._collector.collect(apply_wt, gates=filtered)
                    else:
                        collection = self._collector.collect(apply_wt)
                    self._watchdog.end_phase()

                    # All pass = done
                    if collection.all_pass:
                        snap = IterationSnapshot(
                            iteration=iteration,
                            findings_count=0,
                            finding_types=frozenset(),
                            all_pass=True,
                        )
                        history.append(snap)
                        return self._finish(run_id, "PASS", history)

                    # 2. TRIAGE
                    self._watchdog.start_phase("triage")
                    findings = self._normalizer.normalize(collection.gate_results)
                    findings = self._normalizer.deduplicate(findings)
                    normalized = [f.to_dict() for f in findings]
                    all_findings.extend(normalized)
                    self._pending_findings.extend(normalized)
                    self._watchdog.end_phase()

                    # 3. ROUTE
                    self._watchdog.start_phase("route")
                    decision = self._router.route(findings)
                    all_routing.append(decision.to_dict())
                    self._watchdog.end_phase()

                    # Check for stops
                    if decision.has_stops:
                        stop_code = next(t.stop_code for t in decision.tasks if t.stop_required)
                        return self._finish(run_id, stop_code, history)

                    if decision.has_conflicts:
                        return self._finish(run_id, "STOP_CONFLICT", history)

                    if decision.unroutable:
                        return self._finish(run_id, "STOP_UNROUTABLE", history)

                    # 4. PATCH
                    self._watchdog.start_phase("patch")
                    executor.new_iteration()
                    for task in decision.tasks:
                        executor.execute_task(
                            task,
                            apply_wt,
                            operations=resolved_spec.operations if resolved_spec else None,
                            taskspec=resolved_spec,
                            run_id=run_id,
                        )
                    self._watchdog.end_phase()

                    # 5. VERIFY (DVP) — transition to VERIFYING on first iteration
                    if iteration == 1 and lifecycle.state == State.APPLYING:
                        lifecycle.transition(State.VERIFYING)
                        self._notify_board(state=State.VERIFYING)
                    self._watchdog.start_phase("verify")
                    dvp_report = self._dvp.run_double_verification(
                        gates=[],  # Will use matrix gates
                        apply_wt=apply_wt,
                        verify_wt=verify_wt,
                        repo_path=self._ssid_repo,
                    )

                    if not dvp_report.all_match:
                        return self._finish(run_id, "STOP_MANIPULATION", history)
                    self._watchdog.end_phase()

                    # 6. CANARY CHECK
                    canary_result = self._canary.verify(apply_wt, canary_snap)
                    if not canary_result.is_clean:
                        return self._finish(run_id, "STOP_WORKSPACE_TAMPERED", history)

                    # 7. RECORD ITERATION
                    snap = IterationSnapshot(
                        iteration=iteration,
                        findings_count=len(findings),
                        finding_types=frozenset(f.finding_type for f in findings),
                        all_pass=False,
                    )
                    history.append(snap)

                    # 8. CONVERGENCE
                    verdict = self._convergence.check(history)
                    if verdict == ConvergenceVerdict.CONVERGED:
                        self._circuit.record_success()
                        return self._finish(run_id, "PASS", history)
                    elif verdict != ConvergenceVerdict.CONTINUE:
                        self._circuit.record_failure()
                        return self._finish(run_id, str(verdict), history)

                    self._circuit.record_success()

                except BudgetExceededError:
                    return self._finish(run_id, "STOP_BUDGET_EXCEEDED", history)
                except ExecutorError as e:
                    return self._finish(run_id, e.stop_code, history, error=str(e))
                except WatchdogTimeoutError as e:
                    return self._finish(run_id, "STOP_TIMEOUT", history, error=str(e))

            # Max iterations reached
            lifecycle.fail()
            return self._finish(run_id, "STOP_MAX_ITERATIONS", history)

        except Exception as e:
            if not lifecycle.is_terminal:
                lifecycle.fail()
            return self._finish(run_id, "STOP_ERROR", history, error=str(e))
        finally:
            # Always release lock and save state
            self._lock.release()
            cb_path = self._state_dir / "runs" / run_id / "circuit_breaker.json"
            self._circuit.save(cb_path)

            # Save watchdog report
            wd_path = self._state_dir / "runs" / run_id / "watchdog.json"
            self._watchdog.save_report(wd_path)

            # Save routing decisions
            if all_routing:
                self._reporter.write_routing_decisions(run_id, all_routing)

            # Save findings
            if all_findings:
                self._reporter.write_findings(run_id, all_findings)

    def _notify_board(self, state: State | None = None, result: str | None = None) -> None:
        """Notify BoardSyncAdapter of lifecycle transition or finish."""
        if self._board_sync is None:
            return
        if state is not None:
            self._board_sync.on_lifecycle_transition(state)
        if result is not None:
            self._board_sync.on_finish(result)

    def _finish(
        self,
        run_id: str,
        result: str,
        history: list[IterationSnapshot],
        error: str = "",
    ) -> AutopilotResult:
        """Finalize run: write reports, evidence, and sync board status."""
        # Sync board status
        self._notify_board(result=result)

        # Write handoff
        handoff_path = self._reporter.write_handoff(run_id, result, history)

        # Write convergence
        self._reporter.write_convergence(run_id, history)

        # Seal evidence run (OI-03: extends hash chain; OI-05: writes gate report)
        overall_result = "PASS" if result == "PASS" else "FAIL"
        try:
            if self._evidence.is_sealed(run_id):
                pass  # Already sealed (e.g. duplicate _finish call)
            else:
                # Write sanitized gate report (OI-05)
                gate_findings = [
                    {
                        "code": f.get("finding_type", "UNKNOWN"),
                        "gate": f.get("gate_name", ""),
                        "severity": f.get("severity", "error"),
                        "redacted": True,  # raw text never stored in evidence
                    }
                    for f in self._pending_findings
                ]
                with contextlib.suppress(EvidenceError):
                    self._evidence.write_gate_report(
                        run_id=run_id,
                        findings=gate_findings,
                        overall_result=overall_result,
                    )
                # Finalize manifest
                with contextlib.suppress(EvidenceError):
                    self._evidence.finalize_run(
                        run_id=run_id,
                        result_commit_sha=None,
                        response_sha256=sha256_str(""),
                        response_bytes_len=0,
                        diff_sha256=None,
                        diff_bytes_len=None,
                        overall_result=overall_result,
                        lifecycle_status="DONE" if result == "PASS" else result,
                    )
                # Seal — extends hash chain (OI-03)
                with contextlib.suppress(EvidenceError):
                    self._evidence.seal(run_id)
        except Exception:  # noqa: S110
            pass  # Evidence failures must not break the autopilot result

        # Log completion
        self._event_log.append(
            "autopilot.run.complete",
            {
                "run_id": run_id,
                "result": result,
                "iterations": len(history),
                "error": error,
            },
        )

        return AutopilotResult(
            run_id=run_id,
            result=result,
            iterations=len(history),
            history=history,
            handoff_path=str(handoff_path),
            error=error,
        )
