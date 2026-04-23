"""EMS Audit Trail — Write-once read-many (WORM) logging of all operations.

All control operations are logged here for compliance and forensics.
Logs are structured JSON and immutable (cannot be modified after write).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditEvent:
    """Single audit event."""

    def __init__(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        result: str,
        timestamp: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        self.event_type = event_type
        self.actor = actor
        self.action = action
        self.resource = resource
        self.result = result
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.correlation_id = correlation_id
        self.details = details or {}
        self.error_code = error_code

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "details": self.details,
            "error_code": self.error_code,
        }


class AuditTrail:
    """Write-once audit trail for EMS operations.

    Usage:
        trail = AuditTrail(base_dir=Path(".tmp_state/audit"))
        trail.log_event(
            event_type="startup",
            actor="operator",
            action="start_settlement",
            resource="ssid",
            result="success",
            correlation_id="corr-123",
        )
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Immutable log file — appends only
        self.log_file = self.base_dir / "audit.log"

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        result: str,
        timestamp: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """Log an audit event (append-only)."""
        event = AuditEvent(
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            result=result,
            timestamp=timestamp,
            correlation_id=correlation_id,
            details=details,
            error_code=error_code,
        )

        # Serialize to JSON
        event_json = json.dumps(
            event.to_dict(),
            ensure_ascii=False,
            default=str,
        )

        # Append to log file (WORM pattern)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(event_json + "\n")
            logger.debug(
                "Audit event logged: %s/%s (correlation_id=%s)",
                action,
                result,
                correlation_id,
            )
        except IOError as e:
            # Log failure (but don't crash) — audit logging is critical
            logger.error("Failed to write audit event: %s", e)

    def log_control_startup(
        self,
        actor: str = "system",
        correlation_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log startup control operation."""
        self.log_event(
            event_type="control",
            actor=actor,
            action="startup",
            resource="ssid",
            result="initiated",
            correlation_id=correlation_id,
            details=details or {},
        )

    def log_control_halt(
        self,
        actor: str = "system",
        correlation_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log halt control operation."""
        self.log_event(
            event_type="control",
            actor=actor,
            action="halt",
            resource="ssid",
            result="initiated",
            correlation_id=correlation_id,
            details=details or {},
        )

    def log_control_emergency_drain(
        self,
        actor: str = "system",
        correlation_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log emergency drain control operation."""
        self.log_event(
            event_type="control",
            actor=actor,
            action="emergency_drain",
            resource="ssid",
            result="initiated",
            correlation_id=correlation_id,
            details=details or {},
        )

    def log_operation_success(
        self,
        action: str,
        actor: str = "system",
        correlation_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log successful operation."""
        self.log_event(
            event_type="operation",
            actor=actor,
            action=action,
            resource="ssid",
            result="success",
            correlation_id=correlation_id,
            details=details or {},
        )

    def log_operation_failure(
        self,
        action: str,
        error_code: str,
        error_message: str,
        actor: str = "system",
        correlation_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log failed operation."""
        if details is None:
            details = {}
        details["error_message"] = error_message

        self.log_event(
            event_type="operation",
            actor=actor,
            action=action,
            resource="ssid",
            result="failure",
            error_code=error_code,
            correlation_id=correlation_id,
            details=details,
        )

    def log_policy_violation(
        self,
        policy_name: str,
        violation_details: dict[str, Any],
        actor: str = "system",
        correlation_id: Optional[str] = None,
    ) -> None:
        """Log policy violation."""
        self.log_event(
            event_type="policy",
            actor=actor,
            action=policy_name,
            resource="compliance",
            result="violation",
            correlation_id=correlation_id,
            details=violation_details,
        )

    def read_events(
        self,
        limit: Optional[int] = None,
        event_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Read audit events (read-only)."""
        if not self.log_file.exists():
            return []

        events: list[dict[str, Any]] = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if event_type is None or event.get("event_type") == event_type:
                            events.append(event)
                        if limit and len(events) >= limit:
                            break
                    except json.JSONDecodeError:
                        logger.warning("Invalid audit JSON: %s", line)
        except IOError as e:
            logger.error("Failed to read audit trail: %s", e)

        return events

    def read_events_by_correlation_id(
        self, correlation_id: str
    ) -> list[dict[str, Any]]:
        """Read all events with given correlation ID."""
        all_events = self.read_events()
        return [e for e in all_events if e.get("correlation_id") == correlation_id]
