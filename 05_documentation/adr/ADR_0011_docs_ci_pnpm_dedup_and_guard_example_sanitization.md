# ADR-0011: docs-ci pnpm Dedup and Guard Example Sanitization

## Status
Accepted

## Context
PR #48 updates `.github/workflows/docs_ci.yml` as part of the multi-branch
integration for `SSID-docs`.

Two CI issues were identified on the integration branch:

1. `pnpm/action-setup@v4` failed because the workflow specified `version: 10`
   while `package.json` already declared `packageManager: "pnpm@10.30.3"`.
2. `denylist-gate` failed because `src/content/docs/governance/guards.mdx`
   contained an example path with a real-looking local Windows filesystem path.

Under ADR-0001, workflow changes require an ADR in the same PR.

## Decision

- Remove the explicit `with.version` stanza from `docs_ci.yml` and treat
  `package.json` as the single source of truth for the pnpm version.
- Replace the example absolute local path in `guards.mdx` with a neutral
  workspace-style placeholder path that still communicates the rule without
  leaking a developer-local filesystem pattern.

## Consequences

- `docs-ci` no longer fails due to duplicate pnpm version declarations.
- The absolute-path leak scan remains strict while documentation examples stay
  valid and safe for publication.
- PR #48 satisfies the ADR requirement for workflow changes in
  `Integrator Merge Checks`.
