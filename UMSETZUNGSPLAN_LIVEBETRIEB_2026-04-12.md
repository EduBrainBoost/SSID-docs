# Umsetzungsplan: SSID-docs Livebetrieb-Validierung

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Pfad:** C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID-docs
**Port:** 4331 (G-Zone)
**Stack:** Astro 5.18 + Starlight 0.37.6
**Branch:** repair/pr49-hard-blockers

---

## Zielzustand

SSID-docs läuft betriebsbereit auf Port 4331 mit:
- Fehlerfreier Build (119 Seiten, Pagefind-Index, Sitemap)
- Dev-Server erreichbar auf http://localhost:4331
- Alle Sidebar-Routen auflösbar (keine 404)
- I18N (EN/DE) funktional
- Stresstests reproduzierbar als Code im Repo

---

## Schritt-für-Schritt

### 1. Build-Validierung (Phase 1 — erledigt)
- [x] `astro build` fehlerfrei → 119 Seiten, 9.05s
- [x] Pagefind-Index gebaut (719ms)
- [x] Sitemap generiert

### 2. Dev-Server Start (Phase 3)
- Kommando: `pnpm dev` (= `astro dev --port 4331`)
- Erfolgskriterium: HTTP 200 auf http://localhost:4331/SSID-docs/
- Rollback: `Ctrl+C` beendet Server

### 3. Route-Validierung (Phase 3)
- Alle 59 EN-Sidebar-Slugs per HTTP GET prüfen → HTTP 200
- DE-Locale-Routen stichprobenartig prüfen
- Erfolgskriterium: 0 Routen mit HTTP 404

### 4. Stresstests erstellen (Phase 4)
- `tests/build-stress.test.mjs` — Build-Determinismus, Output-Zählung
- `tests/route-stress.test.mjs` — Alle Sidebar-Routen gegen laufenden Server
- `tests/integration-stress.test.mjs` — Pagefind, Sitemap, CSP-Header
- Erfolgskriterium: Tests als lauffähiger Code im Repo

### 5. Stresstests ausführen (Phase 5)
- Server starten → Tests gegen localhost:4331 ausführen
- Metriken: Antwortzeiten, Status-Codes, Fehlerrate
- Erfolgskriterium: 100% PASS

### 6. Sofort-Fix (Phase 6)
- Jeder Fehler aus Phase 3/4/5 wird sofort gefixt
- Nach Fix: betroffene Phase wiederholen
- Kein "notiert", kein Ticket

### 7. Abschlussbericht (Phase 7)
- Nur bei fehlerfreiem Durchlauf aller Phasen

---

## Abhängigkeiten
- Node.js + pnpm installiert
- node_modules vorhanden (pnpm-lock.yaml aktuell)
- Kein externer Service-Dependency

## Ports
- 4331: SSID-docs Dev-Server (G-Zone, einziger Port)

## Rollback
- Dev-Server: Ctrl+C
- Build-Artefakte: `rm -rf dist/`
- Keine destruktiven Operationen geplant
