"""EMS Operation Controller — Orchestrates SSID control commands.

This module provides high-level control operations:
- Startup: Validate prerequisites, then start settlement
- Shutdown: Graceful or forced shutdown
- Emergency Drain: Stop accepting new operations, drain existing

All operations are logged to audit trail.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from src.runtime.ssid_binding import (
<<<<<<< HEAD
=======
    CommandExecutionResult,
>>>>>>> origin/chore/artifact-cleanup-20260331
    CommandStatus,
    OperationStatus,
    SSIDBinding,
)

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """Type of operation."""

    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    EMERGENCY_DRAIN = "emergency_drain"
    HALT_OPERATIONS = "halt_operations"


class OperationResult(str, Enum):
    """Result of operation."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    PRECONDITION_FAILED = "precondition_failed"


@dataclass
class OperationCheckResult:
    """Result of a pre-operation check."""

    passed: bool
    check_name: str
    error_message: Optional[str] = None


@dataclass
class ControlOperationResult:
    """Result of a control operation."""

    operation_type: OperationType
    result: OperationResult
    timestamp: str
    duration_seconds: float
    checks_passed: list[str]
    checks_failed: list[str]
    ssid_response: Optional[dict] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None


class OperationController:
    """High-level control of SSID operations.

    Usage:
        controller = OperationController(ssid_binding=binding)
        result = await controller.startup()
        if result.result == OperationResult.SUCCESS:
            logger.info("SSID started successfully")
    """

    def __init__(self, ssid_binding: SSIDBinding) -> None:
        self.ssid_binding = ssid_binding

    async def _check_health(self) -> OperationCheckResult:
        """Check SSID core health."""
        result = await self.ssid_binding.health_check(force=True)
        if result.status == OperationStatus.HEALTHY:
            return OperationCheckResult(passed=True, check_name="health_check")
        return OperationCheckResult(
            passed=False,
            check_name="health_check",
            error_message=f"SSID unhealthy: {result.status.value}",
        )

    async def _check_custody(self) -> OperationCheckResult:
        """Stub: Validate custody (calls SSID policy endpoint)."""
        # TODO: Implement actual custody validation
        return OperationCheckResult(passed=True, check_name="custody_validation")

    async def _check_policies(self) -> OperationCheckResult:
        """Stub: Validate compliance policies."""
        # TODO: Implement policy bridge validation
        return OperationCheckResult(passed=True, check_name="policy_validation")

    async def _check_capacity(self) -> OperationCheckResult:
        """Stub: Validate system capacity."""
        # TODO: Implement capacity check
        return OperationCheckResult(passed=True, check_name="capacity_check")

    async def startup(
        self, correlation_id: Optional[str] = None
    ) -> ControlOperationResult:
        """Start SSID settlement operations.

        Runs pre-checks (health, custody, policies, capacity) before
        executing the start_settlement command.
        """
        import time

        start_time = time.time()
        checks_passed: list[str] = []
        checks_failed: list[str] = []

        logger.info("Starting SSID startup sequence (correlation_id=%s)", correlation_id)

        # Run pre-checks
        for check_fn in [
            self._check_health,
            self._check_custody,
            self._check_policies,
            self._check_capacity,
        ]:
            try:
                check_result = await check_fn()
                if check_result.passed:
                    checks_passed.append(check_result.check_name)
                    logger.debug("Check passed: %s", check_result.check_name)
                else:
                    checks_failed.append(check_result.check_name)
                    logger.warning(
                        "Check failed: %s — %s",
                        check_result.check_name,
                        check_result.error_message,
                    )
<<<<<<< HEAD
            except Exception:
=======
            except Exception as e:
>>>>>>> origin/chore/artifact-cleanup-20260331
                logger.exception("Check error: %s", check_fn.__name__)
                checks_failed.append(check_fn.__name__)

        # If any checks failed, don't proceed
        if checks_failed:
            duration = time.time() - start_time
            logger.error(
                "Startup preconditions failed: %s", ", ".join(checks_failed)
            )
            return ControlOperationResult(
                operation_type=OperationType.STARTUP,
                result=OperationResult.PRECONDITION_FAILED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                error_message=f"Preconditions failed: {', '.join(checks_failed)}",
                correlation_id=correlation_id,
            )

        # Execute start command
        cmd_result = await self.ssid_binding.execute_command(
            command_name="start_settlement",
            path="/control/settlement/start",
            method="POST",
            payload={"correlation_id": correlation_id} if correlation_id else {},
            timeout_seconds=30,
            idempotency_key=correlation_id,
        )

        duration = time.time() - start_time

        if cmd_result.status == CommandStatus.SUCCESS:
            logger.info("SSID startup successful (duration=%.1f s)", duration)
            return ControlOperationResult(
                operation_type=OperationType.STARTUP,
                result=OperationResult.SUCCESS,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                ssid_response=cmd_result.ssid_response,
                correlation_id=correlation_id,
            )
        else:
            logger.error(
                "SSID startup failed: %s (status=%s)",
                cmd_result.error_message,
                cmd_result.status.value,
            )
            return ControlOperationResult(
                operation_type=OperationType.STARTUP,
                result=OperationResult.FAILED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                error_message=cmd_result.error_message,
                correlation_id=correlation_id,
            )

    async def halt_operations(
        self, correlation_id: Optional[str] = None
    ) -> ControlOperationResult:
        """Halt SSID operations (graceful pause)."""
        import time

        start_time = time.time()
        logger.info(
            "Halting SSID operations (correlation_id=%s)", correlation_id
        )

        cmd_result = await self.ssid_binding.execute_command(
            command_name="halt_operations",
            path="/control/settlement/halt",
            method="POST",
            payload={"correlation_id": correlation_id} if correlation_id else {},
            timeout_seconds=10,
            idempotency_key=correlation_id,
        )

        duration = time.time() - start_time

        if cmd_result.status == CommandStatus.SUCCESS:
            logger.info("SSID operations halted (duration=%.1f s)", duration)
            return ControlOperationResult(
                operation_type=OperationType.HALT_OPERATIONS,
                result=OperationResult.SUCCESS,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
                checks_passed=["halt_command_executed"],
                checks_failed=[],
                ssid_response=cmd_result.ssid_response,
                correlation_id=correlation_id,
            )
        else:
            logger.error(
                "SSID halt failed: %s", cmd_result.error_message
            )
            return ControlOperationResult(
                operation_type=OperationType.HALT_OPERATIONS,
                result=OperationResult.FAILED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
                checks_passed=[],
                checks_failed=["halt_command_failed"],
                error_message=cmd_result.error_message,
                correlation_id=correlation_id,
            )

    async def emergency_drain(
        self, correlation_id: Optional[str] = None
    ) -> ControlOperationResult:
        """Emergency drain: Stop accepting operations, drain existing."""
        import time

        start_time = time.time()
        logger.critical(
            "Initiating emergency drain (correlation_id=%s)", correlation_id
        )

        cmd_result = await self.ssid_binding.execute_command(
            command_name="drain_emergency",
            path="/control/emergency/drain",
            method="POST",
            payload={"correlation_id": correlation_id} if correlation_id else {},
            timeout_seconds=5,
            idempotency_key=correlation_id,
        )

        duration = time.time() - start_time

        if cmd_result.status == CommandStatus.SUCCESS:
            logger.critical("Emergency drain initiated (duration=%.1f s)", duration)
            return ControlOperationResult(
                operation_type=OperationType.EMERGENCY_DRAIN,
                result=OperationResult.SUCCESS,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
                checks_passed=["drain_command_executed"],
                checks_failed=[],
                ssid_response=cmd_result.ssid_response,
                correlation_id=correlation_id,
            )
        else:
            logger.critical(
                "Emergency drain failed: %s", cmd_result.error_message
            )
            return ControlOperationResult(
                operation_type=OperationType.EMERGENCY_DRAIN,
                result=OperationResult.FAILED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
                checks_passed=[],
                checks_failed=["drain_command_failed"],
                error_message=cmd_result.error_message,
                correlation_id=correlation_id,
            )
