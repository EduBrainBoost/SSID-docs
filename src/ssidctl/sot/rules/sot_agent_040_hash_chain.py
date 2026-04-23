"""SOT_AGENT_040 -- Evidence hash chain integrity verification.

Rule: Each evidence entry must have a valid sha256 hash, and the chain
of entries must be linearly linked via prev_hash references (blockchain-style).
The first entry must have prev_hash == None or "genesis".
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

RULE_ID = "SOT_AGENT_040"
RULE_DESCRIPTION = "Evidence hash chain must be intact (no gaps, no tampered entries)"

GENESIS_SENTINEL = "genesis"


@dataclass
class EvidenceEntry:
    entry_id: str
    payload_hash: str
    prev_hash: str | None
    sequence: int
    raw: dict


@dataclass
class HashChainViolation:
    entry_id: str
    sequence: int
    reason: str


@dataclass
class HashChainResult:
    passed: bool
    chain_length: int = 0
    violations: list[HashChainViolation] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def to_dict(self) -> dict:
        return {
            "rule_id": RULE_ID,
            "passed": self.passed,
            "chain_length": self.chain_length,
            "violation_count": self.violation_count,
            "violations": [
                {
                    "entry_id": v.entry_id,
                    "sequence": v.sequence,
                    "reason": v.reason,
                }
                for v in self.violations
            ],
        }


def _sha256_payload(raw: dict) -> str:
    """Compute sha256 of a canonical JSON representation (sorted keys)."""
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_entries(data: list[dict]) -> list[EvidenceEntry]:
    """Parse raw dicts into EvidenceEntry objects, sorted by sequence."""
    entries: list[EvidenceEntry] = []
    for item in data:
        entries.append(
            EvidenceEntry(
                entry_id=str(item.get("entry_id", "")),
                payload_hash=str(item.get("payload_hash", "")),
                prev_hash=item.get("prev_hash"),
                sequence=int(item.get("sequence", -1)),
                raw=item,
            )
        )
    entries.sort(key=lambda e: e.sequence)
    return entries


def verify_chain(entries_data: list[dict]) -> HashChainResult:
    """Verify the integrity of an evidence hash chain.

    Each entry is validated for:
    1. A non-empty payload_hash field.
    2. A correctly computed sha256 over its payload fields.
    3. A prev_hash that matches the payload_hash of the previous entry
       (or is "genesis"/None for the first entry).
    """
    if not entries_data:
        return HashChainResult(passed=True, chain_length=0)

    entries = _load_entries(entries_data)
    violations: list[HashChainViolation] = []
    prev_hash: str | None = None

    for idx, entry in enumerate(entries):
        # 1. Non-empty hash
        if not entry.payload_hash:
            violations.append(
                HashChainViolation(
                    entry_id=entry.entry_id,
                    sequence=entry.sequence,
                    reason="payload_hash is empty",
                )
            )
            prev_hash = entry.payload_hash
            continue

        # 2. Recompute hash over payload (exclude chain-linking fields)
        payload_fields = {
            k: v for k, v in entry.raw.items() if k not in ("payload_hash", "prev_hash")
        }
        expected_hash = _sha256_payload(payload_fields)
        if entry.payload_hash != expected_hash:
            violations.append(
                HashChainViolation(
                    entry_id=entry.entry_id,
                    sequence=entry.sequence,
                    reason=(
                        f"payload_hash mismatch: stored={entry.payload_hash[:16]}... "
                        f"computed={expected_hash[:16]}..."
                    ),
                )
            )

        # 3. prev_hash linkage
        if idx == 0:
            if entry.prev_hash not in (None, GENESIS_SENTINEL, ""):
                violations.append(
                    HashChainViolation(
                        entry_id=entry.entry_id,
                        sequence=entry.sequence,
                        reason=(
                            f"First entry prev_hash must be None or '{GENESIS_SENTINEL}', "
                            f"got: {entry.prev_hash!r}"
                        ),
                    )
                )
        else:
            if entry.prev_hash != prev_hash:
                violations.append(
                    HashChainViolation(
                        entry_id=entry.entry_id,
                        sequence=entry.sequence,
                        reason=(
                            f"Chain broken: prev_hash={entry.prev_hash!r} "
                            f"does not match previous payload_hash={prev_hash!r}"
                        ),
                    )
                )

        prev_hash = entry.payload_hash

    return HashChainResult(
        passed=len(violations) == 0,
        chain_length=len(entries),
        violations=violations,
    )


def verify_chain_file(path: Path) -> HashChainResult:
    """Load a JSON file containing a list of evidence entries and verify."""
    if not path.exists():
        return HashChainResult(
            passed=False,
            chain_length=0,
            violations=[
                HashChainViolation(
                    entry_id="<file>",
                    sequence=-1,
                    reason=f"Evidence chain file not found: {path}",
                )
            ],
        )

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return HashChainResult(
            passed=False,
            chain_length=0,
            violations=[
                HashChainViolation(
                    entry_id="<file>",
                    sequence=-1,
                    reason="Evidence chain file must contain a JSON array",
                )
            ],
        )

    return verify_chain(raw)
