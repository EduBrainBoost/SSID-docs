#!/usr/bin/env python3
"""
Phase 3 Evidence Validation - Executable CI Gate
Validates presence and JSON validity of Phase-3 artifacts
"""

import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        data_path = Path(__file__).parent.parent.parent / "src" / "data" / "research" / "ai-infrastructure" / "phase3"
    else:
        data_path = Path(sys.argv[1])

    print("="*70)
    print("PHASE 3 EVIDENCE VALIDATION")
    print("="*70)

    required_files = {
        "phase3-claim-inventory.json",
        "phase3-source-manifest.json",
        "phase3-evidence-taxonomy.json",
        "phase3-known-defect-repairs.json",
        "phase3-test-results.json",
        "phase3-repository-scope-audit.json",
        "PHASE_3_AUDIT_CLOSURE_SUMMARY.md",
        "PHASE_3_EXECUTION_SUMMARY.md",
        "phase3-research-execution-framework.json",
        "phase3-human-research-backlog.json",
        "phase3-validation-atlas.json"
    }

    errors = []
    passed = []

    # Check file existence
    for filename in required_files:
        filepath = data_path / filename
        if not filepath.exists():
            errors.append(f"Missing: {filename}")
        else:
            passed.append(f"[OK] {filename}")

    # Validate JSON files
    for filename in required_files:
        if filename.endswith('.json'):
            filepath = data_path / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        json.load(f)
                    passed.append(f"[OK] {filename} valid JSON")
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid JSON in {filename}: {e}")
                except Exception as e:
                    errors.append(f"Error reading {filename}: {e}")

    # Print results
    print("\nVALIDATION RESULTS:")
    print("="*70)
    for msg in passed:
        print(msg)

    if errors:
        print("\nERRORS:")
        for msg in errors:
            print(f"[FAIL] {msg}")
        print("\n" + "="*70)
        print("STATUS: VALIDATION FAILED")
        print("="*70)
        return 1

    print("\n" + "="*70)
    print(f"STATUS: VALIDATION PASSED ({len(passed)} checks)")
    print("="*70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
