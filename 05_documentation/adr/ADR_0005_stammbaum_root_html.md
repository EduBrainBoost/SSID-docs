# ADR-0005: Stammbaum HTML — Root-Level Standalone Page

**Status:** Accepted
**Date:** 2026-03-16
**Author:** docs(stammbaum): sync agents #21-#29

## Context

`stammbaum.html` is an interactive agent genealogy visualization that
displays the full SSID agent hierarchy (Tiers 1–3, nodes #00–#29) as a
self-contained HTML page. It is deployed as a standalone page alongside
the Astro docs site and does not belong inside any numbered module.

## Decision

Allow `stammbaum.html` at the SSID-docs repository root. Add it to
`ALLOWED_ROOT_FILES` in the Integrator Merge Checks workflow.

The file:
- Is a standalone interactive visualization (not documentation prose)
- Has no framework dependencies (vanilla JS + CSS)
- Derives from `SSID-EMS/.claude/agents.lock.json` as canonical source
- Must be kept in sync with `agents.lock.json` when new agents are added

## Consequences

- `stammbaum.html` is a first-class artifact in SSID-docs root
- Future agent additions (Tier 4+) require a matching Stammbaum update PR
- Scope allowlist covers this file going forward

## References

ADR-0001 (Integrator Merge Checks enforcement)
