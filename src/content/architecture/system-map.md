---
title: System Map
description: High-level architecture of the SSID/EMS/Orchestrator/Open-Core system
---

# System Map

## Architecture Overview

This documentation describes the public-facing architecture. Internal components and control-plane details are intentionally omitted.

```
┌────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│         (Web UI, CLI, API Consumers)                       │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                   Open-Core Layer                          │
│              (Public API & Interfaces)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Core API    │  │   Events     │  │   Auth       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                Orchestrator Layer                          │
│         (Public Orchestrator Interfaces)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Workflows   │  │   Metrics    │  │   Status     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Local Stack   │ │    Testnet      │ │ Mainnet (future)│
│   (Port 3100)   │ │    (Port 8100)  │ │  (TBD)          │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Component Descriptions

### Client Layer
- Web UI for end users
- CLI tools for developers
- Third-party API consumers

### Open-Core Layer
- **Core API**: Public REST/GraphQL endpoints
- **Events**: Event streaming and pub/sub
- **Auth**: Authentication and authorization (public interfaces only)

### Orchestrator Layer
- **Workflows**: Public workflow definitions
- **Metrics**: Aggregated public metrics
- **Status**: System status publication

### Network Layers
- **Local Stack**: Development environment (Port 3100)
- **Testnet**: Testing environment (Port 8100)
- **Mainnet**: Production (TBD - not live)

:::warning
**No Internal Details**

Internal control plane, EMS internals, and Level-3 operations are not documented here. These remain in private repositories.
:::

## Network Boundaries

| Environment | Port | Status | Evidence |
|-------------|------|--------|----------|
| Local | 3100 | Active | Local tests |
| Testnet | 8100 | Active | Test reports |
| Mainnet | TBD | **Not Live** | N/A |
