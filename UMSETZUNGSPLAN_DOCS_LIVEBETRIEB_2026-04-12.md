# Umsetzungsplan: SSID-docs Vollvalidierung & Livebetrieb

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Pfad:** C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID-docs
**Branch:** repair/pr49-hard-blockers
**Port:** 4331 (G-Zone)

## Zielzustand

SSID-docs Astro/Starlight-Site:
- Build fehlerfrei (`astro check && astro build`)
- Dev-Server auf Port 4331 erreichbar
- Alle 65 Content-Dateien korrekt gerendert
- I18N (en/de) funktional
- Sidebar vollständig (alle Slugs resolven)
- Bestehende Tests PASS
- Stresstests erstellt und PASS

## Schritte

| Nr | Aktion | Zieldatei(en) | Port | Abhängigkeit | Erfolgskriterium |
|----|--------|---------------|------|-------------|-----------------|
| 1 | pnpm install sicherstellen | node_modules/ | - | - | Exit 0, keine peer-dep-Fehler |
| 2 | astro check | - | - | 1 | Exit 0, keine TS-Fehler |
| 3 | astro build | dist/ | - | 2 | Exit 0, dist/ erzeugt mit HTML |
| 4 | Dev-Server starten | - | 4331 | 3 | HTTP 200 auf localhost:4331 |
| 5 | Health-Check / Route-Check | - | 4331 | 4 | / und /SSID-docs/ erreichbar |
| 6 | Bestehende Tests ausführen | tests/*.mjs | - | 3 | Alle PASS |
| 7 | Stresstests erstellen | tests/stress-*.test.mjs | - | 3 | Dateien existieren |
| 8 | Stresstests ausführen | - | 4331 | 4,7 | Alle PASS |
| 9 | Sofort-Fix bei Fehlern | je nach Befund | - | 6,8 | Betroffene Phase grün |

## Rollback

- Git: `git stash` oder `git checkout -- .` für lokale Änderungen
- Dependencies: `rm -rf node_modules && pnpm install`
- Keine destruktiven Operationen geplant

## Dateien die geändert/erstellt werden

- `tests/stress-build.test.mjs` (neu) — Build-Stresstest
- `tests/stress-routes.test.mjs` (neu) — Route-Vollständigkeitstest
- `tests/stress-i18n.test.mjs` (neu) — I18N-Validierung
- `tests/stress-sidebar.test.mjs` (neu) — Sidebar-Slug-Resolution
- Dieser Umsetzungsplan (neu)

## Risiken

- Windows-spezifische Pfadprobleme bei Astro
- Sharp-Binary-Kompatibilität
- Mögliche fehlende Content-Dateien für Sidebar-Slugs
