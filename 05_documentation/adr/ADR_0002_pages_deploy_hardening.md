# ADR-0002: Pages Deploy Workflow Hardening (DEP-01)

## Status
Accepted

## Context
The `pages.yml` workflow failed on every push to main due to three issues:

1. **pnpm version conflict** — `pnpm/action-setup@v4` specified `version: 10`
   while `package.json` declares `packageManager: pnpm@10.30.3`. The action
   rejects dual version specs since v4.
2. **Missing `configure-pages`** — Without `actions/configure-pages`, GitHub
   Pages cannot detect the framework or apply base-path settings, risking
   silent deploy failures.
3. **`cancel-in-progress: false`** — Stale deploy runs could queue up and
   waste Actions minutes without benefit.

## Decision
Apply three targeted fixes to `.github/workflows/pages.yml`:

1. Remove `with: version: 10` from `pnpm/action-setup@v4` — let
   `packageManager` in `package.json` be the single source of truth.
2. Add `actions/configure-pages@v5` step before install/build.
3. Set `cancel-in-progress: true` in the concurrency block.

No changes to `docs_ci.yml` required (already correct).

## Consequences
- Pages deploy workflow will pass once GitHub Pages is enabled (UI setting).
- pnpm version is managed solely via `package.json` — single source of truth.
- Concurrent deploys are cancelled, reducing wasted Actions minutes.
