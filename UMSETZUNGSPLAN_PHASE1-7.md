# SSID-docs Umsetzungsplan — Phase 1-7 Vollvalidierung

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Pfad:** C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID-docs
**Port (G-Zone):** 4331
**Stack:** Astro 5.18 + Starlight 0.37 + pnpm 10

---

## 1. Zielzustand

- SSID-docs baut fehlerfrei (`astro check && astro build`)
- Dev-Server laeuft auf Port 4331 (G-Zone)
- Alle 58 Sidebar-Routen liefern HTTP 200
- Bestehende Tests (structure, content, theme, security, sidebar-completeness, build-stress, route-stress) PASS
- Stresstests gegen laufenden Stack ausgefuehrt, Metriken dokumentiert
- Abschlussbericht bei fehlerfreiem Durchlauf

## 2. Dateien und Abhaengigkeiten

| Artefakt | Pfad | Status |
|---|---|---|
| Astro Config | astro.config.mjs | vorhanden, 58 Sidebar-Slugs |
| Content Config | src/content.config.ts | vorhanden |
| Content (EN) | src/content/docs/*.mdx | 58 Dateien |
| Content (DE) | src/content/docs/de/ | vorhanden |
| Logos | src/assets/ssid-logo-{light,dark}.svg | vorhanden |
| CSS | src/styles/cyberpunk.css | vorhanden |
| Tests | tests/*.test.mjs, tests/run.mjs | 7 Test-Dateien |
| Package | package.json | pnpm, Astro 5.18, Starlight 0.37 |
| Dependencies | node_modules/ | installiert |
| Build Output | dist/ | vorhanden (vorheriger Build) |

## 3. Ports

| Service | G-Zone | C-Zone |
|---|---|---|
| SSID-docs Dev | 4331 | 4321 |

## 4. Ausfuehrungsschritte

### Phase 3 — Betriebsbereite Vollintegration
1. `pnpm run build` — Astro check + build
2. `pnpm run dev` — Dev-Server starten auf Port 4331
3. Health-Check: HTTP GET http://localhost:4331/SSID-docs/ -> 200
4. Stichproben-Routen pruefen (mind. 10 Sidebar-Slugs)

### Phase 4 — Stresstests erstellen
1. Vorhandene Tests pruefen (7 Dateien)
2. Fehlende Abdeckung identifizieren
3. Ggf. erweitern: Build-Reproduzierbarkeit, Route-Vollstaendigkeit, Locale-Check

### Phase 5 — Stresstests im Livebetrieb
1. `pnpm run test` — alle Tests ausfuehren
2. Route-Stress gegen laufenden Dev-Server
3. Build-Stress: 3x konsekutiver Build, Timing
4. Ergebnisse dokumentieren

### Phase 6 — Sofort-Fix
- Jeder Fehler aus Phase 3/4/5 wird sofort gefixt
- Nach Fix: betroffene Phase erneut durchlaufen

### Phase 7 — Abschlussbericht
- Nur bei fehlerfreiem Durchlauf aller Phasen
- Inhalt: was gebaut, wo, wie gestartet, Testergebnisse, Fehler+Fixes, Restrisiken

## 5. Rollback

- `git stash` vor jeder Aenderung
- Bei kritischem Fehler: `git checkout -- .` auf SSID-docs
- node_modules via `pnpm install` reproduzierbar

## 6. Erfolgskriterien

- [ ] Build PASS (exit 0)
- [ ] Dev-Server HTTP 200 auf Port 4331
- [ ] Alle Sidebar-Routen HTTP 200
- [ ] Alle Tests PASS
- [ ] Stresstests dokumentiert
- [ ] Keine offenen Fehler
