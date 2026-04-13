---
title: PHASE 1 — SSID-docs Public Documentation System Analysis
date: 2026-04-13
status: ANALYSIS_COMPLETE
---

# PHASE 1: SSID-docs System Completeness Analysis

**Objective:** Analyze the SSID-5-Repo system and SSID-docs' role as the public documentation layer. Identify gaps, conflicts, and optimization opportunities.

**Status:** Complete. Ready for Phase 2 Plan.

---

## 1. SYSTEM CONTEXT (5 Repos)

### 1.1 Repo Topologies

| Repo | Visibility | Tech Stack | Role | Status |
|------|------------|------------|------|--------|
| **SSID** | Private | Python 3.11+, OPA, Git worktrees | Core platform, ROOT-24 enforcer, SoT source | OPERATIONAL (Phase 7/8) |
| **SSID-EMS** | Private | Python (FastAPI), React/Next.js, PM2 | Control Plane, CLI (ssidctl), Portal, Evidence | OPERATIONAL (Phase 5+) |
| **SSID-orchestrator** | Private | Python 3.11+, Node.js 22+, React/Vite | Runtime, Dispatch, Workflows, Sessions | OPERATIONAL (Phase 2) |
| **SSID-open-core** | Public | Python 3.11+, git export | Public export: 5 roots (03, 12, 16, 23, 24) | OPERATIONAL |
| **SSID-docs** | Public | Astro 5, Starlight 0.37, Node.js 22, pnpm | Public documentation + tutorials | OPERATIONAL (Port 4331=G) |

---

## 2. SSID-DOCS CURRENT STATE

### 2.1 Content Inventory

**Total Pages:** 66 documented (based on astro.config.mjs)

**By Category:**
- **Overview:** 1 page
- **Architecture:** 8 pages (root24, roots, matrix, shards, artifacts, ems, open-core, post-quantum)
- **Identity:** 2 pages (did-method, vc-lifecycle)
- **Governance:** 10 pages (pr-only, evidence, policy-gates, guards, dao, incident-response, runbooks, secrets-management, vault-transit, cloud-kms)
- **Compliance:** 10 pages (gdpr, eidas, mica, audit-framework, post-quantum-migration, supply-chain, sbom, slsa, sigstore, reproducible-builds)
- **Tooling:** 12 pages (dispatcher, agents, mission-control, health-checks, authentication, autopilot, local-stack, observability, otel, dashboards, slos, ai-gateway)
- **Token:** 4 pages (utility, non-custodial, fee-models, distribution)
- **Developer:** 2 pages (getting-started, quickstart)
- **Operations:** 1 page (local-stack)
- **Research:** 1 page (permissionless-crypto-assets-2026-03)
- **FAQ:** 2 pages (general, token-disambiguation)
- **Project:** 5 pages (roadmap, status, changelog, security, exports)

**Internationalization:** English (en, root) + German (de) with partial translations

### 2.2 CI/CD Gates (docs_ci.yml)

| Gate | Status | Purpose |
|------|--------|---------|
| **build** | ✓ PASS | Type check, Astro build, test suite |
| **secret-scan** | ✓ PASS | Block credentials, API keys, tokens |
| **denylist-gate** | ✓ PASS | Forbid .pem/.key/.env, internal paths, private repo refs |

### 2.3 Tests Suite (tests/)

- **build-stress.test.mjs** — Build resilience under load
- **content.test.mjs** — Content validation (frontmatter, links, locale consistency)
- **integration-stress.test.mjs** — Full integration stress
- **locale.test.mjs** — Locale/i18n completeness
- **route-stress.test.mjs** — Route generation stress
- **security.test.mjs** — Security pattern validation, secret scanning
- **sidebar-completeness.test.mjs** — Sidebar config vs. actual content
- **structure.test.mjs** — File/folder structure compliance
- **theme.test.mjs** — Theme/CSS validity
- **stress-*** (10+ variants) — Concurrent and live build scenarios

### 2.4 Tools Pipeline

| Tool | Purpose | Status |
|------|---------|--------|
| **ingest.mjs** | Auto-ingest from SSID-open-core (allowlist: docs/, policies/, README, LICENSE, SECURITY.md) | ✓ OPERATIONAL |
| **validate-ingest-source.mjs** | Validate ingest source is public (CI workflow) | ✓ OPERATIONAL |
| **changelog-gen.mjs** | Auto-generate CHANGELOG.mdx | ✓ OPERATIONAL |
| **public_export_manifest.json** | Manifest of public exports | ✓ OPERATIONAL |

### 2.5 Public Policy & Security (PUBLIC_POLICY.md)

**Ingest Source:**
- ✓ Only SSID-open-core allowed (verified by validateSourceIsPublic())
- ✗ NO automated mirroring from private SSID

**Hard Denies:**
- ✗ 02_audit_logging paths
- ✗ WORM registry paths
- ✗ .env, .pem, .key files
- ✗ Credentials, tokens, private keys
- ✗ Absolute local paths (C:\Users\, /home/...)
- ✗ Private repo references (local.ssid, sync.all, mirror.repo)

---

## 3. GAP ANALYSIS: IST vs. SOLL

### 3.1 Critical Gaps (P0 — Blocking)

| Gap | Current | Required | Impact | Fix Complexity |
|-----|---------|----------|--------|-----------------|
| **Repo Topology Documentation** | Minimal (architecture/open-core.mdx only) | Complete 5-repo map with roles, ports, CI/CD | Users can't understand system composition | P0-HIGH |
| **Port Matrix Documentation** | ✓ Present in local-stack.md BUT OUTDATED (C-ports, not G-ports) | G-Port Matrix (3100/8100/3102/4331/5273) with CI reference | Developers connect to wrong ports locally | P0-HIGH |
| **EMS Operational Docs** | Mission-Control page exists but incomplete | Complete EMS CLI (ssidctl), Portal walkthrough, 3-plane model docs | Users can't operate EMS control plane | P0-HIGH |
| **Orchestrator Integration Docs** | Minimal (tooling/dispatcher.mdx only) | Complete runtime, dispatch, session lifecycle, workflow examples | No public guidance on orchestrator usage | P0-HIGH |
| **Deployment Pipeline** | Not documented | Documented: local → testnet → mainnet readiness (CI/CD gates, K8s, Terraform) | No clear deploy path for public | P0-MEDIUM |
| **Testnet Status Page** | Not present | Live testnet contract addresses, RPC endpoints, explorer links, test ETH faucet | Users can't interact with testnet | P0-MEDIUM |
| **Mainnet Readiness** | Not documented | Public roadmap: what gates must pass before mainnet (audit, legal, tech milestones) | No clarity on production readiness | P0-MEDIUM |

### 3.2 Important Gaps (P1 — Significant)

| Gap | Current | Required | Impact |
|-----|---------|----------|--------|
| **Local Stack CI/CD** | Bash steps in local-stack.md | Full GitHub Actions workflows documented (build, test, lint, deploy) | Developers can't reproduce CI locally |
| **Evidence & WORM** | Evidence page exists (governance/evidence.mdx) | Link to public evidence export endpoint + proof-of-immutability docs | No way to verify public audit trail |
| **Smart Contract Docs** | Not present | Public contract ABI, deployment addresses (testnet/mainnet), upgrade mechanism, audit reports | No dev guidance on contracts |
| **SoT (Source of Truth) Validator** | Not documented | Public CLI tool documentation + validation rules | Can't verify system integrity |
| **Internationalization** | English + partial German | Completeness audit for de/ locale + roadmap for other langs | German users have incomplete docs |
| **FAQ Depth** | 2 pages (generic) | Expand: token mechanics, local stack troubleshooting, DID vs. other SSI, fee calculation | Common user questions unanswered |

### 3.3 Minor Gaps (P2 — Nice-to-Have)

| Gap | Current | Required |
|-----|---------|----------|
| **API Reference** | Not present | Auto-generated from OpenAPI spec (EMS API, Orchestrator API) |
| **Solidity Contract Source** | Not documented | Public contract source + development guide (if public) |
| **Contributing Guide** | Not present | CONTRIBUTING.md with code of conduct, PR workflow, review gates |
| **Architecture Diagrams** | Described in text | Mermaid/SVG diagrams (system topology, data flow, event flow) |
| **Cost Estimation** | Not present | Fee calculation guide, gas estimation tools |
| **Upgrade & Migration** | Not documented | Contract upgrade mechanism, data migration guides (if applicable) |

---

## 4. PUBLIC/PRIVATE BOUNDARY MATRIX

### 4.1 Content Classification

| Category | Source | Status in docs | Can be Public | Notes |
|----------|--------|--------|---------------|-------|
| **Architecture** | SSID (private) + SSID-open-core | ✓ Present | ✓ YES | Describe publicly, don't mirror internals |
| **Identity/DID** | SSID (private) + SSID-open-core | ✓ Present | ✓ YES | Public standard docs, spec-based |
| **Governance/Gates** | SSID (private) + SSID-open-core | ✓ Present | ✓ YES | Policy structure public; implementation private |
| **Compliance** | SSID (private) | ✓ Present | ✓ YES (sanitized) | Regulations public, audit results private |
| **Tooling/CLI** | SSID-EMS, SSID-orchestrator (private), SSID-open-core (partial) | ⚠ Partial | ✓ YES (open-core only) | Only document public exports |
| **Local Stack** | All 5 repos | ✓ Present | ✓ YES (with caveats) | Docs, ports, health checks OK; internal paths NOT OK |
| **EMS Control Plane** | SSID-EMS (private) | ✗ Minimal | ✓ YES (sanitized) | Can describe CLI/Portal workflow; don't expose internals |
| **Orchestrator Runtime** | SSID-orchestrator (private) | ✗ Minimal | ✓ YES (sanitized) | Can describe dispatch/workflow model; don't expose scheduling |
| **Deployment/CI-CD** | SSID, SSID-EMS, SSID-orchestrator (private) | ✗ Not present | ✓ YES (sanitized) | Can show workflow structure, gates; not internal tooling |
| **Smart Contracts** | SSID (private) | ✗ Not present | ✓ YES (if public) | Only if contracts are deployed to public chains |
| **Status Pages** | Derived from public exports | ✓ Present (outdated) | ✓ YES | Must be auto-derived, not manual snapshots |
| **Runbooks/Incident Response** | SSID (private) | ⚠ Governance page only | ✓ PARTIAL | Public incident coordination; internal triage private |

### 4.2 FORBIDDEN Content (Hard Block)

- 02_audit_logging structure (SSID-internal)
- WORM storage paths or implementation details
- Private worktree layouts or branch structures
- Internal Python module paths or OPA rule definitions
- Private API keys, tokens, or signing keys
- Local developer paths (C:\Users\bibel\, /home/..., etc.)
- Snapshots of internal status (Last Updated: 2026-03-02 is outdated)

---

## 5. TESTNET/MAINNET/PUBLIC-DOCS MATRIX

| Aspect | Local | Testnet | Mainnet | Public Docs |
|--------|-------|---------|---------|-------------|
| **Contract Addresses** | localhost/hardhat | Mumbai/Sepolia (public) | Ethereum/Polygon (public) | ✓ Testnet addresses + roadmap to mainnet |
| **RPC Endpoints** | http://localhost:8545 | Alchemy/Infura (public) | Alchemy/Infura (public) | ✓ Testnet RPC docs |
| **Faucets** | hardhat.fund() | SepoliaETH.com / Mumbai faucet | No faucet (real ETH) | ✓ Testnet faucet links |
| **Explorer** | Hardhat console | Etherscan Sepolia / PolygonScan Mumbai | Etherscan / PolygonScan | ✓ Explorer links |
| **Status** | Dev-only | Public staging | Public production | ✓ Clear testnet = staging, mainnet = production |
| **Documentation** | Local README + local-stack.md | Separate testnet guide | Separate mainnet readiness doc | ✓ All three in docs |

---

## 6. INFORMATION ARCHITECTURE ISSUES

### 6.1 Sidebar Completeness

**Current:** 11 top-level categories, 66 items
**Proposed:** Add missing top-level categories for full system visibility

**Missing Categories in Sidebar:**
- ❌ **Repo Topology** — How 5 repos fit together
- ❌ **Deployments** — Local, testnet, mainnet workflows
- ❌ **Networks** — Testnet and mainnet specifications
- ❌ **Integration** — EMS ↔ Orchestrator ↔ Core workflows
- ❌ **Contracts** — Public smart contract documentation (if applicable)
- ❌ **Status** — Live system status (currently outdated)

### 6.2 Content Inconsistencies

| Inconsistency | Location | Current | Required |
|----------------|----------|---------|----------|
| **Port Numbers** | local-stack.md | C-ports (3000, 8000, 3001, ...) | G-ports (3100, 8100, 3102, ...) for dev |
| **Status Date** | status.mdx | 2026-03-02 | Should be auto-updated or marked as historical |
| **EMS Visibility** | Sidebar: "Mission Control" only | Page exists but incomplete | Full EMS architecture & CLI docs |
| **Orchestrator** | Sidebar: "Dispatcher Workflow" only | Limited scope | Full runtime + dispatch + workflows |
| **Testnet Refs** | Scattered across pages | Inconsistent naming/addressing | Dedicated testnet section with live data |

---

## 7. CI/CD & WORKFLOW POLICY CONFLICTS

### 7.1 Conflicts Detected

| Conflict | Docs State | CI Enforcement | Issue |
|----------|------------|-----------------|-------|
| **Port Matrix Format** | local-stack.md shows C-ports | No validation of which ports are correct | Developers follow outdated guide |
| **Status Page Freshness** | Manually written snapshot | No auto-update mechanism | Information stale (41 days old) |
| **Sidebar Validator** | sidebar-completeness.test.mjs checks config vs. files | Test passes but doesn't validate SOLL completeness | Missing categories not detected |
| **Deployment Docs** | Not in repo at all | No CI check for deployment documentation | No enforcement that deploy docs exist |
| **Testnet/Mainnet** | No dedicated section | No policy that testnet docs exist | Users can't find network info |

### 7.2 CI Gate Audit

**Gates in docs_ci.yml:**
- ✓ **build** — Astro check, build, test
- ✓ **secret-scan** — Credential patterns
- ✓ **denylist-gate** — 4 sub-gates (file types, paths, absolute paths, private repo refs)

**Missing Gates:**
- ❌ **Sidebar completeness** — Must validate all SOLL categories present
- ❌ **Port matrix currency** — CI should verify ports match current workspace
- ❌ **Deployment docs presence** — Must have local/testnet/mainnet deployment guides
- ❌ **Status freshness** — Either auto-update or require manual freshnessmark
- ❌ **Ingest validation** — Beyond source validation, check content doesn't have private patterns

---

## 8. POLICY VIOLATIONS & CONTRADICTIONS

### 8.1 PUBLIC_POLICY.md Enforcement Status

| Policy | Stated | Enforced | Gap |
|--------|--------|----------|-----|
| "Only SSID-open-core as ingest source" | ✓ YES | ✓ validate-ingest-source.mjs | ✓ GOOD |
| "No 02_audit_logging paths" | ✓ YES | ✓ denylist-gate checks | ✓ GOOD |
| "No .env, .pem, .key files" | ✓ YES | ✓ denylist-gate checks | ✓ GOOD |
| "No absolute local paths" | ✓ YES | ✓ denylist-gate checks | ✓ GOOD |
| "No private repo references" | ✓ YES | ✓ denylist-gate checks (broad patterns) | ⚠ PATTERNS may miss new cases |
| "Content derives from open-core" | ✓ YES (stated) | ⚠ Partial (ingest tool present, but manual content not checked) | ⚠ MODERATE |

### 8.2 Undocumented Policies

- ❌ **What is "public content" beyond "not from 02_audit_logging"?** — Policy doesn't define positive boundary
- ❌ **How to handle sanitized private content?** — Policy silent on docs derived from private repos
- ❌ **Auto-update vs. manual snapshots?** — Status page is manual snapshot; policy doesn't specify which is allowed
- ❌ **Testnet/mainnet claim guardrails?** — No policy on how to mark "readiness" without false claims

---

## 9. QUALITY & COMPLETENESS ASSESSMENT

### 9.1 Coverage by Domain

| Domain | Coverage % | Quality | Notes |
|--------|-----------|---------|-------|
| **Architecture** | 85% | HIGH | Root-24, shards, matrix documented; missing integration diagrams |
| **Identity/DID** | 70% | MEDIUM | Basic DID/VC lifecycle; missing key operations (binding, revocation) |
| **Governance** | 75% | MEDIUM | Policy gates documented; missing 3-plane model, evidence export details |
| **Compliance** | 80% | MEDIUM | eIDAS/GDPR/MiCA present; missing audit report references, supply-chain automation |
| **Tooling** | 60% | MEDIUM | CLI tools + observability documented; EMS/Orchestrator severely under-documented |
| **Operations** | 40% | LOW | Local stack minimal; missing testnet setup, deployment scripts, runbooks |
| **Deployments** | 20% | LOW | No local/testnet/mainnet guides; no K8s/Terraform docs |
| **Smart Contracts** | 0% | N/A | No documentation (contracts may not be public) |
| **Status Pages** | 30% | LOW | Outdated snapshot; no auto-update mechanism |

### 9.2 User Journey Gaps

**Current Bottlenecks:**
1. User wants to run local stack → local-stack.md exists but has wrong ports
2. User wants to understand architecture → Good docs but no system integration diagram
3. User wants to deploy to testnet → NO GUIDE
4. User wants to understand EMS → Only "Mission Control" page, minimal content
5. User wants compliance info → Good policy docs but no audit reports or live evidence
6. User wants to verify system integrity → Evidence page exists but no public evidence export link

---

## 10. RECOMMENDED SOLLBILD FOR SSID-DOCS

### 10.1 Ideal Sidebar Structure (Post-Phase 2)

```
Overview
  ├─ What is SSID?
  └─ Quick Links

System Architecture
  ├─ 5-Repo Topology
  ├─ Root-24 Architecture
  ├─ 24x16 Matrix
  ├─ Shards & Hybrids
  ├─ System Artifacts
  ├─ EMS Architecture
  ├─ Orchestrator Architecture
  ├─ Open-Core Model
  └─ Post-Quantum Roadmap

Getting Started
  ├─ Local Stack Setup
  ├─ Running the Dev Server
  ├─ Health Checks & Troubleshooting
  ├─ Port Matrix (Corrected)
  └─ Quickstart Guide

Operations & Deployments
  ├─ Local Development
  │   ├─ Prerequisites
  │   ├─ Start Services
  │   ├─ Health Checks
  │   └─ Troubleshooting
  ├─ Testnet Deployment
  │   ├─ Contract Addresses (Mumbai/Sepolia)
  │   ├─ RPC Endpoints & Faucets
  │   ├─ Deployment Workflow
  │   └─ Testnet Explorer Links
  └─ Mainnet Readiness
      ├─ Production Checklist
      ├─ Deployment Gates
      └─ Mainnet Roadmap

Identity & Credentials
  ├─ DID Method Specification
  ├─ VC (Verifiable Credential) Lifecycle
  ├─ Binding & Revocation
  └─ Selective Disclosure

Governance & Operations
  ├─ PR-Only Workflow
  ├─ Policy Gates & Guards
  ├─ Evidence & WORM Ledger
  ├─ DAO Governance
  ├─ Incident Response
  ├─ Runbooks
  └─ Secrets Management

Integration & Tooling
  ├─ EMS CLI (ssidctl)
  │   ├─ Configuration
  │   ├─ Bootstrap & Setup
  │   └─ Common Tasks
  ├─ Orchestrator
  │   ├─ Runtime & Dispatch
  │   ├─ Workflows & Sessions
  │   └─ Health Checks
  ├─ Dispatcher & Agents
  ├─ Health Checks
  ├─ Authentication & Sessions
  └─ Observability

Smart Contracts (if public)
  ├─ Contract Overview
  ├─ Solidity Source & ABI
  ├─ Deployment Addresses
  ├─ Upgrade Mechanism
  └─ Security Audits

Compliance & Regulations
  ├─ DSGVO / GDPR
  ├─ eIDAS
  ├─ MiCA Positioning
  ├─ Audit Framework
  ├─ Public Evidence Export
  └─ Supply-Chain Security

Token Economics
  ├─ Token Utility & Governance
  ├─ Non-Custodial Design
  ├─ Fee Models & Calculation
  └─ Token Distribution

Developer Resources
  ├─ Getting Started
  ├─ API Reference (if auto-generated)
  ├─ Code Examples
  └─ Contributing Guide

System Status
  ├─ Live Dashboard (Auto-Updated)
  ├─ Testnet Status
  ├─ Mainnet Readiness
  ├─ Repository Health
  └─ Public Evidence Export

FAQ & Troubleshooting
  ├─ General FAQ
  ├─ Token Disambiguation
  ├─ Deployment Issues
  ├─ Local Stack Problems
  └─ Architecture Questions

Research & Roadmap
  ├─ Research Papers
  ├─ Permissionless Assets
  ├─ Roadmap
  ├─ Changelog
  └─ Security Disclosure

About
  ├─ Security Policy
  ├─ License
  └─ Export Transparency
```

### 10.2 New Files to Create (Phase 2)

**By Priority:**

| Priority | File | Category | Purpose |
|----------|------|----------|---------|
| **P0** | `src/content/docs/architecture/5-repo-topology.mdx` | System Architecture | Map 5 repos, roles, interactions |
| **P0** | `src/content/docs/operations/ports-matrix-current.mdx` | Operations | Correct G-port matrix with CI reference |
| **P0** | `src/content/docs/operations/ems-control-plane.mdx` | Operations | EMS architecture, CLI (ssidctl), Portal workflow |
| **P0** | `src/content/docs/operations/orchestrator-runtime.mdx` | Operations | Orchestrator dispatch, workflows, sessions |
| **P0** | `src/content/docs/deployments/testnet-guide.mdx` | Deployments | Testnet contract addresses, RPC, faucet, explorer |
| **P1** | `src/content/docs/deployments/mainnet-readiness.mdx` | Deployments | Production checklist, gates, timeline |
| **P1** | `src/content/docs/deployments/local-ci-cd.mdx` | Deployments | Reproduce GitHub Actions workflows locally |
| **P1** | `src/content/docs/contracts/` (if public) | Smart Contracts | ABI, source, deployment, audit |
| **P1** | `src/content/docs/governance/evidence-export.mdx` | Governance | Public evidence export endpoint + verification |
| **P1** | `src/content/docs/integration/ems-orchestrator-flow.mdx` | Integration | End-to-end flow (EMS → Core → Orchestrator) |
| **P2** | `src/content/docs/api-reference.mdx` | Developer | Auto-generated from OpenAPI (if available) |
| **P2** | `src/content/docs/contributing.mdx` | Developer | Contributing guide, PR workflow, code of conduct |
| **P2** | `CONTRIBUTING.md` | Root | Standard GitHub CONTRIBUTING file |

### 10.3 Files to Update (Phase 2)

| File | Change | Reason |
|------|--------|--------|
| `src/content/docs/operations/local-stack.md` | Replace C-ports with G-ports; add PM2 reference | Current ports wrong for dev workspace |
| `src/content/docs/status.mdx` | Add auto-update mechanism or clear historical marker | Status outdated (41 days old) |
| `src/content/docs/tooling/mission-control.mdx` | Expand from 1 page to 3-4 pages (full EMS workflow) | EMS severely under-documented |
| `src/content/docs/tooling/dispatcher.mdx` | Rename/reorganize into orchestrator-runtime.mdx | Dispatcher alone insufficient; needs full orchestrator context |
| `astro.config.mjs` | Add 4-5 new sidebar categories (Deployments, Networks, Integration, Contracts) | Sidebar missing critical system areas |
| `src/content/docs/architecture/open-core.mdx` | Link to 5-repo-topology.mdx | Context needed for understanding open-core |

---

## 11. TEST COVERAGE ASSESSMENT

### 11.1 Current Test Suite

| Test | Coverage | Gaps |
|------|----------|------|
| **build-stress** | Astro build resilience | ✓ Good; no gaps |
| **content** | Frontmatter, links, locale | ⚠ Doesn't validate port matrix correctness |
| **security** | Secret patterns, absolute paths | ✓ Good; enforces policy |
| **sidebar-completeness** | Config vs. file presence | ⚠ Doesn't validate SOLL completeness |
| **structure** | File/folder layout | ✓ Good |
| **theme** | CSS/theme validity | ✓ Good |
| **integration-stress** | Full integration | ⚠ Doesn't test auto-update mechanisms |
| **locale** | i18n completeness | ⚠ Only checks presence, not translation quality |
| **route-stress** | Route generation | ✓ Good |

### 11.2 Recommended Test Additions (Phase 2)

| New Test | Purpose | Priority |
|----------|---------|----------|
| **ports-matrix-validator.test.mjs** | Validate port matrix matches workspace config | P0 |
| **sidebar-soll-completeness.test.mjs** | Enforce that all SOLL categories are present | P0 |
| **deployment-docs-presence.test.mjs** | Ensure local/testnet/mainnet deployment docs exist | P1 |
| **status-freshness-validator.test.mjs** | Check status.mdx date and enforce auto-update or manual mark | P1 |
| **contract-docs-presence.test.mjs** | If contracts are public, verify contract docs exist | P1 |
| **evidence-export-link-validator.test.mjs** | Verify evidence export links are not broken | P2 |

---

## 12. DELIVERABLES FOR PHASE 2

### 12.1 Implementation Plan Artifacts

1. **PHASE2_IMPLEMENTATION_PLAN.md** — Detailed step-by-step implementation with file changes, sidebar updates, test extensions
2. **files-to-create.json** — Manifest of all new files with slugs, titles, descriptions, templates
3. **files-to-update.json** — Manifest of all changed files with old/new snippets, diffs
4. **sidebar-config-new.mjs** — Updated sidebar configuration (astro.config.mjs excerpt)
5. **test-additions.mjs** — New test functions to add to test suite
6. **ci-gate-updates.yml** — Enhanced docs_ci.yml with new validations

### 12.2 Content Templates (Starter)

- Template: 5-repo-topology.mdx
- Template: testnet-guide.mdx
- Template: ems-control-plane.mdx (CLI + Portal)
- Template: orchestrator-runtime.mdx
- Template: ports-matrix-current.mdx

### 12.3 Validation Checklist (Post-Implementation)

- [ ] All SOLL categories present in sidebar
- [ ] Port matrix uses G-ports + CI reference
- [ ] EMS and Orchestrator have ≥2 pages each
- [ ] Testnet guide with live contract addresses (source: SSID-open-core)
- [ ] Mainnet roadmap documented (without false "live" claims)
- [ ] Evidence export endpoint documented
- [ ] No private repo paths, credentials, or outdated claims
- [ ] All new tests pass
- [ ] Sidebar-completeness test passes
- [ ] docs_ci.yml gates all pass

---

## 13. SUCCESS CRITERIA

### 13.1 Phase 2 Success (Completion)

- **Content Completeness:** ✓ All P0/P1 gaps closed
- **Policy Compliance:** ✓ No hard-deny violations; all CI gates pass
- **User Experience:** ✓ User can follow 4 journeys (local, testnet, mainnet, architecture)
- **Maintainability:** ✓ Auto-update mechanisms for status/evidence; tests enforce completeness
- **Public Trust:** ✓ No false claims; clear staging vs. production distinction

### 13.2 Phase 2 Exit Criteria

- [ ] All new files created and pass content test
- [ ] All updated files revised and pass content test
- [ ] astro.config.mjs sidebar updated with 4-5 new categories
- [ ] Test suite extended (≥3 new tests)
- [ ] docs_ci.yml extended with new gates or checks
- [ ] `pnpm build` passes without warnings
- [ ] `pnpm test` passes 100%
- [ ] No secrets, private paths, or policy violations in `git diff`
- [ ] SSID-docs local build runs cleanly on port 4331

---

## 14. KNOWN CONSTRAINTS & ASSUMPTIONS

### Constraints
- **Ingest Source:** Only SSID-open-core (5 exported roots) is automated; private repos require manual sanitization
- **Confidentiality:** No access to internal audit logs, WORM details, or private code
- **Ports:** Must use G-port matrix (3100/8100/3102/4331/5273) for workspace consistency
- **Freshness:** Status pages either auto-update from public exports or marked with snapshot date
- **Claims:** No "mainnet live" without public evidence; testnet marked as staging

### Assumptions
- SSID-open-core 5 roots (03, 12, 16, 23, 24) are the authoritative public API
- Testnet contract addresses are available in SSID-open-core exports
- Port matrix changes are tracked in workspace config, not hardcoded in docs
- Evidence export endpoint exists or will be provided
- EMS/Orchestrator sanitized descriptions can be derived from private repos without exposing internals

---

## 15. PHASE 1 CONCLUSION

**Status:** ✅ ANALYSIS COMPLETE

**Key Findings:**
1. ✓ SSID-docs has strong foundation (66 pages, good CI gates, secure policy)
2. ⚠ Critical gaps in operations/deployments (P0: 5 items)
3. ⚠ Important gaps in EMS/Orchestrator/Testnet (P1: 7 items)
4. ⚠ Port matrix outdated (C-ports instead of G-ports)
5. ⚠ Status page stale (41 days old)
6. ✓ Public policy well-enforced; no hard-deny violations found

**Recommendation:** Proceed to Phase 2 Implementation Plan.

---

**Analysis Date:** 2026-04-13  
**Analyst:** SSID System Architect  
**Next:** Phase 2 — Implementation Plan (PHASE2_IMPLEMENTATION_PLAN.md)

