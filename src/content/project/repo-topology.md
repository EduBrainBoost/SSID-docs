---
title: Repository Topology
description: Overview of the 5-repository system structure and boundaries
---

# Repository Topology

## System Overview

The SSID project follows a strict 5-repository architecture based on Open-Core principles:

```
┌─────────────────────────────────────────────────────────┐
│                    SSID System                          │
├─────────────────────────────────────────────────────────┤
│  ssid-docs      → Public Open-Core Documentation        │
│  ssid-core      → Public Open-Core Code                 │
│  ssid-orchestrator → Public Orchestrator Interface      │
│  ssid-ems       → Private EMS (internal)                │
│  ssid-system    → Private System/Level-3 (internal)     │
└─────────────────────────────────────────────────────────┘
```

## Repository Boundaries

### Public Repositories (Open-Core)

| Repository | Visibility | Purpose |
|------------|------------|---------|
| `ssid-docs` | Public | Documentation and architecture |
| `ssid-core` | Public | Core open-source components |
| `ssid-orchestrator` | Public | Orchestrator interfaces |

### Private Repositories

| Repository | Visibility | Purpose |
|------------|------------|---------|
| `ssid-ems` | Private | Internal EMS operations |
| `ssid-system` | Private | Level-3 SAFE-FIX details |

## Boundary Rules

:::caution
**No private content in public repositories**

The following must NEVER appear in public repos:
- Internal paths (`/mnt/`, `/var/`, `/etc/`)
- Secrets, tokens, or keys
- Level-3 SAFE-FIX details
- Internal hostnames
- Private deployment configurations
:::

## Mirror Policy

- Public repositories are mirrored to GitHub
- Private content is filtered during mirroring
- SAFE-FIX policy applies: `no_delete`, `move_to_target`, `rewrite_if_missing`

## Evidence Requirements

All claims require public evidence:
- Test results
- Deployment logs
- Audit reports
- Public contract addresses (verified)
