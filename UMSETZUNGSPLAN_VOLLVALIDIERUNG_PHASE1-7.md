# Umsetzungsplan: SSID-docs Vollvalidierung Phase 1–7

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Branch:** repair/pr49-hard-blockers
**Port:** 4331 (G-Zone)

## Ist-Zustand (verifiziert)

| Komponente | Status |
|---|---|
| .git | VORHANDEN (Branch repair/pr49-hard-blockers) |
| astro.config.mjs | VORHANDEN (Starlight, Port 4331, i18n en/de) |
| src/content/docs | 66 Dateien (mdx/md), alle Sidebar-Slugs gedeckt |
| src/assets | Logos (light/dark SVG) vorhanden |
| src/styles | cyberpunk.css vorhanden |
| package.json | Astro 5.18+, Starlight 0.37+ |
| Dev-Server Port 4331 | LISTENING, HTTP 200 |
| Tests (Basis) | 6 Suites in run.mjs |
| Tests (Stress) | 3 Standalone: build, integration, route |
| dist/ | Build-Output vorhanden |
| I18N (de/) | 6 deutsche Dateien |

## Zielzustand

- Dev-Server auf Port 4331 betriebsbereit, alle Routen HTTP 200
- Alle 6 Basis-Tests PASS
- Alle 3 Stress-Tests PASS
- Build fehlerfrei
- Keine offenen Fehler

## Schritte

| # | Aktion | Dateien | Erfolgskriterium |
|---|---|---|---|
| 1 | Basis-Testsuite ausführen | tests/run.mjs | 6/6 PASS |
| 2 | Dev-Server Health prüfen | localhost:4331/SSID-docs/ | HTTP 200 |
| 3 | Build-Stresstest | tests/build-stress.test.mjs | Build OK, dist/ valide |
| 4 | Integration-Stresstest | tests/integration-stress.test.mjs | Content, CSP, i18n OK |
| 5 | Route-Stresstest | tests/route-stress.test.mjs | Alle Routen HTTP 200 |
| 6 | Sofort-Fix bei Fehlern | Betroffene Dateien | Fehler = 0 |
| 7 | Abschlussbericht | Inline | Vollständig |

## Abhängigkeiten

- Node.js / pnpm installiert
- Port 4331 frei (G-Zone)
- Kein Zugriff auf kanonische Zone erforderlich

## Rollback

- `git stash` für lokale Änderungen
- `git checkout -- .` für Config-Revert
- Kein destructive write ohne Evidence
