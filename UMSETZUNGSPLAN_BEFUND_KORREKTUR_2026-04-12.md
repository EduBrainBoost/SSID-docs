# Umsetzungsplan: SSID-docs Befund-Korrektur & Vollvalidierung

**Datum**: 2026-04-12
**Auftrag**: ChatGPT-Befund validieren, SSID-docs Betriebsbereitschaft nachweisen
**Repo**: SSID-docs @ C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID-docs
**Port**: 4331 (G-Zone, per Port-Matrix)

---

## 1. Befund-Korrektur

ChatGPT meldete folgende Artefakte als fehlend — **alle existieren**:

| Angeblich fehlend | IST-Zustand | Pfad |
|---|---|---|
| SSID-docs Verzeichnis | VORHANDEN | Github/SSID-docs/ |
| package.json | VORHANDEN | SSID-docs/package.json |
| pnpm-lock.yaml | VORHANDEN | SSID-docs/pnpm-lock.yaml |
| astro.config.mjs | VORHANDEN | SSID-docs/astro.config.mjs |
| docs_ci.yml | VORHANDEN | .github/workflows/docs_ci.yml |
| pages.yml | VORHANDEN | .github/workflows/pages.yml |
| integrator_merge_checks.yml | VORHANDEN | .github/workflows/integrator_merge_checks.yml |
| 05_documentation/site | VORHANDEN | SSID/05_documentation/site/ |

**Ursache**: ChatGPT lief in isoliertem Container ohne Zugriff auf lokalen Workspace.

## 2. Validierungsschritte

| Nr | Aktion | Zielzustand | Erfolgskriterium |
|---|---|---|---|
| 2.1 | pnpm install --frozen-lockfile | Dependencies installiert | Exit 0, keine Fehler |
| 2.2 | pnpm build (astro check + astro build) | dist/ erzeugt | Exit 0, dist/index.html vorhanden |
| 2.3 | pnpm dev --port 4331 | Dev-Server läuft | HTTP 200 auf localhost:4331 |
| 2.4 | pnpm test | Alle Tests PASS | Exit 0, keine Failures |
| 2.5 | Stresstest-Suite ausführen | Robustheit validiert | Alle Stress-Tests PASS |
| 2.6 | Sidebar-Vollständigkeit | Alle Sidebar-Slugs auflösbar | sidebar-completeness.test PASS |
| 2.7 | CSP-Header-Validierung | CSP in HTML-Output | stress-csp.test PASS |
| 2.8 | I18N-Validierung | DE-Locale funktional | locale.test PASS |

## 3. Abhängigkeiten

- Node.js >= 22
- pnpm >= 10
- Astro 5.x + Starlight 0.37.x

## 4. Rollback

Kein destruktiver Eingriff geplant. Bei Build-Fehler: Fix in Phase 6, kein Rollback nötig.

## 5. Ports

- Dev-Server: 4331 (G-Zone, SSID-docs per Port-Matrix)
- Keine anderen Ports betroffen
