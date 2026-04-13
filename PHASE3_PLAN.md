---
title: Phase 3 German Translation Plan
date: 2026-04-13
status: IN_PROGRESS
---

# Phase 3: German Language Support (9% → 100%)

**Objective**: Complete German translation of 61 documentation files  
**Target Completion**: 2026-05-15  
**Success Metric**: 100% coverage (67/67 files with German equivalents)

---

## Current State (Baseline 2026-04-13)

| Metric | Count | % |
|--------|-------|-----|
| English Files | 67 | 100% |
| German Files | 6 | 9% |
| Translation Gap | 61 | 91% |

**Existing German Files**:
- `de/overview.mdx` — Overview
- `de/index.mdx` — Index/Home
- `de/security.mdx` — Security & Disclosure
- `de/architecture/roots.mdx` — Root-24 Architecture
- `de/compliance/gdpr.mdx` — GDPR Documentation
- `de/developer/getting-started.mdx` — Developer Getting Started

---

## Translation Tiers & Prioritization

### Tier 1: Critical User-Facing (12 files) — WEEK 1
Priority for new users and primary audience (German-speaking Europe).

| File | English Path | Status | Est. Effort |
|------|--------------|--------|-------------|
| Getting Started | `guides/quickstart.mdx` | PENDING | 2h |
| System Overview | `architecture/5-repo-topology.mdx` | PENDING | 2h |
| Local Stack Setup | `operations/local-stack.md` | PENDING | 1.5h |
| Port Matrix Reference | `deployments/ports-matrix-current.mdx` | PENDING | 1h |
| Testnet Guide | `deployments/testnet-guide.mdx` | PENDING | 2h |
| Testnet Addresses | `deployments/testnet-addresses.mdx` | PENDING | 1.5h |
| FAQ General | `faq/general.mdx` | PENDING | 2h |
| FAQ Token | `faq/token-disambiguation.mdx` | PENDING | 1.5h |
| What is SSID | `overview.mdx` (already exists, verify sync) | REVIEW | 0.5h |
| DID Method Basics | `identity/did-method.mdx` | PENDING | 1.5h |
| eIDAS Compliance | `compliance/eidas.mdx` | PENDING | 1h |
| MiCA Positioning | `compliance/mica.mdx` | PENDING | 1h |

**Subtotal Tier 1**: 18.5 hours ≈ 2-3 workdays

### Tier 2: Governance & Compliance (15 files) — WEEKS 2-3
Critical for EU regulatory audience and operational teams.

| File | Path | Type | Est. Effort |
|------|------|------|-------------|
| Evidence & WORM | `governance/evidence-export.mdx` | REFERENCE | 1.5h |
| Evidence (Main) | `governance/evidence.mdx` | REFERENCE | 1.5h |
| Policy Gates | `governance/policy-gates.mdx` | REFERENCE | 1.5h |
| Audit Framework | `compliance/audit-framework.mdx` | REFERENCE | 2h |
| Post-Quantum Migration | `compliance/post-quantum-migration.mdx` | REFERENCE | 2h |
| PR-Only Workflow | `governance/pr-only.mdx` | REFERENCE | 1.5h |
| Guard Rails | `governance/guards.mdx` | REFERENCE | 1.5h |
| DAO Governance | `governance/dao.mdx` | REFERENCE | 1.5h |
| Secrets Management | `governance/secrets-management.mdx` | REFERENCE | 1.5h |
| Incident Response | `governance/incident-response.mdx` | OPERATIONAL | 2h |
| Runbooks | `governance/runbooks.mdx` | OPERATIONAL | 2.5h |
| Vault Transit | `governance/secrets-vault-transit.mdx` | REFERENCE | 1.5h |
| Cloud KMS | `governance/secrets-cloud-kms.mdx` | REFERENCE | 1.5h |
| Supply Chain (Main) | `compliance/supply-chain.mdx` | REFERENCE | 1.5h |
| DSGVO | `compliance/gdpr.mdx` (already exists, sync) | REVIEW | 0.5h |

**Subtotal Tier 2**: 24.5 hours ≈ 3-4 workdays

### Tier 3: Technical Reference (20 files) — WEEKS 4-5
Advanced topics for developers and operators.

| Category | Files | Est. Effort |
|----------|-------|-------------|
| Architecture Details (root24, matrix, shards, artifacts) | 4 | 8h |
| Integration & Tools (EMS, orchestrator, dispatcher, agents, etc.) | 8 | 12h |
| Identity (VC lifecycle) | 1 | 2h |
| Token Economics (utility, non-custodial, fee-models, distribution) | 4 | 6h |
| Observability (health-checks, observability, otel, dashboards, slos) | 3 | 4.5h |

**Subtotal Tier 3**: 32.5 hours ≈ 4-5 workdays

### Tier 4: Supplementary (14 files) — WEEK 6
Lower-priority research, auxiliary content.

| File | Est. Effort |
|------|-------------|
| Roadmap | 1h |
| Changelog | 1.5h |
| Research papers (1 file) | 1h |
| Supply-Chain: SBOM, SLSA, Sigstore, Reproducible Builds (4 files) | 4h |
| AI Gateway | 0.5h |
| Autopilot | 0.5h |
| Health Checks (sidebar reference) | 0.5h |
| Authentication | 0.5h |
| Post-Quantum Crypto (architecture) | 1h |
| Open-Core Model | 1h |
| Permissionless Crypto Assets (research) | 0.5h |
| VC Lifecycle | 1.5h |

**Subtotal Tier 4**: 14 hours ≈ 2 workdays

---

## Translation Approach

### File Structure
Each German file mirrors English structure:
```
src/content/docs/de/path/to/file.mdx
```

### Frontmatter Translation
```yaml
---
title: {{German title}}
description: {{German description}}
---
```

### Content Requirements
1. Complete translation of all body text
2. Preserve all links and cross-references (URLs unchanged)
3. Keep code blocks unchanged (bash, JSON, YAML, etc.)
4. Preserve table headers and data structure
5. Translate alt-text for images/diagrams
6. Update relative links where needed for `/de/` path structure

### Quality Standards
- German technical accuracy (comply with EU standards: eIDAS, GDPR, MiCA)
- Terminology consistency (build German glossary)
- Native speaker review for each file (batched review every 2-3 files)
- Markdown/MDX syntax validation via CI/CD

### CI/CD Validation
Existing locale tests in `tests/sidebar-soll-categories.test.mjs` will verify:
- All German files have valid frontmatter
- All German files have meaningful content (>1000 chars)
- No broken links within German content
- Sidebar references valid

---

## Execution Plan

### Week 1 (Apr 15-21): Tier 1 Batch 1
- Files: Getting Started, Overview, Local Stack, Port Matrix (4 files)
- Effort: ~6.5 hours
- Deliverable: PR with 4 German files + updated sidebar German labels

### Week 1-2 (Apr 22-28): Tier 1 Batch 2 + Tier 2 Batch 1
- Files: Deployment guides (testnet, mainnet), FAQ, compliance basics (6 files)
- Effort: ~8.5 hours
- Deliverable: PR with 6 German files

### Week 3 (Apr 29-May 5): Tier 2 Complete + Tier 3 Start
- Files: Evidence, governance, audit framework, identity basics (8 files)
- Effort: ~12 hours
- Deliverable: PR with 8 German files

### Week 4-5 (May 6-18): Tier 3 Complete
- Files: Architecture details, tooling, token economics (12 files)
- Effort: ~14.5 hours
- Deliverable: PR with 12 German files

### Week 6 (May 19-25): Tier 4 + Cleanup
- Files: Research, supplementary, final validation (8 files)
- Effort: ~7.5 hours
- Deliverable: PR with final 8 files, 100% coverage achieved

---

## Known Constraints & Risks

### Resource Constraints
- Single translator (bias toward technical accuracy over literary quality)
- No professional translation service contracted
- Estimated 32-40 hours total effort (4-5 FTE workdays)

### Technical Constraints
- Sidebar labels currently English-only (separate Phase 4 task)
- No automated translation (manual for accuracy and compliance)
- Multi-language routing via Astro locales (working per astro.config.mjs)

### Compliance Risks
- German regulatory terminology must be precise (eIDAS, DSGVO, MiCA)
- Technical terms must follow EU standards documentation
- Risk mitigation: Reference official EU glossaries, domain-expert review

---

## Success Criteria

| Criterion | Target | Validation |
|-----------|--------|------------|
| File Coverage | 67/67 (100%) | `git ls-files \| grep de/ \| wc -l` |
| CI/CD Gates | 7/7 PASS | locale-test gate completion |
| Frontmatter Validity | 100% valid | build logs verification |
| Link Validation | 0 broken links | build log analysis |
| Content Length | All >1000 chars | test suite validation |
| German Accuracy | Native review approved | peer review per Tier |

---

## Phase 3 Deliverables

1. **67 German content files** (67 `.mdx`/`.md` in `de/` tree)
2. **Updated astro.config.mjs sidebar** with German translation for 150+ labels (Phase 4 task)
3. **German glossary** (documentation of key technical terms)
4. **Phase 3 Completion Report** (coverage metrics, quality audit, lessons learned)
5. **PR #53** (Phase 3: Complete German Language Support)

---

## Known Gaps (Phase 4+)

1. **Sidebar Labels Translation** — 150+ navigation labels currently English-only
2. **Interactive Tool Translations** — Port resolver, deployment wizard UIs
3. **API Reference Generation** — Auto-generated from OpenAPI (not manual)
4. **Video Tutorial Translations** — German voiceover/subtitles (Phase 4)
5. **Multi-language Search** — Algolia search integration (Phase 5)

---

**Status**: PHASE_3_INITIATED  
**Initiated**: 2026-04-13  
**Target Completion**: 2026-05-15  
**Next Review**: 2026-04-20 (EOW Tier 1 progress)
