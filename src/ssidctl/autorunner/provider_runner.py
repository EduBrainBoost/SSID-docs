"""Provider-aware Runner: executes pipeline with multi-provider failover.

Hybrid Two-Tier Architecture:
- Tier 1 (Primary): Direct API providers (OpenAI, Anthropic, Gemini) - preferred
- Tier 2 (Fallback): CLI providers (when API unavailable)

This runner replaces the hardcoded python_script worker with a provider-aware
execution that can fall back to alternative providers on failure.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from ssidctl.autorunner.events import RunEvent, RunEventStream
from ssidctl.autorunner.models import AutoRunnerRun, FailureClass, ProviderAttempt, RunStatus
from ssidctl.core.provider_registry import (
    ProviderSelector,
    ProviderTier,
    build_provider_command,
    classify_error,
    get_registry,
    get_selector,
)

logger = logging.getLogger(__name__)


class ProviderRunResult(BaseModel):
    run_id: str
    success: bool
    summary: str
    provider_used: str | None = None
    provider_tier: str | None = None
    model_used: str | None = None
    provider_attempts: list[dict] = []
    evidence_manifest: str | None = None
    final_report: str | None = None
    stdout: str = ""
    stderr: str = ""


class ProviderRunner:
    def __init__(self, selector: ProviderSelector | None = None) -> None:
        self._selector = selector or get_selector()
        self._registry = get_registry()

    async def run_async(self, run: AutoRunnerRun, events: RunEventStream) -> ProviderRunResult:
        if run.status not in (RunStatus.QUEUED, RunStatus.PLANNED):
            err = f"Can only run a QUEUED or PLANNED run, got: {run.status}"
            logger.error(err)
            run.error = err
            run.transition(RunStatus.FAILED)
            return ProviderRunResult(run_id=run.run_id, success=False, summary=err)

        run.transition(RunStatus.RUNNING)
        events.append(RunEvent(type="run_started", payload={"run_id": run.run_id}))
        run.provider_attempts = []

        try:
            result = await self._execute_with_provider_async(run, events)
            if result.success:
                run.transition(RunStatus.SUCCEEDED)
                run.evidence_manifest = result.evidence_manifest
                run.final_report = result.final_report
                run.final_provider = result.provider_used
                events.append(
                    RunEvent(
                        type="run_succeeded",
                        payload={
                            "summary": result.summary,
                            "provider": result.provider_used,
                            "provider_tier": result.provider_tier,
                            "model_used": result.model_used,
                        },
                    )
                )
            else:
                run.failure_class = FailureClass.PROVIDER_UNAVAILABLE
                run.transition(RunStatus.FAILED)
                run.error = result.summary
                events.append(
                    RunEvent(
                        type="run_failed",
                        payload={
                            "error": result.summary,
                            "provider_attempts": result.provider_attempts,
                        },
                    )
                )
            return result
        except Exception as exc:
            logger.exception("ProviderRunner execution error")
            run.failure_class = FailureClass.TECHNICAL
            run.error = str(exc)
            run.transition(RunStatus.FAILED)
            events.append(
                RunEvent(
                    type="run_failed",
                    payload={"error": str(exc), "failure_class": "technical"},
                )
            )
            return ProviderRunResult(
                run_id=run.run_id,
                success=False,
                summary=f"Execution error: {exc}",
            )

    def run(self, run: AutoRunnerRun, events: RunEventStream) -> ProviderRunResult:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.run_async(run, events))
                    return future.result(timeout=600)
            else:
                return asyncio.run(self.run_async(run, events))
        except RuntimeError:
            return asyncio.run(self.run_async(run, events))

    async def _execute_with_provider_async(
        self, run: AutoRunnerRun, events: RunEventStream
    ) -> ProviderRunResult:
        prompt = run.task_id
        cwd = self._resolve_cwd(run)

        capability = self._infer_capability(run)
        logger.info(
            "ProviderRunner: executing run %s with capability %s",
            run.run_id,
            capability,
        )

        max_attempts = len(self._registry.list_providers())
        exclude: set[str] = set()
        attempts: list[ProviderAttempt] = []

        last_stderr = ""
        for attempt_num in range(max_attempts):
            provider = self._selector.select_provider(
                capability=capability, exclude=exclude, prefer_free=False, prefer_api=False
            )
            if provider is None:
                return ProviderRunResult(
                    run_id=run.run_id,
                    success=False,
                    summary=f"No available provider after {attempt_num} attempts",
                    provider_attempts=[a.model_dump() for a in attempts],
                )

            attempt = ProviderAttempt(
                provider_id=provider.provider_id,
                started_at=datetime.now(UTC).isoformat(),
            )
            events.append(
                RunEvent(
                    type="provider_attempt",
                    payload={
                        "attempt": attempt_num + 1,
                        "provider": provider.provider_id,
                        "tier": provider.tier.value,
                        "capability": capability,
                    },
                )
            )

            logger.info(
                "ProviderRunner: attempt %d using provider %s (tier=%s)",
                attempt_num + 1,
                provider.provider_id,
                provider.tier.value,
            )

            if provider.tier == ProviderTier.API:
                success, stdout, stderr, model_used = await self._execute_api_provider_async(
                    provider.provider_id, prompt
                )
            else:
                success, stdout, stderr = self._execute_provider_command(
                    provider.provider_id, prompt, cwd
                )
                model_used = None
            last_stderr = stderr

            attempt.finished_at = datetime.now(UTC).isoformat()
            attempt.success = success
            run.provider_attempts.append(attempt)

            if success:
                self._registry.mark_available(provider.provider_id)
                run.selected_provider = provider.provider_id
                return ProviderRunResult(
                    run_id=run.run_id,
                    success=True,
                    summary=f"Completed successfully with {provider.provider_id}",
                    provider_used=provider.provider_id,
                    provider_tier=provider.tier.value,
                    model_used=model_used,
                    provider_attempts=[a.model_dump() for a in run.provider_attempts],
                    stdout=stdout,
                    stderr=stderr,
                    evidence_manifest=f"evidence://{run.run_id}/manifest.yaml",
                )

            error_class = classify_error(1, stderr)
            attempt.error_class = error_class.value
            attempt.error_message = stderr[:500] if stderr else ""
            self._registry.mark_failed(provider.provider_id, stderr, error_class)
            exclude.add(provider.provider_id)

            logger.warning(
                "ProviderRunner: provider %s failed with %s: %s",
                provider.provider_id,
                error_class.value,
                stderr[:200] if stderr else "no output",
            )

        return ProviderRunResult(
            run_id=run.run_id,
            success=False,
            summary=(
                f"All providers failed. Last error: "
                f"{last_stderr[:200] if last_stderr else 'unknown'}"
            ),
            provider_attempts=[a.model_dump() for a in run.provider_attempts],
        )

    async def _execute_api_provider_async(
        self, provider_id: str, prompt: str
    ) -> tuple[bool, str, str, str | None]:
        from ssidctl.core.api_providers import get_api_registry

        api_registry = get_api_registry()
        api_provider = api_registry.get_provider(provider_id)
        if not api_provider:
            return False, "", f"API provider {provider_id} not found in registry", None

        if not api_provider.is_available():
            return False, "", f"API provider {provider_id} not available (check API key)", None

        try:
            result = await api_provider.execute(prompt)
            if result.success:
                return True, result.content, "", result.model_used
            return False, "", result.error, None
        except Exception as e:
            logger.exception("API provider %s execution error", provider_id)
            return False, str(e), "", None

    def _execute_provider_command(
        self, provider_id: str, prompt: str, cwd: Path | None
    ) -> tuple[bool, str, str]:
        import shutil

        registry = get_registry()
        provider = registry.get_provider(provider_id)
        if not provider:
            return False, "", f"Provider {provider_id} not found in registry"

        cmd_path = shutil.which(provider.command)
        if not cmd_path:
            return False, "", f"Command not found: {provider.command}"

        cmd = build_provider_command(provider, prompt)
        # Windows fix: use resolved path from shutil.which() so .CMD/.EXE
        # wrappers are found by subprocess.run() without shell=True
        if cmd and cmd[0] == provider.command:
            cmd[0] = cmd_path

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(cwd) if cwd else None,
            )
            if result.returncode == 0:
                return True, result.stdout, result.stderr
            return False, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Provider {provider_id} timed out"
        except Exception as e:
            return False, "", str(e)

    def _resolve_cwd(self, run: AutoRunnerRun) -> Path | None:
        repo_root = Path.cwd()
        if run.scope.repo:
            potential = repo_root.parent / run.scope.repo
            if potential.exists():
                return potential
        return repo_root

    def _infer_capability(self, run: AutoRunnerRun) -> str:
        task_lower = run.task_id.lower()
        if "implement" in task_lower or "fix" in task_lower or "patch" in task_lower:
            return "implementation"
        if "review" in task_lower or "audit" in task_lower:
            return "review"
        if "analyze" in task_lower or "investigate" in task_lower:
            return "analysis"
        return "planning"
