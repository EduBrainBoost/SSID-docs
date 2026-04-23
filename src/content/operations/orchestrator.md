---
title: Orchestrator
description: Public Orchestrator interfaces and operational feed
---

# Orchestrator

## Overview

The Orchestrator provides **public interfaces** for workflow management and operational feeds. Internal control plane is not documented here.

## Public Interfaces

### REST API

```
Base URL: https://api.ssid.io/orchestrator
Version: v1
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/workflows` | List public workflows |
| GET | `/workflows/{id}` | Get workflow details |
| POST | `/workflows/{id}/trigger` | Trigger public workflow |
| GET | `/status` | Orchestrator status |
| GET | `/metrics` | Public metrics |

### Example Request

```bash
curl https://api.ssid.io/orchestrator/v1/status \
  -H "Authorization: Bearer $PUBLIC_TOKEN"
```

### Example Response

```json
{
  "status": "healthy",
  "version": "2.1.0",
  "workflows": {
    "active": 3,
    "completed": 150
  },
  "evidence": {
    "snapshot_date": "2024-04-12T20:00:00Z",
    "source": "public-orchestrator"
  }
}
```

## Operational Feed

### Public Events

The Orchestrator publishes sanitized operational events:

| Event Type | Description |
|------------|-------------|
| `workflow.started` | Workflow execution started |
| `workflow.completed` | Workflow execution completed |
| `workflow.failed` | Workflow execution failed |
| `system.heartbeat` | Orchestrator health check |

### Event Schema

```json
{
  "event": "workflow.started",
  "timestamp": "2024-04-12T20:00:00Z",
  "workflow": {
    "id": "wf_12345",
    "name": "public-test-deployment",
    "trigger": "manual"
  },
  "metadata": {
    "public_only": true
  }
}
```

:::warning
**No Control Plane Details**

Internal control plane operations, configuration, and Level-3 details are intentionally omitted from this public documentation.
:::

## Verification Commands

```bash
# Check orchestrator status
curl https://api.ssid.io/orchestrator/v1/status

# List public workflows
curl https://api.ssid.io/orchestrator/v1/workflows

# Subscribe to public events (if available)
wscat -c wss://api.ssid.io/orchestrator/events
```
