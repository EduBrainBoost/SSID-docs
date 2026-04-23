---
title: Review and Gates
description: CI, Pages, Secret-Scan, Score, Badge, and Review Model
---

# Review and Gates

## Overview

This repository implements comprehensive gates to ensure quality, security, and policy compliance.

## CI/CD Pipeline

### Workflow Files

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `docs_ci.yml` | Build, test, lint | PR, Push |
| `pages.yml` | Deploy to GitHub Pages | Push to main |
| `integrator_merge_checks.yml` | Policy compliance | PR to main |

### CI Checks

```
┌─────────────────────────────────────────────────────────┐
│                    CI Pipeline                          │
├─────────────────────────────────────────────────────────┤
│  1. Checkout code                                       │
│  2. Install dependencies (pnpm)                       │
│  3. Run linter                                        │
│  4. Run tests (vitest)                                │
│  5. Build project                                     │
│  6. Secret scan (TruffleHog)                          │
│  7. Security scan (Trivy)                           │
│  8. Upload artifacts                                  │
└─────────────────────────────────────────────────────────┘
```

## Secret Scanning

### TruffleHog Integration

```yaml
- name: Check for secrets
  uses: trufflesecurity/trufflehog@main
  with:
    extra_args: --only-verified
```

### Blocked Patterns

- API keys
- Private tokens
- Database credentials
- SSH keys
- Environment files (`.env`)

## Score Tracking

### Quality Metrics

| Metric | Target | Badge |
|--------|--------|-------|
| Build | Passing | ![Build](https://img.shields.io/badge/build-passing-brightgreen) |
| Tests | >80% | ![Tests](https://img.shields.io/badge/tests-85%25-brightgreen) |
| Coverage | >80% | ![Coverage](https://img.shields.io/badge/coverage-82%25-brightgreen) |
| Security | No critical | ![Security](https://img.shields.io/badge/security-passing-brightgreen) |

### Badges

```markdown
![Build](https://github.com/ssid-dev/ssid-docs/workflows/Docs%20CI/badge.svg)
![Pages](https://github.com/ssid-dev/ssid-docs/workflows/Pages/badge.svg)
```

## Review Model

### Pull Request Requirements

1. **Branch Protection**
   - Require 1 review
   - Require status checks
   - Require up-to-date branches

2. **Required Checks**
   - ✅ CI / test
   - ✅ CI / build
   - ✅ Policy / check

3. **Merge Requirements**
   - All checks passing
   - No conflicts
   - Signed commits (optional)

### Review Checklist

```markdown
## Review Checklist

- [ ] Code changes reviewed
- [ ] Documentation updated
- [ ] Tests passing
- [ ] No secrets detected
- [ ] No policy violations
- [ ] Build successful
```

## Evidence Requirements

All gates require evidence:

| Gate | Evidence Type | Storage |
|------|---------------|---------|
| Build | Build logs | GitHub Actions |
| Test | Test results | Artifact |
| Security | Scan report | Artifact |
| Policy | Compliance log | GitHub Actions |

## Push Gates

### Pre-Push Hooks

```bash
# Local pre-push checks
pnpm test
pnpm lint
pnpm build
```

### Remote Gates

- Branch protection rules
- Required status checks
- Review requirements

## Failure Handling

### CI Failure

1. Check logs in GitHub Actions
2. Fix identified issues
3. Push fixes
4. Re-run checks

### Policy Failure

1. Review policy violation
2. Sanitize content if needed
3. Request exception if justified
4. Re-submit

## References

- `.github/workflows/docs_ci.yml`
- `.github/workflows/pages.yml`
- `.github/workflows/integrator_merge_checks.yml`
