# Marketing Freeze — Controlled Pilot Mode

## Status: ACTIVE

**Effective Date**: 2026-04-16
**Duration**: Until Closed Pilot validation (target 2026-04-22)
**Authority**: Steering Committee (S1, S7, EX-L, EX-C, EX-P)

## Policy Summary

Marketing offensive is suspended during Controlled Pilot phase. Technical positioning documentation is permitted. All external-facing communications must pass Claim Review Policy gates.

## Permitted Activities

### Technical Documentation (APPROVED)
✓ Architecture documentation (TECHNICAL_POSITIONING.md)
✓ API reference documentation
✓ Integration guides (technical scope only)
✓ Developer onboarding materials
✓ Design decision records (ADRs)
✓ Security & compliance technical details
✓ Code documentation & comments

**Constraint**: No promotional language, feature claims, or business benefit statements.

### Internal Communications (APPROVED)
✓ Team coordination & operational updates
✓ Status reports to steering committee
✓ Internal RFC processes
✓ Engineering documentation

## Suspended Activities

### Branding & PR (P2 POST-PILOT)
✗ Press releases
✗ Media outreach
✗ Public announcements
✗ Branded landing pages
✗ Product launch announcements
✗ Feature promotion

### Community Engagement (P2 POST-PILOT)
✗ Community Discord/Telegram activation
✗ GitHub Discussions engagement
✗ Blog posts
✗ Tutorial content
✗ Developer conferences & speaking engagements
✗ Hackathon sponsorships

### Partnerships & Integrations (P2 POST-PILOT)
✗ Provider partnership announcements
✗ Enterprise customer onboarding
✗ Integration partner outreach
✗ White-label reseller programs
✗ Ecosystem partnerships

## Rationale

### Risk Mitigation
- Gate validation still in progress (6/6 gates required)
- Regulatory exposure risk during pilot phase
- Product feature stability not yet confirmed
- Provider certification pending external audit

### Timing
- Closed Pilot deadline: 2026-04-22 (6 days)
- All gates must PASS before public positioning
- External hard-blocks tracked (EX-001, EX-002, EX-003, EX-004)
- Evidence validation ongoing

### Gate Dependencies
1. **Crypto Gate (EX-C)**: Cryptographic soundness validation
2. **Legal/Regulatory Gate (EX-L)**: Regulatory compliance certification
3. **Privacy Gate (EX-P)**: GDPR/privacy-by-design validation
4. **Product Gate (S7)**: Feature stability & readiness
5. **Operations Gate (S1)**: Infrastructure & SLA readiness
6. **Evidence Gate (S2)**: Audit trail & compliance evidence

**Public Communications Resume**: Only after 6/6 gates PASS

## Claim Review Policy Applicability

All claims in documentation, even "technical" documentation, must pass:
- **Legal Review** (EX-L): Regulatory claims, compliance statements
- **Product Review** (S7): Feature claims, capability statements
- **Privacy Review** (EX-P): Data handling, privacy statements

No exceptions for:
- Marketing materials
- Technical documentation
- Developer guides
- Positioning statements
- Feature descriptions

## Scope of Freeze

### Geographic Scope
- Global (all regions & languages)
- All SSID properties (docs, websites, social media)
- All partner communications

### Organizational Scope
- Official SSID channels
- Authorized partner communications
- Vendor communications (NDA-protected)
- Public appearances by SSID staff

## Exceptions & Escalation

**Exception Process** (if business-critical):
1. Document business case
2. Submit to Steering Committee
3. Require unanimous approval (S1, S7, EX-L, EX-C, EX-P)
4. Update this policy with decision

**No standing exceptions granted** — each case reviewed individually.

## Enforcement

### Monitoring
- SSID Communications review board (Weekly)
- GitHub branch protection on all public repos
- Pre-commit hooks block promotional commits

### Violations
- Immediate content removal
- Incident report to Steering Committee
- Corrective messaging required
- Re-training of responsible teams

## Timeline

| Date | Milestone | Gate Status |
|------|-----------|------------|
| 2026-04-16 | Marketing Freeze Activated | 0/6 gates |
| 2026-04-18 | Product Gate PASS | 1/6 gates |
| 2026-04-19 | Crypto Gate PASS | 2/6 gates |
| 2026-04-20 | Legal Gate PASS | 3/6 gates |
| 2026-04-21 | Privacy Gate PASS | 4/6 gates |
| 2026-04-21 | Operations Gate PASS | 5/6 gates |
| 2026-04-22 | Evidence Gate PASS (Closed Pilot) | 6/6 gates |
| 2026-04-22 | Marketing Freeze Lifted | 6/6 gates |

## Related Policies

- [CLAIM_REVIEW_POLICY.md](../CLAIM_REVIEW_POLICY.md) — Required legal/product gates for all claims
- [TECHNICAL_POSITIONING.md](../intro/TECHNICAL_POSITIONING.md) — Authorized technical content
- [Legal Boundary Memo](../governance/LEGAL_BOUNDARY_MEMO.md) — External counsel mandate

**Status**: ACTIVE
**Last Updated**: 2026-04-16
**Next Review**: 2026-04-22 (or upon gate completion)
