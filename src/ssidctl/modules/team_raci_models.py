"""Team RACI Extension — typed RACI matrix models and validation.

Provides dataclasses and validation for RACI assignments.
Complements team.py's get_raci() with matrix rendering and conflict detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_VALID_RACI_ROLES = frozenset({"R", "A", "C", "I"})

_RACI_LABELS = {
    "R": "Responsible",
    "A": "Accountable",
    "C": "Consulted",
    "I": "Informed",
}


class RACIError(Exception):
    pass


@dataclass(frozen=True)
class RACIAssignment:
    """One agent's RACI role for a specific task type."""

    agent_name: str
    task_type: str
    role: str  # R, A, C, or I

    def __post_init__(self) -> None:
        if self.role not in _VALID_RACI_ROLES:
            raise RACIError(
                f"Invalid RACI role: {self.role!r}. Must be one of {sorted(_VALID_RACI_ROLES)}"
            )


@dataclass
class RACIMatrix:
    """Full RACI matrix across all task types and agents."""

    assignments: list[RACIAssignment] = field(default_factory=list)

    @classmethod
    def from_agents(cls, agents: list[dict[str, Any]]) -> RACIMatrix:
        """Build matrix from team agent dicts (each may have a 'raci' field)."""
        assignments: list[RACIAssignment] = []
        for agent in agents:
            name = agent.get("name", "unknown")
            raci = agent.get("raci", {})
            for task_type, role in raci.items():
                assignments.append(RACIAssignment(agent_name=name, task_type=task_type, role=role))
        return cls(assignments=assignments)

    @property
    def task_types(self) -> list[str]:
        """All unique task types in the matrix, sorted."""
        return sorted({a.task_type for a in self.assignments})

    @property
    def agents(self) -> list[str]:
        """All unique agent names in the matrix, sorted."""
        return sorted({a.agent_name for a in self.assignments})

    def get(self, agent_name: str, task_type: str) -> str | None:
        """Get the RACI role for an agent on a task type, or None."""
        for a in self.assignments:
            if a.agent_name == agent_name and a.task_type == task_type:
                return a.role
        return None

    def get_for_task(self, task_type: str) -> dict[str, str]:
        """Get {agent_name: role} for a given task type."""
        return {a.agent_name: a.role for a in self.assignments if a.task_type == task_type}

    def get_for_agent(self, agent_name: str) -> dict[str, str]:
        """Get {task_type: role} for a given agent."""
        return {a.task_type: a.role for a in self.assignments if a.agent_name == agent_name}

    def validate(self) -> list[str]:
        """Check RACI rules and return list of warnings.

        Rules checked:
        - Each task type should have exactly one 'A' (Accountable).
        - Each task type should have at least one 'R' (Responsible).
        """
        warnings: list[str] = []
        for tt in self.task_types:
            roles = self.get_for_task(tt)
            a_count = sum(1 for r in roles.values() if r == "A")
            r_count = sum(1 for r in roles.values() if r == "R")
            if a_count == 0:
                warnings.append(f"Task type {tt!r}: no Accountable (A) agent assigned")
            elif a_count > 1:
                warnings.append(
                    f"Task type {tt!r}: {a_count} Accountable (A) agents (should be 1)"
                )
            if r_count == 0:
                warnings.append(f"Task type {tt!r}: no Responsible (R) agent assigned")
        return warnings

    def render_text(self) -> str:
        """Render the RACI matrix as an ASCII table."""
        task_types = self.task_types
        agents = self.agents

        if not task_types or not agents:
            return "RACI Matrix: (empty)"

        agent_w = max(len(a) for a in agents)
        agent_w = max(agent_w, 5)
        col_w = max(max((len(t) for t in task_types), default=4), 4)

        header = f"{'Agent':<{agent_w}}"
        for tt in task_types:
            header += f"  {tt:^{col_w}}"
        sep = "-" * len(header)

        lines = ["RACI Matrix", sep, header, sep]
        for agent in agents:
            row = f"{agent:<{agent_w}}"
            for tt in task_types:
                role = self.get(agent, tt) or "-"
                row += f"  {role:^{col_w}}"
            lines.append(row)
        lines.append(sep)
        return "\n".join(lines)


def validate_raci_dict(raci: dict[str, str]) -> list[str]:
    """Validate a single agent's raci dict. Returns list of error strings."""
    errors: list[str] = []
    for task_type, role in raci.items():
        if role not in _VALID_RACI_ROLES:
            errors.append(f"Invalid role {role!r} for task type {task_type!r}")
    return errors


def raci_role_label(role: str) -> str:
    """Return the human-readable label for a RACI role code."""
    return _RACI_LABELS.get(role, f"Unknown({role})")
