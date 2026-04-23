---
title: Local Stack
description: Local development environment configuration and verification
---

# Local Stack

## Overview

The local development stack provides a self-contained environment for development and testing.

## Local Ports

```
┌─────────────────────────────────────────────────────────┐
│                  Local Services                         │
├─────────────────────────────────────────────────────────┤
│  Port 3100  → SSID API (local)                          │
│  Port 3101  → Documentation (local)                   │
│  Port 3310  → Database (local)                        │
│  Port 5273  → Metrics endpoint                          │
│  Port 4331  → Orchestrator local                        │
│  Port 4332  → EMS local                                 │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Node.js >= 20.0.0
- pnpm >= 9.0.0

### Setup

```bash
# Clone repository
git clone https://github.com/ssid-dev/ssid-docs.git
cd ssid-docs

# Install dependencies
pnpm install

# Start local development
pnpm dev
```

## Verification Steps

### Health Check

```bash
# Check API health
curl http://localhost:3100/health

# Expected response:
# {"status": "healthy", "environment": "local"}
```

### Build Verification

```bash
# Build the project
pnpm build

# Verify output
ls -la dist/
```

## Local-Only Scope

:::caution
The local stack is **development-only**:
- No production data
- No production credentials
- Simulated blockchain state
- In-memory databases
:::

## Testing

```bash
# Run unit tests
pnpm test

# Run with coverage
pnpm test:coverage
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Check `lsof -i :3100` and kill process |
| Build fails | Clear `.astro/` cache and retry |
| Dependencies outdated | Run `pnpm update` |
