---
title: Testnet
description: Testnet artifacts, scopes, and verification rules
---

# Testnet

## Overview

The testnet provides a public testing environment with real blockchain connectivity but using test tokens and non-production configurations.

## Status

```
┌─────────────────────────────────────────────────────────┐
│                   TESTNET STATUS                        │
├─────────────────────────────────────────────────────────┤
│  Environment:    Public Testnet                         │
│  Network:        Connected (testnet.blockchain)       │
│  State:          Active                                 │
│  Last Updated:   2024-04-12                             │
│  Evidence:       Test reports, CI logs                  │
└─────────────────────────────────────────────────────────┘
```

## Testnet Configuration

### Endpoint

```
Base URL: https://testnet-api.ssid.io
Chain: testnet
Port: 8100
```

### Testnet Contracts

:::caution
**Verified Test Contracts Only**

All testnet contracts are clearly labeled as TEST. Mainnet contracts are TBD.

| Contract | Address | Type | Status |
|----------|---------|------|--------|
| SSID-Token-TEST | `0xTEST...1234` | ERC-20 | Active |
| SSID-Gateway-TEST | `0xTEST...5678` | Gateway | Active |
| SSID-Registry-TEST | `0xTEST...9012` | Registry | Active |
:::

## Test Scopes

### Allowed Testing

- ✅ Token transfers
- ✅ Smart contract interactions
- ✅ API endpoint testing
- ✅ Wallet integrations
- ✅ Performance testing

### Prohibited on Testnet

- ❌ Production data
- ❌ Real user funds
- ❌ Production credentials
- ❌ Mainnet claims

## Verification Rules

### Test Evidence Requirements

All testnet activity must include:

1. **Transaction Hash**: Every on-chain action
2. **Timestamp**: ISO 8601 format
3. **Test Account**: Clearly labeled test account
4. **Expected Result**: Pass/fail criteria

### Example Evidence

```json
{
  "test": "token-transfer",
  "tx_hash": "0xabcd...1234",
  "timestamp": "2024-04-12T20:00:00Z",
  "test_account": "0xTEST...ACCOUNT",
  "result": "pass",
  "block": 12345678,
  "evidence_url": "https://testnet-explorer.io/tx/0xabcd...1234"
}
```

## Verification Commands

```bash
# Check testnet health
curl https://testnet-api.ssid.io:8100/health

# Get testnet status
curl https://testnet-api.ssid.io:8100/status
```

## Testnet vs Mainnet

| Aspect | Testnet | Mainnet |
|--------|---------|---------|
| Tokens | Test tokens | Real tokens |
| Value | No real value | Real value |
| State | Resettable | Permanent |
| Performance | May vary | Production-grade |
| Status | Active | **Not Live** |

:::warning
**Mainnet Not Live**

As of the snapshot date, mainnet is NOT active. Any claims of "mainnet live" without evidence are invalid.
:::
