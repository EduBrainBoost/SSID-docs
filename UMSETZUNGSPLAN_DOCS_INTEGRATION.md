# SSID-docs Vollintegration — Umsetzungsplan

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Port:** 4331 (G-Workspace)
**Stack:** Astro 5.18 + Starlight 0.37.6
**Branch:** repair/pr49-hard-blockers

## Zielzustand

1. SSID-docs Dev-Server läuft auf Port 4331
2. Build produziert 119+ fehlerfreie HTML-Seiten
3. Health-Endpoint `/SSID-docs/` liefert HTTP 200
4. Pagefind-Suche funktioniert
5. I18N-Fallback EN→DE aktiv
6. Stresstests (Build-Stress, Route-Stress, Locale-Stress, Sidebar-Completeness) PASS

## Dateien

| Datei | Zweck |
|---|---|
| `astro.config.mjs` | Hauptkonfig, Port 4331, Sidebar, I18N |
| `package.json` | Scripts: dev, build, test |
| `src/content/docs/**/*.mdx` | 60 Content-Dateien |
| `src/styles/cyberpunk.css` | Custom-Theme |
| `src/assets/*.svg` | Logos |
| `tests/build-stress.test.mjs` | Build-Stresstest |
| `tests/route-stress.test.mjs` | Route-Validierung gegen Dev-Server |
| `tests/locale.test.mjs` | I18N-Route-Test |
| `tests/sidebar-completeness.test.mjs` | Sidebar↔Content Abgleich |

## Ports

- Dev-Server: 4331 (G-Workspace gemäß Port-Policy)
- Keine anderen Ports betroffen

## Abhängigkeiten

- Node.js ≥18 (vorhanden: v25.8.2)
- pnpm (über node_modules/.pnpm vorhanden)
- Keine externen Services benötigt (statische Docs-Site)

## Rollback

- `git checkout -- .` auf Branch repair/pr49-hard-blockers
- Keine DB, keine externen State-Änderungen

## Erfolgskriterien

1. `astro build` → 0 Fehler, 119+ Seiten
2. `astro dev --port 4331` → HTTP 200 auf localhost:4331/SSID-docs/
3. Alle 4 Stresstests PASS
4. Keine offenen TODOs oder Platzhalter
