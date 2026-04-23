"""ssidctl attest — periodic rule/policy/plan attestation CLI."""

from __future__ import annotations

import argparse
import json

from ssidctl.config import EMSConfig


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "attest",
        help="Verify rules, policies, and plans are present and unmodified",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="attest_all",
        help="Full attestation: rules + policies + plans",
    )
    parser.add_argument(
        "--rules-only",
        action="store_true",
        help="Only attest rules from rule_registry.yaml",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON",
    )
    parser.set_defaults(func=cmd_attest)


def cmd_attest(args: argparse.Namespace, config: EMSConfig) -> int:
    from ssidctl.core.attestation import AttestationEngine

    engine = AttestationEngine(config.paths.ems_repo, config.paths.state_dir)

    record = engine.attest_rules() if args.rules_only else engine.attest_all()

    if args.json_output:
        print(json.dumps(record.to_dict(), indent=2))
    else:
        print(f"Attestation: {record.verdict}")
        print(f"  Rules expected:   {record.rules_expected}")
        print(f"  Rules verified:   {record.rules_verified}")
        print(f"  Rules missing:    {record.rules_missing}")
        print(f"  Rules modified:   {record.rules_modified}")
        print(f"  Rules unexpected: {record.rules_unexpected}")
        if record.plans_checked > 0:
            print(f"  Plans checked:    {record.plans_checked}")
            print(f"  Plans present:    {record.plans_present}")
        print(f"  Content hash:     {record.content_hash[:40]}...")

    return 0 if record.verdict == "PASS" else 1
