"""System Profiles Extension — multi-profile config management.

Provides profile discovery, loading, merging, and validation
for the EMS multi-profile configuration system. Complements
config.py's load_config() with profile overlay support.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class ProfileError(Exception):
    pass


_EMS_PROFILE_ENV = "EMS_PROFILE"
_PROFILES_DIR_NAME = "profiles"


def profiles_dir(config_dir: Path) -> Path:
    """Return the profiles directory path."""
    return config_dir / _PROFILES_DIR_NAME


def list_profiles(config_dir: Path) -> list[str]:
    """List available profile names (YAML files in profiles/ dir)."""
    pdir = profiles_dir(config_dir)
    if not pdir.is_dir():
        return []
    return sorted(p.stem for p in pdir.iterdir() if p.suffix in (".yaml", ".yml") and p.is_file())


def active_profile() -> str | None:
    """Get the currently active profile from EMS_PROFILE env var."""
    return os.environ.get(_EMS_PROFILE_ENV)


def load_profile(config_dir: Path, profile_name: str) -> dict[str, Any]:
    """Load a single profile's config dict from profiles/{name}.yaml."""
    pdir = profiles_dir(config_dir)
    for suffix in (".yaml", ".yml"):
        path = pdir / f"{profile_name}{suffix}"
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data is None:
                return {}
            if not isinstance(data, dict):
                raise ProfileError(
                    f"Profile {profile_name} must be a YAML mapping, got {type(data).__name__}"
                )
            return data
    raise ProfileError(f"Profile not found: {profile_name} (searched in {pdir})")


def merge_configs(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge overlay config onto base config.

    - Dict values are merged recursively.
    - List values are replaced (not appended).
    - Scalar values are overwritten.
    """
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def resolve_config(
    base_config: dict[str, Any],
    config_dir: Path,
    profile: str | None = None,
) -> dict[str, Any]:
    """Resolve final config by merging base with profile overlay.

    Resolution order:
    1. base_config (from ems.yaml)
    2. Profile overlay (from profiles/{profile}.yaml)
    3. Environment variable EMS_PROFILE (if profile not explicitly given)
    """
    profile_name = profile or active_profile()
    if not profile_name:
        return dict(base_config)

    try:
        overlay = load_profile(config_dir, profile_name)
    except ProfileError:
        # Profile not found — return base config unchanged
        return dict(base_config)

    return merge_configs(base_config, overlay)


def validate_profile(config_dir: Path, profile_name: str) -> list[str]:
    """Validate a profile and return list of warnings/errors."""
    warnings: list[str] = []

    try:
        data = load_profile(config_dir, profile_name)
    except ProfileError as e:
        return [str(e)]

    # Check for unknown top-level keys
    known_keys = {"paths", "tools", "gates", "agents", "features", "logging", "security"}
    unknown = set(data.keys()) - known_keys
    if unknown:
        warnings.append(f"Unknown top-level keys: {', '.join(sorted(unknown))}")

    # Check paths are valid if present
    paths = data.get("paths", {})
    if isinstance(paths, dict):
        for name, value in paths.items():
            if isinstance(value, str):
                p = Path(value)
                if p.is_absolute() and not p.exists():
                    warnings.append(f"Path {name}={value} does not exist")

    return warnings


def create_profile(
    config_dir: Path,
    profile_name: str,
    config: dict[str, Any],
    overwrite: bool = False,
) -> Path:
    """Create a new profile YAML file.

    Returns the path to the created file.
    """
    pdir = profiles_dir(config_dir)
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / f"{profile_name}.yaml"

    if path.exists() and not overwrite:
        raise ProfileError(f"Profile already exists: {profile_name} (use overwrite=True)")

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    return path


def delete_profile(config_dir: Path, profile_name: str) -> bool:
    """Delete a profile YAML file. Returns True if deleted."""
    pdir = profiles_dir(config_dir)
    for suffix in (".yaml", ".yml"):
        path = pdir / f"{profile_name}{suffix}"
        if path.is_file():
            path.unlink()
            return True
    return False


def render_profiles_text(config_dir: Path) -> str:
    """Render available profiles as text listing."""
    profiles = list_profiles(config_dir)
    current = active_profile()

    lines = ["Available Profiles:", "-" * 30]
    if not profiles:
        lines.append("  (none)")
    else:
        for name in profiles:
            marker = " *" if name == current else ""
            lines.append(f"  {name}{marker}")
    if current:
        lines.append(f"\n  Active: {current} (from {_EMS_PROFILE_ENV})")
    return "\n".join(lines)
