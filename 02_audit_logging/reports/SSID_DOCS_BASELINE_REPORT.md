# SSID-docs Baseline Report

**Date:** 2026-03-23
**Branch:** fix/ssid-docs-baseline-sot-ia-csp-lock
**Base:** main (commit a6047c3)
**Commit:** 5ae84a9

## Remote Verification

| Check | Result |
|-------|--------|
| Branch on origin | PASS — `origin/fix/ssid-docs-baseline-sot-ia-csp-lock` |
| Commit SHA on remote | PASS — `5ae84a93b9923826f26281eb109abb07f554c0ff` |
| Working tree clean | PASS |
| Protected | false |

## Repo-Inventar

| Aspekt | Wert |
|--------|------|
| Stack | Astro 5.18.0 + Starlight 0.37.6 |
| Package Manager | pnpm 10.30.3 (enforced via packageManager) |
| TypeScript | 5.9.3 (strict mode) |
| Node (CI) | 22 |
| Locales | EN (root), DE |

## Seiten-/Slug-Struktur (main-Stand)

| Sektion | Seiten | Slugs |
|---------|--------|-------|
| Overview | 1 | overview |
| Architecture | 4 | architecture/{matrix,shards,artifacts,ems} |
| Governance | 5 | governance/{pr-only,evidence,policy-gates,incident-response,secrets-management} |
| Compliance | 4 | compliance/{gdpr,eidas,mica,supply-chain} |
| Tooling | 7 (6 in Sidebar) | tooling/{dispatcher,agents,mission-control,health-checks,observability,ai-gateway,local-stack} |
| Token | 2 | token/{utility,non-custodial} |
| FAQ | 2 | faq/{general,token-disambiguation} |
| Project | 5 | roadmap, status, changelog, security, exports |
| Research | 1 (nicht in Sidebar) | research/permissionless-crypto-assets-2026-03 |
| Home | 1 | index (redirect) |

**Gesamt: 32 Content-Dateien, 30 Sidebar-Eintraege**

## Sidebar-Struktur (main)

8 Sektionen: Overview, Architecture, Governance, Compliance, Tooling, Token, FAQ, Project

**Strukturelle Luecken:**
- `tooling/local-stack.mdx` existiert, fehlt in Sidebar
- `research/permissionless-crypto-assets-2026-03.md` existiert, fehlt in Sidebar

## Build-/Test-Befehle

| Befehl | Zweck |
|--------|-------|
| `pnpm dev` | Dev-Server (4321 default) |
| `pnpm build` | astro check + astro build |
| `pnpm test` | 4 Suiten (structure, content, theme, security) |
| `pnpm ingest` | Deterministic ingest from SSID-open-core |

## Port-Annahmen

| Kontext | Port | Quelle |
|---------|------|--------|
| Kanonisch / Original | 4321 | Astro default |
| Workspace / Arbeitsstand | 4331 | CLAUDE.md |
| Production | N/A (GitHub Pages) | pages.yml |

**Port-Kollision:** KEINE

## Scope-/Pfad-/Config-Risiken

| Risiko | Status |
|--------|--------|
| Globale CLI-/Skill-/Provider-Dateien im Repo | KEINE |
| Absolute lokale Pfade in Content | KEINE (CLAUDE.md hat Dev-Tooling-Pfad, akzeptabel) |
| CSP | FEHLEND auf main — Medium-Fund |
| CLAUDE.md Stack-Angabe | FALSCH — sagt "Docusaurus" statt "Astro + Starlight" |
| EMS-Akronym | INKONSISTENT — architecture/ems.mdx vs tooling/mission-control.mdx |
| matrix.mdx Root-Namen | VERALTET — nicht-kanonischer Draft-Satz |
| Base-Path | OK — `process.env.NODE_ENV === 'production'` trennt sauber |
