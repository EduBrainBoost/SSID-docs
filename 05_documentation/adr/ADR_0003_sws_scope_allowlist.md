# ADR-0003: Add `sws/` to Integrator Merge Checks Scope Allowlist

**Date:** 2026-04-16  
**Status:** ACCEPTED  
**Decision Maker:** SWS Artifact Contracts Working Group  
**Affected Component:** `.github/workflows/integrator_merge_checks.yml`

---

## Context

The SSID-docs repository maintains operational runbooks, artifact contracts, and operator documentation for the Streaming Workflow System (SWS) pipeline. These assets live in the `sws/` directory and include:

- `sws/runbooks/` — Operator Quickstart Runbook, recovery procedures, CLI reference
- `sws/contracts/` — Artifact contract specifications (13 artifact types)

The current Integrator Merge Checks workflow's scope allowlist does not include `sws/`, preventing legitimate SWS documentation from being published to the repository.

---

## Decision

Add `sws/` to the allowed path prefixes in `.github/workflows/integrator_merge_checks.yml`.

```yaml
ALLOWED_PREFIXES=(
  ".github/"
  "02_audit_logging/"
  "05_documentation/"
  "docs/"
  "public/"
  "src/"
  "sws/"           # ← NEW
  "tests/"
  "tools/"
)
```

---

## Rationale

1. **Operational Necessity:** SWS runbooks and artifact contracts are production documentation required for system operation and maintenance.

2. **Scope Alignment:** The `sws/` directory follows the same organizational principle as other documentation directories (`docs/`, `tools/`, `public/`).

3. **Security Intact:** The allowlist change does not alter forbidden metadata checks (Check 2) or ADR requirements. SWS artifacts remain subject to full validation.

4. **No Precedent Violation:** SWS is a first-party SSID pipeline system, not a third-party integration. The scope expansion is consistent with ROOT-24 rules (all within canonical infrastructure).

---

## Consequences

### Positive
- Enables canonical SWS documentation publication to SSID-docs
- Supports operational runbook distribution
- Maintains security posture (all checks remain active)

### Negative
- None identified

---

## Alternatives Considered

1. **Place SWS docs elsewhere:** Would create fragmentation and reduce visibility for operators. Rejected.
2. **Require separate approval workflow:** Unnecessary ceremony for production runbooks. Rejected.

---

## Implementation

- File modified: `.github/workflows/integrator_merge_checks.yml`
- Change: Add `"sws/"` to `ALLOWED_PREFIXES` array (line 55)
- Backward compatible: No change to existing paths or validation logic

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-16 | Initial decision (ACCEPTED) |
