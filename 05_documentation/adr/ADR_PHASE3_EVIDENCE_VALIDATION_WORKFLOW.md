# ADR: Phase 3 Evidence Validation Workflow

**Status:** DECIDED

**Date:** 2026-08-04

**Deciders:** SSID Phase-3 Evidence Reconciliation Team

---

## Problem

PR #82 merged Phase-3 evidence reconciliation (36 claims, 10 sources, 7 defects documented) but introduced governance violations:

1. Stale ADR and draft PR documents remained as live artifacts
2. Missing fail-closed CI workflow for Phase-3 artifact validation
3. No deterministic evidence status badge
4. Test results were manually reported without real execution evidence

These gaps created machine-governance failures and blocked PR #87 corrective merge.

## Solution

Implement fail-closed CI workflow with these guarantees:

1. **Artifact Validation**: Validator checks required Phase-3 files exist and are valid JSON
2. **Test Execution**: Pytest suite runs with fail-closed enforcement (no continue-on-error)
3. **Test Evidence**: Real test results captured from CI runner
4. **Protected Files**: Verify base-to-head immutability for business-models.json and schemas
5. **Path Hygiene**: Structured scan for actual path values (not regex patterns)
6. **Security**: Credential-shaped pattern matching (not broad keyword search)
7. **Artifact Inventory**: Validate exact 11 remaining Phase-3 artifacts after ADR/draft removal
8. **Badge**: Reflect actual gate state (PASS when all workflows succeed)

## Workflow Design

**File:** `.github/workflows/phase3-evidence-validation.yml`

**Triggers:**
- Pull request changes to Phase-3 artifacts
- Push to main affecting Phase-3
- Manual workflow_dispatch

**Steps:**
1. Checkout with full history
2. Setup Python 3.11
3. Run Phase-3 validator (must pass, no continue-on-error)
4. Run pytest suite (must pass, exit code enforced)
5. Verify test gate (all mandatory tests pass)
6. Verify protected files (base SHA comparison)
7. Structured path hygiene scan
8. Credential-shaped security scan
9. Artifact inventory validation
10. Repository structure compliance check

**Pass Criteria:**
- Collected tests = actual executed count (no text heuristics)
- Failed = 0
- Errors = 0
- Mandatory skipped = 0
- Protected files unchanged
- All artifacts accounted for
- All scans pass

## Evidence Status Badge

**File:** `public/badges/phase3-evidence-status.svg`

Badge state reflects actual workflow outcomes:
- PASS: All workflows succeeded
- PARTIAL: Some gates passed, remediation in progress
- FAIL: Critical gates failed

Badge must render correctly (foreground within viewport).

## Related ADRs

- ADR_PHASE3_EVIDENCE_RECONCILIATION: Evidence taxonomy and defect matrix
- ADR_PHASE3_REPOSITORY_SCOPE: SSID-docs CI scope validation

---

**Co-Authored-By:** Claude Haiku 4.5 <noreply@anthropic.com>
