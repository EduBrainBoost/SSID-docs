# Umsetzungsplan: SSID-docs Sidebar-Vollstaendigkeit

Datum: 2026-04-12
Basis: ANALYSE_IST_SOLL_2026-04-12.md

## Zielzustand
Alle 56 navigierbaren Content-Dateien sind in der Starlight-Sidebar sichtbar.
Build PASS, Tests 4/4 PASS, keine Content-Aenderungen, keine Secrets.

## Betroffene Dateien
| # | Datei | Aenderung |
|---|-------|-----------|
| 1 | astro.config.mjs | Sidebar-Konfiguration erweitern |

## Abhaengigkeiten
- Keine externen Abhaengigkeiten
- Keine neuen Pakete
- Keine Port-Aenderungen (bleibt 4331)

## Schritt-fuer-Schritt

### Schritt 1: Sidebar in astro.config.mjs erweitern
Neue/erweiterte Sektionen:

```
Architecture (erweitert):
  + Root-24 Architecture (roots) — bleibt
  + Root-24 Details (architecture/root24) — NEU
  + 24x16 Matrix (matrix) — bleibt
  + Shards & Hybrid Charts (shards) — bleibt
  + Deterministic Artifacts (artifacts) — bleibt
  + EMS Architecture (ems) — bleibt
  + Open-Core Model (open-core) — NEU
  + Post-Quantum Crypto (post-quantum) — NEU

Identity (NEU):
  + DID Method (identity/did-method)
  + VC Lifecycle (identity/vc-lifecycle)

Governance (erweitert):
  + PR-Only Workflow — bleibt
  + Evidence & WORM — bleibt
  + Policy Gates — bleibt
  + Guard Rails (governance/guards) — NEU
  + DAO Governance — bleibt
  + Incident Response & DR — bleibt
  + Runbooks (governance/runbooks) — NEU
  + Secrets Management — bleibt
  + Vault Transit (governance/secrets-vault-transit) — NEU
  + Cloud KMS (governance/secrets-cloud-kms) — NEU

Compliance (erweitert):
  + DSGVO / GDPR — bleibt
  + eIDAS — bleibt
  + MiCA Positioning — bleibt
  + Audit Framework (compliance/audit-framework) — NEU
  + Post-Quantum Migration (compliance/post-quantum-migration) — NEU
  + Supply-Chain Security — bleibt (Hauptseite)
  + Supply-Chain: SBOM (compliance/supply-chain-sbom) — NEU
  + Supply-Chain: SLSA (compliance/supply-chain-slsa) — NEU
  + Supply-Chain: Sigstore (compliance/supply-chain-sigstore) — NEU
  + Supply-Chain: Reproducible Builds (compliance/supply-chain-reproducible-builds) — NEU

Tooling (erweitert):
  + Dispatcher Workflow — bleibt
  + Agent Roles — bleibt
  + Mission Control (EMS) — bleibt
  + Health Checks — bleibt
  + Authentication (tooling/authentication) — NEU
  + Autopilot (tooling/autopilot) — NEU
  + Local Stack (tooling/local-stack) — NEU
  + Observability — bleibt (Hauptseite)
  + Observability: OpenTelemetry (tooling/observability-otel) — NEU
  + Observability: Dashboards (tooling/observability-dashboards) — NEU
  + Observability: SLOs (tooling/observability-slos) — NEU
  + AI Gateway — bleibt

Developer (NEU):
  + Getting Started (developer/getting-started)
  + Quickstart Guide (guides/quickstart)

Operations (NEU):
  + Local Stack Setup (operations/local-stack)

Research (NEU):
  + Permissionless Crypto Assets (research/permissionless-crypto-assets-2026-03)
```

### Schritt 2: Build verifizieren
- `pnpm build` muss PASS
- Seitenzahl: weiterhin 119 (keine neuen Seiten, nur Sidebar-Verlinkung)

### Schritt 3: Tests ausfuehren
- `node tests/run.mjs` muss 4/4 PASS

### Schritt 4: Dev-Server starten und Sidebar pruefen
- `pnpm dev --port 4331`
- Alle neuen Sidebar-Eintraege muessen navigierbar sein

## Rollback
- `git checkout astro.config.mjs` stellt Originalzustand her
- Keine anderen Dateien betroffen

## Erfolgskriterien
1. Alle 56 Content-Seiten in Sidebar sichtbar
2. Build PASS (119 Seiten)
3. Tests 4/4 PASS
4. Keine neuen Content-Dateien erstellt
5. Keine Secrets im Code
6. Port 4331 unveraendert
