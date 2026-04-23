"""ssidctl stack — local stack lifecycle management."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from ssidctl.config import EMSConfig
from ssidctl.core.timeutil import utcnow_iso
from ssidctl.stack.evidence import append_ledger
from ssidctl.stack.manifest import ManifestError, load_manifest
from ssidctl.stack.ports import PortError, find_free_port, wait_for_health
from ssidctl.stack.processes import ProcessRunner
from ssidctl.stack.state import StackState, load_state, save_state

_DEFAULT_MANIFEST = (
    Path(r"C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID")
    / "16_codex"
    / "local_stack"
    / "local_stack_manifest.yaml"
)

_runner: ProcessRunner | None = None


def _get_runner() -> ProcessRunner:
    global _runner
    if _runner is None:
        _runner = ProcessRunner()
    return _runner


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("stack", help="Local stack lifecycle (up/down/status/health)")
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help=f"Path to local_stack_manifest.yaml (default: {_DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--log-mode",
        choices=["minimal", "forensic"],
        default="minimal",
        help="Log verbosity (default: minimal)",
    )

    sub = parser.add_subparsers(dest="stack_action")
    sub.add_parser("status", help="Show current stack state")
    sub.add_parser("up", help="Start managed stack components")
    sub.add_parser("down", help="Stop managed stack components")
    sub.add_parser("health", help="Check health of all components")

    parser.set_defaults(func=cmd_stack)


def _resolve_manifest(args: argparse.Namespace, config: EMSConfig) -> Path:
    if args.manifest:
        return Path(args.manifest)
    manifest_in_ssid = (
        config.paths.ssid_repo / "16_codex" / "local_stack" / "local_stack_manifest.yaml"
    )
    if manifest_in_ssid.exists():
        return manifest_in_ssid
    return _DEFAULT_MANIFEST


def _evidence_paths(config: EMSConfig) -> tuple[Path, Path]:
    """Return (state_file, ledger_file) paths under evidence_dir."""
    base = config.paths.evidence_dir / "local_stack"
    return base / "state" / "local-stack.json", base / "ledger.jsonl"


def cmd_stack(args: argparse.Namespace, config: EMSConfig) -> int:
    manifest_path = _resolve_manifest(args, config)

    try:
        manifest = load_manifest(manifest_path)
    except ManifestError as e:
        print(f"Manifest error: {e}", file=sys.stderr)
        return 2

    state_file, ledger_file = _evidence_paths(config)

    action = args.stack_action

    if action == "status":
        return _cmd_status(state_file)
    elif action == "up":
        return _cmd_up(manifest, state_file, ledger_file, args.log_mode)
    elif action == "down":
        return _cmd_down(state_file, ledger_file)
    elif action == "health":
        return _cmd_health(manifest, state_file)
    else:
        print("Usage: ssidctl stack {status|up|down|health}", file=sys.stderr)
        return 1


def _cmd_status(state_file: Path) -> int:
    state = load_state(state_file)
    if state is None:
        print(json.dumps({"state": None}, indent=2))
    else:
        print(json.dumps({"state": asdict(state)}, indent=2))
    return 0


def _cmd_up(manifest, state_file, ledger_file, log_mode) -> int:
    runner = _get_runner()
    components_state = {}
    failed = False

    for name, comp in manifest.components.items():
        if not comp.managed:
            continue

        try:
            port = find_free_port(comp.port_candidates)
        except PortError as e:
            print(f"FAIL: {name}: {e}", file=sys.stderr)
            failed = True
            continue

        cmd = [c.replace("{port}", str(port)) for c in comp.start_template]
        proc = runner.start(name=name, cmd=cmd, workdir=comp.workdir)

        url = comp.health_url_template.replace("{port}", str(port))
        healthy = wait_for_health(url, comp.health_expect_status, max_retries=30, backoff=0.5)

        if not healthy:
            print(f"FAIL: {name}: health check timeout on {url}", file=sys.stderr)
            runner.stop(proc, name=name)
            failed = True
            continue

        components_state[name] = {
            "pid": proc.pid,
            "port": port,
            "status": "running",
        }
        print(f"PASS: {name} started (pid={proc.pid}, port={port})")

    state = StackState(
        stack_id=manifest.stack_id,
        components=components_state,
        started_at=utcnow_iso(),
    )
    save_state(state, state_file)
    append_ledger(
        ledger_file,
        action="stack_up",
        details={
            "components": list(components_state.keys()),
            "log_mode": log_mode,
        },
    )

    return 1 if failed else 0


def _cmd_down(state_file, ledger_file) -> int:
    state = load_state(state_file)
    if state is None:
        print("No active stack state found.")
        return 0

    import os
    import signal
    import subprocess as sp

    failed = False

    for name, info in state.components.items():
        pid = info.get("pid")
        if pid is None:
            continue

        if sys.platform == "win32":
            result = sp.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                capture_output=True,
            )
            if result.returncode != 0:
                print(f"FAIL: {name} (pid={pid}): stop failed", file=sys.stderr)
                failed = True
            else:
                print(f"PASS: {name} stopped (pid={pid})")
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"PASS: {name} stopped (pid={pid})")
            except ProcessLookupError:
                print(f"PASS: {name} already exited (pid={pid})")
            except OSError:
                print(f"FAIL: {name} (pid={pid}): stop failed", file=sys.stderr)
                failed = True

    state.stopped_at = utcnow_iso()
    state.components = {}
    save_state(state, state_file)
    append_ledger(ledger_file, action="stack_down", details={})

    return 1 if failed else 0


def _cmd_health(manifest, state_file) -> int:
    from ssidctl.stack.ports import _http_get_status

    state = load_state(state_file)
    all_pass = True

    for name, comp in manifest.components.items():
        port = None
        if state and name in state.components:
            port = state.components[name].get("port")
        if port is None:
            port = comp.port_preferred

        url = comp.health_url_template.replace("{port}", str(port))
        status = _http_get_status(url)

        if status == comp.health_expect_status:
            print(f"PASS: {name} ({url}) -> {status}")
        else:
            print(f"FAIL: {name} ({url}) -> {status}")
            all_pass = False

    return 0 if all_pass else 1
