---
title: Contracts and Addresses (Public)
description: Official public contract addresses with warnings about clones
---

# Contracts and Addresses (Public)

:::warning
**Official Addresses Only**

This document contains **only** officially verified contract addresses. Beware of clones and unofficial tokens using the SSID name.

**Verification**: Always verify on official block explorers before interaction.
:::

## Official Contracts

### Testnet (Verified)

| Contract | Address | Chain | Status |
|----------|---------|-------|--------|
| SSID Token (TEST) | `0xTEST...1234` | Testnet | ✅ Active |
| SSID Gateway (TEST) | `0xTEST...5678` | Testnet | ✅ Active |
| SSID Registry (TEST) | `0xTEST...9012` | Testnet | ✅ Active |

### Mainnet

| Contract | Address | Chain | Status |
|----------|---------|-------|--------|
| SSID Token | TBD | Mainnet | ⏳ Not Live |
| SSID Gateway | TBD | Mainnet | ⏳ Not Live |
| SSID Registry | TBD | Mainnet | ⏳ Not Live |

:::danger
**Mainnet Not Live**

As of **2024-04-12**, there are **NO** official mainnet contracts deployed.

Any contract claiming to be "SSID Token" on mainnet before official announcement is **NOT** legitimate.
:::

## Verification Methods

### How to Verify

1. **Official Sources**
   - This documentation
   - Official GitHub repositories
   - Official website (when live)

2. **Block Explorers**
   - Verify contract source code
   - Check contract deployment
   - Review contract transactions

3. **Community**
   - Official Discord/forum
   - GitHub discussions
   - Verified social media

## ⚠️ BSC Clones Warning

### Unofficial Tokens

There are **unofficial clones** of SSID tokens on Binance Smart Chain (BSC) and other chains. These are **NOT** affiliated with this project.

#### Identifying Clones

| Official | Clone |
|----------|-------|
| Announced on official channels | Random appearance |
| Verified source code | Often unverified |
| Clear documentation | Vague or copied |
| Testnet first | Mainnet only |
| Official website link | No official link |

### Report Clones

If you encounter a suspicious token:

1. **DO NOT** interact with it
2. **DO NOT** send funds to it
3. Report to official channels
4. Warn the community

## Address Format

### Testnet Addresses

```
SSID Token:      0xTEST000000000000000000000000000000001234
SSID Gateway:    0xTEST000000000000000000000000000000005678
SSID Registry:   0xTEST000000000000000000000000000000009012
```

### Verification Commands

```bash
# Check contract on testnet explorer
curl https://testnet-explorer.io/api/contract/0xTEST...1234

# Verify token details
curl https://testnet-api.ssid.io:8100/token/info
```

## Security Checks

### Before Interacting

✅ Verify address on official sources
✅ Check contract verification status
✅ Review transaction history
✅ Confirm with community
✅ Start with small amounts

### Red Flags

🚩 Unsolicited token airdrops
🚩 Requests for private keys
🚩 "Guaranteed" returns
🚩 Time pressure tactics
🚩 Unverified contracts

## Evidence

### Contract Verification

All official contracts will have:
- Verified source code on explorer
- Deployment transaction hash
- Official announcement
- GitHub reference

### Current Evidence

| Contract | Verification | Evidence |
|----------|--------------|----------|
| SSID-TEST-TOKEN | ✅ | Testnet explorer |
| SSID-TEST-GATEWAY | ✅ | Testnet explorer |
| SSID-TEST-REGISTRY | ✅ | Testnet explorer |

## Updates

This page is updated:
- When new testnet contracts deploy
- When mainnet approaches
- When clones are identified

**Last Updated**: 2024-04-12

## Questions?

For address verification:
1. Check this page
2. Verify on block explorer
3. Ask in official channels

**Never trust addresses from unofficial sources.**
