"""API Providers: Direct API integration for EMS multi-provider failover.

Tier 1 providers using direct API calls (non-interactive, CI-friendly):
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google Gemini

These providers bypass CLI limitations and work in CI/automation environments.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class APIProviderType(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class APIProviderStatus(StrEnum):
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


@dataclass
class APIProviderConfig:
    provider_id: str
    provider_type: APIProviderType
    api_key_env: str
    api_base_url: str
    default_model: str
    priority: int = 10
    timeout_seconds: int = 120
    max_retries: int = 2
    enabled: bool = True

    def get_api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


@dataclass
class APIProviderResult:
    success: bool
    content: str = ""
    error: str = ""
    model_used: str = ""
    tokens_used: int = 0
    finish_reason: str = ""
    latency_ms: float = 0.0


OPENAI_CONFIG = APIProviderConfig(
    provider_id="openai_api",
    provider_type=APIProviderType.OPENAI,
    api_key_env="OPENAI_API_KEY",
    api_base_url="https://api.openai.com/v1",
    default_model="gpt-4o-mini",
    priority=10,
)

ANTHROPIC_CONFIG = APIProviderConfig(
    provider_id="anthropic_api",
    provider_type=APIProviderType.ANTHROPIC,
    api_key_env="ANTHROPIC_API_KEY",
    api_base_url="https://api.anthropic.com/v1",
    default_model="claude-3-haiku-20240307",
    priority=15,
)

GEMINI_CONFIG = APIProviderConfig(
    provider_id="gemini_api",
    provider_type=APIProviderType.GEMINI,
    api_key_env="GEMINI_API_KEY",
    api_base_url="https://generativelanguage.googleapis.com/v1beta",
    default_model="gemini-1.5-flash",
    priority=20,
)


class BaseAPIProvider(ABC):
    def __init__(self, config: APIProviderConfig) -> None:
        self.config = config
        self._status = APIProviderStatus.AVAILABLE
        self._last_error: str | None = None
        self._rate_limit_until: str | None = None

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    @property
    def status(self) -> APIProviderStatus:
        return self._status

    def is_available(self) -> bool:
        if not self.config.enabled:
            return False
        if self._status == APIProviderStatus.DISABLED:
            return False
        if self._rate_limit_until:
            now = datetime.now(UTC).isoformat()
            if self._rate_limit_until > now:
                return False
            self._rate_limit_until = None
            self._status = APIProviderStatus.AVAILABLE
        api_key = self.config.get_api_key()
        if not api_key:
            return False
        return self._status in (APIProviderStatus.AVAILABLE, APIProviderStatus.RATE_LIMITED)

    @abstractmethod
    async def execute(self, prompt: str, model: str | None = None) -> APIProviderResult:
        pass

    @abstractmethod
    def build_request_body(self, prompt: str, model: str | None = None) -> dict[str, Any]:
        pass

    @abstractmethod
    def parse_response(self, response_data: dict[str, Any]) -> APIProviderResult:
        pass

    def mark_rate_limited(self, until: str | None = None) -> None:
        self._status = APIProviderStatus.RATE_LIMITED
        self._rate_limit_until = until or datetime.now(UTC).isoformat()
        logger.warning(
            "API provider %s rate limited until %s",
            self.provider_id,
            self._rate_limit_until,
        )

    def mark_auth_error(self, error: str) -> None:
        self._status = APIProviderStatus.AUTH_ERROR
        self._last_error = error
        logger.error("API provider %s auth error: %s", self.provider_id, error)

    def mark_available(self) -> None:
        self._status = APIProviderStatus.AVAILABLE
        self._rate_limit_until = None
        self._last_error = None


class OpenAIProvider(BaseAPIProvider):
    def __init__(self, config: APIProviderConfig | None = None) -> None:
        super().__init__(config or OPENAI_CONFIG)

    async def execute(self, prompt: str, model: str | None = None) -> APIProviderResult:
        if not self.is_available():
            return APIProviderResult(
                success=False, error=f"Provider {self.provider_id} not available"
            )

        api_key = self.config.get_api_key()
        if not api_key:
            return APIProviderResult(success=False, error="OPENAI_API_KEY not set")

        model = model or self.config.default_model
        url = f"{self.config.api_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = self.build_request_body(prompt, model)

        start_time = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=body)
                latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

                if response.status_code == 429:
                    retry_after = response.headers.get("retry-after", "60")
                    self.mark_rate_limited()
                    return APIProviderResult(
                        success=False,
                        error=f"Rate limited. Retry after {retry_after}s",
                        latency_ms=latency_ms,
                    )

                if response.status_code == 401:
                    self.mark_auth_error("Invalid API key")
                    return APIProviderResult(
                        success=False, error="Authentication failed", latency_ms=latency_ms
                    )

                if response.status_code != 200:
                    error_text = response.text[:500]
                    return APIProviderResult(
                        success=False,
                        error=f"API error {response.status_code}: {error_text}",
                        latency_ms=latency_ms,
                    )

                data = response.json()
                result = self.parse_response(data)
                result.latency_ms = latency_ms
                self.mark_available()
                return result

        except httpx.TimeoutException:
            return APIProviderResult(success=False, error="Request timed out")
        except Exception as e:
            logger.exception("OpenAI API error")
            return APIProviderResult(success=False, error=str(e))

    def build_request_body(self, prompt: str, model: str | None = None) -> dict[str, Any]:
        return {
            "model": model or self.config.default_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.7,
        }

    def parse_response(self, response_data: dict[str, Any]) -> APIProviderResult:
        try:
            choices = response_data.get("choices", [])
            if not choices:
                return APIProviderResult(success=False, error="No choices in response")

            message = choices[0].get("message", {})
            content = message.get("content", "")
            finish_reason = choices[0].get("finish_reason", "")

            usage = response_data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)

            return APIProviderResult(
                success=True,
                content=content,
                model_used=response_data.get("model", self.config.default_model),
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )
        except Exception as e:
            return APIProviderResult(success=False, error=f"Parse error: {e}")


class AnthropicProvider(BaseAPIProvider):
    def __init__(self, config: APIProviderConfig | None = None) -> None:
        super().__init__(config or ANTHROPIC_CONFIG)

    async def execute(self, prompt: str, model: str | None = None) -> APIProviderResult:
        if not self.is_available():
            return APIProviderResult(
                success=False, error=f"Provider {self.provider_id} not available"
            )

        api_key = self.config.get_api_key()
        if not api_key:
            return APIProviderResult(success=False, error="ANTHROPIC_API_KEY not set")

        model = model or self.config.default_model
        url = f"{self.config.api_base_url}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = self.build_request_body(prompt, model)

        start_time = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=body)
                latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

                if response.status_code == 429:
                    self.mark_rate_limited()
                    return APIProviderResult(
                        success=False, error="Rate limited", latency_ms=latency_ms
                    )

                if response.status_code == 401:
                    self.mark_auth_error("Invalid API key")
                    return APIProviderResult(
                        success=False, error="Authentication failed", latency_ms=latency_ms
                    )

                if response.status_code != 200:
                    error_text = response.text[:500]
                    return APIProviderResult(
                        success=False,
                        error=f"API error {response.status_code}: {error_text}",
                        latency_ms=latency_ms,
                    )

                data = response.json()
                result = self.parse_response(data)
                result.latency_ms = latency_ms
                self.mark_available()
                return result

        except httpx.TimeoutException:
            return APIProviderResult(success=False, error="Request timed out")
        except Exception as e:
            logger.exception("Anthropic API error")
            return APIProviderResult(success=False, error=str(e))

    def build_request_body(self, prompt: str, model: str | None = None) -> dict[str, Any]:
        return {
            "model": model or self.config.default_model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }

    def parse_response(self, response_data: dict[str, Any]) -> APIProviderResult:
        try:
            content_blocks = response_data.get("content", [])
            if not content_blocks:
                return APIProviderResult(success=False, error="No content in response")

            text_content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text_content += block.get("text", "")

            usage = response_data.get("usage", {})
            tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

            return APIProviderResult(
                success=True,
                content=text_content,
                model_used=response_data.get("model", self.config.default_model),
                tokens_used=tokens_used,
                finish_reason=response_data.get("stop_reason", ""),
            )
        except Exception as e:
            return APIProviderResult(success=False, error=f"Parse error: {e}")


class GeminiProvider(BaseAPIProvider):
    def __init__(self, config: APIProviderConfig | None = None) -> None:
        super().__init__(config or GEMINI_CONFIG)

    async def execute(self, prompt: str, model: str | None = None) -> APIProviderResult:
        if not self.is_available():
            return APIProviderResult(
                success=False, error=f"Provider {self.provider_id} not available"
            )

        api_key = self.config.get_api_key()
        if not api_key:
            return APIProviderResult(success=False, error="GEMINI_API_KEY not set")

        model = model or self.config.default_model
        url = f"{self.config.api_base_url}/models/{model}:generateContent"
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        body = self.build_request_body(prompt, model)

        start_time = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=body)
                latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

                if response.status_code == 429:
                    self.mark_rate_limited()
                    return APIProviderResult(
                        success=False, error="Rate limited", latency_ms=latency_ms
                    )

                if response.status_code == 401 or response.status_code == 403:
                    self.mark_auth_error("Invalid API key")
                    return APIProviderResult(
                        success=False, error="Authentication failed", latency_ms=latency_ms
                    )

                if response.status_code != 200:
                    error_text = response.text[:500]
                    return APIProviderResult(
                        success=False,
                        error=f"API error {response.status_code}: {error_text}",
                        latency_ms=latency_ms,
                    )

                data = response.json()
                result = self.parse_response(data)
                result.latency_ms = latency_ms
                self.mark_available()
                return result

        except httpx.TimeoutException:
            return APIProviderResult(success=False, error="Request timed out")
        except Exception as e:
            logger.exception("Gemini API error")
            return APIProviderResult(success=False, error=str(e))

    def build_request_body(self, prompt: str, model: str | None = None) -> dict[str, Any]:
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 4096,
                "temperature": 0.7,
            },
        }

    def parse_response(self, response_data: dict[str, Any]) -> APIProviderResult:
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                return APIProviderResult(success=False, error="No candidates in response")

            parts = candidates[0].get("content", {}).get("parts", [])
            text_content = ""
            for part in parts:
                text_content += part.get("text", "")

            finish_reason = candidates[0].get("finishReason", "")

            usage = response_data.get("usageMetadata", {})
            tokens_used = usage.get("totalTokenCount", 0)

            return APIProviderResult(
                success=True,
                content=text_content,
                model_used=self.config.default_model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )
        except Exception as e:
            return APIProviderResult(success=False, error=f"Parse error: {e}")


DEFAULT_API_PROVIDERS: list[APIProviderConfig] = [
    OPENAI_CONFIG,
    ANTHROPIC_CONFIG,
    GEMINI_CONFIG,
]


def create_api_provider(config: APIProviderConfig) -> BaseAPIProvider:
    if config.provider_type == APIProviderType.OPENAI:
        return OpenAIProvider(config)
    elif config.provider_type == APIProviderType.ANTHROPIC:
        return AnthropicProvider(config)
    elif config.provider_type == APIProviderType.GEMINI:
        return GeminiProvider(config)
    else:
        raise ValueError(f"Unknown provider type: {config.provider_type}")


class APIProviderRegistry:
    _instance: APIProviderRegistry | None = None

    def __new__(cls) -> APIProviderRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._providers: dict[str, BaseAPIProvider] = {}
        for config in DEFAULT_API_PROVIDERS:
            provider = create_api_provider(config)
            self._providers[provider.provider_id] = provider

    @classmethod
    def reset_for_testing(cls) -> None:
        cls._instance = None

    def get_provider(self, provider_id: str) -> BaseAPIProvider | None:
        return self._providers.get(provider_id)

    def list_providers(self) -> list[BaseAPIProvider]:
        return list(self._providers.values())

    def list_available(self) -> list[BaseAPIProvider]:
        available = [p for p in self._providers.values() if p.is_available()]
        return sorted(available, key=lambda p: p.config.priority)

    def get_highest_priority_available(self) -> BaseAPIProvider | None:
        available = self.list_available()
        return available[0] if available else None


def get_api_registry() -> APIProviderRegistry:
    return APIProviderRegistry()
