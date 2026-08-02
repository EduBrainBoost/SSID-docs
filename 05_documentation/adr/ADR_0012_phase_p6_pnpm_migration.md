# ADR-0012: Phase P6 Workflow Migration to pnpm

## Status
Accepted

## Context

The `phase-p6-docs-build-publish.yml` workflow was configured to use npm (node-version: 18, cache: 'npm', run: npm ci), but the SSID-docs repository is managed exclusively with pnpm (package.json declares packageManager: "pnpm@10.30.3", pnpm-lock.yaml is the lockfile).

This mismatch caused CI failures in PR #72 (feat: complete AI infrastructure catalogs) where the workflow could not resolve dependencies:

```
[error] Dependencies lock file is not found in /home/runner/work/SSID-docs/SSID-docs.
Supported file patterns: package-lock.json, npm-shrinkwrap.json, yarn.lock
```

The phase-p6 workflow is responsible for documentation build verification and evidence collection before pages publication. Its failure blocked legitimate PRs despite local builds passing.

Under ADR-0001, workflow changes require an ADR in the same PR.

## Decision

Update `phase-p6-docs-build-publish.yml` to use pnpm consistently with the rest of the repository:

1. Add `pnpm/action-setup@v4` step
2. Change setup-node cache from 'npm' to 'pnpm'
3. Update node-version from '18' to '22' (consistency with pages.yml and docs_ci.yml)
4. Replace `npm ci` with `pnpm install --frozen-lockfile`
5. Replace `npm run build` with `pnpm build`

This aligns phase-p6 with existing workflows (pages.yml, docs_ci.yml) that already use pnpm correctly.

## Consequences

- Phase P6 workflow now resolves dependencies correctly using pnpm-lock.yaml
- CI gate for documentation builds now passes for pnpm-managed repositories
- Node.js version bumped to 22 for better ES2024 support and LTS consistency
- AI infrastructure catalog integration (PR #72) can now complete CI verification
- Future workflow changes targeting this repository must use pnpm by default
