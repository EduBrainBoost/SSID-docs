"""Build uvicorn command for EMS backend with env-gated reload policy.

Rules:
- EMS_ENV=dev  -> --reload is allowed
- EMS_ENV=staging|production (or any non-dev value) -> --reload is forbidden
- If --reload appears in extra_args while EMS_ENV != dev -> raises ValueError
"""

from __future__ import annotations

import os

_EMS_APP = "portal.backend.main:app"
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000


def is_dev_env(ems_env: str | None = None) -> bool:
    """Return True if EMS_ENV is 'dev'."""
    raw = ems_env if ems_env is not None else os.environ.get("EMS_ENV", "production")
    env = raw.lower().strip()
    return env == "dev"


def build_uvicorn_cmd(
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    ems_env: str | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build a deterministic uvicorn command list.

    Raises ValueError if --reload is requested outside dev environment.
    """
    dev = is_dev_env(ems_env)
    extras = list(extra_args or [])

    # Guard: reject --reload injection in non-dev environments
    if not dev and "--reload" in extras:
        raise ValueError(
            f"--reload is forbidden when EMS_ENV != dev "
            f"(current: {ems_env or os.environ.get('EMS_ENV', 'production')}). "
            f"Reload causes zombie worker processes in staging/production."
        )

    cmd = [
        "python",
        "-m",
        "uvicorn",
        _EMS_APP,
        "--host",
        host,
        "--port",
        str(port),
    ]

    if dev:
        cmd.append("--reload")

    # Append any extra args (already validated above)
    cmd.extend(e for e in extras if e != "--reload")

    return cmd
