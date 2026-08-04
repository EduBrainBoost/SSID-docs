#!/usr/bin/env python3
"""Phase 3 Evidence Validation - Canonical Main Reconstruction"""

import json
import sys
from pathlib import Path

def main():
    base = Path(__file__).parent.parent.parent.parent / "src" / "data" / "research" / "ai-infrastructure" / "phase3"

    print("="*70)
    print("PHASE 3 EVIDENCE VALIDATION")
    print("="*70)

    files = [
        "phase3-claim-inventory.json",
        "phase3-source-manifest.json",
        "phase3-evidence-taxonomy.json",
        "phase3-known-defect-repairs.json",
        "phase3-repository-scope-audit.json",
        "PHASE_3_AUDIT_CLOSURE_SUMMARY.md",
        "PHASE_3_EXECUTION_SUMMARY.md"
    ]

    errors = []

    for f in files:
        p = base / f
        if not p.exists():
            errors.append(f"Missing: {f}")
            continue
        if f.endswith(".json"):
            try:
                with open(p) as fp:
                    json.load(fp)
                print(f"✓ {f}")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in {f}")
        else:
            print(f"✓ {f}")

    if errors:
        for e in errors:
            print(f"✗ {e}")
        return 1

    print("="*70)
    print("VALIDATION PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
