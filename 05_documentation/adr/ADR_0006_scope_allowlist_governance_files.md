# ADR-0006: Scope Allowlist — Governance & Config Root Files

**Status:** Accepted
**Date:** 2026-04-01
**Author:** fix(docs): cross-repo remediation PR #36

## Context

PR #36 introduces governance and configuration files at the repository
root that are standard for open-source and internal repositories:

- `.pre-commit-config.yaml` — pre-commit hook configuration
- `CLAUDE.md` — AI assistant project instructions
- `CONTRIBUTING.md` — contribution guidelines
- `env.example.template` — environment variable template (renamed from
  `.env.example` to pass the denylist gate for `.env.*` patterns)
- `.env.example` — canonical environment example file

These files were blocked by the Integrator Merge Checks scope allowlist
(Check 1) because they were not listed in `ALLOWED_ROOT_FILES`.

## Decision

Add the five files to `ALLOWED_ROOT_FILES` in
`.github/workflows/integrator_merge_checks.yml`.

These are legitimate root-level configuration and governance files that
do not contain secrets and follow repository best practices.

## Consequences

- Scope allowlist covers these files going forward
- Future PRs adding similar governance files should follow this ADR pattern
- The `.env.*` denylist (Check 2) still blocks actual environment files
