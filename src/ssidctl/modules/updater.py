"""Self-update module — check for new versions and upgrade via pip.

Queries PyPI for the latest ssidctl version and offers self-update.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from typing import Any

PYPI_URL = "https://pypi.org/pypi/ssidctl/json"
CURRENT_VERSION = "0.1.0"


class UpdateError(Exception):
    pass


def check_update() -> dict[str, Any]:
    """Check PyPI for a newer version.

    Returns {current, latest, update_available}.
    """
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
            latest = data.get("info", {}).get("version", CURRENT_VERSION)
    except Exception:
        # If PyPI is unreachable, report no update
        return {
            "current": CURRENT_VERSION,
            "latest": CURRENT_VERSION,
            "update_available": False,
            "error": "Could not reach PyPI",
        }

    update_available = latest != CURRENT_VERSION
    return {
        "current": CURRENT_VERSION,
        "latest": latest,
        "update_available": update_available,
    }


def self_update() -> dict[str, Any]:
    """Run pip install --upgrade ssidctl.

    Returns {success, output}.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "ssidctl"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip() or result.stderr.strip(),
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise UpdateError(f"Update failed: {e}") from e
