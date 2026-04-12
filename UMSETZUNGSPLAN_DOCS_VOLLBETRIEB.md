# Umsetzungsplan: SSID-docs Vollbetrieb

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Branch:** repair/pr49-hard-blockers
**Port:** 4331 (G-Zone)

## Ist-Zustand

| Prueffeld | Status |
|---|---|
| Git-Checkout | OK, Branch repair/pr49-hard-blockers |
| Remote | origin = github.com/EduBrainBoost/SSID-docs.git |
| astro.config.mjs | OK, Port 4331, Starlight, 2 Locales (en, de) |
| Content (en) | 60 .mdx/.md Dateien — alle Sidebar-Slugs vorhanden |
| Content (de) | 6 Dateien — Teilabdeckung |
| Assets | ssid-logo-light.svg, ssid-logo-dark.svg vorhanden |
| CSS | cyberpunk.css vorhanden |
| node_modules | FEHLT — pnpm install erforderlich |
| Tests | 10 Testdateien vorhanden |
| Build-Output | dist/ vorhanden (veraltet) |

## Schritte

### Schritt 1: Abhaengigkeiten installieren
- Ziel: node_modules vollstaendig via pnpm
- Befehl: `pnpm install`
- Erfolgskriterium: Exit-Code 0, node_modules/.package-lock.json vorhanden

### Schritt 2: Build ausfuehren
- Ziel: Statischer Build in dist/
- Befehl: `pnpm run build`
- Erfolgskriterium: Exit-Code 0, dist/ aktualisiert, keine Fehler

### Schritt 3: Dev-Server starten
- Ziel: Astro Dev-Server auf Port 4331
- Befehl: `pnpm run dev`
- Erfolgskriterium: HTTP 200 auf http://localhost:4331/SSID-docs/

### Schritt 4: Health-Check
- Ziel: Startseite und Unterseiten erreichbar
- Pruefung: curl auf /, /SSID-docs/overview/, /SSID-docs/architecture/roots/
- Erfolgskriterium: HTTP 200, HTML-Content

### Schritt 5: Vorhandene Tests ausfuehren
- Ziel: Alle 10 Testdateien gruen
- Befehl: `pnpm test`
- Erfolgskriterium: Alle Tests PASS

### Schritt 6: Stresstests erstellen und ausfuehren
- Ziel: Build-Stress, Route-Stress, Sidebar-Completeness, Locale-Tests
- Dateien: tests/build-stress.test.mjs, tests/route-stress.test.mjs, tests/sidebar-completeness.test.mjs, tests/locale.test.mjs, tests/integration-stress.test.mjs
- Erfolgskriterium: Alle Stresstests PASS

## Abhaengigkeiten
- pnpm >= 10
- Node.js (vorinstalliert)

## Rollback
- `rm -rf node_modules dist`
- `git checkout -- astro.config.mjs tests/run.mjs`

## Ports
- SSID-docs Dev-Server: 4331 (G-Zone, gemaess Port-Policy)

## Restrisiken
- Deutsche Locale hat nur 6 von 60 Seiten — kein Blocker fuer Betrieb
- Branch ist repair/pr49-hard-blockers, nicht main
