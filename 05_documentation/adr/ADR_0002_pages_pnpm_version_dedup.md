# ADR-0002: Remove Duplicate pnpm Version Spec from pages.yml

## Status
Accepted

## Context
`pnpm/action-setup@v4` now rejects workflows that specify a pnpm version both
in the action's `with.version` parameter AND in `package.json`'s
`packageManager` field. The Pages deploy workflow (`pages.yml`) had
`version: 10` while `package.json` declares `packageManager: "pnpm@10.30.3"`.

This caused the Pages deploy to fail after merging V-01 verification PR:
```
Error: Multiple versions of pnpm specified:
  - version 10 in the GitHub Action config with the key "version"
  - version pnpm@10.30.3 in the package.json with the key "packageManager"
```

The `docs_ci.yml` workflow was not affected (it omits `with.version`).

## Decision
Remove the `with.version: 10` parameter from `pages.yml`. The `package.json`
`packageManager` field is the single source of truth for the pnpm version.

This aligns with the pattern already used in `docs_ci.yml`.

## Consequences
- Pages deploy workflow uses the exact pnpm version from `package.json`.
- Future pnpm upgrades only require updating `package.json` (one place).
- No workflow parameter drift between `docs_ci.yml` and `pages.yml`.
