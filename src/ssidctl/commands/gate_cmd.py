"""ssidctl gate — list and run individual gates from the matrix."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.gates.matrix import load_matrix
from ssidctl.gates.runner import run_gate


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("gate", help="List or run individual gates")
    sub = parser.add_subparsers(dest="gate_action")

    sub.add_parser("list", help="List all gates from matrix")

    run_p = sub.add_parser("run", help="Run a single gate by name")
    run_p.add_argument("name", type=str, help="Gate name to run")
    run_p.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")

    parser.set_defaults(func=cmd_gate)


def cmd_gate(args: argparse.Namespace, config: EMSConfig) -> int:
    matrix = load_matrix()

    if args.gate_action == "list":
        return _list_gates(matrix)
    elif args.gate_action == "run":
        return _run_gate(args.name, args.timeout, matrix, config)
    else:
        print("Usage: ssidctl gate {list|run <name>}", file=sys.stderr)
        return 1


def _list_gates(matrix) -> int:
    """List all guards and gates from the matrix."""
    print("  Guards:")
    for g in matrix.guards:
        enabled = "on " if g.enabled else "off"
        print(f"    {enabled}  {g.name:30s}  phase={g.phase}  bootstrap={g.bootstrap}")

    print()
    print("  Gates:")
    for g in matrix.gates:
        skip = f" (skip: {g.skip_reason})" if g.skip_reason else ""
        print(f"    {g.name:30s}  mode={g.mode}  script={g.script}{skip}")

    return 0


def _run_gate(name: str, timeout: int, matrix, config: EMSConfig) -> int:
    """Run a single gate by name."""
    gate_def = None
    for g in matrix.gates:
        if g.name == name:
            gate_def = g
            break

    if gate_def is None:
        available = [g.name for g in matrix.gates]
        print(f"Gate not found: {name}", file=sys.stderr)
        print(f"Available gates: {', '.join(available)}", file=sys.stderr)
        return 1

    result = run_gate(gate_def, config.paths.ssid_repo, timeout=timeout)

    status = "PASS" if result.result == "PASS" else "FAIL"
    print(f"  {status}  {result.gate_name} (exit={result.exit_code})")

    if result.stdout.strip():
        for line in result.stdout.strip().splitlines()[:20]:
            print(f"         {line}")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines()[:10]:
            print(f"    err: {line}")

    return 0 if result.result == "PASS" else 1
