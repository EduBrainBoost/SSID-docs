# ADR-0001: Integrator Merge Checks Enforced via CI

## Status
Accepted

## Context
The SSID-docs public documentation site needs the same merge hygiene as the
private SSID repo. Without automated enforcement, forbidden files (.env, .pem,
secrets), scope violations, and missing ADRs can slip into the public repo.

## Decision
Add a GitHub Actions workflow `integrator_merge_checks.yml` that runs on every
`pull_request` event and blocks merge on failure. Three automated checks:

1. **Scope Allowlist Guard** — Files changed must be within declared zones:
   `.github/`, `02_audit_logging/`, `05_documentation/`, `docs/`, `public/`,
   `src/`, `tests/`, `tools/`, plus allowed root files (`package.json`,
   `astro.config.mjs`, `pnpm-lock.yaml`, etc.). FAIL if outside.

2. **No-Forbidden-Metadata Guard** — Blocks `.claude/`, `.devcontainer/`,
   `*.code-workspace`, `.DS_Store`, `Thumbs.db`, `.env*`, `*.pem`, `*.key`,
   `id_rsa`, `secrets/`.

3. **ADR-Pflicht Guard** — Changes in `.github/workflows/` require an
   `05_documentation/adr/ADR_*.md` in the same PR.

Additionally:
- PR template updated with Integrator-Merge-Checks checklist.
- Workflow added as required status check in branch protection.

## Trigger Rules (ADR-Pflicht)

| Prefix | ADR Required |
|--------|-------------|
| `.github/workflows/` | Yes |
| All other paths | No |

## Consequences
- Every PR validated before merge. No manual enforcement needed.
- PRs introducing forbidden files or scope violations are blocked at CI level.
- New allowed paths can be added to the scope allowlist in the workflow.
- Branch protection must list `Integrator Merge Checks` as required check.
