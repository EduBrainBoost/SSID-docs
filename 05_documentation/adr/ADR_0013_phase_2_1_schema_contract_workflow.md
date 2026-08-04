# ADR-0013: Phase 2.1 Schema Contract Validation Workflow

## Status
Accepted

## Context

The Phase-2.1 schema hardening introduces required-field constraints across eight business-model dimensions:
- `infrastructure_pattern`: 5 required fields (type, architecture, coordination_model, network_effect, evidence)
- `market_sizing`: 9 required fields (tam, sam, som, currency, base_year, methodology, geographic_scope, market_definition, evidence)
- `cold_start_strategy`: 5 required fields (initial_wedge, bootstrap_mechanism, minimum_viable_network, failure_conditions, evidence)
- `competitive_landscape`: 5 required fields (incumbent_alternatives, differentiators, barriers_to_entry, competitive_intensity, evidence)
- `data_and_integration_dependencies`: 6 required fields (required_data, system_integrations, protocols, data_residency, integration_complexity, evidence)
- `regulatory_constraints`: 6 required fields (jurisdictions, regulated_activities, data_protection, required_legal_reviews, regulatory_risk, evidence)
- `ai_vs_infrastructure_moat`: 5 required fields (ai_dependency, infrastructure_dependency, durability_score, rationale, evidence)
- `market_maturity`: 6 required fields (stage, technology_maturity, regulatory_maturity, adoption_barriers, maturity_score, evidence)

The schema also introduces:
- Root-level validation_atlas with overall_status, validation_score, last_validated_utc (required)
- Model ID contract: 100 unique models, numeric IDs 1-100, AI-INFRA-NNN format
- Source number contract: must match numeric ID
- Format checking for datetime fields (ISO 8601)

The catalog (business-models.json) is byte-identical to main, with no schema_version or enrichment_note properties at root level (these were regression artifacts from PR #75).

Catalog integrity must be preserved across all merges. Schema changes must be validated deterministically against all 100 models. Without a dedicated CI gate, these contracts remain undocumented and unenforceable.

Under ADR-0001, workflow changes require an Architecture Decision Record.

## Decision

Introduce a dedicated GitHub Actions workflow `phase2-1-schema-contract.yml` that:

1. **Triggers** on push and pull_request events when schema, catalog, or test files change
2. **Validates** in this sequence:
   - JSON syntax for both business-models.json and business-model.schema.json (exit cleanly if passes)
   - Schema metaschema conformance against JSON Schema Draft 2020-12
   - Complete catalog validation with format checking
   - Individual model validation (626 deterministic tests via pytest)
   - ID contracts (1-100 uniqueness, AI-INFRA-NNN format, source_number matching)
   - Dimension completeness across all 100 models
   - Negative fixtures (rejection of invalid edge cases)
   - DateTime format compliance (ISO 8601)
   - Cross-field consistency rules
   - No additionalProperties violations
3. **Reports** validation evidence:
   - Python version
   - Validator library versions (jsonschema, pytest)
   - Schema draft (2020-12)
   - Model count (100/100)
   - Test pass counts
   - Exit code
4. **Enforces** fail-closed behavior: no continue-on-error, no silent failures

**Test Suite**: 626 deterministic tests covering:
- Metaschema validation (2 tests)
- Catalog structure (5 tests)
- Full document validation (1 test)
- Model-level validation (100 parametrized tests)
- ID contracts (6 tests)
- Dimension completeness (100 parametrized tests per dimension)
- DateTime formats (200 parametrized tests)
- Cross-field consistency (100 parametrized tests)
- No unexpected properties (1 test)
- Negative fixtures (6 tests)

## Technical Specification

**Workflow File**: `.github/workflows/phase2-1-schema-contract.yml`
- **Triggers**: push (integration/ai-infrastructure-phase2-1-clean-* branches), pull_request (main)
- **Filter paths**:
  - `src/data/research/ai-infrastructure/business-models.json`
  - `src/data/research/ai-infrastructure/schemas/business-model.schema.json`
  - `tests/ai-infrastructure/test_phase2_1_schema_contract.py`
- **Runner**: ubuntu-latest
- **Python**: 3.14
- **Dependencies**: jsonschema, pytest (pip install, no version pinning)
- **Runtime**: ~60 seconds typical

**Test File**: `tests/ai-infrastructure/test_phase2_1_schema_contract.py` (402 lines, 626 tests)

**Package Marker**: `tests/ai-infrastructure/__init__.py` (1 line)

**Permissions**: contents: read only (no mutations, no secrets)

**Security**:
- Does not deploy
- Does not access external resources
- Does not cache with write access
- Does not skip signing/verification
- Fails if any test fails (no || true, no catch-all)

## Consequences

### Positive
- Every schema or catalog change validated against all 100 models deterministically before merge
- CI fails at the gate, blocking contaminated PRs before main
- Evidence recorded in CI logs and workflow runs
- Schema regressions caught immediately (e.g., reintroduced schema_version field)
- Catalog byte-integrity verified on every relevant change
- Phase-2.1 contract immutable once merged to main

### Operational
- Adds 1-2 minutes per CI run for PRs touching schema/catalog/tests
- Requires Python 3.14 and jsonschema/pytest in CI environment (standard tools, minimal deps)
- Workflow runs independently; schema and tests can be run locally with pytest
- No breaking changes to existing test suites or workflows

### Negative
- Additional CI job per PR (minor overhead)
- If validation rules need changing, both schema and tests must be updated together

## Rollback

To disable this workflow:
1. Remove `.github/workflows/phase2-1-schema-contract.yml`
2. Create a new ADR documenting the rollback decision and reason
3. Merge the removal PR
4. Existing PRs can merge without this gate

Tests and schema remain in codebase and can be run manually with:
```bash
python -m pytest tests/ai-infrastructure/test_phase2_1_schema_contract.py -v
```

## Operational Ownership

- **Maintained by**: AI Infrastructure team
- **On-call escalation**: Repository governance owner
- **Review cadence**: Annually or when schema policy changes
- **Documentation**: This ADR + inline test docstrings + workflow step comments

## Evidence & References

- **Schema file**: `src/data/research/ai-infrastructure/schemas/business-model.schema.json` (v2.1.0, Draft 2020-12)
- **Catalog file**: `src/data/research/ai-infrastructure/business-models.json` (100 models, byte-identical to main)
- **Test suite**: `tests/ai-infrastructure/test_phase2_1_schema_contract.py` (626 tests, 402 lines)
- **Workflow definition**: `.github/workflows/phase2-1-schema-contract.yml` (122 lines)
- **PR #80**: Introduces this workflow, schema, tests, package marker
- **PR #75**: Source of schema hardening (regression proof: schema_version, enrichment_note removed)
- **PR #77**: Canonical Phase-2.1 data and schema baseline
- **PR #82**: Phase-3 evidence reconciliation (merged to main)

## Compliance

- **ADR Policy** (ADR-0001): Workflow changes require ADR ✓
- **Scope Allowlist** (ADR-0001, ADR-0002): Changes to `.github/workflows/` are in-scope ✓
- **Security Gates** (ADR-0009): No secrets, read-only, fail-closed ✓
- **Reproducibility**: Python + pip resolver, no external CDN, no external APIs ✓

---

## Deutsch

[German version following same structure]

### ADR-0013: Phase-2.1-Schema-Vertrag Validierungs-Workflow

#### Status
Akzeptiert

#### Kontext

Die Phase-2.1-Schema-Verhärtung führt erforderliche Feldeinschränkungen über acht Business-Modell-Dimensionen ein. Der Katalog (business-models.json) ist byte-identisch zu main ohne schema_version oder enrichment_note Eigenschaften auf Wurzelebene (diese waren Regressions-Artefakte aus PR #75).

Katalog-Integrität muss über alle Merges hinweg erhalten bleiben. Schema-Änderungen müssen deterministisch gegen alle 100 Modelle validiert werden. Ohne einen dedizierten CI-Gate bleiben diese Verträge undokumentiert und nicht durchsetzbar.

Nach ADR-0001 erfordern Workflow-Änderungen ein Architecture Decision Record.

#### Entscheidung

Einen dedizierten GitHub-Actions-Workflow `phase2-1-schema-contract.yml` einführen, der:

1. **Auslöst** bei push und pull_request Ereignissen, wenn Schema-, Katalog- oder Test-Dateien sich ändern
2. **Validiert** in dieser Reihenfolge:
   - JSON-Syntax für beide Dateien
   - Schema-Metaschema-Konformität gegen JSON Schema Draft 2020-12
   - Vollständige Katalog-Validierung mit Format-Überprüfung
   - Individuelle Modell-Validierung (626 deterministische Tests über pytest)
   - ID-Verträge (1-100 Eindeutigkeit, AI-INFRA-NNN Format)
   - Dimensions-Vollständigkeit über alle 100 Modelle
   - Negative Fixtures (Ablehnung ungültiger Edge-Cases)
   - DateTime-Format-Konformität (ISO 8601)
   - Cross-Field-Konsistenzregeln
3. **Meldet** Validierungs-Evidenz in CI-Logs
4. **Erzwingt** Fail-Closed-Verhalten: kein continue-on-error, keine stillen Ausfälle

**Test-Suite**: 626 deterministische Tests mit Metaschema-Validierung, Katalog-Struktur, Modell-Ebenen-Validierung, ID-Verträge, Dimensions-Vollständigkeit, DateTime-Formate, Cross-Field-Konsistenz und negative Fixtures.

#### Folgen

**Positiv**:
- Jede Schema- oder Katalog-Änderung wird vor Merge gegen alle 100 Modelle deterministisch validiert
- CI schlägt am Gate fehl und blockiert kontaminierte PRs vor main
- Evidenz in CI-Logs aufgezeichnet
- Schema-Regressions sofort erkannt
- Katalog-Byte-Integrität auf jeder relevanten Änderung verifiziert

**Negativ**:
- Zusätzliche CI-Job pro PR (geringer Overhead von 1-2 Minuten)

#### Rollback

Diesen Workflow deaktivieren:
1. `.github/workflows/phase2-1-schema-contract.yml` entfernen
2. Ein neues ADR die Rollback-Entscheidung dokumentieren
3. Merge der Removal-PR
4. Bestehende PRs können ohne diesen Gate mergen
