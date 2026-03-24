# SoT-to-Docs Mapping

**Date:** 2026-03-23
**Branch:** fix/ssid-docs-baseline-sot-ia-csp-lock
**SoT Base:** C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID\16_codex

## Core Architecture

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| ssid_master_definition_corrected_v1.1.1 | 24 Root Modules | architecture/matrix | exists (root names updated) | low |
| ssid_master_definition_corrected_v1.1.1 | 16 Shards | architecture/shards | exists | none |
| ssid_master_definition_corrected_v1.1.1 | 24x16 Matrix | architecture/matrix | exists | none |
| SSID_opencore_structure_level3 | Open-Core public/private | — | missing | medium |
| ssid_master_definition_corrected_v1.1.1 | Deterministic Artifacts | architecture/artifacts | exists | none |
| ssid_master_definition_corrected_v1.1.1 | EMS Architecture | architecture/ems | exists | low |
| SSID_structure_level3_part1_MAX | Post-Quantum (Root 21) | — | missing | low |
| ssid_master_definition_corrected_v1.1.1 | Create-on-use pattern | — (erwaehnt in matrix) | partial | low |

## Token & Economics

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| ssid_master_definition_corrected_v1.1.1 | Token (utility/governance) | token/utility | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Non-custodial | token/non-custodial | exists | none |
| SSID_structure_gebuehren_abo_modelle | Fee-/Abo-Modelle | — | missing | high |
| SSID_structure_gebuehren_abo_modelle | POFI / Distribution | — | missing | medium |
| SSID_structure_gebuehren_abo_modelle_ROOTS_16_21_ADDENDUM | Dev-Reward by Root | — | missing | medium |

## Governance

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| ssid_master_definition_corrected_v1.1.1 | PR-only Workflow | governance/pr-only | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Evidence & WORM | governance/evidence | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Policy Gates | governance/policy-gates | exists | none |
| SSID_structure_level3_part2_MAX | DAO Governance / MoSCoW | — | missing | medium |
| SSID_structure_level3_part2_MAX | Promotion/Deprecation Rules | — | missing | medium |
| ssid_master_definition_corrected_v1.1.1 | Incident Response | governance/incident-response | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Secrets Management | governance/secrets-management | exists | none |

## Compliance

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| SSID_structure_level3_part3_MAX | GDPR/DSGVO | compliance/gdpr | exists | none |
| SSID_structure_level3_part3_MAX | eIDAS 2.0 | compliance/eidas | exists | none |
| SSID_structure_level3_part1_MAX | MiCA | compliance/mica | exists | none |
| ssid_master_definition_corrected_v1.1.1 | Supply-Chain Security | compliance/supply-chain | exists | none |
| SSID_structure_level3_part3_MAX | Audit Framework / CI Gates | — | missing | medium |
| SSID_structure_level3_part3_MAX | Global Compliance Matrix | — | n/a (private) | none |

## Developer & Roles

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| SSID_structure_level3_part1_MAX | Developer/Publisher Roles | — | missing | medium |
| ssid_master_definition_corrected_v1.1.1 | Local Stack Setup | tooling/local-stack | exists | none |

## EMS-Abgrenzung

| SoT Source | Thema | Zielseite | Status | Risiko |
|------------|-------|-----------|--------|--------|
| ssid_master_definition_corrected_v1.1.1 | EMS = External Mgmt System | architecture/ems | exists | low |
| ssid_master_definition_corrected_v1.1.1 | EMS/SSID Trennung | tooling/mission-control (korrigiert) | exists | none |

## Summary

| Status | Count |
|--------|-------|
| exists | 18 |
| partial | 1 |
| missing | 9 |
| n/a | 1 |
| **Total** | **29** |

**Fehlende Kernseiten (fuer spaetere Laeufe):**
1. Open-Core Structure (high priority)
2. Fee & Subscription Models (high priority, high risk)
3. DAO Governance / MoSCoW (medium)
4. Token Distribution / POFI (medium)
5. Developer Roles & Guide (medium)
6. Audit Framework Detail (medium)
7. Post-Quantum Crypto (low, draft shell)
8. Dev-Reward by Root (medium)
9. Promotion/Deprecation Rules (medium)

**Keine ungemappten Kernbereiche.** Alle SoT-Themen haben mindestens eine Statuserfassung.
