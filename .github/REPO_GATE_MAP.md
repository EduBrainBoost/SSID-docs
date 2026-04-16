# SSID-docs Repo Gate Map

## Overview
This document defines the 4 mandatory gates for SSID-docs repository code, design, and deployment decisions. All code changes must pass these gates sequentially before merging to main.

**Repository:** SSID-docs  
**Total Gates:** 4  
**Gate Sequence:** Regulatory → Privacy → Product → Evidence

---

## Gate 1: Regulatory (EX-L)

**Owner:** External Legal/Regulatory Mandate (EX-L)

### Minimum Pass Evidence
- [ ] No system secrets in documentation
- [ ] EU AI Act compliance statements included (Articles 22-25)
- [ ] API documentation matches OpenAPI definitions (not manually written)
- [ ] Audit trail documentation present
- [ ] Regulatory framework references correct
- [ ] No hardcoded credentials in examples

### Hard Fail Triggers
- System secrets exposed in docs
- EU AI Act compliance missing
- API docs manually written instead of generated
- Regulatory frameworks misrepresented
- Hardcoded credentials in code examples
- License terms missing or incorrect

---

## Gate 2: Privacy (EX-P)

**Owner:** External Privacy Mandate (EX-P)

### Minimum Pass Evidence
- [ ] No PII examples in documentation
- [ ] Privacy policy link included
- [ ] Data handling practices documented
- [ ] GDPR compliance statement present
- [ ] User consent mechanisms explained
- [ ] No federated learning implementation details exposed

### Hard Fail Triggers
- PII examples in code snippets
- Privacy policy missing or outdated
- Data handling practices undefined
- GDPR compliance statement missing
- User consent mechanisms unexplained
- Sensitive implementation details exposed

---

## Gate 3: Product (S7)

**Owner:** Seat-7 (Product Lead)

### Minimum Pass Evidence
- [ ] Documentation matches current API version
- [ ] User guides complete and tested
- [ ] Architecture diagrams up-to-date
- [ ] Deployment instructions verified
- [ ] Getting started guide functional
- [ ] Migration guides provided (if applicable)
- [ ] Backwards compatibility documented

### Hard Fail Triggers
- Docs outdated relative to codebase
- Getting started guide non-functional
- Architecture diagrams contradictory
- Deployment instructions fail
- Missing migration guidance
- Backwards compatibility undocumented

---

## Gate 4: Evidence (S5)

**Owner:** Seat-5 (Evidence & Audit)

### Minimum Pass Evidence
- [ ] Evidence log completed (documentation changes tracked)
- [ ] Docs build validated (no broken links)
- [ ] SHA256 hashes recorded for major revisions
- [ ] All commits signed and attributed
- [ ] Documentation source verified (not auto-generated incorrectly)
- [ ] I18N compliance verified

### Hard Fail Triggers
- Evidence log missing
- Build validation failed (broken links)
- SHA256 hashes not recorded
- Unsigned commits detected
- Auto-generation pipeline broken
- I18N compliance violated

---

## Gate Sequence Logic

```
Regulatory (EX-L) ✓
    ↓ [PASS]
Privacy (EX-P) ✓
    ↓ [PASS]
Product (S7) ✓
    ↓ [PASS]
Evidence (S5) ✓
    ↓ [PASS]
→ MERGEABLE TO MAIN
```

**Sequential Gates Rule:** Each gate must PASS before proceeding to the next. No gate skipping.

---

## Documentation Standards (SSID-Docs Specific)

### Technology Stack
- **SSG:** Astro/Starlight-based
- **Format:** MDX with full Markdown support
- **I18N:** Multi-language required (not optional)

### Content Rules
- **API Documentation:** Generated from OpenAPI (not manually written)
- **System Documentation:** Belongs in 16_codex root (not in docs/)
- **Reference Docs:** Only reference_doc type in docs/
- **Artifacts:** Stored in audit-specific subzones (never root)

### Build & Validation
- [ ] Astro build passes without warnings
- [ ] All links validated (internal & external)
- [ ] MDX syntax correct
- [ ] I18N keys complete (all languages)
- [ ] Search indexing working

### Forbidden Content
- No system secrets
- No hardcoded API endpoints
- No raw credentials
- No private key examples
- No manual API documentation (must be generated)

---

## Integration with Pilot Control Plane

This gate map is integrated with:
- **Documentation & I18N Rules:** Astro/Starlight stack, MDX format mandatory
- **Regulatory Gates:** EU AI Act compliance statements
- **Pilot Decision Matrix:** Documentation decisions tracked (D10-D12)

---

## Enforcement

- **CI Integration:** Astro build + link validation in GitHub Actions
- **Evidence Tracking:** Each gate decision logged
- **Abort Logic:** Build failures or broken links block merge
- **Status Transparency:** Gate status visible in PR checks
- **I18N Verification:** All language keys checked before merge

---

## Testing & Deployment

- Docs deployment: Automatic on main merge
- Staging: All PRs generate preview URLs
- Production: docs.ssid.io (or configured domain)
- Search indexing: Verified on deployment

Last Updated: 2026-04-16
