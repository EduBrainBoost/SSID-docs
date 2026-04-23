"""Data Minimization Policy enforcement — MINIMAL default + FORENSIC TTL.

Centralizes all data-minimization controls required by DSGVO Art.5(1)(c)
and the SSID retention policy. Integrates with existing log_mode.py and
ttl_purge.py modules but provides a single policy object that can be
loaded from environment variables and validated at startup.

Environment variables:
    SSID_LOG_MODE          MINIMAL (default) | FORENSIC
    SSID_RETENTION_TTL     Hours to retain forensic data (default 72)
    SSID_REDACTION_ENABLED 0|1 (default 1)
    SSID_PROMPT_PERSIST    0|1 (default 0)
    SSID_STDOUT_PERSIST    0|1 (default 0)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class LogMode(Enum):
    """Logging verbosity mode."""

    MINIMAL = "MINIMAL"
    FORENSIC = "FORENSIC"


@dataclass(frozen=True)
class DataMinPolicy:
    """Immutable data-minimization policy.

    Attributes:
        log_mode: MINIMAL strips prompts/stdout/responses; FORENSIC keeps all.
        retention_ttl_hours: Maximum hours to retain forensic artifacts.
                             Only meaningful when log_mode is FORENSIC.
                             Default 72 hours.
        redaction_enabled: When True, PII/secrets are redacted before persistence.
        prompt_persistence: When True, raw prompts may be persisted.
                            Must be False in MINIMAL mode.
        stdout_persistence: When True, raw stdout may be persisted.
                            Must be False in MINIMAL mode.
    """

    log_mode: LogMode = LogMode.MINIMAL
    retention_ttl_hours: int = 72
    redaction_enabled: bool = True
    prompt_persistence: bool = False
    stdout_persistence: bool = False


def _parse_bool(value: str, default: bool = False) -> bool:
    """Parse a string to boolean (1/true/yes -> True, else False)."""
    if not value:
        return default
    return value.strip().lower() in ("1", "true", "yes")


def load_policy(env: dict[str, str] | None = None) -> DataMinPolicy:
    """Load data-minimization policy from environment variables.

    Args:
        env: Optional environment dict override (defaults to os.environ).

    Returns:
        A frozen DataMinPolicy instance reflecting the current configuration.
    """
    if env is None:
        env = dict(os.environ)

    raw_mode = env.get("SSID_LOG_MODE", "MINIMAL").upper().strip()
    if raw_mode == "FORENSIC":
        log_mode = LogMode.FORENSIC
    else:
        log_mode = LogMode.MINIMAL

    ttl_raw = env.get("SSID_RETENTION_TTL", "72")
    try:
        retention_ttl_hours = int(ttl_raw)
    except (ValueError, TypeError):
        retention_ttl_hours = 72

    redaction_enabled = _parse_bool(
        env.get("SSID_REDACTION_ENABLED", "1"), default=True
    )
    prompt_persistence = _parse_bool(
        env.get("SSID_PROMPT_PERSIST", "0"), default=False
    )
    stdout_persistence = _parse_bool(
        env.get("SSID_STDOUT_PERSIST", "0"), default=False
    )

    return DataMinPolicy(
        log_mode=log_mode,
        retention_ttl_hours=retention_ttl_hours,
        redaction_enabled=redaction_enabled,
        prompt_persistence=prompt_persistence,
        stdout_persistence=stdout_persistence,
    )


class PolicyViolation(Exception):
    """Raised when the current configuration violates data-minimization rules."""


def enforce_policy(policy: DataMinPolicy | None = None) -> list[str]:
    """Validate that the given policy is internally consistent.

    Rules enforced:
    1. MINIMAL mode must NOT allow prompt or stdout persistence.
    2. FORENSIC mode must have a positive retention TTL.
    3. Redaction must be enabled (only explicit override can disable).

    Args:
        policy: Policy to validate.  Loads from env if None.

    Returns:
        List of violation descriptions (empty if compliant).

    Raises:
        PolicyViolation: If any violations are found.
    """
    if policy is None:
        policy = load_policy()

    violations: list[str] = []

    # Rule 1: MINIMAL mode prohibits prompt/stdout persistence
    if policy.log_mode == LogMode.MINIMAL:
        if policy.prompt_persistence:
            violations.append(
                "MINIMAL mode forbids prompt persistence "
                "(SSID_PROMPT_PERSIST must be 0)"
            )
        if policy.stdout_persistence:
            violations.append(
                "MINIMAL mode forbids stdout persistence "
                "(SSID_STDOUT_PERSIST must be 0)"
            )

    # Rule 2: FORENSIC mode requires a positive TTL
    if policy.log_mode == LogMode.FORENSIC:
        if policy.retention_ttl_hours <= 0:
            violations.append(
                "FORENSIC mode requires positive retention TTL "
                f"(got {policy.retention_ttl_hours}h)"
            )

    # Rule 3: Redaction should be enabled by default
    if not policy.redaction_enabled:
        violations.append(
            "Redaction is disabled — PII/secrets may leak into persistence layer"
        )

    if violations:
        raise PolicyViolation(
            f"Data minimization policy violated: {'; '.join(violations)}"
        )

    return violations
