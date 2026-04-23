---
title: Deploy Verify Rollback (Public)
description: Public runbook for deployment verification and rollback procedures
---

# Deploy Verify Rollback (Public)

## Overview

This runbook describes **public-facing** deployment, verification, and rollback procedures. Internal procedures remain in private repositories.

:::caution
**Public Scope Only**

This document covers:
- ✅ Public deployment processes
- ✅ Verification methods
- ✅ Public rollback triggers
- ✅ Evidence collection

Does NOT cover:
- ❌ Internal deployment mechanisms
- ❌ Private credentials
- ❌ Internal pathways
:::

## Deployment Flow

```
┌─────────────────────────────────────────────────────────┐
│               PUBLIC DEPLOYMENT FLOW                    │
├─────────────────────────────────────────────────────────┤
│  1. Code Review & Approval                              │
│  2. CI/CD Pipeline Execution                          │
│  3. Artifact Generation                               │
│  4. Public Deployment (GitHub Pages)                  │
│  5. Verification                                      │
│  6. Evidence Collection                               │
└─────────────────────────────────────────────────────────┘
```

## Pre-Deployment Checklist

### Public Requirements

- [ ] PR approved by reviewer
- [ ] All CI checks passing
- [ ] No secrets detected
- [ ] Documentation updated
- [ ] Tests passing
- [ ] Build successful

### Evidence Requirements

| Check | Evidence | Location |
|-------|----------|----------|
| Code review | PR approval | GitHub PR |
| CI status | Action logs | GitHub Actions |
| No secrets | Scan report | CI artifact |
| Tests | Test results | CI artifact |
| Build | Build artifact | CI artifact |

## Deployment Commands

### GitHub Pages Deployment

```bash
# Triggered automatically on push to main
# See .github/workflows/pages.yml
```

### Local Verification

```bash
# Verify local build
pnpm build

# Verify local preview
pnpm preview
```

## Verification Steps

### Post-Deployment Verification

1. **URL Check**
   ```bash
   curl -I https://ssid-docs.github.io/ssid-docs/
   # Expect: HTTP 200
   ```

2. **Content Check**
   ```bash
   curl https://ssid-docs.github.io/ssid-docs/project/repo-topology/
   # Expect: Valid HTML, no errors
   ```

3. **Links Check**
   ```bash
   # Verify internal links work
   # Verify external links work
   ```

4. **Assets Check**
   ```bash
   # Verify CSS loaded
   # Verify JS loaded
   # Verify images loaded
   ```

## Rollback Procedures

### When to Rollback

| Trigger | Action | Evidence |
|---------|--------|----------|
| Broken build | Revert PR | Git history |
| Missing content | Emergency fix | Commit log |
| Security issue | Immediate revert | Incident log |
| Failed verification | Rollback | Test results |

### Public Rollback Steps

1. **Identify Issue**
   - Check CI logs
   - Verify deployment
   - Collect evidence

2. **Revert Change**
   ```bash
   # Revert via GitHub UI or CLI
   git revert <commit>
   git push origin main
   ```

3. **Verify Rollback**
   - Check site loads
   - Verify previous content
   - Run smoke tests

4. **Document**
   - Update incident log
   - Record evidence
   - Notify team

## Evidence Collection

### Required Evidence

| Phase | Evidence | Format |
|-------|----------|--------|
| Pre-deploy | PR approval | GitHub |
| Deploy | Action logs | GitHub |
| Verify | Screenshot/URL | PNG/Link |
| Rollback | Git history | Git |

### Evidence Storage

- CI artifacts (30 days)
- Git history (permanent)
- Incident logs (wiki)

## Release Gates

### Push Gates

```
┌─────────────────────────────────────────────────────────┐
│                   PUSH GATES                            │
├─────────────────────────────────────────────────────────┤
│  ✅ Branch protection enabled                           │
│  ✅ Required reviews: 1                                 │
│  ✅ Status checks required                            │
│  ✅ No secrets in code                                  │
│  ✅ No policy violations                                │
│  ✅ Build passes                                        │
└─────────────────────────────────────────────────────────┘
```

### Evidence Gate

All deployments must have:
- Timestamp
- Commit SHA
- Deployer identity
- Test results
- Verification results

## Success Criteria

A deployment is successful when:
- [ ] Site loads without errors
- [ ] All links functional
- [ ] No console errors
- [ ] Mobile responsive
- [ ] Evidence collected

## References

- `.github/workflows/pages.yml`
- `.github/workflows/docs_ci.yml`
- `public-system-status.md`
