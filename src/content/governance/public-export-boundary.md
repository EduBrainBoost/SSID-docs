---
title: Public Export Boundary
description: What is public-safe, what is sanitizable, and what is forbidden
---

# Public Export Boundary

## Open-Core Philosophy

This project follows strict **Open-Core** principles. Only public, open-source components are included in this repository.

## Allowed Content ✅

### Public Documentation
- Architecture overviews
- Public API documentation
- General system descriptions
- Public workflows
- Sanitized operational procedures

### Open Source Code
- Core functionality
- Public interfaces
- Example implementations
- Test cases (sanitized)

### Public Data
- Testnet addresses
- Public metrics
- Sanitized logs
- Public contract addresses

## Sanitizable Content ⚠️

Content that requires sanitization before public export:

### Examples
- Internal URLs → Replace with public endpoints
- Internal paths → Remove or generalize
- Hostnames → Replace with service names
- Timestamps → Keep, but verify timezone

### Sanitization Process

```
1. Identify sensitive elements
2. Replace with public equivalents
3. Remove internal references
4. Verify no secrets remain
5. Review by second person
```

## Forbidden Content ❌

### NEVER in Public Repos

| Category | Examples | Reason |
|----------|----------|--------|
| Secrets | API keys, tokens, passwords | Security risk |
| Private paths | `/mnt/`, `/var/`, `C:\internal` | Information disclosure |
| Internal hosts | `internal.company.com` | Attack surface |
| Level-3 details | SAFE-FIX internals | Policy violation |
| Private configs | `.env.production` | Security risk |
| Personal data | User emails, names | Privacy violation |

### SAFE-FIX Policy

:::warning
**Level-3/SAFE-FIX Details Are Private**

SAFE-FIX (Sanitized Automated File Exchange) includes sensitive operational details. These remain in private repositories only.

SAFE-FIX Principles:
- `no_delete`: Never remove content
- `move_to_target`: Relocate sensitive data
- `rewrite_if_missing`: Rewrite when necessary
- `no_quarantine`: No automatic quarantine
:::

## Verification

### Pre-Push Checklist

```bash
# Check for secrets
grep -r -i "password\|secret\|token\|key" --include="*.md" .

# Check for internal paths
grep -r "/mnt/\|/var/\|/etc/\|C:\\" --include="*.md" .

# Check for emails
grep -r "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" --include="*.md" .
```

### Automated Checks

The repository includes automated checks in CI:
- Secret scanning (TruffleHog)
- Path validation
- Content boundary checks

## Reporting Violations

If you find private content in this public repository:

1. **DO NOT** create a public issue
2. Report via private security channel
3. Wait for resolution before further action

## References

- Security Policy: `SECURITY.md`
- Contributing Guide: `CONTRIBUTING.md`
- SAFE-FIX Documentation: (Private Repository)
