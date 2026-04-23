"""Autopilot Feedback Loop — bounded self-healing CI loop.

Collect → Triage → Route → Patch → Verify → PR Update → Report → Repeat

Components:
- ReportBus: collect findings from CI/gates into inbox, dispatch to outbox
- Router: map finding category to agent/action
- Executor: sequential patch→verify→commit under WriteLock
- Convergence: PASS→handoff, STOP→manual-required

Bounded autonomy: MAX_ITER, change budget, stop criteria enforcement.
Deterministic protocol outputs: worklog.jsonl, manifest.json, handoff.md, findings.json
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from ssidctl.core.event_log import EventLog
from ssidctl.core.hashing import sha256_str
from ssidctl.core.timeutil import utcnow_iso
from ssidctl.core.write_lock import LockAcquireError, WriteLock


class AutopilotError(Exception):
    pass


class StopCriterionError(AutopilotError):
    """Raised when a hard stop criterion is triggered."""


class BudgetExceededError(AutopilotError):
    """Raised when change budget is exceeded."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class FindingCategory(StrEnum):
    LINT = "lint"
    TEST = "test"
    TYPE_CHECK = "type-check"
    SECRET = "secret"  # noqa: S105
    SCHEMA = "schema"
    COVERAGE = "coverage"
    ROOT_LOCK = "root-lock"
    UNKNOWN = "unknown"


class IterationResult(StrEnum):
    PASS = "PASS"  # noqa: S105
    FAIL = "FAIL"
    STOP = "STOP"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


@dataclass
class Finding:
    """A single CI/gate finding."""

    finding_id: str
    category: FindingCategory
    source: str  # e.g. "ruff", "pytest", "mypy", "gitleaks"
    message: str
    file: str = ""
    line: int = 0
    rule: str = ""
    severity: str = "error"


@dataclass
class RoutedTask:
    """A finding routed to a specific agent/action."""

    task_id: str
    finding: Finding
    agent: str  # agent name from routing matrix
    action: str  # e.g. "ruff-fix", "pytest-fix", "mypy-fix"
    auto_fixable: bool = False


@dataclass
class IterationReport:
    """Report for a single autopilot iteration."""

    iteration: int
    result: IterationResult
    findings_count: int
    fixed_count: int
    remaining_count: int
    files_changed: int
    stop_reason: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ChangeBudget:
    """Bounded autonomy: limits on what autopilot may change."""

    max_files: int = 50
    max_diff_lines: int = 500
    files_changed: int = 0
    diff_lines: int = 0

    def check(self, new_files: int = 0, new_lines: int = 0) -> None:
        """Raise BudgetExceeded if limits would be breached."""
        if self.files_changed + new_files > self.max_files:
            raise BudgetExceededError(
                f"File budget exceeded: {self.files_changed + new_files} > {self.max_files}"
            )
        if self.diff_lines + new_lines > self.max_diff_lines:
            raise BudgetExceededError(
                f"Diff budget exceeded: {self.diff_lines + new_lines} > {self.max_diff_lines}"
            )

    def consume(self, files: int, lines: int) -> None:
        self.files_changed += files
        self.diff_lines += lines


# ---------------------------------------------------------------------------
# Routing matrix: finding category → agent + action
# ---------------------------------------------------------------------------

ROUTING_MATRIX: dict[FindingCategory, dict[str, str]] = {
    FindingCategory.LINT: {"agent": "agent-03", "action": "ruff-fix"},
    FindingCategory.TEST: {"agent": "agent-03", "action": "pytest-fix"},
    FindingCategory.TYPE_CHECK: {"agent": "agent-03", "action": "mypy-fix"},
    FindingCategory.SECRET: {"agent": "agent-05", "action": "secret-remediate"},
    FindingCategory.SCHEMA: {"agent": "agent-03", "action": "schema-fix"},
    FindingCategory.COVERAGE: {"agent": "agent-03", "action": "coverage-improve"},
    FindingCategory.ROOT_LOCK: {"agent": "agent-02", "action": "root-lock-enforce"},
    FindingCategory.UNKNOWN: {"agent": "agent-03", "action": "manual-review"},
}

# Hard stop categories — autopilot must NOT auto-fix these
STOP_CATEGORIES: frozenset[FindingCategory] = frozenset(
    {
        FindingCategory.SECRET,
        FindingCategory.ROOT_LOCK,
    }
)


# ---------------------------------------------------------------------------
# ReportBus
# ---------------------------------------------------------------------------


class ReportBus:
    """Collect findings from CI into inbox, dispatch routed tasks to outbox."""

    def __init__(self, bus_dir: Path) -> None:
        self._bus_dir = bus_dir
        self._inbox = bus_dir / "inbox"
        self._outbox = bus_dir / "outbox"
        self._inbox.mkdir(parents=True, exist_ok=True)
        self._outbox.mkdir(parents=True, exist_ok=True)

    def submit_finding(self, finding: Finding) -> Path:
        """Write a finding to the inbox."""
        filename = f"{finding.finding_id}.json"
        path = self._inbox / filename
        path.write_text(
            json.dumps(asdict(finding), indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def collect_findings(self) -> list[Finding]:
        """Read all findings from inbox."""
        findings: list[Finding] = []
        for path in sorted(self._inbox.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            findings.append(
                Finding(
                    finding_id=data["finding_id"],
                    category=FindingCategory(data["category"]),
                    source=data["source"],
                    message=data["message"],
                    file=data.get("file", ""),
                    line=data.get("line", 0),
                    rule=data.get("rule", ""),
                    severity=data.get("severity", "error"),
                )
            )
        return findings

    def submit_routed(self, task: RoutedTask) -> Path:
        """Write a routed task to the outbox."""
        filename = f"{task.task_id}.json"
        path = self._outbox / filename
        data = asdict(task)
        data["finding"] = asdict(task.finding)
        path.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def clear_inbox(self) -> int:
        """Remove all inbox findings. Returns count removed."""
        count = 0
        for path in self._inbox.glob("*.json"):
            path.unlink()
            count += 1
        return count

    def clear_outbox(self) -> int:
        """Remove all outbox tasks. Returns count removed."""
        count = 0
        for path in self._outbox.glob("*.json"):
            path.unlink()
            count += 1
        return count


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class Router:
    """Map findings to agents/actions using the routing matrix."""

    def __init__(
        self,
        matrix: dict[FindingCategory, dict[str, str]] | None = None,
        stop_categories: frozenset[FindingCategory] | None = None,
    ) -> None:
        self._matrix = matrix or ROUTING_MATRIX
        self._stop_categories = stop_categories if stop_categories is not None else STOP_CATEGORIES

    def route(self, finding: Finding) -> RoutedTask:
        """Route a single finding to an agent/action."""
        entry = self._matrix.get(finding.category, self._matrix[FindingCategory.UNKNOWN])
        auto_fixable = finding.category not in self._stop_categories
        return RoutedTask(
            task_id=f"APT-{uuid.uuid4().hex[:8]}",
            finding=finding,
            agent=entry["agent"],
            action=entry["action"],
            auto_fixable=auto_fixable,
        )

    def route_all(self, findings: list[Finding]) -> tuple[list[RoutedTask], list[RoutedTask]]:
        """Route all findings. Returns (auto_fixable, stop_required)."""
        auto: list[RoutedTask] = []
        stop: list[RoutedTask] = []
        for f in findings:
            task = self.route(f)
            if task.auto_fixable:
                auto.append(task)
            else:
                stop.append(task)
        return auto, stop

    def is_stop_category(self, category: FindingCategory) -> bool:
        return category in self._stop_categories


# ---------------------------------------------------------------------------
# CI Collector — parse CI output into findings
# ---------------------------------------------------------------------------


class CICollector:
    """Parse CI tool outputs into Finding objects."""

    @staticmethod
    def parse_ruff_output(output: str) -> list[Finding]:
        """Parse ruff check --output-format=json output."""
        findings: list[Finding] = []
        try:
            entries = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return findings
        for entry in entries:
            findings.append(
                Finding(
                    finding_id=f"RUFF-{uuid.uuid4().hex[:8]}",
                    category=FindingCategory.LINT,
                    source="ruff",
                    message=entry.get("message", ""),
                    file=entry.get("filename", ""),
                    line=entry.get("location", {}).get("row", 0),
                    rule=entry.get("code", ""),
                )
            )
        return findings

    @staticmethod
    def parse_pytest_output(output: str) -> list[Finding]:
        """Parse pytest --tb=line output for failures."""
        findings: list[Finding] = []
        for line in output.splitlines():
            if line.startswith("FAILED "):
                findings.append(
                    Finding(
                        finding_id=f"TEST-{uuid.uuid4().hex[:8]}",
                        category=FindingCategory.TEST,
                        source="pytest",
                        message=line.strip(),
                    )
                )
        return findings

    @staticmethod
    def parse_mypy_output(output: str) -> list[Finding]:
        """Parse mypy output (file:line: error: message [code])."""
        findings: list[Finding] = []
        for line in output.splitlines():
            if ": error:" in line:
                parts = line.split(":", maxsplit=3)
                file_path = parts[0] if len(parts) > 0 else ""
                line_no = int(parts[1]) if len(parts) > 1 and parts[1].strip().isdigit() else 0
                msg = parts[3].strip() if len(parts) > 3 else line
                findings.append(
                    Finding(
                        finding_id=f"MYPY-{uuid.uuid4().hex[:8]}",
                        category=FindingCategory.TYPE_CHECK,
                        source="mypy",
                        message=msg,
                        file=file_path,
                        line=line_no,
                    )
                )
        return findings

    @staticmethod
    def from_ci_job(job_name: str, exit_code: int, stdout: str, stderr: str) -> list[Finding]:
        """Auto-detect parser based on job name."""
        combined = stdout + "\n" + stderr
        if "ruff" in job_name.lower():
            return CICollector.parse_ruff_output(combined)
        elif "test" in job_name.lower() or "pytest" in job_name.lower():
            return CICollector.parse_pytest_output(combined)
        elif "mypy" in job_name.lower():
            return CICollector.parse_mypy_output(combined)
        elif exit_code != 0:
            return [
                Finding(
                    finding_id=f"CI-{uuid.uuid4().hex[:8]}",
                    category=FindingCategory.UNKNOWN,
                    source=job_name,
                    message=f"Job {job_name} failed with exit code {exit_code}",
                )
            ]
        return []


# ---------------------------------------------------------------------------
# Executor — runs one fix cycle under WriteLock
# ---------------------------------------------------------------------------


class Executor:
    """Run auto-fix commands for routed tasks."""

    def __init__(self, repo_path: Path, budget: ChangeBudget) -> None:
        self._repo = repo_path
        self._budget = budget

    def execute_ruff_fix(self) -> tuple[int, str]:
        """Run ruff check --fix and ruff format. Returns (files_changed, output)."""
        outputs: list[str] = []

        # ruff check --fix
        result = subprocess.run(
            ["python", "-m", "ruff", "check", "--fix", "src/", "tests/"],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
            timeout=120,
        )
        outputs.append(result.stdout + result.stderr)

        # ruff format
        result = subprocess.run(
            ["python", "-m", "ruff", "format", "src/", "tests/"],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
            timeout=120,
        )
        outputs.append(result.stdout + result.stderr)

        # Count changes
        diff_stat = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
        )
        files_changed = len([line for line in diff_stat.stdout.splitlines() if "|" in line])
        return files_changed, "\n".join(outputs)

    def count_diff_lines(self) -> int:
        """Count total diff lines in working tree."""
        result = subprocess.run(
            ["git", "diff", "--numstat"],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
        )
        total = 0
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                with contextlib.suppress(ValueError):
                    total += int(parts[0]) + int(parts[1])
        return total

    def stage_and_verify(self) -> tuple[bool, str]:
        """Stage changes, run verification (ruff + pytest). Returns (pass, output)."""
        # Stage
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(self._repo),
            capture_output=True,
        )

        # Verify: ruff check
        ruff_result = subprocess.run(
            ["python", "-m", "ruff", "check", "src/", "tests/"],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if ruff_result.returncode != 0:
            return False, f"Ruff check failed:\n{ruff_result.stdout}\n{ruff_result.stderr}"

        # Verify: pytest
        test_result = subprocess.run(
            ["python", "-m", "pytest", "-q", "--tb=line"],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if test_result.returncode != 0:
            return False, f"Tests failed:\n{test_result.stdout}\n{test_result.stderr}"

        return True, "Verification passed"


# ---------------------------------------------------------------------------
# AutopilotManager — orchestrates the full loop
# ---------------------------------------------------------------------------


class AutopilotManager:
    """Orchestrate the autopilot feedback loop.

    Lifecycle per iteration:
        Collect → Triage → Route → Patch → Verify → Report

    Stop criteria (hard stop, no auto-fix):
        - Secret exposure findings
        - ROOT-24-LOCK violations
        - MAX_ITER reached
        - Change budget exceeded

    Protocol outputs (per run):
        - worklog.jsonl  — event-sourced iteration log
        - manifest.json  — run metadata + hashes
        - handoff.md     — human-readable summary
        - findings.json  — all findings across iterations
    """

    def __init__(
        self,
        state_dir: Path,
        repo_path: Path,
        max_iter: int = 5,
        max_files: int = 50,
        max_diff_lines: int = 500,
    ) -> None:
        self._state_dir = state_dir
        self._repo = repo_path
        self._max_iter = max_iter
        self._budget = ChangeBudget(max_files=max_files, max_diff_lines=max_diff_lines)

        # Run identity
        self._run_id = f"APR-{utcnow_iso().replace(':', '').replace('-', '')[:15]}"

        # Directories
        self._run_dir = state_dir / "autopilot" / "runs" / self._run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)

        # Components
        self._bus = ReportBus(state_dir / "autopilot" / "bus")
        self._router = Router()
        self._worklog = EventLog(self._run_dir / "worklog.jsonl")
        self._lock = WriteLock(state_dir / "locks", "AUTOPILOT")

        # State
        self._iteration = 0
        self._all_findings: list[dict[str, Any]] = []
        self._reports: list[IterationReport] = []

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def run(self) -> dict[str, Any]:
        """Execute the autopilot loop. Returns final manifest."""
        self._worklog.append(
            "autopilot.started",
            {
                "run_id": self._run_id,
                "max_iter": self._max_iter,
                "repo": str(self._repo),
                "budget": {
                    "max_files": self._budget.max_files,
                    "max_diff": self._budget.max_diff_lines,
                },
            },
            actor="autopilot",
        )

        # Acquire lock
        try:
            sha = self._get_head_sha()
            self._lock.acquire("autopilot", sha, ttl_seconds=1800)
        except LockAcquireError as e:
            self._worklog.append(
                "autopilot.lock_failed",
                {"error": str(e)},
                actor="autopilot",
            )
            raise AutopilotError(f"Cannot acquire lock: {e}") from e

        final_result = IterationResult.FAIL
        try:
            for i in range(1, self._max_iter + 1):
                self._iteration = i
                report = self._run_iteration(i)
                self._reports.append(report)

                if report.result == IterationResult.PASS:
                    final_result = IterationResult.PASS
                    break
                elif report.result == IterationResult.STOP:
                    final_result = IterationResult.STOP
                    break
                elif report.result == IterationResult.BUDGET_EXCEEDED:
                    final_result = IterationResult.BUDGET_EXCEEDED
                    break
                # FAIL → continue to next iteration
        finally:
            self._lock.release(force=True)

        # Write protocol outputs
        manifest = self._write_manifest(final_result)
        self._write_findings()
        self._write_handoff(final_result)

        self._worklog.append(
            "autopilot.completed",
            {
                "run_id": self._run_id,
                "result": final_result.value,
                "iterations": self._iteration,
                "total_findings": len(self._all_findings),
            },
            actor="autopilot",
        )

        return manifest

    def _run_iteration(self, iteration: int) -> IterationReport:
        """Execute one iteration of the feedback loop."""
        self._worklog.append(
            "iteration.started",
            {"iteration": iteration},
            actor="autopilot",
        )

        # 1. Collect — run CI checks and parse findings
        findings = self._collect_findings()
        self._all_findings.extend([asdict(f) for f in findings])

        if not findings:
            self._worklog.append(
                "iteration.no_findings",
                {"iteration": iteration},
                actor="autopilot",
            )
            return IterationReport(
                iteration=iteration,
                result=IterationResult.PASS,
                findings_count=0,
                fixed_count=0,
                remaining_count=0,
                files_changed=0,
            )

        # 2. Route findings
        auto_tasks, stop_tasks = self._router.route_all(findings)

        # 3. Check stop criteria
        if stop_tasks:
            stop_reasons = [f"{t.finding.category.value}: {t.finding.message}" for t in stop_tasks]
            self._worklog.append(
                "iteration.stop_criterion",
                {
                    "iteration": iteration,
                    "stop_findings": len(stop_tasks),
                    "reasons": stop_reasons,
                },
                actor="autopilot",
            )
            return IterationReport(
                iteration=iteration,
                result=IterationResult.STOP,
                findings_count=len(findings),
                fixed_count=0,
                remaining_count=len(findings),
                files_changed=0,
                stop_reason="; ".join(stop_reasons),
                findings=[asdict(f) for f in findings],
            )

        # 4. Patch — execute auto-fixes
        try:
            files_changed, fix_output = self._execute_fixes(auto_tasks)
            diff_lines = Executor(self._repo, self._budget).count_diff_lines()
            self._budget.check(files_changed, diff_lines)
            self._budget.consume(files_changed, diff_lines)
        except BudgetExceededError as e:
            self._worklog.append(
                "iteration.budget_exceeded",
                {"iteration": iteration, "error": str(e)},
                actor="autopilot",
            )
            return IterationReport(
                iteration=iteration,
                result=IterationResult.BUDGET_EXCEEDED,
                findings_count=len(findings),
                fixed_count=0,
                remaining_count=len(findings),
                files_changed=0,
                stop_reason=str(e),
            )

        # 5. Verify
        executor = Executor(self._repo, self._budget)
        passed, verify_output = executor.stage_and_verify()

        self._worklog.append(
            "iteration.completed",
            {
                "iteration": iteration,
                "findings": len(findings),
                "auto_fixable": len(auto_tasks),
                "files_changed": files_changed,
                "verify_passed": passed,
            },
            actor="autopilot",
        )

        if passed:
            # Re-collect to count remaining
            remaining = self._collect_findings()
            return IterationReport(
                iteration=iteration,
                result=IterationResult.PASS if not remaining else IterationResult.FAIL,
                findings_count=len(findings),
                fixed_count=len(findings) - len(remaining),
                remaining_count=len(remaining),
                files_changed=files_changed,
            )

        return IterationReport(
            iteration=iteration,
            result=IterationResult.FAIL,
            findings_count=len(findings),
            fixed_count=0,
            remaining_count=len(findings),
            files_changed=files_changed,
        )

    def _collect_findings(self) -> list[Finding]:
        """Run CI checks and parse output into findings."""
        all_findings: list[Finding] = []

        # Ruff check (JSON output for parsing)
        try:
            result = subprocess.run(
                ["python", "-m", "ruff", "check", "--output-format=json", "src/", "tests/"],
                cwd=str(self._repo),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                all_findings.extend(CICollector.parse_ruff_output(result.stdout))
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Mypy
        try:
            result = subprocess.run(
                ["python", "-m", "mypy", "src/ssidctl/"],
                cwd=str(self._repo),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                all_findings.extend(CICollector.parse_mypy_output(result.stdout))
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Pytest (quick check)
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-q", "--tb=line", "-x"],
                cwd=str(self._repo),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                all_findings.extend(CICollector.parse_pytest_output(result.stdout))
        except (subprocess.TimeoutExpired, OSError):
            pass

        return all_findings

    def _execute_fixes(self, tasks: list[RoutedTask]) -> tuple[int, str]:
        """Execute auto-fix for given tasks. Returns (files_changed, output)."""
        executor = Executor(self._repo, self._budget)
        total_files = 0
        outputs: list[str] = []

        # Group by action type
        has_lint = any(t.action == "ruff-fix" for t in tasks)
        if has_lint:
            files, output = executor.execute_ruff_fix()
            total_files += files
            outputs.append(output)

        return total_files, "\n".join(outputs)

    def _get_head_sha(self) -> str:
        """Get current HEAD SHA."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()[:12]

    # --- Protocol outputs ---

    def _write_manifest(self, result: IterationResult) -> dict[str, Any]:
        """Write manifest.json with run metadata and hashes."""
        manifest = {
            "run_id": self._run_id,
            "result": result.value,
            "iterations": self._iteration,
            "max_iter": self._max_iter,
            "repo": str(self._repo),
            "head_sha": self._get_head_sha(),
            "budget_used": {
                "files": self._budget.files_changed,
                "diff_lines": self._budget.diff_lines,
            },
            "budget_limit": {
                "max_files": self._budget.max_files,
                "max_diff_lines": self._budget.max_diff_lines,
            },
            "reports": [asdict(r) for r in self._reports],
            "created_utc": utcnow_iso(),
            "worklog_hash": self._hash_file(self._run_dir / "worklog.jsonl"),
        }
        path = self._run_dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest

    def _write_findings(self) -> Path:
        """Write findings.json with all findings across iterations."""
        path = self._run_dir / "findings.json"
        path.write_text(
            json.dumps(self._all_findings, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def _write_handoff(self, result: IterationResult) -> Path:
        """Write handoff.md with human-readable summary."""
        lines = [
            f"# Autopilot Run {self._run_id}",
            "",
            f"**Result:** {result.value}",
            f"**Iterations:** {self._iteration}/{self._max_iter}",
            f"**Total findings:** {len(self._all_findings)}",
            f"**Budget used:** {self._budget.files_changed} files, "
            f"{self._budget.diff_lines} diff lines",
            "",
            "## Iteration Summary",
            "",
        ]
        for report in self._reports:
            lines.append(
                f"- **Iter {report.iteration}:** {report.result.value} "
                f"({report.findings_count} findings, "
                f"{report.fixed_count} fixed, "
                f"{report.remaining_count} remaining, "
                f"{report.files_changed} files changed)"
            )
            if report.stop_reason:
                lines.append(f"  - Stop reason: {report.stop_reason}")
        lines.append("")

        if result == IterationResult.STOP:
            lines.extend(
                [
                    "## Manual Action Required",
                    "",
                    "Autopilot stopped due to hard stop criteria.",
                    "Review findings.json for details.",
                    "",
                ]
            )
        elif result == IterationResult.PASS:
            lines.extend(
                [
                    "## Handoff",
                    "",
                    "All CI checks pass. Ready for PR review.",
                    "",
                ]
            )

        path = self._run_dir / "handoff.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    @staticmethod
    def _hash_file(path: Path) -> str:
        """SHA-256 hash of file contents, or empty string if missing."""
        if not path.exists():
            return ""
        return sha256_str(path.read_text(encoding="utf-8"))

    # --- Status / query ---

    def status(self) -> dict[str, Any]:
        """Return current autopilot status."""
        return {
            "run_id": self._run_id,
            "iteration": self._iteration,
            "max_iter": self._max_iter,
            "budget": asdict(self._budget),
            "reports": [asdict(r) for r in self._reports],
            "lock": self._lock.status(),
        }

    @staticmethod
    def list_runs(state_dir: Path) -> list[dict[str, Any]]:
        """List all autopilot runs from state directory."""
        runs_dir = state_dir / "autopilot" / "runs"
        if not runs_dir.exists():
            return []
        runs: list[dict[str, Any]] = []
        for run_dir in sorted(runs_dir.iterdir()):
            manifest_path = run_dir / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                runs.append(
                    {
                        "run_id": manifest.get("run_id"),
                        "result": manifest.get("result"),
                        "iterations": manifest.get("iterations"),
                        "created_utc": manifest.get("created_utc"),
                    }
                )
        return runs

    @staticmethod
    def show_run(state_dir: Path, run_id: str) -> dict[str, Any]:
        """Show details of a specific autopilot run."""
        run_dir = state_dir / "autopilot" / "runs" / run_id
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            raise AutopilotError(f"Run not found: {run_id}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        handoff_path = run_dir / "handoff.md"
        if handoff_path.exists():
            manifest["handoff"] = handoff_path.read_text(encoding="utf-8")
        return manifest
