# ADR-0008: Phase-2.1 Generator Lossless Validation Workflow

**Date:** 2026-08-04  
**Status:** Accepted  
**Decision Makers:** SSID Infrastructure Team  

## Problem

The canonical AI infrastructure catalog generator (`tools/build-ai-infrastructure-catalogs.mjs`) requires Phase-2.1 hardening dimensions from an external enrichment atlas. Without automated validation:

- Phase-2.1 data could be silently lost during regeneration
- The enrichment atlas dependency is implicit and undocumented
- No CI gates prevent data loss from accidental file deletion or corruption
- Generator changes could introduce determinism bugs undetected

## Decision

Implement a dedicated GitHub Actions workflow (`phase-2-1-lossless-generation.yml`) that runs on all changes to:
- The generator source code
- The enrichment atlas
- Legacy source documents  
- The schema definition
- Generator tests

The workflow enforces:
1. Enrichment atlas presence and completeness (100 exact records)
2. First generation produces no unexpected changes
3. Second generation produces byte-identical output (determinism proof)
4. All Phase-2.1 dimensions present in all models
5. Schema validation of complete catalog and all models
6. Comprehensive negative mutation testing

## Rationale

- **Fail-closed**: Generator halts if enrichment atlas is missing or incomplete
- **Deterministic**: Double-run comparison proves idempotent generation
- **Complete**: Schema validation includes all 100 models, not spot-checks
- **Testable**: Negative controls verify generator rejects invalid data
- **Policy-compliant**: Uses repository's canonical pnpm package manager with frozen lockfiles

## Consequences

- Positive: Eliminates risk of silent data loss, ensures schema compliance, proves determinism
- Positive: Workflow runs only on relevant changes, reducing noise
- Negative: Workflow requires ADR documentation (this decision)
- Negative: Schema validation dependency may require new tooling if existing validators insufficient

## Implementation Notes

- Workflow uses pnpm with `--frozen-lockfile` for reproducible installs
- No npm legacy flags or package-lock.json creation
- Schema validation uses both JSON parsing and JSON Schema instance validation
- Negative mutations create isolated temporary fixtures, never modify canonical sources
- Test harness reports exact pass/fail counts with nonzero exit on any failure
- Integrator Merge Checks compatible (no unauthorized file changes)

## Alternatives Considered

1. **Manual testing**: Insufficient - relies on human memory and inconsistent execution
2. **Post-merge validation**: Too late - data loss would already be committed
3. **Generator-only validation**: Insufficient - missing independent schema validation
4. **No workflow**: High risk - Phase-2.1 data unprotected

## References

- Phase-2.1 Hardening Dimensions: infrastructure_pattern, market_sizing, cold_start_strategy, competitive_landscape, data_and_integration_dependencies, regulatory_constraints, ai_vs_infrastructure_moat, market_maturity, evidence_status, validation_atlas
- Canonical Package Manager: pnpm@10.33.0 (from package.json)
- Schema Version: JSON Schema 2020-12 (from business-model.schema.json)
