"""SSID Core Runtime Binding — Maps SSID endpoints to EMS control layer.

This module provides the low-level HTTP binding to SSID core:
- Health checks (is SSID running and healthy?)
- Status polling (get current operation status)
- Command execution (trigger workflows, halt operations, drain emergency)
- Error handling with retry logic

All communication is synchronous, rate-limited, and logged for audit.
"""

from __future__ import annotations

import asyncio
import logging
import time
<<<<<<< HEAD
from dataclasses import dataclass
=======
from dataclasses import dataclass, asdict
>>>>>>> origin/chore/artifact-cleanup-20260331
from enum import Enum
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class OperationStatus(str, Enum):
    """SSID operation status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"


class CommandStatus(str, Enum):
    """Command execution status."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


@dataclass
class HealthCheckResult:
    """Result of health check against SSID core."""

    status: OperationStatus
    timestamp: str
    latency_ms: float
    ssid_version: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class StatusQueryResult:
    """Result of status query to SSID."""

    settlement_running: bool
    operations_paused: bool
    current_operation_id: Optional[str] = None
    estimated_completion_seconds: Optional[int] = None
    error_rate_percent: float = 0.0
    timestamp: str = ""


@dataclass
class CommandExecutionResult:
    """Result of command execution."""

    status: CommandStatus
    command_id: str
    timestamp: str
    latency_ms: float
    ssid_response: Optional[dict] = None
    error_message: Optional[str] = None


class CircuitBreaker:
    """Simple circuit breaker for SSID endpoint protection."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds

        self.failure_count = 0
        self.success_count = 0
        self.is_open = False
        self.opened_at: Optional[float] = None

    def record_success(self) -> None:
        """Record a successful call."""
        self.failure_count = 0
        self.success_count += 1

        if self.is_open and self.success_count >= self.success_threshold:
            logger.info("Circuit breaker RESET (closed)")
            self.is_open = False
            self.success_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.success_count = 0
        self.failure_count += 1

        if not self.is_open and self.failure_count >= self.failure_threshold:
            logger.warning(
                "Circuit breaker OPEN after %d failures", self.failure_threshold
            )
            self.is_open = True
            self.opened_at = time.time()

    def allow_request(self) -> bool:
        """Check if request is allowed through."""
        if not self.is_open:
            return True

        # Check if timeout has passed
        if (
            self.opened_at
            and time.time() - self.opened_at >= self.timeout_seconds
        ):
            logger.info("Circuit breaker HALF-OPEN, allowing retry")
            self.success_count = 0
            return True

        return False


class SSIDBinding:
    """Operational binding to SSID core dispatcher.

    Usage:
        binding = SSIDBinding(
            ssid_endpoint="https://localhost:9000",
            bearer_token="...",
            health_check_interval_seconds=5,
        )
        result = await binding.health_check()
        if result.status == OperationStatus.HEALTHY:
            cmd_result = await binding.execute_command("start_settlement")
    """

    def __init__(
        self,
        ssid_endpoint: str,
        bearer_token: Optional[str] = None,
        health_check_interval_seconds: int = 5,
        health_check_timeout_seconds: int = 10,
        status_poll_timeout_seconds: int = 15,
        verify_tls: bool = True,
    ) -> None:
        self.ssid_endpoint = ssid_endpoint.rstrip("/")
        self.bearer_token = bearer_token
        self.health_check_interval_seconds = health_check_interval_seconds
        self.health_check_timeout_seconds = health_check_timeout_seconds
        self.status_poll_timeout_seconds = status_poll_timeout_seconds
        self.verify_tls = verify_tls

        self.circuit_breaker = CircuitBreaker()
        self._last_health_check: Optional[HealthCheckResult] = None
        self._last_health_check_time: float = 0.0

    def _get_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    async def health_check(self, force: bool = False) -> HealthCheckResult:
        """Check SSID core health.

        Returns cached result unless force=True and interval not exceeded.
        """
        now = time.time()
        if (
            not force
            and self._last_health_check is not None
            and now - self._last_health_check_time
            < self.health_check_interval_seconds
        ):
            return self._last_health_check

        if not self.circuit_breaker.allow_request():
            return HealthCheckResult(
                status=OperationStatus.UNREACHABLE,
                timestamp=time.time().__str__(),
                latency_ms=0.0,
                error_message="Circuit breaker is OPEN",
            )

        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.ssid_endpoint}/health"
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(
                        total=self.health_check_timeout_seconds
                    ),
                    ssl=self.verify_tls,
                ) as resp:
                    latency_ms = (time.time() - start_time) * 1000

                    if resp.status != 200:
                        self.circuit_breaker.record_failure()
                        result = HealthCheckResult(
                            status=OperationStatus.UNHEALTHY,
                            timestamp=time.time().__str__(),
                            latency_ms=latency_ms,
                            error_message=f"HTTP {resp.status}",
                        )
                        logger.warning(
                            "SSID health check failed: %s", result.error_message
                        )
                        return result

                    data = await resp.json()
                    self.circuit_breaker.record_success()

                    # Determine status from response
                    status = OperationStatus.HEALTHY
                    if data.get("status") == "degraded":
                        status = OperationStatus.DEGRADED

                    result = HealthCheckResult(
                        status=status,
                        timestamp=time.time().__str__(),
                        latency_ms=latency_ms,
                        ssid_version=data.get("version"),
                    )
                    self._last_health_check = result
                    self._last_health_check_time = now
                    return result

        except asyncio.TimeoutError:
            self.circuit_breaker.record_failure()
            return HealthCheckResult(
                status=OperationStatus.UNREACHABLE,
                timestamp=time.time().__str__(),
                latency_ms=(time.time() - start_time) * 1000,
                error_message="Health check timeout",
            )
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.exception("SSID health check error: %s", e)
            return HealthCheckResult(
                status=OperationStatus.UNREACHABLE,
                timestamp=time.time().__str__(),
                latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )

    async def get_operation_status(self) -> StatusQueryResult:
        """Query current operation status from SSID."""
        if not self.circuit_breaker.allow_request():
            return StatusQueryResult(
                settlement_running=False,
                operations_paused=True,
                error_rate_percent=100.0,
                timestamp=time.time().__str__(),
            )

        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.ssid_endpoint}/status/operations"
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(
                        total=self.status_poll_timeout_seconds
                    ),
                    ssl=self.verify_tls,
                ) as resp:
<<<<<<< HEAD
                    _latency_ms = (time.time() - start_time) * 1000
=======
                    latency_ms = (time.time() - start_time) * 1000
>>>>>>> origin/chore/artifact-cleanup-20260331

                    if resp.status != 200:
                        self.circuit_breaker.record_failure()
                        logger.warning(
                            "Status query failed: HTTP %d", resp.status
                        )
                        return StatusQueryResult(
                            settlement_running=False,
                            operations_paused=True,
                            error_rate_percent=100.0,
                            timestamp=time.time().__str__(),
                        )

                    data = await resp.json()
                    self.circuit_breaker.record_success()

                    result = StatusQueryResult(
                        settlement_running=data.get("settlement_running", False),
                        operations_paused=data.get("operations_paused", False),
                        current_operation_id=data.get("current_operation_id"),
                        estimated_completion_seconds=data.get(
                            "estimated_completion_seconds"
                        ),
                        error_rate_percent=data.get("error_rate_percent", 0.0),
                        timestamp=time.time().__str__(),
                    )
                    return result

        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.exception("Status query error: %s", e)
            return StatusQueryResult(
                settlement_running=False,
                operations_paused=True,
                error_rate_percent=100.0,
                timestamp=time.time().__str__(),
            )

    async def execute_command(
        self,
        command_name: str,
        path: str,
        method: str = "POST",
        payload: Optional[dict[str, Any]] = None,
        timeout_seconds: int = 30,
        idempotency_key: Optional[str] = None,
    ) -> CommandExecutionResult:
        """Execute a control command on SSID.

        Args:
            command_name: Name of the command (for logging)
            path: API path (e.g., "/control/settlement/start")
            method: HTTP method (GET, POST, etc.)
            payload: Request payload (for POST/PUT)
            timeout_seconds: Command timeout
            idempotency_key: Optional idempotency key for retry safety

        Returns:
            CommandExecutionResult with status and SSID response
        """
        if not self.circuit_breaker.allow_request():
            return CommandExecutionResult(
                status=CommandStatus.REJECTED,
                command_id=command_name,
                timestamp=time.time().__str__(),
                latency_ms=0.0,
                error_message="Circuit breaker is OPEN",
            )

        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.ssid_endpoint}{path}"
                headers = self._get_headers()
                if idempotency_key:
                    headers["Idempotency-Key"] = idempotency_key

                method_fn = getattr(session, method.lower())
                async with method_fn(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                    ssl=self.verify_tls,
                ) as resp:
                    latency_ms = (time.time() - start_time) * 1000

                    if resp.status >= 400:
                        self.circuit_breaker.record_failure()
                        error_msg = f"HTTP {resp.status}"
                        try:
                            data = await resp.json()
                            error_msg = data.get("error_message", error_msg)
                        except Exception:
                            pass
                        logger.warning(
                            "Command %s failed: %s", command_name, error_msg
                        )
                        return CommandExecutionResult(
                            status=CommandStatus.FAILED,
                            command_id=command_name,
                            timestamp=time.time().__str__(),
                            latency_ms=latency_ms,
                            error_message=error_msg,
                        )

                    data = await resp.json() if resp.status < 400 else {}
                    self.circuit_breaker.record_success()

                    logger.info(
                        "Command %s executed: HTTP %d (%.1f ms)",
                        command_name,
                        resp.status,
                        latency_ms,
                    )
                    return CommandExecutionResult(
                        status=CommandStatus.SUCCESS,
                        command_id=command_name,
                        timestamp=time.time().__str__(),
                        latency_ms=latency_ms,
                        ssid_response=data,
                    )

        except asyncio.TimeoutError:
            self.circuit_breaker.record_failure()
            return CommandExecutionResult(
                status=CommandStatus.TIMEOUT,
                command_id=command_name,
                timestamp=time.time().__str__(),
                latency_ms=(time.time() - start_time) * 1000,
                error_message="Command timeout",
            )
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.exception("Command %s error: %s", command_name, e)
            return CommandExecutionResult(
                status=CommandStatus.FAILED,
                command_id=command_name,
                timestamp=time.time().__str__(),
                latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )
