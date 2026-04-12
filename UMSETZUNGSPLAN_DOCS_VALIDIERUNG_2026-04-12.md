# Umsetzungsplan: SSID-docs Vollvalidierung

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Branch:** repair/pr49-hard-blockers
**Port:** 4331 (G-Zone)

## 1. Ist-Zustand

| Prüffeld | Status |
|---|---|
| astro.config.mjs | vorhanden, Starlight konfiguriert |
| package.json | Astro 5.18 + Starlight 0.37.6 |
| src/content/docs/ | 60 .mdx Dateien (EN + DE) |
| Sidebar-Slugs | 58/58 resolved |
| Build | 119 Seiten, Pagefind-Index, Sitemap |
| I18N (de) | Locale konfiguriert, DE-Inhalte vorhanden |
| Tests | 13 Testdateien vorhanden |
| Port | 4331 konfiguriert (server + dev-Script) |

## 2. Zielzustand

- Dev-Server läuft auf Port 4331
- Health-Endpunkt `/SSID-docs/` liefert HTTP 200
- Alle 119 Seiten erreichbar
- Pagefind-Suche funktioniert
- DE-Locale erreichbar unter /de/
- Stresstests bestehen: Concurrent-Load, Route-Coverage, CSP, Build-Reproduzierbarkeit

## 3. Schritte

| # | Aktion | Dateien | Erfolgskriterium |
|---|---|---|---|
| 3.1 | Dev-Server starten | - | Port 4331 antwortet |
| 3.2 | Health prüfen | - | HTTP 200 auf /SSID-docs/ |
| 3.3 | Route-Stichprobe | - | 10+ Routen HTTP 200 |
| 3.4 | DE-Locale prüfen | - | /SSID-docs/de/ HTTP 200 |
| 3.5 | Existing Tests ausführen | tests/*.mjs | Alle PASS |
| 3.6 | Stresstests erstellen | tests/stress-live-*.mjs | Dateien im Repo |
| 3.7 | Stresstests live ausführen | - | Alle PASS |
| 3.8 | Fehler fixen | bei Bedarf | Kein FAIL übrig |
| 3.9 | Abschlussbericht | - | Vollständiger Bericht |

## 4. Abhängigkeiten

- Node.js 25.x (vorhanden)
- pnpm via npx (Corepack defekt, Workaround: `npx pnpm`)
- Kein externer Service nötig (statische Docs-Site)

## 5. Rollback

- `git checkout -- .` revertiert alle Änderungen
- Keine Infrastruktur-Änderungen, kein Rollback nötig

## 6. Ports

- SSID-docs Dev-Server: **4331** (G-Zone, kanonisch)
- Keine anderen Ports betroffen
