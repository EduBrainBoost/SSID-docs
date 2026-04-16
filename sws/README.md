# Social Workflow System (SWS) — Documentation Index

## Overview

SWS is the deterministic social content intelligence subsystem within the SSID ecosystem. It decomposes foreign or native videos into reproducible structural artifacts, compiles blueprints, and uses them to generate new content with proprietary or licensed assets.

**Status:** Foundation Specs v1.0 — Canonical Documentation Deployment  
**Last Updated:** 2026-04-16  
**Scope:** Complete SWS architecture, build specification, and implementation roadmap for V1.0+

---

## Core Documentation

| Document | Location | Purpose | Audience |
|---|---|---|---|
| **SWS Foundation Spec v1.0** | [`architecture/SOCIAL_WORKFLOW_SYSTEM_FOUNDATION_SPEC_v1.0.md`](./architecture/SOCIAL_WORKFLOW_SYSTEM_FOUNDATION_SPEC_v1.0.md) | Canonical system architecture, layer model (L0–L5), 11 kanonische Shards, job/run model, rights model, RBAC, retention, observability. Non-negotiable invariants: determinism, additive writes, job isolation, rights-first, audit trail. | Architects, Platform Engineers, Compliance |
| **SWS V1 Build Spec v1.0** | [`roadmap/SWS_V1_BUILD_SPEC_v1.0.md`](./roadmap/SWS_V1_BUILD_SPEC_v1.0.md) | Implementable V1 rollout roadmap in SSID style. Defines V1 scope (MUST/SHOULD/NOT), 5 waves of delivery, CLI canonical, artifact minimum, 6 gates (Contract→Analyzer→Blueprint→Orchestration→EMS→Retention), 8 completion criteria. | Engineering Leads, Product, DevOps |
| **SWS Architektur-Ergänzung v1.0** | [`architecture/SWS_Architektur_Ergaenzung_v1.0.md`](./architecture/SWS_Architektur_Ergaenzung_v1.0.md) | Complete gap-closure supplement to Foundation Spec. Detailed artifact schemas (job_manifest, rebuild_blueprint, brand_profile, platform_policy, niche_registry, performance_signal, locale_variants), error/retry/DLQ policies, auth/RBAC model, DSGVO retention, audit logs, V1 scope recalibration, analytics feedback loop, observability stack, testing strategy, deployment architecture. | Architects, Backend Engineers, Security/Compliance |

---

## Navigation Quick Links

### By Role

**Product & Strategy:**
- [Foundation Spec: Purposes & Invariants](./architecture/SOCIAL_WORKFLOW_SYSTEM_FOUNDATION_SPEC_v1.0.md#1-zweck)
- [V1 Build Spec: Deliverables & Roadmap](./roadmap/SWS_V1_BUILD_SPEC_v1.0.md#3-v1-deliverables-nach-repo)

**Engineering:**
- [Foundation: Layer Model L0–L5](./architecture/SOCIAL_WORKFLOW_SYSTEM_FOUNDATION_SPEC_v1.0.md#4-layer-modell-l0l5)
- [Architektur-Ergänzung: Artifact Schemas](./architecture/SWS_Architektur_Ergaenzung_v1.0.md#5-fehlende-artefakt-schemas)
- [V1 Build: Shard Sequence & Gates](./roadmap/SWS_V1_BUILD_SPEC_v1.0.md#4-shard-reihenfolge-für-v1)

**Compliance & Security:**
- [Foundation: Rights & Risk Model](./architecture/SOCIAL_WORKFLOW_SYSTEM_FOUNDATION_SPEC_v1.0.md#7-rechte--und-risikomodell)
- [Ergänzung: DSGVO Retention Policy](./architecture/SWS_Architektur_Ergaenzung_v1.0.md#8-data-retention-policy-dsgvo)
- [Ergänzung: Audit Log Schema](./architecture/SWS_Architektur_Ergaenzung_v1.0.md#9-audit-log-schema)

**Operations:**
- [Ergänzung: Error Handling & Retry](./architecture/SWS_Architektur_Ergaenzung_v1.0.md#6-error-handling-retry-policy-und-dead-letter-queue)
- [Ergänzung: Deployment Architecture](./architecture/SWS_Architektur_Ergaenzung_v1.0.md#14-deployment-architektur)

---

## Key Architecture Concepts

### The 11 Canonical Shards

1. **sws-intake** — URL/File Intake, Rights-Precheck, Hashing
2. **sws-media-analyzer** — Shot, Audio, Transcript, OCR
3. **sws-fingerprint-compiler** — Hook, Narrative, Style, Thumbnail, Caption Patterns
4. **sws-blueprint-compiler** — Aggregation aller Analyseartefakte
5. **sws-replacement-engine** — Brand-/Asset-Mapping, Script Reconstruction
6. **sws-render-engine** — Timeline Builder, FFmpeg-Render
7. **sws-qa-engine** — Similarity, Compliance, Render-Readiness
8. **sws-asset-registry** — Asset-Provenance, Lizenzstatus
9. **sws-blueprint-library** — Searchable Blueprint Library
10. **sws-publish-packager** — Platform-specific Export Bundles
11. **sws-daily-studio** — Blueprint-based Daily Production

### Layer Model (L0–L5)

- **L5:** Governance & Compliance
- **L4:** Orchestration & Operations
- **L3:** Intelligence & Production
- **L2:** Media Processing
- **L1:** Ingest & Normalization
- **L0:** Storage & Infrastructure

### Job Model

- **Deterministic Pipeline:** Non-generative stages produce byte-identical outputs
- **Job Isolation (JOB-LOCK):** Complete context isolation per job
- **Additive Writes:** No artifact destruction, only append or versioning
- **Status Automaton:** CREATED → RIGHTS_CHECK → INGEST → ANALYZING → ANALYZED → REBUILD_PENDING → ... → PUBLISHED (with FAILED branches)

---

## Versioning & Governance

| Version | Status | Release Date | Scope |
|---|---|---|---|
| v1.0 | Canonical Foundation | 2026-04-16 | Core architecture, invariants, layer model, RBAC, retention |
| v1.5 (Planned) | Rebuild & QA | TBD | Script reconstruction, rendering, similarity QA, compliance reporting |
| v2.0 (Planned) | Daily Operations | TBD | Daily Content Studio, analytics feedback loop, semantic search |

---

## Implementation Roadmap (V1.0)

**Wave 1:** Contracts & Docs (THIS DEPLOYMENT)  
**Wave 2:** Analyzer Core  
**Wave 3:** Orchestration  
**Wave 4:** EMS UI  
**Wave 5:** Hardening & Testing  

See [`roadmap/SWS_V1_BUILD_SPEC_v1.0.md#4-shard-reihenfolge-für-v1`](./roadmap/SWS_V1_BUILD_SPEC_v1.0.md#4-shard-reihenfolge-für-v1) for details.

---

## Repository Mapping

| Repository | SWS Responsibility |
|---|---|
| `SSID-docs` | Architecture, Runbooks, Policies, ADRs (THIS LOCATION) |
| `SSID-open-core` | Schemas, Contracts, Analyzer/Compiler Libraries |
| `SSID-orchestrator` | DAGs, Queue, Worker, Retry, DLQ |
| `SSID-EMS` | Browser App (Job Queue, Blueprint Viewer, Rebuild Studio) |
| `SSID` | Central Governance, Audit Standards, Compliance Rules |

---

## Acceptance Criteria (V1.0)

Per [`roadmap/SWS_V1_BUILD_SPEC_v1.0.md#11-abschlusskriterium-v1`](./roadmap/SWS_V1_BUILD_SPEC_v1.0.md#11-abschlusskriterium-v1):

1. ✓ URL- oder File-Job erfolgreich startbar
2. ✓ Job deterministisch bis `ANALYZED` lauffähig
3. ✓ Alle Pflichtartefakte erzeugt und schema-validiert
4. ✓ `rebuild_blueprint.json` erzeugt
5. ✓ EMS zeigt Job und Blueprint sichtbar
6. ✓ Audit/Retention/RBAC baseline aktiv
7. ✓ Golden- und Integration-Tests grün

---

## Contact & Governance

**Documentation Owner:** Platform Architecture Team  
**Last Review:** 2026-04-16  
**Next Review:** 2026-05-16 (or upon V1.5 initiation)

For questions, issues, or contributions, please file issues against this repository with label `sws-docs`.

---

*SWS Foundation Specs deployed as canonical SSID-docs documentation. All three v1.0 specifications are deterministic, versioned, and subject to RFC-based changes only.*
