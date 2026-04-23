"""Environment Configuration — fail-closed env/tier separation.

Supports DEV, STAGING, PROD tiers with strict defaults.
PROD mode enforces: no debug, no CORS wildcard, no verbose logging.

Principle: fail-closed — unknown env values default to PROD restrictions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EnvTier(StrEnum):
    """Deployment environment tiers."""

    DEV = "DEV"
    STAGING = "STAGING"
    PROD = "PROD"


_TIER_MAP: dict[str, EnvTier] = {
    "dev": EnvTier.DEV,
    "development": EnvTier.DEV,
    "staging": EnvTier.STAGING,
    "stage": EnvTier.STAGING,
    "prod": EnvTier.PROD,
    "production": EnvTier.PROD,
}


@dataclass(frozen=True)
class EnvConfig:
    """Environment configuration with fail-closed defaults."""

    tier: EnvTier
    debug: bool
    verbose_logging: bool
    cors_allow_all: bool
    bind_host: str
    bind_port: int
    secret_masking: bool
    pii_redaction: bool
    strict_validation: bool
    max_request_size_bytes: int

    @property
    def is_prod(self) -> bool:
        return self.tier == EnvTier.PROD

    @property
    def is_dev(self) -> bool:
        return self.tier == EnvTier.DEV

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": str(self.tier),
            "debug": self.debug,
            "verbose_logging": self.verbose_logging,
            "cors_allow_all": self.cors_allow_all,
            "bind_host": self.bind_host,
            "bind_port": self.bind_port,
            "secret_masking": self.secret_masking,
            "pii_redaction": self.pii_redaction,
            "strict_validation": self.strict_validation,
            "max_request_size_bytes": self.max_request_size_bytes,
        }


# ---------------------------------------------------------------------------
# Tier-specific defaults
# ---------------------------------------------------------------------------

_TIER_DEFAULTS: dict[EnvTier, dict[str, Any]] = {
    EnvTier.DEV: {
        "debug": True,
        "verbose_logging": True,
        "cors_allow_all": True,
        "bind_host": "127.0.0.1",
        "bind_port": 8000,
        "secret_masking": True,
        "pii_redaction": False,
        "strict_validation": False,
        "max_request_size_bytes": 10 * 1024 * 1024,  # 10 MiB
    },
    EnvTier.STAGING: {
        "debug": False,
        "verbose_logging": True,
        "cors_allow_all": False,
        "bind_host": "127.0.0.1",
        "bind_port": 8000,
        "secret_masking": True,
        "pii_redaction": True,
        "strict_validation": True,
        "max_request_size_bytes": 5 * 1024 * 1024,  # 5 MiB
    },
    EnvTier.PROD: {
        "debug": False,
        "verbose_logging": False,
        "cors_allow_all": False,
        "bind_host": "127.0.0.1",
        "bind_port": 8000,
        "secret_masking": True,
        "pii_redaction": True,
        "strict_validation": True,
        "max_request_size_bytes": 2 * 1024 * 1024,  # 2 MiB
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_tier() -> EnvTier:
    """Detect the environment tier from env vars.

    Checks SSID_ENV, SSID_EMS_ENV, then defaults to DEV.
    Unknown values → PROD (fail-closed).
    """
    raw = os.environ.get("SSID_ENV") or os.environ.get("SSID_EMS_ENV") or ""
    raw = raw.strip().lower()
    if not raw:
        return EnvTier.DEV
    tier = _TIER_MAP.get(raw)
    if tier is None:
        # Fail-closed: unknown tier = PROD restrictions
        return EnvTier.PROD
    return tier


def get_config(tier: EnvTier | None = None) -> EnvConfig:
    """Build EnvConfig for the given or detected tier.

    Args:
        tier: Explicit tier override.  If None, auto-detected.

    Returns:
        Frozen EnvConfig with tier-appropriate defaults.
    """
    if tier is None:
        tier = detect_tier()
    defaults = _TIER_DEFAULTS.get(tier, _TIER_DEFAULTS[EnvTier.PROD])
    return EnvConfig(tier=tier, **defaults)


def validate_prod_safety(config: EnvConfig) -> list[str]:
    """Validate that PROD config has no unsafe settings.

    Returns list of violation descriptions (empty = safe).
    """
    violations: list[str] = []
    if config.tier != EnvTier.PROD:
        return violations

    if config.debug:
        violations.append("PROD must not have debug=True")
    if config.cors_allow_all:
        violations.append("PROD must not have cors_allow_all=True")
    if config.verbose_logging:
        violations.append("PROD must not have verbose_logging=True")
    if not config.secret_masking:
        violations.append("PROD must have secret_masking=True")
    if not config.pii_redaction:
        violations.append("PROD must have pii_redaction=True")
    if not config.strict_validation:
        violations.append("PROD must have strict_validation=True")
    if config.bind_host == "0.0.0.0":  # noqa: S104
        violations.append("PROD must not bind to 0.0.0.0")

    return violations
