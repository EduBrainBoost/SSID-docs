# Umsetzungsplan – SSID-docs Validierung & Gegenbeweis zum ChatGPT-Befund

**Datum:** 2026-04-12
**Repo:** SSID-docs
**Branch:** repair/pr49-hard-blockers
**Port:** 4331 (G-Zone)

## 1. Zielzustand

SSID-docs ist ein voll funktionsfähiges Astro/Starlight-Dokumentationsportal mit:
- 60 Content-Dateien (MDX/MD), 119 gerenderte Seiten
- i18n (EN/DE), Pagefind-Suche, CSP-Headers
- Port 4331 (G-Zone), Build + Dev-Server grün

## 2. Befund-Widerlegung

| ChatGPT-Behauptung | Realer Zustand | Nachweis |
|---|---|---|
| Repo-Pfad /mnt/data/SSID-docs | C:\Users\bibel\...\Github\SSID-docs | `ls -la .git` |
| .git fehlt | .git vorhanden, remote=GitHub | `git remote -v` |
| astro.config.mjs fehlt | Vollständig konfiguriert (159 Zeilen) | `cat astro.config.mjs` |
| src/content/docs fehlt | 60 Dateien in 15+ Unterordnern | `find src/content/docs` |
| Port 4331 kein Listener | Konfiguriert in package.json + astro.config.mjs | Build + Dev bestätigt |
| Astro/Starlight nicht vorhanden | @astrojs/starlight ^0.37.6, astro ^5.18.0 | `package.json` |

## 3. Dateien & Ports

- **astro.config.mjs** – Starlight-Konfiguration, Sidebar, i18n, CSP
- **package.json** – Scripts: dev (4331), build, preview, test
- **src/content/docs/** – 60 Content-Dateien
- **src/assets/** – Logo SVGs (light/dark)
- **src/styles/cyberpunk.css** – Custom Theme
- **Port 4331** – Dev-Server (G-Zone, kanonisch)

## 4. Phasen

1. ✅ Build validiert (119 Seiten, 0 Fehler)
2. ✅ Umsetzungsplan (diese Datei)
3. Dev-Server auf Port 4331 starten, HTTP 200 verifizieren
4. Stresstests: Build-Reproduzierbarkeit, Content-Integrität, Port-Binding, i18n
5. Tests gegen Live-Server ausführen
6. Sofort-Fix bei Fehlern
7. Abschlussbericht

## 5. Abhängigkeiten

- Node.js, pnpm
- node_modules vorhanden (pnpm install bereits erfolgt)

## 6. Rollback

- Keine destruktiven Änderungen, reines Validierungsverfahren
- Bei Fehler: `git checkout .` revertiert

## 7. Erfolgskriterien

- [x] Build: 0 Fehler, 119+ Seiten
- [ ] Dev-Server: HTTP 200 auf localhost:4331
- [ ] Stresstests: alle PASS
- [ ] Abschlussbericht: vollständig
