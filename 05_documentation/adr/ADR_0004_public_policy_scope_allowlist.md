# ADR-0004: Add PUBLIC_POLICY.md to Scope Allowlist

## Status
Accepted

## Context
The integrator merge checks enforce a scope allowlist for root-level files.
`PUBLIC_POLICY.md` defines the public content policy for SSID-docs and is a
legitimate root-level document alongside `SECURITY.md`, `LICENSE`, etc.

Drift-sentinel flagged `PUBLIC_POLICY.md` for containing a literal Windows
path example (`C:\Users\...`). Fixing this requires modifying the file, which
triggers the scope violation because it was not in the allowlist.

## Decision
Add `PUBLIC_POLICY.md` to `ALLOWED_ROOT_FILES` in
`.github/workflows/integrator_merge_checks.yml`.

## Consequences
- `PUBLIC_POLICY.md` can be modified via PR without scope violations.
- No new path prefixes or wildcard changes introduced.
- Consistent with existing policy files (`SECURITY.md`, `LICENSE`) already in the list.
