# ADR-0013: Phase 2.1 Catalog Regeneration Fail-Closed Gate

## Status
Accepted

## Context

PR #81 merged the Phase-2.1 generator repair (commit bb6dd7c). The repair implements a critical fix: the generator was overwriting Phase-2.1 hardening data (10 dimensions) with legacy-only fields.

The repair adds:
- `enrichment-atlas.json`: canonical source of Phase-2.1 data for all 100 models
- Generator merge logic to load enrichment + legacy fields
- Validation assertions (100 models, 1-100 IDs, all dimensions present)

However, without explicit gating to enforce regeneration determinism and contract validation, future developers could:
- Modify the generator in ways that break determinism
- Break the enrichment contract (e.g., introduce empty hardening dimensions)
- Introduce duplicate or missing IDs
- Silently degrade Phase-2.1 data quality

Under normal development, these degradations would only surface during manual review or after merge to main.

## Decision

Implement fail-closed regeneration gating via CI:

### 1. GitHub Actions Workflow
**File:** `.github/workflows/phase2-1-regeneration-gate.yml`

Runs on all pushes to main and test/* branches:
- Execute generator run 1 → verify no diff
- Execute generator run 2 → verify no diff  
- Compare SHA256 hashes → must be identical (determinism gate)
- Run contract tests (30+ assertions)
- Fail on any contract violation

Exit code 1 for any failure (fail-closed).

### 2. Contract Validation Tests
**File:** `tests/ai-infrastructure/test-phase2-1-regeneration-contract.mjs`

Comprehensive assertions:
- Enrichment atlas: exactly 100 records
- Catalog: exactly 100 models
- ID range: 1-100 complete, no gaps, no duplicates
- All 10 hardening dimensions present and non-empty per model
- model_id/source_number sync to id
- Schema compliance: no extra properties, valid enums, valid timestamps
- Negative controls: empty dimensions, duplicates, missing IDs, missing enrichment

### 3. Integration into Test Pipeline
**Updated:** `package.json`

```json
"test:ai-infrastructure": "node tests/ai-infrastructure.test.mjs && node tests/ai-infrastructure/test-phase2-1-regeneration-contract.mjs"
```

## Consequences

- Generator cannot silently degrade without CI failure
- Determinism enforced: any non-deterministic change breaks CI
- Contract enforced: any enrichment violation detected immediately
- Phase-2.1 data quality protected by automated gates
- Developers cannot merge changes that break regeneration without explicit awareness and fix
- All future changes to Phase-2.1 schema or generator require passing these gates

## Rationale

Phase-2.1 is a critical integration layer (100 hardened business models, 10 dimensions per model, 1.6MB catalog). Without regeneration gating:
- Silent data loss risk if enrichment is removed or corrupted
- Lack of determinism signals hidden generator bugs
- No early detection of schema regressions

These gates provide defense-in-depth: code review + automated validation.
