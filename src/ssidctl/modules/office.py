"""Office Screen module — agent dashboard.

Aggregates status from team registry, board, and run history.
Provides snapshot and polling (watch) modes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.timeutil import utcnow_iso


@dataclass(frozen=True)
class AgentPanel:
    name: str
    role: str
    availability: str
    active_task: str | None
    last_run: str | None
    task_counts: dict[str, int]
    avatar: str | None = None


class OfficeScreen:
    """Aggregates agent and system status for the office dashboard."""

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def snapshot(self) -> dict[str, Any]:
        """Build a full office snapshot."""
        agents = self._load_agents()
        board_summary = self._board_summary()
        panels = []

        for agent in agents:
            name = agent.get("name", "unknown")
            active_task = self._find_active_task(name)
            last_run = self._find_last_run(name)
            task_counts = self._agent_task_counts(name)

            panels.append(
                AgentPanel(
                    name=name,
                    role=agent.get("role", "unknown"),
                    availability=agent.get("availability", "IDLE"),
                    active_task=active_task,
                    last_run=last_run,
                    task_counts=task_counts,
                    avatar=agent.get("avatar"),
                )
            )

        return {
            "timestamp": utcnow_iso(),
            "agents": panels,
            "board": board_summary,
        }

    def render_text(self, snap: dict[str, Any] | None = None) -> str:
        """Render the office dashboard as text."""
        if snap is None:
            snap = self.snapshot()

        lines = []
        lines.append("=" * 60)
        lines.append(f"  SSID-EMS Office Screen   {snap['timestamp']}")
        lines.append("=" * 60)
        lines.append("")

        # Board summary
        board = snap["board"]
        lines.append("  Board Summary:")
        for status, count in sorted(board.items()):
            if count > 0:
                lines.append(f"    {status:12s} {count}")
        lines.append("")

        # Agent panels
        lines.append("  Agent Panels:")
        lines.append(f"  {'Av':3s} {'Name':16s} {'Role':16s} {'Status':10s} {'Task':20s}")
        lines.append("  " + "-" * 62)

        for agent in snap["agents"]:
            task_str = agent.active_task or "-"
            if len(task_str) > 20:
                task_str = task_str[:17] + "..."
            av = agent.avatar or "   "
            if len(av) > 3:
                av = av[:3]
            lines.append(
                f"  {av:3s} {agent.name:16s} {agent.role:16s} "
                f"{agent.availability:10s} {task_str:20s}"
            )

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def export_status(self) -> dict[str, Any]:
        """Export status as a serializable dict (for status.json)."""
        snap = self.snapshot()
        return {
            "timestamp": snap["timestamp"],
            "agents": [
                {
                    "name": a.name,
                    "role": a.role,
                    "availability": a.availability,
                    "active_task": a.active_task,
                    "last_run": a.last_run,
                    "task_counts": a.task_counts,
                    "avatar": a.avatar,
                }
                for a in snap["agents"]
            ],
            "board": snap["board"],
        }

    def render_markdown(self, snap: dict[str, Any] | None = None) -> str:
        """Render office dashboard as Markdown."""
        if snap is None:
            snap = self.snapshot()
        lines = [
            "# SSID-EMS Office Status",
            "",
            f"*Generated: {snap['timestamp']}*",
            "",
            "## Board Summary",
            "",
            "| Status | Count |",
            "|--------|-------|",
        ]
        for status, count in sorted(snap["board"].items()):
            if count > 0:
                lines.append(f"| {status} | {count} |")
        lines.extend(
            [
                "",
                "## Agent Panels",
                "",
                "| Name | Role | Status | Active Task |",
                "|------|------|--------|-------------|",
            ]
        )
        for agent in snap["agents"]:
            task_str = agent.active_task or "-"
            lines.append(f"| {agent.name} | {agent.role} | {agent.availability} | {task_str} |")
        lines.append("")
        return "\n".join(lines)

    def _load_agents(self) -> list[dict[str, Any]]:
        team_path = self._state_dir / "team" / "team.yaml"
        if not team_path.exists():
            return []
        with open(team_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return []
        return data.get("agents", [])

    def _board_summary(self) -> dict[str, int]:
        board_path = self._state_dir / "board" / "tasks.yaml"
        if not board_path.exists():
            return {}
        with open(board_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return {}

        tasks = data.get("tasks", {})
        counts: dict[str, int] = {}
        for task in tasks.values():
            status = task.get("status", "UNKNOWN")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _find_active_task(self, agent_name: str) -> str | None:
        """Find the currently active task for an agent (DOING status)."""
        board_path = self._state_dir / "board" / "tasks.yaml"
        if not board_path.exists():
            return None
        with open(board_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return None

        for task in data.get("tasks", {}).values():
            owner = task.get("owner", "")
            if owner == f"agent:{agent_name}" and task.get("status") == "DOING":
                return task.get("task_id")
        return None

    def _find_last_run(self, agent_name: str) -> str | None:
        """Find the last run associated with an agent."""
        runs_path = self._state_dir / "runs" / "runs.jsonl"
        if not runs_path.exists():
            return None

        last = None
        with open(runs_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("actor") == agent_name:
                        last = entry.get("run_id")
                except (json.JSONDecodeError, KeyError):
                    continue
        return last

    def _agent_task_counts(self, agent_name: str) -> dict[str, int]:
        """Count tasks per status for an agent."""
        board_path = self._state_dir / "board" / "tasks.yaml"
        if not board_path.exists():
            return {}
        with open(board_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return {}

        counts: dict[str, int] = {}
        for task in data.get("tasks", {}).values():
            if task.get("owner") == f"agent:{agent_name}":
                status = task.get("status", "UNKNOWN")
                counts[status] = counts.get(status, 0) + 1
        return counts
