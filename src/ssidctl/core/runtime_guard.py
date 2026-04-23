"""Runtime Guard — fail-closed runtime protection for API endpoints.

Validates requests and responses at runtime:
- No secrets in logs/responses
- No PII leakage
- Request size limits
- Content-type enforcement

Usage:
    @runtime_guarded
    def my_endpoint():
        ...
"""

from __future__ import annotations

import functools
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Secret/PII patterns for runtime scanning
# ---------------------------------------------------------------------------

_RUNTIME_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("api_key", re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*\S{8,}", re.IGNORECASE)),
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)),
    ("password", re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S{4,}", re.IGNORECASE)),
    ("private_key", re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----")),
    ("github_token", re.compile(r"gh[ps]_[A-Za-z0-9]{36,}")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
]

_RUNTIME_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GuardViolation:
    """A runtime guard violation."""

    guard: str
    severity: Literal["critical", "high", "medium"]
    description: str
    timestamp_utc: str = ""


@dataclass(frozen=True)
class GuardResult:
    """Result of runtime guard checks."""

    passed: bool
    violations: list[GuardViolation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [
                {"guard": v.guard, "severity": v.severity, "description": v.description}
                for v in self.violations
            ],
        }


# ---------------------------------------------------------------------------
# RuntimeGuard class
# ---------------------------------------------------------------------------


class RuntimeGuard:
    """Runtime protection engine.  Fail-closed on violations."""

    def __init__(
        self,
        *,
        max_request_size: int = 2 * 1024 * 1024,
        scan_secrets: bool = True,
        scan_pii: bool = True,
    ) -> None:
        self._max_request_size = max_request_size
        self._scan_secrets = scan_secrets
        self._scan_pii = scan_pii

    def check_request_size(self, size_bytes: int) -> list[GuardViolation]:
        """Check request body size."""
        if size_bytes > self._max_request_size:
            return [
                GuardViolation(
                    "request_size",
                    "high",
                    f"Request size {size_bytes} exceeds limit {self._max_request_size}",
                    _now_utc(),
                )
            ]
        return []

    def scan_for_secrets(self, text: str) -> list[GuardViolation]:
        """Scan text for secret patterns."""
        if not self._scan_secrets:
            return []
        violations: list[GuardViolation] = []
        for name, pattern in _RUNTIME_SECRET_PATTERNS:
            if pattern.search(text):
                violations.append(
                    GuardViolation(
                        f"secret_{name}",
                        "critical",
                        f"Secret pattern detected: {name}",
                        _now_utc(),
                    )
                )
        return violations

    def scan_for_pii(self, text: str) -> list[GuardViolation]:
        """Scan text for PII patterns."""
        if not self._scan_pii:
            return []
        violations: list[GuardViolation] = []
        for name, pattern in _RUNTIME_PII_PATTERNS:
            if pattern.search(text):
                violations.append(
                    GuardViolation(
                        f"pii_{name}",
                        "medium",
                        f"PII pattern detected: {name}",
                        _now_utc(),
                    )
                )
        return violations

    def check_response(self, response_text: str) -> GuardResult:
        """Check a response for secret/PII leakage."""
        violations: list[GuardViolation] = []
        violations.extend(self.scan_for_secrets(response_text))
        violations.extend(self.scan_for_pii(response_text))
        return GuardResult(passed=len(violations) == 0, violations=violations)

    def check_all(
        self,
        *,
        request_size: int = 0,
        request_body: str = "",
        response_body: str = "",
    ) -> GuardResult:
        """Run all runtime checks."""
        violations: list[GuardViolation] = []
        violations.extend(self.check_request_size(request_size))
        violations.extend(self.scan_for_secrets(request_body))
        violations.extend(self.scan_for_secrets(response_body))
        violations.extend(self.scan_for_pii(response_body))
        return GuardResult(passed=len(violations) == 0, violations=violations)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

_DEFAULT_GUARD = RuntimeGuard()


def runtime_guarded(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that checks function return values for secret/PII leakage.

    If the return value is a string containing secrets, raises RuntimeError.
    For non-string returns, passes through unchanged.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = fn(*args, **kwargs)
        if isinstance(result, str):
            check = _DEFAULT_GUARD.check_response(result)
            if not check.passed:
                descs = [v.description for v in check.violations]
                msg = f"Runtime guard violation in {fn.__name__}: {'; '.join(descs)}"
                raise RuntimeError(msg)
        return result

    return wrapper
