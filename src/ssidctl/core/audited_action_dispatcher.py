"""Audited action dispatcher: the sole real-execution choke point.

All adapter executions must go through this dispatcher. It:
1. Validates the lease claim before allowing execution.
2. Blocks actions requiring approval unless approval is present.
3. Logs all dispatch decisions to the event log.
"""

from __future__ import annotations

from typing import Any

from ssidctl.core.action_adapter_registry import get_adapter, get_dispatch_entry
from ssidctl.core.action_adapters.base_adapter import AdapterInput, AdapterOutput
from ssidctl.core.event_log import EventLog
from ssidctl.core.timeutil import utcnow_iso
from ssidctl.core.worker_lease_store import WorkerLeaseStore


class AuditedActionDispatcher:
    """Dispatch adapter execution with lease validation and audit logging."""

    def __init__(self, event_log: EventLog, lease_store: WorkerLeaseStore) -> None:
        self._log = event_log
        self._leases = lease_store

    def dispatch(
        self,
        action_type: str,
        target_ref: str,
        repo_root: str,
        worker_id: str,
        claim_id: str,
        item_id: str,
        dry_run: bool = False,
        approval_token: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AdapterOutput:
        """Dispatch an action to its adapter.

        Returns an AdapterOutput. Blocked outcomes are returned (never raised).
        """
        started = utcnow_iso()

        # 1. Validate lease
        if not self._leases.validate_claim(item_id, claim_id, worker_id):
            self._log.append(
                "dispatcher.blocked",
                {
                    "item_id": item_id,
                    "action_type": action_type,
                    "reason": "Invalid lease claim",
                },
                actor=worker_id,
            )
            return AdapterOutput(
                outcome="blocked",
                stderr_summary="Dispatch rejected: invalid or expired lease claim",
                dry_run=dry_run,
                started_at=started,
                finished_at=utcnow_iso(),
            )

        # 2. Look up dispatch entry
        entry = get_dispatch_entry(action_type)
        if entry is None:
            self._log.append(
                "dispatcher.blocked",
                {
                    "item_id": item_id,
                    "action_type": action_type,
                    "reason": "Not in dispatch matrix",
                },
                actor=worker_id,
            )
            return AdapterOutput(
                outcome="blocked",
                stderr_summary=f"Dispatch rejected: '{action_type}' not in dispatch matrix",
                dry_run=dry_run,
                started_at=started,
                finished_at=utcnow_iso(),
            )

        # 3. Check approval requirement
        if entry.requires_approval and not approval_token:
            self._log.append(
                "dispatcher.blocked",
                {
                    "item_id": item_id,
                    "action_type": action_type,
                    "reason": "Approval required",
                },
                actor=worker_id,
            )
            return AdapterOutput(
                outcome="blocked",
                stderr_summary=f"Dispatch rejected: '{action_type}' requires approval",
                dry_run=dry_run,
                started_at=started,
                finished_at=utcnow_iso(),
            )

        # 4. Get adapter
        adapter = get_adapter(action_type)
        if adapter is None:
            self._log.append(
                "dispatcher.blocked",
                {"item_id": item_id, "action_type": action_type, "reason": "No adapter found"},
                actor=worker_id,
            )
            return AdapterOutput(
                outcome="blocked",
                stderr_summary=f"No adapter registered for '{action_type}'",
                dry_run=dry_run,
                started_at=started,
                finished_at=utcnow_iso(),
            )

        # 5. Execute
        inp = AdapterInput(
            action_type=action_type,
            target_ref=target_ref,
            repo_root=repo_root,
            dry_run=dry_run,
            extra=extra or {},
        )
        result = adapter.execute(inp)

        self._log.append(
            "dispatcher.dispatched",
            {
                "item_id": item_id,
                "action_type": action_type,
                "worker_id": worker_id,
                "outcome": result.outcome,
                "dry_run": dry_run,
            },
            actor=worker_id,
        )

        return result
