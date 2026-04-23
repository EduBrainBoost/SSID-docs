---
title: Local Network
description: Local-only network status and boundaries
---

# Local Network

## Overview

The local network is a **development-only** environment running on localhost with no external connectivity.

## Status

```
┌─────────────────────────────────────────────────────────┐
│                   LOCAL STATUS                          │
├─────────────────────────────────────────────────────────┤
│  Environment:    Local Development                      │
│  Network:        Isolated (localhost only)              │
│  State:          Active                                 │
│  Last Updated:   2024-04-12                             │
│  Evidence:       Local tests passing                    │
└─────────────────────────────────────────────────────────┘
```

## Boundaries

:::danger
**Local-Only Restriction**

The local network is strictly isolated:
- ❌ No external network access
- ❌ No production data
- ❌ No real blockchain state
- ❌ No internal service connections
- ✅ Development only
- ✅ Simulated state
- ✅ Local testing
:::

## Configuration

### Default Ports

| Service | Port | Purpose |
|---------|------|---------|
| API | 3100 | Local API endpoint |
| Docs | 3101 | Local documentation |
| Database | 3310 | Local database |
| Metrics | 5273 | Local metrics |
| Orchestrator | 4331 | Local orchestrator |
| EMS | 4332 | Local EMS |

### CORS Settings

```javascript
// Local only - no external origins
const allowedOrigins = [
  'http://localhost:3100',
  'http://localhost:3101',
  'http://127.0.0.1:3100'
];
```

## Verification

```bash
# Test local API
curl http://localhost:3100/health

# Expected response:
# {"status": "healthy", "environment": "local"}

# Test local documentation
curl http://localhost:3101/
```

## Limitations

| Feature | Local | Testnet | Mainnet |
|---------|-------|---------|---------|
| Real blockchain | ❌ | ✅ | ✅ |
| External API calls | ❌ | ✅ | ✅ |
| Production data | ❌ | Test data | Live data |
| Public endpoints | ❌ | ✅ | ✅ |
| Wallet integration | Mock | Test wallets | Real wallets |

## Evidence Requirements

All local-only claims must be validated through:
- Local test results
- Mock data verification
- No external dependency assertions
