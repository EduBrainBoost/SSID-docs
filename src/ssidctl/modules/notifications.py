"""Notification module — output-only channels (Telegram, Discord, Email, Log).

Channels are configured in policies/notifications.yaml.
All messages are sanitized before sending.
"""

from __future__ import annotations

import json
import smtplib
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import yaml

from ssidctl.core.sanitizer import sanitize_text
from ssidctl.core.timeutil import utcnow_iso


@dataclass(frozen=True)
class Channel:
    name: str
    type: str  # "telegram" | "discord" | "email" | "log"
    config: dict[str, Any]


class NotificationDispatcher:
    def __init__(self, channels: list[Channel]) -> None:
        self._channels = {c.name: c for c in channels}

    @classmethod
    def from_yaml(cls, path: Path) -> NotificationDispatcher:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        channels = [
            Channel(name=c["name"], type=c["type"], config=c.get("config", {}))
            for c in data.get("channels", [])
        ]
        return cls(channels)

    def list_channels(self) -> list[str]:
        return list(self._channels.keys())

    def send(self, message: str, channel: str, sanitize: bool = True) -> dict[str, Any]:
        if channel not in self._channels:
            return {"status": "error", "reason": f"Unknown channel: {channel}"}

        ch = self._channels[channel]
        text = sanitize_text(message).text if sanitize else message
        timestamp = utcnow_iso()

        try:
            if ch.type == "log":
                log_path = Path(ch.config.get("log_path", "/tmp/ssidctl_notify.log"))  # noqa: S108
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps({"timestamp": timestamp, "channel": channel, "message": text})
                        + "\n"
                    )
            elif ch.type == "telegram":
                bot_token = ch.config.get("bot_token", "")
                chat_id = ch.config.get("chat_id", "")
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
                req = urllib.request.Request(  # noqa: S310
                    url, data=payload, headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=10)  # noqa: S310
            elif ch.type == "discord":
                webhook_url = ch.config.get("webhook_url", "")
                payload = json.dumps({"content": text}).encode()
                req = urllib.request.Request(  # noqa: S310
                    webhook_url, data=payload, headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=10)  # noqa: S310
            elif ch.type == "email":
                msg = EmailMessage()
                msg["Subject"] = ch.config.get("subject", "SSID-EMS Notification")
                msg["From"] = ch.config.get("from_addr", "ssidctl@localhost")
                msg["To"] = ch.config.get("to_addr", "")
                msg.set_content(text)
                with smtplib.SMTP(
                    ch.config.get("smtp_host", "localhost"), ch.config.get("smtp_port", 25)
                ) as s:
                    s.send_message(msg)
            else:
                return {"status": "error", "reason": f"Unknown type: {ch.type}"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

        return {"status": "sent", "channel": channel, "timestamp": timestamp}
