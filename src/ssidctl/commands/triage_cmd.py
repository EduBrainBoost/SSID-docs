"""ssidctl triage — classify failure + next steps."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.core.evidence_store import EvidenceStore
from ssidctl.gates.matrix import load_failure_taxonomy


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("triage", help="Classify failure + suggest next steps")
    parser.add_argument("run_id", type=str, help="Run ID to triage")
    parser.set_defaults(func=cmd_triage)


def cmd_triage(args: argparse.Namespace, config: EMSConfig) -> int:
    store = EvidenceStore(config.paths.evidence_dir)
    taxonomy = load_failure_taxonomy()

    try:
        manifest = store.get_manifest(args.run_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    report = store.get_gate_report(args.run_id)

    print(f"Run: {args.run_id}")
    print(f"Task: {manifest.get('task_id', '?')}")
    print(f"Result: {manifest.get('overall_result', '?')}")
    print(f"Status: {manifest.get('lifecycle_status', '?')}")
    print()

    if manifest.get("overall_result") == "PASS":
        print("No failure to triage.")
        return 0

    # Classify findings
    if report:
        findings = report.get("findings", [])
        classified = _classify_findings(findings, taxonomy)
        for code, items in classified.items():
            desc = taxonomy.get(code, {}).get("description", "Unknown")
            print(f"  [{code}] {desc}")
            for item in items:
                print(f"    - {item.get('summary', '?')}")
            print()
    else:
        print("  No gate report found. Classification: UNKNOWN")

    return 0


def _classify_findings(findings: list[dict], taxonomy: dict) -> dict[str, list[dict]]:
    """Classify findings into taxonomy codes."""
    classified: dict[str, list[dict]] = {}
    gate_to_code = {
        "root_24_lock": "STRUCTURE_FAIL",
        "structure_guard": "STRUCTURE_FAIL",
        "sot_validation": "SOT_FAIL",
        "sot_write_guard": "SOT_FAIL",
        "secret_pii_scan": "SECRET_FAIL",
        "qa_check": "TEST_FAIL",
        "forbidden_extensions": "SCOPE_FAIL",
        "forbidden_paths": "SCOPE_FAIL",
        "token_legal_lexicon": "SCOPE_FAIL",
    }

    for f in findings:
        gate = f.get("gate", "")
        code = gate_to_code.get(gate, "UNKNOWN")
        classified.setdefault(code, []).append(f)

    return classified
