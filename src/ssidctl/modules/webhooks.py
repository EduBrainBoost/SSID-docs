"""Webhook module — event-driven command dispatch.

CLI-first: webhooks trigger ssidctl commands, not external HTTP calls.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import yaml

# Strict allowlist for payload values — only safe characters
_SAFE_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:/\-@=+ ]{0,256}$")


def _sanitize_value(value: str) -> str:
    """Validate and sanitize a payload value for use in commands.

    Rejects values containing shell metacharacters or exceeding length limits.
    """
    s = str(value)
    if not _SAFE_VALUE_RE.match(s):
        raise ValueError(
            f"Webhook payload value contains unsafe characters or is too long: {s[:50]!r}"
        )
    return s


class WebhookRegistry:
    def __init__(self, webhook_dir: Path) -> None:
        self._dir = webhook_dir
        self._path = webhook_dir / "hooks.yaml"

    def _load(self) -> list[dict[str, str]]:
        if not self._path.exists():
            return []
        with open(self._path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return (data or {}).get("hooks", [])

    def _save(self, hooks: list[dict[str, str]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump({"hooks": hooks}, f, default_flow_style=False)

    def register(self, event: str, command: str) -> None:
        hooks = self._load()
        hooks.append({"event": event, "command": command})
        self._save(hooks)

    def unregister(self, event: str) -> None:
        hooks = [h for h in self._load() if h["event"] != event]
        self._save(hooks)

    def list_hooks(self) -> list[dict[str, str]]:
        return self._load()

    def dispatch(self, event: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        for hook in self._load():
            if hook["event"] == event:
                cmd_template = hook["command"]
                # Sanitize all payload values before substitution
                try:
                    safe_payload = {k: _sanitize_value(v) for k, v in payload.items()}
                except ValueError as exc:
                    results.append(
                        {
                            "event": event,
                            "command": cmd_template,
                            "exit_code": -3,
                            "stdout": f"payload rejected: {exc}",
                        }
                    )
                    continue

                # Substitute placeholders with sanitized values
                resolved = cmd_template
                for k, v in safe_payload.items():
                    resolved = resolved.replace(f"{{{k}}}", v)

                # Execute as argv list (no shell)
                argv = shlex.split(resolved)
                try:
                    r = subprocess.run(
                        argv,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    results.append(
                        {
                            "event": event,
                            "command": resolved,
                            "exit_code": r.returncode,
                            "stdout": r.stdout[:200],
                        }
                    )
                except subprocess.TimeoutExpired:
                    results.append(
                        {
                            "event": event,
                            "command": resolved,
                            "exit_code": -2,
                            "stdout": "timeout",
                        }
                    )
                except FileNotFoundError:
                    results.append(
                        {
                            "event": event,
                            "command": resolved,
                            "exit_code": -1,
                            "stdout": f"command not found: {argv[0] if argv else '(empty)'}",
                        }
                    )
        return results
