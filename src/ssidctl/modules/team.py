"""Team Registry module — agent profiles and availability.

Stores agent profiles in team.yaml. Each agent has:
- name, role, responsibilities, tools_allowed, scope_allowed, availability
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.event_log import EventLog

_VALID_AVAILABILITY = frozenset({"IDLE", "RUNNING", "BLOCKED"})


class TeamError(Exception):
    pass


class TeamRegistry:
    """Team registry for agent profiles."""

    def __init__(self, team_dir: Path) -> None:
        self._dir = team_dir
        self._path = team_dir / "team.yaml"
        self._event_log = EventLog(team_dir / "team.jsonl")

    def _load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        with open(self._path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return []
        return data.get("agents", [])

    def _save(self, agents: list[dict[str, Any]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"agents": agents},
                f,
                default_flow_style=False,
                allow_unicode=True,
            )

    def list_agents(self) -> list[dict[str, Any]]:
        return self._load()

    def show(self, name: str) -> dict[str, Any]:
        for agent in self._load():
            if agent["name"] == name:
                return agent
        raise TeamError(f"Agent not found: {name}")

    def set_status(self, name: str, availability: str, actor: str = "user") -> dict[str, Any]:
        if availability not in _VALID_AVAILABILITY:
            raise TeamError(f"Invalid availability: {availability}")

        agents = self._load()
        for agent in agents:
            if agent["name"] == name:
                old = agent.get("availability", "IDLE")
                agent["availability"] = availability
                self._save(agents)
                self._event_log.append(
                    "team.status_changed",
                    {"name": name, "from": old, "to": availability},
                    actor,
                )
                return agent
        raise TeamError(f"Agent not found: {name}")

    def get_raci(self, task_type: str) -> dict[str, str]:
        """Get RACI matrix for a given task type.

        Returns {agent_name: "R"|"A"|"C"|"I"} for agents that have
        a raci mapping covering this task_type.
        """
        result: dict[str, str] = {}
        for agent in self._load():
            raci = agent.get("raci", {})
            if task_type in raci:
                result[agent["name"]] = raci[task_type]
        return result

    def seed(self, seed_path: Path, actor: str = "user") -> None:
        """Load agents from a seed file (initial setup)."""
        if not seed_path.exists():
            raise TeamError(f"Seed file not found: {seed_path}")
        with open(seed_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        agents = data.get("agents", [])
        self._save(agents)
        self._event_log.append(
            "team.seeded",
            {"source": str(seed_path), "agent_count": len(agents)},
            actor,
        )
