"""ssidctl serve — Mission Control local dashboard."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "serve",
        help="Launch Mission Control dashboard (loopback-only)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8484,
        help="Port to bind (default: 8484)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind (default: 127.0.0.1, loopback only)",
    )
    parser.set_defaults(func=cmd_serve)


def cmd_serve(args: argparse.Namespace, config: EMSConfig) -> int:
    # Enforce loopback-only binding
    if args.host not in _LOOPBACK_HOSTS:
        print(
            f"Error: host '{args.host}' rejected. "
            "Mission Control binds to loopback only (127.0.0.1).",
            file=sys.stderr,
        )
        return 1

    try:
        from ssidctl.services.dashboard import create_dashboard_app
    except Exception as exc:
        print(f"Error loading dashboard: {exc}", file=sys.stderr)
        return 1

    app = create_dashboard_app(config)
    print(f"Mission Control starting on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
    return 0
