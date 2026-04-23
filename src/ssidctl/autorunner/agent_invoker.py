"""AutoRunner P3 — Agent Invoker: triggers Claude CLI on AR FAIL.

Only invoked when:
  1. ar_result["status"] != "PASS"
  2. The AR_ID has an agent_id configured
  3. Claude CLI is available (graceful degradation otherwise)
"""
from __future__ import annotations

from dataclasses import dataclass

from ssidctl.claude.subprocess_driver import EXIT_CLI_NOT_FOUND, invoke_claude

# Sentinel for "no agent configured for this AR ID"
NO_AGENT_FOR_AR = "NO_AGENT_FOR_AR"

# Model name → full Claude model ID
_MODEL_MAP = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

# Agent config per AR module (agent_id, model)
_AGENT_CONFIG: dict[str, tuple[str, str]] = {
    "AR-01": ("SEC-05", "opus"),
    "AR-03": ("OPS-08", "haiku"),
    "AR-04": ("CMP-14", "sonnet"),
    "AR-06": ("DOC-20", "haiku"),
    "AR-09": ("ARS-29", "opus"),
    "AR-10": ("CMP-14", "sonnet"),
}

# Prompt template per AR module
_PROMPT_TEMPLATES: dict[str, str] = {
    "AR-01": (
        "You are SEC-05, SSID security auditor. A PII scan returned FAIL_POLICY.\n"
        "Result: {result}\n"
        "Summarize: which file/line has PII, probable cause, recommended fix. "
        "Output plain text only. No code changes."
    ),
    "AR-03": (
        "You are OPS-08, SSID evidence auditor. Evidence anchoring returned an error.\n"
        "Result: {result}\n"
        "Diagnose: why did anchoring fail, which files are unanchored, recommended action."
    ),
    "AR-04": (
        "You are CMP-14, SSID compliance auditor. DORA IR plan check returned FAIL_DORA.\n"
        "Result: {result}\n"
        "List missing IRP paths. For each, state whether template stub creation is appropriate."
    ),
    "AR-06": (
        "You are DOC-20, SSID documentation auditor. Doc generation failed.\n"
        "Result: {result}\n"
        "Identify which chart/module YAML caused the failure and why."
    ),
    "AR-09": (
        "You are ARS-29, SSID fairness auditor. Bias/fairness audit returned FAIL_POLICY.\n"
        "Result: {result}\n"
        "Identify which demographic group failed parity/opportunity threshold and likely cause."
    ),
    "AR-10": (
        "You are CMP-14, SSID compliance auditor. Fee distribution audit returned FAIL_POLICY.\n"
        "Result: {result}\n"
        "Identify which policy check failed (7-Säulen sum, subscription model, POFI, DAO params)."
    ),
}


@dataclass
class AgentInvokerResult:
    invoked: bool
    agent_id: str = ""
    model: str = ""
    analysis: str = ""
    exit_code: int = 0
    reason: str = ""     # populated when invoked=False


class AgentInvoker:
    def invoke_on_fail(
        self,
        ar_id: str,
        ar_result: dict,
        timeout: int = 60,
    ) -> AgentInvokerResult:
        """Invoke Claude agent if ar_result is a FAIL status.

        Returns AgentInvokerResult. Never raises — failures are captured in result.
        """
        # Do not invoke on PASS
        status = ar_result.get("status", "ERROR")
        if status == "PASS":
            return AgentInvokerResult(invoked=False, reason="status=PASS")

        # Look up agent config
        if ar_id not in _AGENT_CONFIG:
            return AgentInvokerResult(invoked=False, reason=NO_AGENT_FOR_AR)

        agent_id, model_key = _AGENT_CONFIG[ar_id]
        model_full = _MODEL_MAP.get(model_key, "claude-haiku-4-5-20251001")
        template = _PROMPT_TEMPLATES.get(ar_id, "AR {ar_id} failed. Result: {result}")
        prompt = template.format(ar_id=ar_id, result=str(ar_result)[:2000])

        response = invoke_claude(prompt=prompt, model=model_full, timeout=timeout)

        if response.exit_code == EXIT_CLI_NOT_FOUND:
            return AgentInvokerResult(
                invoked=False,
                agent_id=agent_id,
                model=model_full,
                exit_code=response.exit_code,
                reason=f"CLI not found: {response.error}",
            )

        return AgentInvokerResult(
            invoked=True,
            agent_id=agent_id,
            model=model_full,
            analysis=response.text,
            exit_code=response.exit_code,
        )
