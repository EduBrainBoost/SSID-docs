---
title: Local Stack Operations
description: Start, stop, and verify the SSID local development stack
---

# Local Stack Operations

## Prerequisites

- Node.js 20+, Python 3.12+, pnpm 9+
- All 5 repos cloned under `~/Documents/Github/`

## Port Matrix

| Service              | Port | Health URL                          |
|----------------------|------|-------------------------------------|
| EMS Portal Frontend  | 3000 | http://localhost:3000                |
| EMS Portal Backend   | 8000 | http://localhost:8000/api/health     |
| Legacy Website       | 3001 | http://localhost:3001                |
| CCT Docs             | 3002 | http://localhost:3002                |
| Orchestrator API     | 3210 | http://localhost:3210/api/           |
| Orchestrator Web UI  | 5173 | http://localhost:5173                |
| SSID-docs            | 4321 | http://localhost:4321                |
| CCT Dashboard        | 4322 | http://localhost:4322                |

## Start Services

```bash
# EMS Backend
cd SSID-EMS && python -m uvicorn portal.backend.main:app --port 8000

# EMS Frontend
cd SSID-EMS/portal/frontend && pnpm dev --port 3000

# Orchestrator
cd SSID-orchestrator && pnpm dev

# Docs
cd SSID-docs && pnpm dev
```

## Health Checks

```bash
curl http://localhost:8000/api/health
curl http://localhost:3210/api/
```

## Port Conflicts

If a port is occupied, check with `netstat -ano | findstr :<PORT>` and terminate the conflicting process.

## Troubleshooting

- **CORS errors**: Ensure backend allows localhost origins
- **Cookie issues**: Use localhost not 127.0.0.1
- **Missing env**: Copy `.env.example` to `.env` in each repo
