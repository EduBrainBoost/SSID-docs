"""Routing Engine — maps findings to responsible agents.

Uses routing_matrix.yaml to determine which agent handles each finding.
Handles priority ordering, conflict detection, and stop-on-core logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ssidctl.autopilot.normalizer import Finding
from ssidctl.core.protected_paths import ProtectedPaths


@dataclass(frozen=True)
class RouteRule:
    """A single routing rule from the matrix."""

    finding_type: str
    agents: list[str]
    priority: int
    stop_on_core: bool


@dataclass
class RoutedTask:
    """A finding assigned to agent(s) for remediation."""

    finding: Finding
    agents: list[str]
    priority: int
    stop_required: bool = False
    stop_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_type": self.finding.finding_type,
            "gate_name": self.finding.gate_name,
            "agents": self.agents,
            "priority": self.priority,
            "stop_required": self.stop_required,
            "stop_code": self.stop_code,
            "paths": self.finding.paths,
        }


@dataclass
class RoutingDecision:
    """Complete routing decision for a set of findings."""

    tasks: list[RoutedTask] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    unroutable: list[Finding] = field(default_factory=list)

    @property
    def has_stops(self) -> bool:
        return any(t.stop_required for t in self.tasks)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tasks": [t.to_dict() for t in self.tasks],
            "conflicts": self.conflicts,
            "unroutable": [f.to_dict() for f in self.unroutable],
            "has_stops": self.has_stops,
            "has_conflicts": self.has_conflicts,
        }


class RoutingEngine:
    """Routes findings to agents based on routing matrix."""

    def __init__(
        self,
        matrix_path: Path,
        protected_paths: ProtectedPaths | None = None,
    ) -> None:
        self._matrix_path = matrix_path
        self._protected = protected_paths
        self._rules: list[RouteRule] = []
        self._conflict_policy = "STOP_CONFLICT"

    def load(self) -> None:
        """Load routing matrix from YAML."""
        data = yaml.safe_load(self._matrix_path.read_text(encoding="utf-8"))

        self._rules = [
            RouteRule(
                finding_type=r["finding_type"],
                agents=r.get("agents", []),
                priority=r.get("priority", 5),
                stop_on_core=r.get("stop_on_core", False),
            )
            for r in data.get("routes", [])
        ]

        cr = data.get("conflict_resolution", {})
        self._conflict_policy = cr.get("same_path_policy", "STOP_CONFLICT")

    def route(self, findings: list[Finding]) -> RoutingDecision:
        """Route findings to agents.

        Args:
            findings: Normalized findings from gate results.

        Returns:
            RoutingDecision with tasks, conflicts, and unroutable findings.
        """
        if not self._rules:
            self.load()

        decision = RoutingDecision()
        path_assignments: dict[str, list[tuple[str, str]]] = {}  # path -> [(finding_type, agent)]

        for finding in findings:
            rule = self._find_rule(finding.finding_type)

            if rule is None:
                decision.unroutable.append(finding)
                continue

            # Check if finding affects protected paths
            stop_required = False
            stop_code = ""

            if rule.stop_on_core and finding.paths and self._protected:
                violations = self._protected.check(finding.paths)
                if violations:
                    stop_required = True
                    stop_code = "STOP_CORE_CHANGE"

            if not rule.agents:
                stop_required = True
                stop_code = stop_code or "STOP_UNROUTABLE"

            task = RoutedTask(
                finding=finding,
                agents=list(rule.agents),
                priority=rule.priority,
                stop_required=stop_required,
                stop_code=stop_code,
            )
            decision.tasks.append(task)

            # Track path-to-agent assignments for conflict detection.
            # key: path -> set of (finding_type, agent) tuples.
            # Agents from the SAME finding type are collaborators (not conflicting).
            for path in finding.paths:
                assigned = path_assignments.setdefault(path, [])
                for agent in rule.agents:
                    entry = (finding.finding_type, agent)
                    if entry not in assigned:
                        assigned.append(entry)

        # Detect conflicts: same path assigned to agents from DIFFERENT finding types
        for path, entries in path_assignments.items():
            # Group agents by finding_type
            finding_types = {ft for ft, _ in entries}
            agents = list({a for _, a in entries})
            if len(finding_types) > 1 and len(agents) > 1:
                decision.conflicts.append(
                    {
                        "path": path,
                        "agents": agents,
                        "policy": self._conflict_policy,
                    }
                )
                if self._conflict_policy == "STOP_CONFLICT":
                    # Mark first relevant task as stop-required
                    for task in decision.tasks:
                        if path in task.finding.paths and not task.stop_required:
                            task.stop_required = True
                            task.stop_code = "STOP_CONFLICT"
                            break

        # Sort by priority (lowest number = highest priority)
        decision.tasks.sort(key=lambda t: t.priority)

        return decision

    def _find_rule(self, finding_type: str) -> RouteRule | None:
        """Find the routing rule for a finding type."""
        for rule in self._rules:
            if rule.finding_type == finding_type:
                return rule
        return None
