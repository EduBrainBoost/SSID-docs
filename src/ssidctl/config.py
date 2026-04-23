"""EMS configuration loader and validator."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "ems.schema.yaml"


@dataclass(frozen=True)
class PathsConfig:
    ssid_repo: Path
    ems_repo: Path
    state_dir: Path
    evidence_dir: Path
    vault_dir: Path


@dataclass(frozen=True)
class ClaudeConfig:
    command: str = "claude"
    timeout_seconds: int = 120


@dataclass(frozen=True)
class GuardsConfig:
    token_legal_lexicon_enabled: bool = True


@dataclass(frozen=True)
class ScopeDefaults:
    max_changed_files: int = 12
    max_changed_lines: int = 600
    allowed_file_types: tuple[str, ...] = (
        ".py",
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".txt",
        ".toml",
    )


@dataclass(frozen=True)
class EMSConfig:
    mode: str
    paths: PathsConfig
    concurrency: int = 1
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    guards: GuardsConfig = field(default_factory=GuardsConfig)
    scope_defaults: ScopeDefaults = field(default_factory=ScopeDefaults)


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


def _load_schema() -> dict[str, Any]:
    """Load the JSON-Schema-as-YAML for config validation."""
    if not _SCHEMA_PATH.exists():
        raise ConfigError(f"Schema not found: {_SCHEMA_PATH}")
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_raw(raw: dict[str, Any]) -> None:
    """Validate raw config dict against schema."""
    schema = _load_schema()
    try:
        jsonschema.validate(instance=raw, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ConfigError(f"Config validation failed: {exc.message}") from exc


def _validate_paths(paths: PathsConfig) -> None:
    """Validate that configured paths exist."""
    for name in ("ssid_repo", "ems_repo", "state_dir", "evidence_dir", "vault_dir"):
        p = getattr(paths, name)
        if not p.exists():
            raise ConfigError(f"Path does not exist: {name}={p}")


def _parse_config(raw: dict[str, Any]) -> EMSConfig:
    """Parse validated raw dict into EMSConfig."""
    paths_raw = raw["paths"]
    paths = PathsConfig(
        ssid_repo=Path(paths_raw["ssid_repo"]),
        ems_repo=Path(paths_raw["ems_repo"]),
        state_dir=Path(paths_raw["state_dir"]),
        evidence_dir=Path(paths_raw["evidence_dir"]),
        vault_dir=Path(paths_raw["vault_dir"]),
    )

    claude_raw = raw.get("claude", {})
    claude = ClaudeConfig(
        command=claude_raw.get("command", "claude"),
        timeout_seconds=claude_raw.get("timeout_seconds", 120),
    )

    guards_raw = raw.get("guards", {})
    guards = GuardsConfig(
        token_legal_lexicon_enabled=guards_raw.get("token_legal_lexicon_enabled", True),
    )

    scope_raw = raw.get("scope_defaults", {})
    scope = ScopeDefaults(
        max_changed_files=scope_raw.get("max_changed_files", 12),
        max_changed_lines=scope_raw.get("max_changed_lines", 600),
        allowed_file_types=tuple(
            scope_raw.get(
                "allowed_file_types",
                [
                    ".py",
                    ".yaml",
                    ".yml",
                    ".json",
                    ".md",
                    ".txt",
                    ".toml",
                ],
            )
        ),
    )

    return EMSConfig(
        mode=raw["mode"],
        paths=paths,
        concurrency=raw.get("concurrency", 1),
        claude=claude,
        guards=guards,
        scope_defaults=scope,
    )


def load_config(config_path: Path | None = None, validate_paths: bool = True) -> EMSConfig:
    """Load and validate EMS configuration.

    Args:
        config_path: Explicit path to ems.yaml. If None, uses config/ems.yaml
                     relative to ems_repo, or EMS_CONFIG_PATH env var.
        validate_paths: Whether to check that configured paths exist on disk.
    """
    if config_path is None:
        env_path = os.environ.get("EMS_CONFIG_PATH")
        config_path = Path(env_path) if env_path else _SCHEMA_PATH.parent / "ems.yaml"

    if not config_path.exists():
        raise ConfigError(
            f"Config file not found: {config_path}\n"
            f"Copy config/ems.sample.yaml to config/ems.yaml and adjust paths."
        )

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(f"Config must be a YAML mapping, got {type(raw).__name__}")

    _validate_raw(raw)
    config = _parse_config(raw)

    if validate_paths:
        _validate_paths(config.paths)

    return config


def list_profiles(config_dir: Path | None = None) -> list[str]:
    """List available config profiles from config/profiles/ directory.

    Returns list of profile names (filename stems).
    """
    if config_dir is None:
        config_dir = _SCHEMA_PATH.parent
    profiles_dir = config_dir / "profiles"
    if not profiles_dir.exists():
        return []
    return sorted(p.stem for p in profiles_dir.glob("*.yaml"))


def load_profile(
    profile_name: str, config_dir: Path | None = None, validate_paths: bool = True
) -> EMSConfig:
    """Load a named config profile from config/profiles/{name}.yaml.

    Args:
        profile_name: Name of profile (without .yaml extension).
        config_dir: Base config directory. Defaults to config/ next to schema.
        validate_paths: Whether to check that configured paths exist on disk.
    """
    if config_dir is None:
        config_dir = _SCHEMA_PATH.parent
    profile_path = config_dir / "profiles" / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise ConfigError(f"Profile not found: {profile_name} (looked in {profile_path})")
    return load_config(profile_path, validate_paths=validate_paths)
