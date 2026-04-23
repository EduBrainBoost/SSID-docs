"""Claude Code CLI subprocess driver — AI Gateway.

Invokes `claude --print` or `claude -p` for non-interactive operation.
Enforces: model allowlist, pre-flight prompt redaction, rate/spend limits,
output guard (no direct execution of LLM output).
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field

from ssidctl.core.hashing import sha256_bytes
from ssidctl.core.sanitizer import contains_secrets, sanitize_text

# --- Model Allowlist ---
ALLOWED_MODELS: set[str] = {
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
}

# --- Output Guard: patterns that must not appear in output ---
_OUTPUT_DENY_PATTERNS: list[tuple[str, str]] = [
    ("rm -rf", "rm -rf"),
    ("DROP TABLE", "drop table"),
    ("DELETE FROM", "delete from"),
    ("format c:", "format c:"),
    ("sudo rm", "sudo rm"),
    ("git push --force", "git push --force"),
    ("git reset --hard", "git reset --hard"),
    ("--no-verify", "--no-verify"),
]

# --- Exit Code Constants ---
EXIT_CLI_NOT_FOUND = -1
EXIT_TIMEOUT = -2
EXIT_MODEL_REJECTED = -3
EXIT_RATE_LIMITED = -4

# --- Null SHA-256 for error responses ---
_NULL_SHA256 = "sha256:" + "0" * 64


@dataclass
class ClaudeResponse:
    """Response from Claude CLI invocation."""

    text: str
    sha256: str
    bytes_len: int
    exit_code: int
    prompt_sha256: str = ""
    prompt_bytes_len: int = 0
    prompt_redacted: bool = False
    output_guard_flags: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class RateLimiter:
    """Simple in-process rate limiter for Claude invocations."""

    max_calls_per_minute: int = 10
    max_calls_per_hour: int = 100
    _calls: list[float] = field(default_factory=list)

    def check(self) -> str | None:
        """Return error message if rate limit exceeded, else None."""
        now = time.time()
        kept: list[float] = []
        minute_count = 0
        for t in self._calls:
            if now - t < 3600:
                kept.append(t)
                if now - t < 60:
                    minute_count += 1
        self._calls = kept
        if minute_count >= self.max_calls_per_minute:
            return f"Rate limit: {self.max_calls_per_minute} calls/min exceeded"
        if len(self._calls) >= self.max_calls_per_hour:
            return f"Rate limit: {self.max_calls_per_hour} calls/hour exceeded"
        return None

    def record(self) -> None:
        self._calls.append(time.time())


# Module-level rate limiter (single-flight, Concurrency=1)
_rate_limiter = RateLimiter()


def _redact_prompt(prompt: str) -> tuple[str, bool]:
    """Pre-flight prompt redaction: strip secrets/PII before sending to LLM."""
    if contains_secrets(prompt):
        result = sanitize_text(prompt)
        return result.text, True
    return prompt, False


def _guard_output(text: str) -> list[str]:
    """Output guard: flag dangerous patterns in LLM response."""
    flags: list[str] = []
    lower = text.lower()
    for display, lowered in _OUTPUT_DENY_PATTERNS:
        if lowered in lower:
            flags.append(f"OUTPUT_GUARD: dangerous pattern '{display}' in response")
    return flags


def invoke_claude(
    prompt: str,
    command: str = "claude",
    timeout: int = 120,
    cwd: str | None = None,
    model: str | None = None,
    skip_redaction: bool = False,
) -> ClaudeResponse:
    """Invoke Claude Code CLI with a prompt via the AI Gateway.

    Enforces:
    - Pre-flight prompt redaction (secrets/PII stripped before LLM call)
    - Model allowlist validation
    - Rate limiting (per-minute and per-hour)
    - Output guard (flags dangerous patterns in response)

    Args:
        prompt: The prompt text to send.
        command: Claude CLI command name.
        timeout: Max seconds to wait.
        cwd: Working directory for the subprocess.
        model: Model to use (must be in ALLOWED_MODELS if set).
        skip_redaction: Skip prompt redaction (for pre-sanitized prompts).

    Returns:
        ClaudeResponse with text, hashes, and gateway metadata.
    """
    # --- Model Allowlist ---
    if model and model not in ALLOWED_MODELS:
        return ClaudeResponse(
            text="",
            sha256=_NULL_SHA256,
            bytes_len=0,
            exit_code=EXIT_MODEL_REJECTED,
            error=f"Model '{model}' not in allowlist: {sorted(ALLOWED_MODELS)}",
        )

    # --- Rate Limiting ---
    rate_err = _rate_limiter.check()
    if rate_err:
        return ClaudeResponse(
            text="",
            sha256=_NULL_SHA256,
            bytes_len=0,
            exit_code=EXIT_RATE_LIMITED,
            error=rate_err,
        )

    # --- Pre-flight Prompt Redaction ---
    prompt_raw = prompt.encode("utf-8")
    prompt_sha = sha256_bytes(prompt_raw)
    prompt_len = len(prompt_raw)

    if skip_redaction:
        safe_prompt = prompt
        was_redacted = False
    else:
        safe_prompt, was_redacted = _redact_prompt(prompt)

    # --- Invoke CLI ---
    try:
        cmd = [command, "-p", safe_prompt]
        if model:
            cmd.extend(["--model", model])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        response_text = result.stdout
        raw = response_text.encode("utf-8")

        # --- Output Guard ---
        output_flags = _guard_output(response_text)

        _rate_limiter.record()

        return ClaudeResponse(
            text=response_text,
            sha256=sha256_bytes(raw),
            bytes_len=len(raw),
            exit_code=result.returncode,
            prompt_sha256=prompt_sha,
            prompt_bytes_len=prompt_len,
            prompt_redacted=was_redacted,
            output_guard_flags=output_flags,
            error=result.stderr if result.returncode != 0 else None,
        )

    except FileNotFoundError:
        return ClaudeResponse(
            text="",
            sha256=_NULL_SHA256,
            bytes_len=0,
            exit_code=EXIT_CLI_NOT_FOUND,
            error=f"Claude CLI not found: {command}",
        )
    except subprocess.TimeoutExpired:
        return ClaudeResponse(
            text="",
            sha256=_NULL_SHA256,
            bytes_len=0,
            exit_code=EXIT_TIMEOUT,
            error=f"Claude CLI timed out after {timeout}s",
        )
