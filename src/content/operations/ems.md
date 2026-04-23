---
title: EMS Operations
description: Public-facing EMS operational documentation
---

# EMS Operations

## Overview

This document describes the **public-facing** EMS (Event Management System) operations. Internal EMS details remain in private repositories.

## Public EMS Interface

### Supported Operations

| Operation | Description | Endpoint |
|-----------|-------------|----------|
| Status Check | Get public system status | `GET /ems/status` |
| Metrics | Retrieve public metrics | `GET /ems/metrics` |
| Events | Public event stream | `WS /ems/events` |

### Response Format

```json
{
  "status": "operational",
  "timestamp": "2024-04-12T20:00:00Z",
  "environment": "testnet",
  "version": "1.2.3",
  "evidence": {
    "last_update": "2024-04-12T19:55:00Z",
    "source": "public-mirror"
  }
}
```

## Public API Limits

- Rate limit: 100 requests/minute
- Authentication: Public key only (no secrets)
- Response caching: 60 seconds

:::caution
**Internal Operations Not Documented**

The following are NOT in this public documentation:
- Internal control plane operations
- Private EMS configuration
- Level-3 SAFE-FIX procedures
- Internal hostnames or paths
:::

## Event Types (Public)

| Event | Description | Public |
|-------|-------------|--------|
| `system.status` | System status changes | ✅ Yes |
| `deployment.start` | Deployment initiated | ✅ Yes |
| `deployment.complete` | Deployment finished | ✅ Yes |
| `internal.config` | Configuration changes | ❌ No (private) |
| `internal.auth` | Authentication events | ❌ No (private) |

## Verification

```bash
# Check EMS status
curl https://api.ssid.io/ems/status

# Subscribe to public events
wscat -c wss://api.ssid.io/ems/events
```

## Support

For issues with the public EMS interface:
1. Check this documentation
2. Review public API reference
3. Open an issue in the public repository

Internal EMS issues are handled through private channels.
