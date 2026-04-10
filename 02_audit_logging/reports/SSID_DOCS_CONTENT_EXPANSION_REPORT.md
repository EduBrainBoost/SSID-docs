# SSID-docs Content Expansion Report

**Date:** 2026-03-23
**Branch:** fix/ssid-docs-baseline-sot-ia-csp-lock
**Commit:** 75b9774

## New Pages Created (8)

| File | Title | SoT Source | Lines |
|------|-------|------------|-------|
| architecture/roots.mdx | 24 Root Modules | ssid_master_definition_corrected_v1.1.1 | 88 |
| architecture/open-core.mdx | Open-Core Structure | SSID_opencore_structure_level3 | 88 |
| architecture/post-quantum.mdx | Post-Quantum Cryptography | SSID_structure_level3_part1_MAX | 48 |
| token/fee-models.mdx | Fee & Subscription Models | SSID_structure_gebuehren_abo_modelle | 105 |
| token/distribution.mdx | Token Distribution & Fairness | SSID_structure_gebuehren_abo_modelle | 64 |
| governance/dao.mdx | DAO Governance & Change Process | SSID_structure_level3_part2_MAX | 70 |
| compliance/audit-framework.mdx | Audit Framework | SSID_structure_level3_part3_MAX | 68 |
| developer/getting-started.mdx | Developer Guide | SSID_structure_level3_part1_MAX | 72 |

## Sidebar Changes

| Section | Before | After | Added |
|---------|--------|-------|-------|
| Architecture | 4 | 7 | roots, open-core, post-quantum |
| Governance | 5 | 6 | dao |
| Compliance | 4 | 5 | audit-framework |
| Developer | 0 | 1 | getting-started (new section) |
| Token | 2 | 4 | fee-models, distribution |
| **Total** | **32** | **40** | **+8** |

## SoT-Claim-Review (Mandatory for High-Risk Pages)

### fee-models.mdx — PASS

| Claim | SoT Source | Verdict |
|-------|-----------|---------|
| 0.12% avg fee | SSID_structure_gebuehren_abo_modelle | Belegt |
| 97/1/2 split | SSID_structure_gebuehren_abo_modelle | Belegt |
| System pool 0.50/0.35/0.25/0.10 | SSID_structure_gebuehren_abo_modelle | Belegt |
| 4 Enterprise-Tiers | SSID_structure_gebuehren_abo_modelle | Belegt |
| Hybrid payout 100 EUR / 1.1x | SSID_structure_gebuehren_abo_modelle | Belegt |
| Dev rewards 7 Roots | ROOTS_16_21_ADDENDUM | Belegt |
| Non-custodial disclaimer | SSID_structure_gebuehren_abo_modelle | Belegt |
| Unbelegte Claims | — | 0 |

### distribution.mdx — PASS

| Claim | SoT Source | Verdict |
|-------|-----------|---------|
| POFI-Formel | SSID_structure_gebuehren_abo_modelle | Belegt |
| Impact-Metriken | SSID_structure_gebuehren_abo_modelle | Belegt |
| Enterprise 30/50/10/10 | SSID_structure_gebuehren_abo_modelle | Belegt |
| Legal Safe Harbor | SSID_structure_level3_part1_MAX | Belegt |
| Stablecoin hypothetisch markiert | Explizit | Belegt |
| Unbelegte Claims | — | 0 |

### dao.mdx — PASS

| Claim | SoT Source | Verdict |
|-------|-----------|---------|
| 5 Governance-Rollen | SSID_structure_level3_part2_MAX | Belegt |
| MoSCoW 4 Level | SSID_structure_level3_part2_MAX | Belegt |
| Promotion/Deprecation Rules | SSID_structure_level3_part2_MAX | Belegt |
| 14d/67% Voting | SSID_structure_level3_part2_MAX | Belegt |
| 4-Layer Maintainer | SSID_structure_level3_part2_MAX | Belegt |
| Unbelegte Claims | — | 0 |

## Build / Test / Runtime Verification

| Check | Result |
|-------|--------|
| pnpm build | PASS — 81 pages |
| pnpm test | PASS — 4/4 suites |
| Runtime 4331 sweep | PASS — 13/13 routes HTTP 200 |
| CSP in output | PASS |
| Base-path not regressed | PASS |
| No scope violation | PASS |
