"""Idempotency key generation and input hash computation for durable workflows.

All hashes use the canonical 'sha256:<hex>' prefix format via the shared
hashing helper. Outputs are fully deterministic: same inputs always produce
the same key, enabling safe audit replay and exactly-once step execution.
"""

from __future__ import annotations

import json

from ssidctl.core.hashing import sha256_str


def compute_idempotency_key(
    workflow_name: str,
    event_fingerprint: str,
    policy_version: str,
    step_type: str,
) -> str:
    """Return a deterministic idempotency key for a workflow step.

    The key is the SHA-256 hash of the pipe-delimited concatenation:
        "{workflow_name}|{event_fingerprint}|{policy_version}|{step_type}"

    Args:
        workflow_name: Unique name that identifies the workflow definition.
        event_fingerprint: Canonical fingerprint of the triggering event.
        policy_version: Version string of the governing policy at execution time.
        step_type: Logical type/name of the step within the workflow.

    Returns:
        A ``sha256:<hex>`` string that uniquely identifies this step invocation.
    """
    raw = f"{workflow_name}|{event_fingerprint}|{policy_version}|{step_type}"
    return sha256_str(raw)


def compute_input_hash(input_data: dict) -> str:  # type: ignore[type-arg]
    """Return a deterministic hash of a dictionary of input data.

    The dict is serialised to JSON with sorted keys and minimal separators so
    that key insertion order does not affect the output.  Two dicts with
    identical keys and values will always produce the same hash regardless of
    the order in which the keys were inserted.

    Args:
        input_data: Arbitrary JSON-serialisable dictionary.

    Returns:
        A ``sha256:<hex>`` string derived from the canonical JSON form.
    """
    canonical_json = json.dumps(input_data, sort_keys=True, separators=(",", ":"))
    return sha256_str(canonical_json)
