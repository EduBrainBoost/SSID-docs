"""Provider Reality Report: Scans local system for actual provider availability.

Classifies each registered provider as:
- REAL_CLI: Binary found via shutil.which and health-check passes
- REAL_CLI_NO_HEALTH: Binary found but health-check fails or times out
- MOCK: Provider uses mock execution path (python scripts/ems_mock_provider.py)
- STUB: Provider uses stub execution path (python -c print(...))
- API_ONLY: Provider is API-tier (no local binary expected)
- UNAVAILABLE: Binary not found on PATH

No external API calls are made. Only local binary presence is checked.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ssidctl.core.provider_registry import (
    DEFAULT_PROVIDERS,
    MOCK_PROVIDER,
    STUB_PROVIDER,
    Provider,
<<<<<<< HEAD
    ProviderTier,
=======
    ProviderRegistry,
    ProviderTier,
    get_registry,
>>>>>>> origin/chore/artifact-cleanup-20260331
)


class RealityClass(StrEnum):
    REAL_CLI = "REAL_CLI"
    REAL_CLI_NO_HEALTH = "REAL_CLI_NO_HEALTH"
    MOCK = "MOCK"
    STUB = "STUB"
    API_ONLY = "API_ONLY"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class ProviderScanResult:
    provider_id: str
    command: str
    tier: str
    reality_class: RealityClass
    binary_path: str | None = None
    health_check_passed: bool | None = None
    health_check_output: str | None = None
    health_check_error: str | None = None
    cost_tier: str = "free"
    capabilities: list[str] = field(default_factory=list)
    prompt_arg: str = "positional"
    scanned_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "command": self.command,
            "tier": self.tier,
            "reality_class": self.reality_class.value,
            "binary_path": self.binary_path,
            "health_check_passed": self.health_check_passed,
            "health_check_output": self.health_check_output,
            "health_check_error": self.health_check_error,
            "cost_tier": self.cost_tier,
            "capabilities": self.capabilities,
            "prompt_arg": self.prompt_arg,
            "scanned_at": self.scanned_at,
        }


def scan_provider_availability(
    health_check_timeout: int = 5,
) -> dict[str, ProviderScanResult]:
    """Scan all registered providers for local availability.

    Returns a dict keyed by provider_id with scan results.
    No external API calls are made.
    """
    registry = _build_full_provider_list()
    results: dict[str, ProviderScanResult] = {}

    for provider in registry:
        result = _scan_single_provider(provider, health_check_timeout)
        results[provider.provider_id] = result

    return results


def _build_full_provider_list() -> list[Provider]:
    """Build complete provider list including mock/stub for scanning."""
    providers: list[Provider] = []
    for pd in DEFAULT_PROVIDERS:
        providers.append(Provider.from_dict(pd))
    providers.append(Provider.from_dict(MOCK_PROVIDER))
    providers.append(Provider.from_dict(STUB_PROVIDER))
    return providers


def _scan_single_provider(
    provider: Provider, health_check_timeout: int
) -> ProviderScanResult:
    """Scan a single provider for availability."""
    tier = getattr(provider, "tier", ProviderTier.CLI)
    prompt_arg = getattr(provider, "prompt_arg", "positional")

    # API-only providers: no local binary expected
    if tier == ProviderTier.API:
        return ProviderScanResult(
            provider_id=provider.provider_id,
            command=provider.command,
            tier=tier.value if hasattr(tier, "value") else str(tier),
            reality_class=RealityClass.API_ONLY,
            cost_tier=provider.cost_tier.value,
            capabilities=list(provider.capabilities),
            prompt_arg=prompt_arg,
        )

    # Stub providers: always use python -c
    if prompt_arg == "stub":
        python_path = shutil.which("python") or shutil.which("python3")
        return ProviderScanResult(
            provider_id=provider.provider_id,
            command=provider.command,
            tier=tier.value if hasattr(tier, "value") else str(tier),
            reality_class=RealityClass.STUB,
            binary_path=python_path,
            health_check_passed=python_path is not None,
            cost_tier=provider.cost_tier.value,
            capabilities=list(provider.capabilities),
            prompt_arg=prompt_arg,
        )

    # Mock providers: use python + mock script
    if prompt_arg == "mock":
        python_path = shutil.which("python") or shutil.which("python3")
        return ProviderScanResult(
            provider_id=provider.provider_id,
            command=provider.command,
            tier=tier.value if hasattr(tier, "value") else str(tier),
            reality_class=RealityClass.MOCK,
            binary_path=python_path,
            health_check_passed=python_path is not None,
            cost_tier=provider.cost_tier.value,
            capabilities=list(provider.capabilities),
            prompt_arg=prompt_arg,
        )

    # CLI providers: check binary presence and health
    cmd_path = shutil.which(provider.command)
    if not cmd_path:
        return ProviderScanResult(
            provider_id=provider.provider_id,
            command=provider.command,
            tier=tier.value if hasattr(tier, "value") else str(tier),
            reality_class=RealityClass.UNAVAILABLE,
            binary_path=None,
            health_check_passed=False,
            cost_tier=provider.cost_tier.value,
            capabilities=list(provider.capabilities),
            prompt_arg=prompt_arg,
        )

    # Binary found -- run health check
    health_passed, health_output, health_error = _run_health_check(
        provider, health_check_timeout
    )

    if health_passed:
        reality_class = RealityClass.REAL_CLI
    else:
        reality_class = RealityClass.REAL_CLI_NO_HEALTH

    return ProviderScanResult(
        provider_id=provider.provider_id,
        command=provider.command,
        tier=tier.value if hasattr(tier, "value") else str(tier),
        reality_class=reality_class,
        binary_path=cmd_path,
        health_check_passed=health_passed,
        health_check_output=health_output,
        health_check_error=health_error,
        cost_tier=provider.cost_tier.value,
        capabilities=list(provider.capabilities),
        prompt_arg=prompt_arg,
    )


def _run_health_check(
    provider: Provider, timeout: int
) -> tuple[bool, str | None, str | None]:
    """Run health check for a provider. No external API calls."""
    try:
        result = subprocess.run(
            [provider.command] + provider.health_check_args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()[:200], None
        return False, None, result.stderr.strip()[:200]
    except subprocess.TimeoutExpired:
        return False, None, f"Health check timed out after {timeout}s"
    except FileNotFoundError:
        return False, None, f"Command not found: {provider.command}"
    except Exception as e:
        return False, None, str(e)[:200]


def generate_reality_report(
    health_check_timeout: int = 5,
) -> dict[str, Any]:
    """Generate a structured reality report for all providers.

    Returns a dict with:
    - scan_timestamp: ISO timestamp of the scan
    - summary: counts by reality class
    - providers: list of per-provider scan results
    - non_interactive_capable: whether at least one real provider is available
    - verdict: overall assessment string
    """
    scan_results = scan_provider_availability(health_check_timeout)
    timestamp = datetime.now(UTC).isoformat()

    # Count by class
    summary: dict[str, int] = {}
    for result in scan_results.values():
        cls_name = result.reality_class.value
        summary[cls_name] = summary.get(cls_name, 0) + 1

    # Check if non-interactive run is possible
    real_providers = [
        r
        for r in scan_results.values()
        if r.reality_class in (RealityClass.REAL_CLI, RealityClass.REAL_CLI_NO_HEALTH)
    ]
    mock_or_stub = [
        r
        for r in scan_results.values()
        if r.reality_class in (RealityClass.MOCK, RealityClass.STUB)
    ]
    api_only = [
        r for r in scan_results.values() if r.reality_class == RealityClass.API_ONLY
    ]
    unavailable = [
        r for r in scan_results.values() if r.reality_class == RealityClass.UNAVAILABLE
    ]

    if len(real_providers) > 0:
        verdict = (
            f"PARTIAL_CAPABILITY: {len(real_providers)} CLI provider(s) found, "
            f"{len(unavailable)} unavailable, {len(api_only)} API-only, "
            f"{len(mock_or_stub)} mock/stub"
        )
    elif len(mock_or_stub) > 0:
        verdict = (
            f"MOCK_ONLY: No real CLI providers found. "
            f"{len(mock_or_stub)} mock/stub available for testing. "
            f"{len(api_only)} API-only (require API keys)."
        )
    else:
        verdict = (
            f"NO_PROVIDERS: No CLI providers found. "
            f"{len(api_only)} API-only (require API keys)."
        )

    return {
        "scan_timestamp": timestamp,
        "summary": summary,
        "providers": [r.to_dict() for r in scan_results.values()],
        "real_cli_count": len(real_providers),
        "mock_stub_count": len(mock_or_stub),
        "api_only_count": len(api_only),
        "unavailable_count": len(unavailable),
        "non_interactive_capable": len(real_providers) > 0,
        "verdict": verdict,
    }
