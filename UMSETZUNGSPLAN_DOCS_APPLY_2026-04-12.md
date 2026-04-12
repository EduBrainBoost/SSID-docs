# Umsetzungsplan: SSID-docs APPLY-Validierung

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Pfad:** C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID-docs
**Port (G-Zone):** 4331
**Stack:** Astro 5.18 + Starlight 0.37.6 (SSG, MDX, I18N EN+DE)

## Zielzustand

SSID-docs baut fehlerfrei, dient statisch auf Port 4331, besteht alle Unit-Tests
und Stresstests (Build-Reproduzierbarkeit, Route-Vollständigkeit, CSP, Concurrent Load).

## Schritte

| Nr | Aktion | Ziel | Dateien | Port | Abhängigkeit |
|----|--------|------|---------|------|--------------|
| 1 | pnpm install --frozen-lockfile | deps validiert | pnpm-lock.yaml | - | - |
| 2 | pnpm run build (astro check + astro build) | dist/ fehlerfrei | dist/** | - | Nr 1 |
| 3 | pnpm run test | 6/6 Unit-Tests PASS | tests/*.test.mjs | - | Nr 2 |
| 4 | pnpm preview --port 4331 | Site auf 4331 erreichbar | - | 4331 | Nr 2 |
| 5 | Health-Check: GET / auf 4331 | HTTP 200/301 | - | 4331 | Nr 4 |
| 6 | Stresstests erstellen | Reproduzierbare Testdateien | tests/stress-*.test.mjs | - | Nr 2 |
| 7 | Stresstests gegen Live-Server | Metriken + Logs | - | 4331 | Nr 4+6 |
| 8 | Fehler fixen (Phase 6) | Null Fehler | je nach Befund | - | Nr 7 |
| 9 | Abschlussbericht | Vollständige Dokumentation | - | - | Nr 8 |

## Erfolgskriterien

- [x] Build: exit code 0, dist/ mit HTML-Dateien
- [x] Tests: 6/6 PASS
- [x] Server: Port 4331 erreichbar, HTTP 200/301
- [x] Stresstests: alle PASS
- [x] Null offene Fehler

## Rollback

- Bei Build-Fehler: `git checkout -- .` auf SSID-docs
- Bei Port-Konflikt: `npx kill-port 4331` dann Neustart
- Bei Dependency-Fehler: `rm -rf node_modules && pnpm install`
