# SSID-docs CSP & Base-Path Report

**Date:** 2026-03-23
**Branch:** fix/ssid-docs-baseline-sot-ia-csp-lock

## CSP-Implementierung

### Methode
Meta-Tag via Starlight `head` Config in `astro.config.mjs`.

### Directives

| Directive | Value | Begruendung |
|-----------|-------|-------------|
| default-src | 'self' | Kein externer Content |
| script-src | 'self' 'unsafe-inline' | Pagefind + Starlight benoetigten inline Scripts |
| style-src | 'self' 'unsafe-inline' | Starlight Theme inline Styles |
| img-src | 'self' data: | SVGs koennen data: URIs nutzen |
| connect-src | 'self' | Keine externen API-Calls in Production |
| font-src | 'self' | Nur self-hosted |
| frame-src | 'none' | Anti-Clickjacking |
| object-src | 'none' | Keine Plugins |
| base-uri | 'self' | Verhindert base-tag Injection |
| form-action | 'self' | Beschraenkt Form-Targets |

### Zusaetzliche Security-Header
- `Referrer-Policy: strict-origin-when-cross-origin` via meta-Tag

### Nicht adressierbar (Plattform-Limitation)
Folgende HTTP-only Headers koennen auf GitHub Pages NICHT gesetzt werden:
- `Strict-Transport-Security` (HSTS)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options`
- `Permissions-Policy`

Dies ist eine GitHub-Pages-Limitation, kein Repo-Problem. GitHub Pages setzt eigene HSTS-Header.

### Verifikation
- CSP meta-Tag im Build-Output (dist/overview/index.html): VORHANDEN
- Referrer-Policy meta-Tag: VORHANDEN

**Medium-Fund Status: GESCHLOSSEN** (soweit repo-lokal moeglich)

## Base-Path-Analyse

### Aktuelle Logik (astro.config.mjs Zeile 6)
```javascript
base: process.env.NODE_ENV === 'production' ? '/SSID-docs' : '/',
```

### Verhalten nach Kontext

| Kontext | NODE_ENV | Base Path | Status |
|---------|----------|-----------|--------|
| Production (GitHub Pages) | production | /SSID-docs | KORREKT |
| Local Dev (pnpm dev) | undefined | / | KORREKT |
| Workspace Dev (4331) | undefined | / | KORREKT |
| Preview (pnpm preview) | undefined | / | KORREKT |
| CI Build (pages.yml) | production | /SSID-docs | KORREKT |

### Regressionscheck
- Frueherer Fix (commit c0947f7): `fix(docs): use /SSID-docs base only in production` — NICHT REGRESSIERT
- Root-Redirect: public/index.html leitet auf /overview/ — INTAKT
- Assets: CSS, SVG-Logos korrekt geladen unter / (dev) und /SSID-docs (prod)

### Port-Trennung

| Port | Verwendung | Kollision |
|------|-----------|-----------|
| 4321 | Kanonischer Dev-Run | KEINE |
| 4331 | Workspace Dev-Run | KEINE |

**Base-Path Status: NICHT REGRESSIV**
