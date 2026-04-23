"""ssidctl bootstrap — SSID repo bootstrap commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.modules.bootstrap import (
    BootstrapError,
    bootstrap_and_pr,
    bootstrap_ems_state,
    generate_gates_surface,
    generate_skeleton,
    validate_skeleton,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("bootstrap", help="Bootstrap SSID repo")
    sub = parser.add_subparsers(dest="bootstrap_action")

    ssid_p = sub.add_parser("ssid", help="Generate SSID 24-root skeleton")
    ssid_p.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target directory (default: configured ssid_repo path)",
    )
    ssid_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without writing",
    )
    ssid_p.add_argument(
        "--commit",
        action="store_true",
        help="Create branch and commit after skeleton generation",
    )

    validate_p = sub.add_parser("validate", help="Validate SSID skeleton")
    validate_p.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target directory (default: configured ssid_repo path)",
    )

    sub.add_parser("ems", help="Bootstrap EMS state directories")

    parser.set_defaults(func=cmd_bootstrap)


def cmd_bootstrap(args: argparse.Namespace, config: EMSConfig) -> int:
    from pathlib import Path

    target = Path(args.target) if getattr(args, "target", None) else config.paths.ssid_repo

    try:
        if args.bootstrap_action == "ssid":
            if args.dry_run:
                print(f"Would create 24-root skeleton in: {target}")
                from ssidctl.modules.bootstrap import ROOT_24_DIRS

                for d in ROOT_24_DIRS:
                    print(f"  {d}/")
                    print("    README.md")
                    print("    .gitkeep")
                print("\nGate stubs in: 12_tooling/")
                return 0

            if getattr(args, "commit", False):
                result = bootstrap_and_pr(target)
                print(f"Skeleton created and committed: {result['root_count']} roots")
                print(f"Branch: {result['branch']}")
                print(f"Commit: {result['commit_sha']}")
                print(f"Files: {result['files_created']}")
                print("\nNext step: push and create PR")
            else:
                result = generate_skeleton(target)
                gates = generate_gates_surface(target)
                print(f"Skeleton created: {result['root_count']} root directories")
                print(f"Files created: {len(result['files'])}")
                print(f"Gate stubs: {len(gates)}")
                print(f"\nTarget: {target}")
                print("\nNext steps:")
                print("  1. cd into the target directory")
                print("  2. git add -A && git commit -m 'feat: SSID 24-root skeleton'")
                print("  3. Create PR for review")

        elif args.bootstrap_action == "validate":
            result = validate_skeleton(target)
            if result["valid"]:
                print(f"PASS: {result['root_count']}/24 root directories present")
                return 0
            else:
                print(f"FAIL: {result['root_count']}/24 root directories present")
                for m in result["missing"]:
                    print(f"  Missing: {m}")
                return 1

        elif args.bootstrap_action == "ems":
            result = bootstrap_ems_state(
                config.paths.state_dir,
                config.paths.evidence_dir,
                config.paths.vault_dir,
            )
            print("EMS state bootstrapped:")
            print(f"  State dir:    {result['state_dir']}")
            print(f"  Evidence dir: {result['evidence_dir']}")
            print(f"  Vault dir:    {result['vault_dir']}")
            print(f"  Directories created: {len(result['dirs_created'])}")
            for d in result["dirs_created"]:
                print(f"    {d}/")

        else:
            print("Usage: ssidctl bootstrap {ssid|validate|ems}", file=sys.stderr)
            return 1
    except BootstrapError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
