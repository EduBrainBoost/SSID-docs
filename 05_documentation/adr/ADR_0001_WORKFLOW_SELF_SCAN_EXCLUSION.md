# ADR-0001: Workflow File Exclusion from CI Gate Pattern Scans

**Status:** ACCEPTED  
**Date:** 2026-04-11  
**Context:** PR #50 (Repair: Fix hard blockers in branch integration)

## Problem

CI gates in `.github/workflows/docs_ci.yml` scan for forbidden patterns (e.g., `local.ssid`, `rsync.*SSID`, `git.filter-repo`) to prevent private repo references from being accidentally committed to the public SSID-docs repository.

However, these pattern strings must be listed in the workflow file itself (as part of the PRIVATE_PATTERNS array) to perform the scan. The scan logic was matching these pattern strings in the workflow file, causing false positives.

## Decision

Exclude `.github/workflows/docs_ci.yml` from the private repo reference pattern scan by adding a grep filter: `| grep -v ".github/workflows/docs_ci.yml"` to the step that checks for private SSID repo patterns.

This allows the workflow file to contain the pattern definitions without triggering the gate on itself.

## Rationale

1. **Pattern definitions must be in the workflow file** — the gate's detection logic requires these patterns to be defined in the workflow.
2. **Self-reference is necessary** — CI gates must be able to contain the patterns they check for, without false positives.
3. **Consistent with other gates** — the secret-scan and absolute-path-leak gates already exclude the workflow file from their checks for the same reason.

## Implementation

Modified `.github/workflows/docs_ci.yml`:
- Added `| grep -v ".github/workflows/docs_ci.yml"` to the private repo reference scan step (line 177)
- This allows denylist-gate to PASS while still protecting against actual private repo references in source code

## Status

All three main CI gates now pass:
- ✅ build
- ✅ secret-scan
- ✅ denylist-gate
