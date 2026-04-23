"""Webhook CLI command."""

from __future__ import annotations

import argparse
import json

from ssidctl.modules.webhooks import WebhookRegistry


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("webhook", help="Webhook event-driven dispatch")
    sub = p.add_subparsers(dest="webhook_action")
    reg_p = sub.add_parser("register")
    reg_p.add_argument("event")
    reg_p.add_argument("command")
    unreg_p = sub.add_parser("unregister")
    unreg_p.add_argument("event")
    sub.add_parser("list")
    disp_p = sub.add_parser("dispatch")
    disp_p.add_argument("event")
    disp_p.add_argument("--payload", default="{}")
    p.set_defaults(func=cmd_webhook)


def cmd_webhook(args, config) -> int:
    wr = WebhookRegistry(config.paths.state_dir / "webhooks")
    action = args.webhook_action
    if action == "register":
        wr.register(args.event, args.command)
        print(f"Registered: {args.event}")
    elif action == "unregister":
        wr.unregister(args.event)
        print(f"Unregistered: {args.event}")
    elif action == "list":
        for h in wr.list_hooks():
            print(f"  {h['event']} -> {h['command']}")
    elif action == "dispatch":
        payload = json.loads(args.payload)
        results = wr.dispatch(args.event, payload)
        for r in results:
            print(f"  [{r['exit_code']}] {r['command']}")
    else:
        print("Usage: ssidctl webhook {register|unregister|list|dispatch}")
        return 1
    return 0
