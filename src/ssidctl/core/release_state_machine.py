"""Release State Machine — canonical release lifecycle management.

Defines the release lifecycle with fail-closed state transitions:
    DRAFT -> CANDIDATE -> GATE_PENDING -> PROMOTED -> PUBLISHED
    PROMOTED/PUBLISHED -> ROLLED_BACK -> DRAFT (corrective)

Principle: fail-closed — unknown transitions are blocked.
No implicit state changes.  Every transition requires evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Release States
# ---------------------------------------------------------------------------


class ReleaseState(StrEnum):
    """Canonical release lifecycle states."""

    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    GATE_PENDING = "GATE_PENDING"
    PROMOTED = "PROMOTED"
    PUBLISHED = "PUBLISHED"
    ROLLED_BACK = "ROLLED_BACK"


# ---------------------------------------------------------------------------
# Transition matrix — fail-closed
# ---------------------------------------------------------------------------

_TRANSITIONS: dict[ReleaseState, frozenset[ReleaseState]] = {
    ReleaseState.DRAFT: frozenset({ReleaseState.CANDIDATE}),
    ReleaseState.CANDIDATE: frozenset({ReleaseState.GATE_PENDING}),
    ReleaseState.GATE_PENDING: frozenset(
        {
            ReleaseState.PROMOTED,
            ReleaseState.CANDIDATE,  # gate failed -> back to candidate
        }
    ),
    ReleaseState.PROMOTED: frozenset(
        {
            ReleaseState.PUBLISHED,
            ReleaseState.ROLLED_BACK,
        }
    ),
    ReleaseState.PUBLISHED: frozenset({ReleaseState.ROLLED_BACK}),
    ReleaseState.ROLLED_BACK: frozenset({ReleaseState.DRAFT}),  # corrective
}


# ---------------------------------------------------------------------------
# Semver-compatible Release Version
# ---------------------------------------------------------------------------

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z\-.]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z\-.]+))?$"
)


@dataclass(frozen=True)
class ReleaseVersion:
    """Semver 2.0.0 compatible version."""

    major: int
    minor: int
    patch: int
    pre_release: str = ""
    build_metadata: str = ""

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            v += f"-{self.pre_release}"
        if self.build_metadata:
            v += f"+{self.build_metadata}"
        return v

    def __lt__(self, other: ReleaseVersion) -> bool:
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other: ReleaseVersion) -> bool:
        return (self.major, self.minor, self.patch) <= (
            other.major,
            other.minor,
            other.patch,
        )

    @classmethod
    def parse(cls, version_str: str) -> ReleaseVersion:
        """Parse a semver string.  Raises ValueError on invalid input."""
        m = _SEMVER_RE.match(version_str.strip())
        if not m:
            msg = f"Invalid semver: {version_str!r}"
            raise ValueError(msg)
        return cls(
            major=int(m.group("major")),
            minor=int(m.group("minor")),
            patch=int(m.group("patch")),
            pre_release=m.group("pre") or "",
            build_metadata=m.group("build") or "",
        )

    def bump_major(self) -> ReleaseVersion:
        return ReleaseVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> ReleaseVersion:
        return ReleaseVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> ReleaseVersion:
        return ReleaseVersion(self.major, self.minor, self.patch + 1)


# ---------------------------------------------------------------------------
# Transition result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionResult:
    """Outcome of a state transition attempt."""

    allowed: bool
    from_state: ReleaseState
    to_state: ReleaseState
    reason: str = ""
    evidence_hash: str = ""
    timestamp_utc: str = ""


# ---------------------------------------------------------------------------
# Release Record
# ---------------------------------------------------------------------------


@dataclass
class ReleaseRecord:
    """Tracks the lifecycle of a single release."""

    release_id: str
    version: ReleaseVersion
    state: ReleaseState = ReleaseState.DRAFT
    history: list[dict[str, Any]] = field(default_factory=list)
    created_utc: str = ""
    updated_utc: str = ""

    def __post_init__(self) -> None:
        if not self.created_utc:
            self.created_utc = _now_utc()
        if not self.updated_utc:
            self.updated_utc = self.created_utc

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_id": self.release_id,
            "version": str(self.version),
            "state": str(self.state),
            "history": self.history,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReleaseRecord:
        return cls(
            release_id=data["release_id"],
            version=ReleaseVersion.parse(data["version"]),
            state=ReleaseState(data["state"]),
            history=data.get("history", []),
            created_utc=data.get("created_utc", ""),
            updated_utc=data.get("updated_utc", ""),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _evidence_hash(from_state: str, to_state: str, ts: str, reason: str) -> str:
    payload = json.dumps(
        {"from": from_state, "to": to_state, "ts": ts, "reason": reason},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_transition(
    from_state: ReleaseState,
    to_state: ReleaseState,
    *,
    gate_passed: bool | None = None,
    operator: str = "",
) -> TransitionResult:
    """Validate a state transition.  Fail-closed on unknown transitions.

    Args:
        from_state: Current release state.
        to_state: Requested target state.
        gate_passed: Whether the gate evaluation passed (required for
            GATE_PENDING -> PROMOTED).
        operator: Operator identifier (required for PROMOTED -> PUBLISHED).

    Returns:
        TransitionResult with allowed=True/False.
    """
    ts = _now_utc()
    allowed_targets = _TRANSITIONS.get(from_state, frozenset())

    if to_state not in allowed_targets:
        reason = f"Transition {from_state}->{to_state} not allowed"
        return TransitionResult(
            allowed=False,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            evidence_hash=_evidence_hash(from_state, to_state, ts, reason),
            timestamp_utc=ts,
        )

    # Gate-specific: GATE_PENDING -> PROMOTED requires gate pass
    gate_block = (
        from_state == ReleaseState.GATE_PENDING
        and to_state == ReleaseState.PROMOTED
        and gate_passed is not True
    )
    if gate_block:
        reason = "Gate must pass before promotion"
        return TransitionResult(
            allowed=False,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            evidence_hash=_evidence_hash(from_state, to_state, ts, reason),
            timestamp_utc=ts,
        )

    # Publish requires operator
    if from_state == ReleaseState.PROMOTED and to_state == ReleaseState.PUBLISHED and not operator:
        reason = "Operator required for publish"
        return TransitionResult(
            allowed=False,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            evidence_hash=_evidence_hash(from_state, to_state, ts, reason),
            timestamp_utc=ts,
        )

    reason = f"Transition {from_state}->{to_state} allowed"
    return TransitionResult(
        allowed=True,
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        evidence_hash=_evidence_hash(from_state, to_state, ts, reason),
        timestamp_utc=ts,
    )


def apply_transition(
    record: ReleaseRecord,
    to_state: ReleaseState,
    *,
    gate_passed: bool | None = None,
    operator: str = "",
    reason: str = "",
) -> TransitionResult:
    """Validate and apply a transition to a ReleaseRecord.

    Mutates record.state and record.history on success.
    Returns the TransitionResult (check .allowed before trusting record state).
    """
    result = validate_transition(
        record.state,
        to_state,
        gate_passed=gate_passed,
        operator=operator,
    )
    if result.allowed:
        old_state = record.state
        record.state = to_state
        record.updated_utc = result.timestamp_utc
        record.history.append(
            {
                "from": str(old_state),
                "to": str(to_state),
                "operator": operator,
                "reason": reason or result.reason,
                "evidence_hash": result.evidence_hash,
                "timestamp_utc": result.timestamp_utc,
            }
        )
    return result


def get_allowed_transitions(state: ReleaseState) -> frozenset[ReleaseState]:
    """Return the set of valid target states from a given state."""
    return _TRANSITIONS.get(state, frozenset())
