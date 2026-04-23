"""Notification CLI command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ssidctl.modules.notifications import NotificationDispatcher


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("notify", help="Send notifications")
    sub = p.add_subparsers(dest="notify_action")
    send_p = sub.add_parser("send")
    send_p.add_argument("message")
    send_p.add_argument("--channel", required=True)
    sub.add_parser("list-channels")
    test_p = sub.add_parser("test")
    test_p.add_argument("--channel", required=True)
    p.set_defaults(func=cmd_notify)


def cmd_notify(args, config) -> int:
    policy_path = Path(__file__).parent.parent.parent.parent / "policies" / "notifications.yaml"
    if not policy_path.exists():
        print("No notifications.yaml found in policies/")
        return 1
    nd = NotificationDispatcher.from_yaml(policy_path)
    action = args.notify_action
    if action == "send":
        result = nd.send(args.message, args.channel)
        print(f"{result['status']}: {result.get('reason', 'OK')}")
        return 0 if result["status"] == "sent" else 1
    elif action == "list-channels":
        for name in nd.list_channels():
            print(f"  {name}")
    elif action == "test":
        result = nd.send("[TEST] SSID-EMS notification test", args.channel)
        print(f"Test: {result['status']}")
        return 0 if result["status"] == "sent" else 1
    else:
        print("Usage: ssidctl notify {send|list-channels|test}")
        return 1
    return 0
