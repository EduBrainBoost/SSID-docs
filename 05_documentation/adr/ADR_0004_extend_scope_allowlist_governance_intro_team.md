# ADR-0004 — Extend Scope Allowlist: governance/, intro/, team/

**Date:** 2026-04-18  
**Status:** Accepted  
**Deciders:** S7 (Product & DX Lead), S1 (Founder / Chief Architect)

## Context

The SSID-docs repo contains operational documentation directories (`governance/`, `intro/`, `team/`) that are legitimate documentation artifacts under the RACI model. These paths were not included in the original integrator scope allowlist (ADR-0001), causing CI gate failures when updating these directories.

## Decision

Add the following prefixes to the Integrator Merge Checks scope allowlist:
- `governance/` — RACI, mandate tracking, operational governance docs
- `intro/` — Technical positioning, system introduction docs
- `team/` — Organigramm, seat descriptions, accountability matrix

## Consequences

- PRs touching these directories will pass the scope guard
- All other constraints (no forbidden metadata, ADR-pflicht for workflow changes) remain in force
- No security or compliance risk: these are documentation files, not code or config
