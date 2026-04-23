"""Office Avatars Extension — avatar registry and formatting helpers.

Provides avatar assignment, validation, and rendering utilities
for the office dashboard. Complements office.py's AgentPanel.avatar field.
"""

from __future__ import annotations

from typing import Any

# Default avatar catalog — short 2-3 char labels for console display.
# Keys are canonical role names used in team_seed.yaml.
DEFAULT_AVATARS: dict[str, str] = {
    "orchestrator": "ORC",
    "implementer": "IMP",
    "verifier": "VER",
    "reviewer": "REV",
    "planner": "PLN",
    "security": "SEC",
    "pr_integrator": "PRI",
    "content_writer": "CW",
    "board_manager": "BM",
    "incident_commander": "IC",
    "doctor": "DOC",
    "deployer": "DEP",
}

MAX_AVATAR_LEN = 3


class AvatarError(Exception):
    pass


def validate_avatar(avatar: str) -> str:
    """Validate and normalize an avatar string (max 3 chars)."""
    avatar = avatar.strip()
    if len(avatar) > MAX_AVATAR_LEN:
        raise AvatarError(
            f"Avatar too long: {avatar!r} ({len(avatar)} chars, max {MAX_AVATAR_LEN})"
        )
    if not avatar:
        raise AvatarError("Avatar must not be empty")
    return avatar


def resolve_avatar(agent: dict[str, Any]) -> str:
    """Resolve the avatar for an agent dict.

    Priority:
    1. agent["avatar"] if present and non-empty
    2. DEFAULT_AVATARS lookup by agent["role"]
    3. First 3 chars of agent["name"] uppercased
    """
    explicit = agent.get("avatar")
    if explicit and isinstance(explicit, str) and explicit.strip():
        return explicit.strip()[:MAX_AVATAR_LEN]

    role = agent.get("role", "")
    role_key = role.lower().replace(" ", "_").replace("-", "_")
    if role_key in DEFAULT_AVATARS:
        return DEFAULT_AVATARS[role_key]

    name = agent.get("name", "???")
    return name[:MAX_AVATAR_LEN].upper()


def assign_avatars(agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign avatars to all agents that don't have one.

    Returns the agents list with 'avatar' field filled in.
    Does NOT mutate the originals — returns new dicts.
    """
    result: list[dict[str, Any]] = []
    used: set[str] = set()
    for agent in agents:
        new_agent = dict(agent)
        avatar = resolve_avatar(agent)
        # Deduplicate: if avatar already used, append number
        if avatar in used:
            for i in range(2, 100):
                candidate = f"{avatar[:2]}{i}"
                if candidate not in used:
                    avatar = candidate
                    break
        used.add(avatar)
        new_agent["avatar"] = avatar
        result.append(new_agent)
    return result


def render_avatar_legend(agents: list[dict[str, Any]]) -> str:
    """Render a legend mapping avatars to agent names."""
    lines = ["Avatar Legend:", "-" * 30]
    for agent in agents:
        avatar = resolve_avatar(agent)
        name = agent.get("name", "unknown")
        role = agent.get("role", "unknown")
        lines.append(f"  {avatar:3s}  {name} ({role})")
    return "\n".join(lines)


def format_avatar_cell(avatar: str | None, width: int = 3) -> str:
    """Format an avatar for a fixed-width table cell."""
    if not avatar:
        return " " * width
    return avatar[:width].ljust(width)
