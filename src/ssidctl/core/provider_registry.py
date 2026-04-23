"""Provider Registry: Multi-provider support for EMS runner system.

Hybrid Two-Tier Architecture:
- Tier 1 (Primary): Direct API providers (OpenAI, Anthropic, Gemini) - CI-friendly
- Tier 2 (Fallback): CLI providers (claude, codex, gemini, copilot)

API providers are preferred for production runs as they:
- Are non-interactive (work in CI/automation)
- Have better error handling and rate limit awareness
- Provide consistent response formats
- No terminal/TTY dependencies

CLI providers are kept as best-effort fallbacks for edge cases.

Removed providers (2026-03-29):
- opencode: never verified as working CLI, removed from default failover
- kilo: never verified as working CLI, removed from default failover
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ssidctl.core.api_providers import APIProviderRegistry

logger = logging.getLogger(__name__)


class ProviderErrorClass(StrEnum):
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    TIMEOUT = "timeout"
    COMMAND_NOT_FOUND = "command_not_found"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    QUOTA_EXCEEDED = "quota_exceeded"
    NONZERO_EXIT = "nonzero_exit"
    UNKNOWN_PROVIDER_FAILURE = "unknown_provider_failure"


class CostTier(StrEnum):
    FREE = "free"
    PAID = "paid"


class ProviderTier(StrEnum):
    API = "api"
    CLI = "cli"
    MOCK = "mock"
    STUB = "stub"


class ProviderStatus(StrEnum):
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


@dataclass
class Provider:
    provider_id: str
    command: str
    health_check_args: list[str] = field(default_factory=lambda: ["--version"])
    availability: ProviderStatus = ProviderStatus.AVAILABLE
    priority: int = 100
    cost_tier: CostTier = CostTier.FREE
    tier: ProviderTier = ProviderTier.CLI
    capabilities: list[str] = field(
        default_factory=lambda: ["planning", "implementation", "review"]
    )
    enabled: bool = True
    last_check: str | None = None
    last_error: str | None = None
    rate_limit_until: str | None = None
    prompt_arg: str = "positional"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "command": self.command,
            "health_check_args": self.health_check_args,
            "availability": self.availability.value,
            "priority": self.priority,
            "cost_tier": self.cost_tier.value,
            "tier": self.tier.value,
            "capabilities": self.capabilities,
            "enabled": self.enabled,
            "last_check": self.last_check,
            "last_error": self.last_error,
            "rate_limit_until": self.rate_limit_until,
            "prompt_arg": self.prompt_arg,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Provider:
        return cls(
            provider_id=d["provider_id"],
            command=d["command"],
            health_check_args=d.get("health_check_args", ["--version"]),
            availability=ProviderStatus(d.get("availability", "available")),
            priority=d.get("priority", 100),
            cost_tier=CostTier(d.get("cost_tier", "free")),
            tier=ProviderTier(d.get("tier", "cli")),
            capabilities=d.get("capabilities", ["planning", "implementation", "review"]),
            enabled=d.get("enabled", True),
            last_check=d.get("last_check"),
            last_error=d.get("last_error"),
            rate_limit_until=d.get("rate_limit_until"),
            prompt_arg=d.get("prompt_arg", "positional"),
        )


DEFAULT_PROVIDERS: list[dict[str, Any]] = [
    {
        "provider_id": "openai_api",
        "command": "openai_api",
        "priority": 10,
        "cost_tier": "paid",
        "tier": "api",
        "capabilities": ["planning", "implementation", "review", "analysis", "reasoning"],
        "prompt_arg": "api",
    },
    {
        "provider_id": "anthropic_api",
        "command": "anthropic_api",
        "priority": 15,
        "cost_tier": "paid",
        "tier": "api",
        "capabilities": ["planning", "implementation", "review", "analysis", "reasoning"],
        "prompt_arg": "api",
    },
    {
        "provider_id": "gemini_api",
        "command": "gemini_api",
        "priority": 20,
        "cost_tier": "paid",
        "tier": "api",
        "capabilities": ["planning", "implementation", "review", "analysis", "multimodal"],
        "prompt_arg": "api",
    },
    {
        "provider_id": "claude",
        "command": "claude",
        "priority": 30,
        "cost_tier": "paid",
        "tier": "cli",
        "capabilities": ["planning", "implementation", "review", "analysis", "reasoning"],
        "prompt_arg": "print",
    },
    {
        "provider_id": "codex",
        "command": "codex",
        "priority": 35,
        "cost_tier": "paid",
        "tier": "cli",
        "capabilities": ["planning", "implementation", "analysis"],
        "prompt_arg": "exec",
    },
    {
        "provider_id": "gemini",
        "command": "gemini",
        "priority": 40,
        "cost_tier": "paid",
        "tier": "cli",
        "capabilities": ["planning", "implementation", "review", "analysis", "multimodal"],
        "prompt_arg": "positional",
    },
    {
        "provider_id": "copilot",
        "command": "copilot",
        "priority": 45,
        "cost_tier": "paid",
        "tier": "cli",
        "capabilities": ["planning", "implementation", "code_completion"],
        "prompt_arg": "positional",
    },
]

MOCK_PROVIDER: dict[str, Any] = {
    "provider_id": "mock",
    "command": "python",
    "priority": 900,
    "cost_tier": "free",
    "tier": "mock",
    "capabilities": ["planning", "implementation", "review", "analysis"],
    "prompt_arg": "mock",
}

STUB_PROVIDER: dict[str, Any] = {
    "provider_id": "stub",
    "command": "python",
    "priority": 999,
    "cost_tier": "free",
    "tier": "stub",
    "capabilities": ["planning", "implementation", "review", "analysis"],
    "prompt_arg": "stub",
}


def build_provider_command(provider: Provider, prompt: str) -> list[str]:
    """Build the correct CLI command for each provider."""
    prompt_arg = getattr(provider, "prompt_arg", "positional")
    tier = getattr(provider, "tier", ProviderTier.CLI)

    if tier == ProviderTier.API:
        return ["python", "-c", f"print('API call required for {provider.provider_id}')"]
    elif prompt_arg == "stub":
        return ["python", "-c", f"print('stub: {prompt[:50]}')"]
    elif prompt_arg == "mock":
        return ["python", "scripts/ems_mock_provider.py", prompt]
    elif prompt_arg == "exec":
        return [provider.command, "exec", prompt]
    elif prompt_arg == "run":
        return [provider.command, "run", prompt]
    elif prompt_arg == "print":
        return [provider.command, "-p", prompt]
    else:
        return [provider.command, prompt]


def execute_provider_command(
    provider: Provider, prompt: str, cwd: str | None = None, timeout: int = 300
) -> tuple[bool, str, str]:
    """Execute a provider command with proper handling."""
    import subprocess

    prompt_arg = getattr(provider, "prompt_arg", "positional")
    tier = getattr(provider, "tier", ProviderTier.CLI)

    if tier == ProviderTier.API:
        return False, "", "API providers require async execution via APIProviderRegistry"

    if prompt_arg == "stub":
        return True, f"Stub: {prompt[:100]}", ""

    if prompt_arg == "mock":
        cmd = ["python", "scripts/ems_mock_provider.py", prompt]
    elif prompt_arg == "exec":
        cmd = [provider.command, "exec", prompt]
    elif prompt_arg == "run":
        cmd = [provider.command, "run", prompt]
    elif prompt_arg == "print":
        cmd = [provider.command, "-p", prompt]
    else:
        cmd = [provider.command, prompt]

    # Windows fix: resolve .CMD/.EXE wrappers via shutil.which()
    import shutil as _shutil

    if cmd and cmd[0] == provider.command:
        _resolved = _shutil.which(provider.command)
        if _resolved:
            cmd[0] = _resolved

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        if result.returncode == 0:
            return True, result.stdout, result.stderr
        return False, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Provider {provider.provider_id} timed out"
    except Exception as e:
        return False, "", str(e)


class ProviderRegistry:
    _instance: ProviderRegistry | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> ProviderRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        providers: list[Provider] | None = None,
        allow_mock: bool | None = None,
        allow_stub: bool | None = None,
        production_mode: bool | None = None,
    ) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._providers: dict[str, Provider] = {}
        if production_mode is None:
            production_mode = (
                os.environ.get("EMS_PRODUCTION_MODE", "").lower() == "true"
            )
        self._production_mode = production_mode
        if allow_mock is None:
            if production_mode:
                allow_mock = False
            else:
                allow_mock = (
                    os.environ.get("EMS_ALLOW_MOCK_PROVIDER", "false").lower()
                    == "true"
                )
        if allow_stub is None:
            allow_stub = (
                os.environ.get("EMS_ALLOW_STUB_PROVIDER", "").lower() == "true"
            )
        self._allow_mock = allow_mock
        self._allow_stub = allow_stub
        if providers:
            for p in providers:
                self._providers[p.provider_id] = p
        else:
            for pd in DEFAULT_PROVIDERS:
                p = Provider.from_dict(pd)
                self._providers[p.provider_id] = p
            if self._allow_mock:
                p = Provider.from_dict(MOCK_PROVIDER)
                self._providers[p.provider_id] = p
            if self._allow_stub:
                p = Provider.from_dict(STUB_PROVIDER)
                self._providers[p.provider_id] = p
        self._api_registry: APIProviderRegistry | None = None

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset singleton for testing purposes."""
        cls._instance = None
        from ssidctl.core.api_providers import APIProviderRegistry

        APIProviderRegistry.reset_for_testing()

    def _get_api_registry(self) -> APIProviderRegistry:
        if self._api_registry is None:
            from ssidctl.core.api_providers import get_api_registry

            self._api_registry = get_api_registry()
        return self._api_registry

    def get_provider(self, provider_id: str) -> Provider | None:
        return self._providers.get(provider_id)

    def list_providers(self) -> list[Provider]:
        return list(self._providers.values())

    def list_available(
        self, capability: str | None = None, tier: ProviderTier | None = None
    ) -> list[Provider]:
        now = datetime.now(UTC).isoformat()
        available = []
        for p in self._providers.values():
            if not p.enabled:
                continue
            if p.availability == ProviderStatus.DISABLED:
                continue
            if p.rate_limit_until and p.rate_limit_until > now:
                continue
            if capability and capability not in p.capabilities:
                continue
            if tier and p.tier != tier:
                continue
            available.append(p)
        return sorted(available, key=lambda x: x.priority)

    def list_api_providers(self) -> list[Provider]:
        return self.list_available(tier=ProviderTier.API)

    def list_cli_providers(self) -> list[Provider]:
        return self.list_available(tier=ProviderTier.CLI)

    def get_best_api_provider(self) -> Provider | None:
        api_providers = self.list_api_providers()
        api_registry = self._get_api_registry()
        for p in api_providers:
            api_provider = api_registry.get_provider(p.provider_id)
            if api_provider and api_provider.is_available():
                return p
        return None

    def check_health(self, provider_id: str) -> tuple[bool, str | None]:
        p = self._providers.get(provider_id)
        if not p:
            return False, f"Provider {provider_id} not found"
        if p.tier == ProviderTier.API:
            api_registry = self._get_api_registry()
            api_provider = api_registry.get_provider(provider_id)
            if api_provider:
                available = api_provider.is_available()
                if available:
                    p.availability = ProviderStatus.AVAILABLE
                    p.last_check = datetime.now(UTC).isoformat()
                    return True, None
                else:
                    p.availability = ProviderStatus.UNAVAILABLE
                    p.last_error = "API key not configured or provider disabled"
                    return False, p.last_error
            return False, f"API provider {provider_id} not found in registry"
        cmd_path = shutil.which(p.command)
        if not cmd_path:
            p.availability = ProviderStatus.UNAVAILABLE
            p.last_error = f"Command not found: {p.command}"
            return False, p.last_error
        try:
            # Windows fix: use resolved path for .CMD/.EXE wrappers
            result = subprocess.run(
                [cmd_path] + p.health_check_args,
                capture_output=True,
                text=True,
                timeout=10,
            )
            p.last_check = datetime.now(UTC).isoformat()
            if result.returncode == 0:
                p.availability = ProviderStatus.AVAILABLE
                p.last_error = None
                return True, None
            else:
                p.availability = ProviderStatus.UNAVAILABLE
                p.last_error = f"Health check failed: {result.stderr[:200]}"
                return False, p.last_error
        except subprocess.TimeoutExpired:
            p.availability = ProviderStatus.UNAVAILABLE
            p.last_error = "Health check timeout"
            return False, p.last_error
        except Exception as e:
            p.availability = ProviderStatus.UNAVAILABLE
            p.last_error = str(e)
            return False, p.last_error

    def mark_rate_limited(self, provider_id: str, until: str | None = None) -> None:
        p = self._providers.get(provider_id)
        if p:
            p.availability = ProviderStatus.RATE_LIMITED
            p.rate_limit_until = until or datetime.now(UTC).isoformat()
            logger.warning("Provider %s rate limited until %s", provider_id, p.rate_limit_until)

    def mark_available(self, provider_id: str) -> None:
        p = self._providers.get(provider_id)
        if p:
            p.availability = ProviderStatus.AVAILABLE
            p.rate_limit_until = None
            p.last_error = None

    def mark_failed(self, provider_id: str, error: str, error_class: ProviderErrorClass) -> None:
        p = self._providers.get(provider_id)
        if not p:
            return
        p.last_error = error
        if error_class == ProviderErrorClass.RATE_LIMIT:
            self.mark_rate_limited(provider_id)
        elif (
            error_class in (ProviderErrorClass.AUTH_ERROR, ProviderErrorClass.QUOTA_EXCEEDED)
            or error_class == ProviderErrorClass.COMMAND_NOT_FOUND
        ):
            p.availability = ProviderStatus.UNAVAILABLE


def classify_error(returncode: int, stderr: str, timeout: bool = False) -> ProviderErrorClass:
    if timeout:
        return ProviderErrorClass.TIMEOUT
    stderr_lower = stderr.lower()
    if "rate limit" in stderr_lower or "429" in stderr_lower:
        return ProviderErrorClass.RATE_LIMIT
    if "auth" in stderr_lower or "401" in stderr_lower or "403" in stderr_lower:
        return ProviderErrorClass.AUTH_ERROR
    if "quota" in stderr_lower:
        return ProviderErrorClass.QUOTA_EXCEEDED
    if "command not found" in stderr_lower or "not found" in stderr_lower:
        return ProviderErrorClass.COMMAND_NOT_FOUND
    if returncode != 0:
        return ProviderErrorClass.NONZERO_EXIT
    return ProviderErrorClass.UNKNOWN_PROVIDER_FAILURE


class ProviderSelector:
    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or ProviderRegistry()

    def select_provider(
        self,
        capability: str = "planning",
        exclude: set[str] | None = None,
        prefer_free: bool = False,
        prefer_api: bool = True,
    ) -> Provider | None:
        exclude = exclude or set()
        if prefer_api:
            api_providers = self._registry.list_available(
                capability=capability, tier=ProviderTier.API
            )
            for p in api_providers:
                if p.provider_id not in exclude:
                    api_registry = self._registry._get_api_registry()
                    api_provider = api_registry.get_provider(p.provider_id)
                    if api_provider and api_provider.is_available():
                        return p
        available = self._registry.list_available(capability=capability)
        candidates = [
            p
            for p in available
            if p.provider_id not in exclude
            and p.tier not in (ProviderTier.MOCK, ProviderTier.STUB)
        ]
        if prefer_free:
            free = [p for p in candidates if p.cost_tier == CostTier.FREE]
            if free:
                return free[0]
        return candidates[0] if candidates else None

    async def execute_with_failover_async(
        self,
        prompt: str,
        capability: str = "planning",
        max_attempts: int = 3,
        timeout: int = 120,
        cwd: str | None = None,
    ) -> tuple[bool, str, str, Provider | None]:
        exclude: set[str] = set()
        last_stderr: str = ""
        for attempt in range(max_attempts):
            provider = self.select_provider(capability=capability, exclude=exclude)
            if provider is None:
                return False, "", f"No available provider after {attempt} attempts", None
            logger.info(
                "ProviderSelector: attempt %d using %s (tier=%s) for capability %s",
                attempt + 1,
                provider.provider_id,
                provider.tier.value,
                capability,
            )
            if provider.tier == ProviderTier.API:
                success, stdout, stderr = await self._execute_api_provider(
                    provider, prompt
                )
            else:
                success, stdout, stderr = self._execute_single(
                    provider, prompt, timeout, cwd
                )
            if success:
                self._registry.mark_available(provider.provider_id)
                return True, stdout, stderr, provider
            error_class = classify_error(1, stderr)
            self._registry.mark_failed(provider.provider_id, stderr, error_class)
            exclude.add(provider.provider_id)
            last_stderr = f"{provider.provider_id}: {stderr}"
            logger.warning(
                "ProviderSelector: %s failed with %s, trying next provider",
                provider.provider_id,
                error_class.value,
            )
        return False, "", f"All providers failed. Last error: {last_stderr}", None

    async def _execute_api_provider(
        self, provider: Provider, prompt: str
    ) -> tuple[bool, str, str]:
        api_registry = self._registry._get_api_registry()
        api_provider = api_registry.get_provider(provider.provider_id)
        if not api_provider:
            return False, "", f"API provider {provider.provider_id} not found"
        try:
            result = await api_provider.execute(prompt)
            if result.success:
                return True, result.content, ""
            return False, "", result.error
        except Exception as e:
            return False, "", str(e)

    def execute_with_failover(
        self,
        prompt: str,
        capability: str = "planning",
        max_attempts: int = 3,
        timeout: int = 120,
        cwd: str | None = None,
    ) -> tuple[bool, str, str, Provider | None]:
        exclude: set[str] = set()
        last_stderr: str = ""
        for attempt in range(max_attempts):
            provider = self.select_provider(capability=capability, exclude=exclude)
            if provider is None:
                return False, "", f"No available provider after {attempt} attempts", None
            logger.info(
                "ProviderSelector: attempt %d using %s for capability %s",
                attempt + 1,
                provider.provider_id,
                capability,
            )
            success, stdout, stderr = self._execute_single(provider, prompt, timeout, cwd)
            if success:
                self._registry.mark_available(provider.provider_id)
                return True, stdout, stderr, provider
            error_class = classify_error(1, stderr)
            self._registry.mark_failed(provider.provider_id, stderr, error_class)
            exclude.add(provider.provider_id)
            last_stderr = f"{provider.provider_id}: {stderr}"
            logger.warning(
                "ProviderSelector: %s failed with %s, trying next provider",
                provider.provider_id,
                error_class.value,
            )
        return False, "", f"All providers failed. Last error: {last_stderr}", None

    def _execute_single(
        self,
        provider: Provider,
        prompt: str,
        timeout: int,
        cwd: str | None,
    ) -> tuple[bool, str, str]:
        cmd = build_provider_command(provider, prompt)
        cmd_path = shutil.which(cmd[0])
        if not cmd_path:
            return False, "", f"Command not found: {cmd[0]}"
        # Windows fix: use resolved path for .CMD/.EXE wrappers
        if cmd[0] != cmd_path:
            cmd[0] = cmd_path
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            if result.returncode == 0:
                return True, result.stdout, result.stderr
            return False, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Timeout"
        except Exception as e:
            return False, "", str(e)


def get_registry() -> ProviderRegistry:
    return ProviderRegistry()


def get_selector() -> ProviderSelector:
    return ProviderSelector(get_registry())
