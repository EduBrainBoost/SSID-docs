---
title: Local Stack Operations
description: Starten, stoppen und überprüfen Sie den SSID Local Development Stack
---

# Local Stack Operations

## Voraussetzungen

- Node.js 20+, Python 3.12+, pnpm 9+
- Alle 5 Repos geklont unter `~/Documents/Github/`

## Port Matrix (G-Workspace)

**⚠️ Dies sind G-Workspace (Development) Ports. Für die vollständige Referenz einschließlich C-Canonical (Production) Ports siehe [Port Matrix (Aktuell)](../deployments/ports-matrix-current).**

| Dienst              | Port | Health URL                          |
|----------------------|------|-------------------------------------|
| EMS Portal Frontend  | 3100 | http://localhost:3100                |
| EMS Portal Backend   | 8100 | http://localhost:8100/health     |
| SSID-docs            | 4331 | http://localhost:4331                |
| Orchestrator API     | 3310 | http://localhost:3310/health           |
| Orchestrator Web UI  | 5273 | http://localhost:5273                |

## Dienste starten

```bash
# EMS Backend (G-Port 8100)
cd SSID-EMS && python -m uvicorn portal.backend.main:app --port 8100

# EMS Frontend (G-Port 3100)
cd SSID-EMS/portal/frontend && pnpm dev --port 3100

# Orchestrator (G-Ports: API 3310, UI 5273)
cd SSID-orchestrator && pnpm dev

# Docs (G-Port 4331)
cd SSID-docs && pnpm dev
```

## Health Checks

```bash
curl http://localhost:8100/health
curl http://localhost:3310/health
curl http://localhost:4331
```

## Port-Konflikte

Wenn ein Port belegt ist, überprüfen Sie mit `netstat -ano | findstr :<PORT>` und terminieren Sie den konflikt verursachenden Prozess.

## Workspace-Konfiguration

Der lokale Stack läuft in der **G-Workspace**-Umgebung. Alle 5 Repositories müssen im selben Workspace-Verzeichnis geklont werden, um die ordnungsgemäße lokale Entwicklung zu gewährleisten:
- SSID (privat, Quelle der Wahrheit)
- SSID-EMS (privat, Kontrollplane)
- SSID-orchestrator (privat, Runtime-Engine)
- SSID-open-core (öffentlich, exportiertes SDK)
- SSID-docs (öffentlich, diese Dokumentations-Site)

## Fehlerbehebung

- **CORS-Fehler**: Stellen Sie sicher, dass das Backend Localhost-Ursprünge zulässt
- **Cookie-Probleme**: Verwenden Sie `localhost` nicht `127.0.0.1`
- **Fehlende env**: Kopieren Sie `.env.example` zu `.env` in jedem Repository
- **Port-Konflikte**: Stellen Sie sicher, dass alle Dienste die richtigen G-Ports verwenden (3100, 8100, 3310, 5273, 4331)
