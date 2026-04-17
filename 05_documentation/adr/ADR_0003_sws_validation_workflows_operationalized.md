# ADR-0003: Operationalize SWS Validation Workflows on SSID-docs

**Date:** 2026-04-17  
**Status:** ACCEPTED  
**Decision Maker:** SSID-docs Integrator / SWS Validation Closeout  
**Affected Components:**
- `.github/workflows/phase-p0-truth-gate.yml`
- `.github/workflows/phase-p4-evidence-verify.yml`
- `.github/workflows/phase-p6-docs-build-publish.yml`

---

## Context

The SWS V1 documentation artifacts are already canonical on `main`, but the validation workflow layer shipped with multiple operational defects:

1. `phase-p0-truth-gate.yml` validated the legacy `docs/` tree instead of the active Starlight content tree in `src/content/docs/`.
2. `phase-p4-evidence-verify.yml` used a pipe-fed `while` loop, so invalid JSON evidence could still produce a passing status.
3. `phase-p6-docs-build-publish.yml` used `npm ci` in a `pnpm` repository, performed non-functional link validation, and allowed build errors to be softened.
4. Stricter link validation exposed broken internal links in existing docs pages.

This meant the workflows existed, but were not trustworthy as merge or publication gates.

---

## Decision

Operationalize the workflows so they validate the real repository state and fail on real defects.

### P0 Truth Gate
- Validate `src/content/docs/` alongside `docs/`
- Require `pnpm-lock.yaml`
- Count markdown files from the actual content tree
- Detect locale structure from `src/content/docs/`

### P4 Evidence Verification
- Replace the pipe-fed loop with process substitution so invalid JSON truly flips the failure flag
- Fail the job when evidence JSON is invalid

### P6 Docs Build & Publish
- Trigger on `src/content/docs/**`, `public/**`, `package.json`, and `pnpm-lock.yaml`
- Install `pnpm` before `actions/setup-node` cache initialization
- Use `pnpm install --frozen-lockfile`
- Use `pnpm build`
- Remove `continue-on-error` from the docs build gate
- Replace placeholder link checking with actual internal link validation against source files and generated routes

### Content Cleanup
- Repair broken internal links revealed by the stricter validation in:
  - `src/content/docs/deployments/ports-matrix-current.mdx`
  - `src/content/docs/deployments/testnet-guide.mdx`
  - `src/content/docs/tooling/ems-control-plane.mdx`

---

## Rationale

1. **Trustworthy gates:** A validation workflow that silently passes on invalid inputs is operationally worse than no gate because it creates false assurance.
2. **Repository alignment:** SSID-docs is a `pnpm` + Astro/Starlight repository; workflows must follow the actual toolchain and content layout.
3. **Fast failure:** Merge gates must fail immediately on broken builds, invalid evidence, or broken internal links.
4. **Canonical closeout:** With SWS V1 artifacts already on `main`, the remaining work is to make the enforcement layer operational and deterministic.

---

## Consequences

### Positive
- SWS validation workflows become executable and meaningful
- Broken internal docs links are now caught before merge
- Evidence verification correctly fails on malformed JSON
- Build/publish validation uses the same package manager and content layout as the repo itself

### Negative
- Previously hidden content defects now fail CI until corrected
- Future workflow changes continue to require ADR coverage

---

## Implementation Notes

- This ADR accompanies the workflow changes to satisfy repository ADR policy for `.github/workflows/` modifications.
- The change is intentionally limited to operational correctness; it does not alter the canonical SWS artifact scope.

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-17 | Initial decision (ACCEPTED) |
