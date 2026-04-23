"""Identity integration — bridges identity_lib with ssidctl RBAC.

Resolves the current caller's identity and maps it to an authz.Identity
for permission checking throughout ssidctl commands.
"""

from __future__ import annotations

import getpass
import os
from pathlib import Path

from ssidctl.core.authz import Identity, resolve_role

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


class IdentityResolveError(Exception):
    """Raised when identity cannot be resolved."""


def _resolve_username(env_var: str = "SSID_IDENTITY") -> tuple[str, str]:
    """Resolve username from ENV or OS.

    Returns:
        (username, source) where source is "env" or "os".
    """
    env_val = os.environ.get(env_var, "").strip()
    if env_val:
        return env_val, "env"
    return getpass.getuser(), "os"


def _load_identities_yaml(path: Path) -> dict:
    """Load identities.yaml. Returns empty dict if file missing or yaml unavailable."""
    if not _HAS_YAML or not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return {}
    return data


def resolve_caller(
    identities_path: Path | None = None,
    env_var: str = "SSID_IDENTITY",
    default_role: str = "readonly",
) -> Identity:
    """Resolve the current caller to an authz.Identity.

    Resolution:
    1. Username from SSID_IDENTITY env var, or OS user
    2. Role from identities.yaml lookup
    3. Fallback to default_role for unknown users

    Args:
        identities_path: Path to identities.yaml. None = skip file lookup.
        env_var: ENV var name for identity override.
        default_role: Role for unknown users (must be low-privilege).

    Returns:
        authz.Identity ready for permission checks.
    """
    username, _source = _resolve_username(env_var)

    if identities_path is not None:
        data = _load_identities_yaml(identities_path)
        identities = data.get("identities", {})
        file_default = data.get("default_role", default_role)

        entry = identities.get(username)
        if entry is not None:
            role = resolve_role(entry["role"])
            return Identity(username=username, role=role)

        # Unknown user -> file default or param default
        role = resolve_role(file_default)
        return Identity(username=username, role=role)

    # No identities file -> default role
    role = resolve_role(default_role)
    return Identity(username=username, role=role)


def resolve_caller_from_config(config) -> Identity:
    """Resolve caller using EMSConfig identity settings.

    Reads identity.identities_path from config and resolves relative
    to the config file's directory (ems_repo/config/ or the path itself).

    Args:
        config: EMSConfig instance.

    Returns:
        authz.Identity for the current caller.
    """
    identity_cfg = getattr(config, "identity", None)

    if identity_cfg is None:
        # Config has no identity section -> try standard location
        ssidctl_cfg = "12_tooling" / Path("ops/ssidctl/config")
        std_path = config.paths.ssid_repo / ssidctl_cfg / "identities.yaml"
        return resolve_caller(identities_path=std_path)

    identities_rel = getattr(identity_cfg, "identities_path", "identities.yaml")
    env_var = getattr(identity_cfg, "env_var", "SSID_IDENTITY")
    default_role = getattr(identity_cfg, "default_role", "readonly")

    # Resolve path: if relative, look next to ems.yaml (ssid config dir)
    id_path = Path(identities_rel)
    if not id_path.is_absolute():
        ssidctl_cfg = "12_tooling" / Path("ops/ssidctl/config")
        id_path = config.paths.ssid_repo / ssidctl_cfg / identities_rel

    return resolve_caller(
        identities_path=id_path,
        env_var=env_var,
        default_role=default_role,
    )
