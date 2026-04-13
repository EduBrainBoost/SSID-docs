---
title: Local Stack Operations
description: Start, stop, and verify the SSID local development stack
---

# Local Stack Operations

## Prerequisites

- Node.js 20+, Python 3.12+, pnpm 9+
- All 5 repos cloned under `~/Documents/Github/`

## Port Matrix (G-Workspace)

**⚠️ These are G-workspace (development) ports. For complete reference including C-canonical (production) ports, see [Port Matrix (Current)](../deployments/ports-matrix-current).**

| Service              | Port | Health URL                          |
|----------------------|------|-------------------------------------|
| EMS Portal Frontend  | 3100 | http://localhost:3100                |
| EMS Portal Backend   | 8100 | http://localhost:8100/health     |
| SSID-docs            | 4331 | http://localhost:4331                |
| Orchestrator API     | 3310 | http://localhost:3310/health           |
| Orchestrator Web UI  | 5273 | http://localhost:5273                |

## Start Services

```bash
# EMS Backend (G-port 8100)
cd SSID-EMS && python -m uvicorn portal.backend.main:app --port 8100

# EMS Frontend (G-port 3100)
cd SSID-EMS/portal/frontend && pnpm dev --port 3100

# Orchestrator (G-ports: API 3310, UI 5273)
cd SSID-orchestrator && pnpm dev

# Docs (G-port 4331)
cd SSID-docs && pnpm dev
```

## Health Checks

```bash
curl http://localhost:8100/health
curl http://localhost:3310/health
curl http://localhost:4331
```

## Port Conflicts

If a port is occupied, check with `netstat -ano | findstr :<PORT>` and terminate the conflicting process.

## Workspace Configuration

The local stack runs in the **G-workspace** environment under:
```
C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\
```

All 5 repositories must be cloned here for proper local development:
- SSID (private, source of truth)
- SSID-EMS (private, control plane)
- SSID-orchestrator (private, runtime engine)
- SSID-open-core (public, exported SDK)
- SSID-docs (public, this documentation site)

## Troubleshooting

- **CORS errors**: Ensure backend allows localhost origins
- **Cookie issues**: Use `localhost` not `127.0.0.1`
- **Missing env**: Copy `.env.example` to `.env` in each repo
- **Port conflicts**: Verify all services use correct G-ports (3100, 8100, 3310, 5273, 4331)
