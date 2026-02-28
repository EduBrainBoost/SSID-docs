## Summary

<!-- Brief description of changes -->

## Integrator Merge Checks

> Merge only when **all** CI checks PASS. Squash & merge, delete branch.

- [ ] **Scope**: Files changed only within allowed zones (`src/`, `docs/`, `.github/`, `tools/`, etc.)
- [ ] **No forbidden metadata**: No `.claude/`, `.env*`, `*.pem`, `id_rsa`, `secrets/`
- [ ] **ADR-Pflicht**: If `.github/workflows/**` changed, ADR included in `05_documentation/adr/`
- [ ] **No secrets committed**: No API keys, tokens, passwords, PII
- [ ] **CI Gates**: docs-ci (build + test) + secret-scan + Integrator Merge Checks = all PASS
- [ ] **Branch up-to-date**: Rebased on latest `main`

## Test Plan

<!-- How to verify these changes -->
