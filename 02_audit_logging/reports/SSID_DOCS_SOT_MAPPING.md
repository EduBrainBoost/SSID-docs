# SoT-to-Docs Mapping

**Date:** 2026-03-23 (updated after content expansion)
**Branch:** fix/ssid-docs-baseline-sot-ia-csp-lock
**SoT Base:** SSID/16_codex (Arbeitsstand)

## Core Architecture

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| ssid_master_definition_corrected_v1.1.1 | 24 Root Modules | architecture/roots | exists | none |
| ssid_master_definition_corrected_v1.1.1 | 16 Shards | architecture/shards | exists | none |
| ssid_master_definition_corrected_v1.1.1 | 24x16 Matrix | architecture/matrix | exists (root names canonicalized) | none |
| SSID_opencore_structure_level3 | Open-Core public/private | architecture/open-core | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Deterministic Artifacts | architecture/artifacts | exists | none |
| ssid_master_definition_corrected_v1.1.1 | EMS Architecture | architecture/ems | exists | none |
| SSID_structure_level3_part1_MAX | Post-Quantum (Root 21) | architecture/post-quantum | exists (draft shell) | low |
| ssid_master_definition_corrected_v1.1.1 | Create-on-use pattern | architecture/open-core (section) + architecture/roots (section) | exists | none |

## Token & Economics

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| ssid_master_definition_corrected_v1.1.1 | Token (utility/governance) | token/utility | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Non-custodial | token/non-custodial | exists | none |
| SSID_structure_gebuehren_abo_modelle | Fee-/Abo-Modelle | token/fee-models | exists (SoT-Claim-Review PASS) | none |
| SSID_structure_gebuehren_abo_modelle | POFI / Distribution | token/distribution | exists (SoT-Claim-Review PASS) | none |
| SSID_structure_gebuehren_abo_modelle_ROOTS_16_21_ADDENDUM | Dev-Reward by Root | token/fee-models (section) | exists | none |

## Governance

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| ssid_master_definition_corrected_v1.1.1 | PR-only Workflow | governance/pr-only | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Evidence & WORM | governance/evidence | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Policy Gates | governance/policy-gates | exists | none |
| SSID_structure_level3_part2_MAX | DAO Governance / MoSCoW | governance/dao | exists (SoT-Claim-Review PASS) | none |
| SSID_structure_level3_part2_MAX | Promotion/Deprecation Rules | governance/dao (section) | exists (integrated) | none |
| ssid_master_definition_corrected_v1.1.1 | Incident Response | governance/incident-response | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Secrets Management | governance/secrets-management | exists | none |

## Compliance

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| SSID_structure_level3_part3_MAX | GDPR/DSGVO | compliance/gdpr | exists | none |
| SSID_structure_level3_part3_MAX | eIDAS 2.0 | compliance/eidas | exists | none |
| SSID_structure_level3_part1_MAX | MiCA | compliance/mica | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Supply-Chain Security | compliance/supply-chain | exists | none |
| SSID_structure_level3_part3_MAX | Audit Framework / CI Gates | compliance/audit-framework | exists | none |
| SSID_structure_level3_part3_MAX | Global Compliance Matrix | — | n/a (private layer) | none |

## Developer & Roles

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| SSID_structure_level3_part1_MAX | Developer/Publisher Roles | developer/getting-started | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Local Stack Setup | tooling/local-stack | exists | none |

## EMS-Abgrenzung

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| ssid_master_definition_corrected_v1.1.1 | EMS = External Mgmt System | architecture/ems | exists | none |
| ssid_master_definition_corrected_v1.1.1 | EMS/SSID Trennung | tooling/mission-control (korrigiert) | exists | none |

## Summary

| Status | Count |
|--------|-------|
| exists | 28 |
| exists (draft) | 1 |
| n/a | 1 |
| missing | 0 |
| **Total** | **30** |

**Fehlende Kernseiten: 0**

Alle 9 ehemals fehlenden Bereiche sind jetzt abgedeckt:
- Open-Core → architecture/open-core.mdx
- Fee-Models → token/fee-models.mdx (Claim-Review PASS)
- DAO/MoSCoW → governance/dao.mdx (Claim-Review PASS, inkl. Promotion/Deprecation)
- Distribution/POFI → token/distribution.mdx (Claim-Review PASS)
- Developer Guide → developer/getting-started.mdx
- Audit Framework → compliance/audit-framework.mdx
- Post-Quantum → architecture/post-quantum.mdx (draft shell)
- Dev-Rewards → token/fee-models.mdx (Abschnitt)
- Roots Reference → architecture/roots.mdx
