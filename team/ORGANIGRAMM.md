# SSID Team Organigramm

## Overview

SSID operates under a binding 8-Seat operative governance model, supplemented by 4 external review mandates. The model fixes repo ownership, gate authority, decision rights, and hard separation rules across the full SSID stack.

**Current Phase:** Internal operations baseline active  
**Public Production:** blocked until 6/6 gates PASS plus separate S1 release

---

## The 8 Operative Seats

### S1 — Founder & Chief Architect
Provides overall strategic direction, serves as escalation endpoint for critical decisions, and holds final production lock authority. Approves all cross-repo changes and ensures governance coherence.

**Key Responsibilities:**
- Strategic direction & SSID vision
- Cross-repo scope integration
- Final production sign-off
- Escalation resolution

---

### S2 — Core Protocol Lead
Leads smart contract architecture, zero-knowledge proof design, and identity core logic. Owns Phase 6-10 delivery (SSID-Orchestrator hardening for testnet/mainnet).

**Key Responsibilities:**
- Smart contract & protocol design
- DID/identity core logic
- Integration layer architecture
- Phase 6-10 testnet/mainnet hardening

---

### S3 — Security & Compliance Lead
Establishes security architecture, manages compliance frameworks (EU AI Act, regulatory), and ensures proper audit instrumentation. Primary owner of threat modeling and incident response.

**Key Responsibilities:**
- Security architecture & threat modeling
- Compliance audit frameworks
- Penetration testing & incident response
- RLS & access control design

---

### S4 — Crypto & PQC Lead
Internal operative seat for post-quantum cryptography, key lifecycle, and crypto architecture integration. Works in enforced separation from the external crypto reviewer.

**Key Responsibilities:**
- Post-quantum cryptography standards
- Quantum-safe architecture design
- Key management specification
- Crypto roadmap (5+ years)

---

### S5 — Audit & Evidence Lead
Maintains continuous audit framework, evidence logging, and chain-of-custody procedures. Validates Truth Gate and produces quarterly compliance reports.

**Key Responsibilities:**
- Audit logging framework
- Evidence collection & chain-of-custody
- Truth Gate validation
- Compliance reporting

---

### S6 — Platform Ops Lead
Manages infrastructure provisioning (Vault, staging, production), DevOps pipeline hardening, disaster recovery, and production health monitoring. Coordinates on-call procedures.

**Key Responsibilities:**
- Infrastructure architecture
- CI/CD pipeline hardening
- Disaster recovery & incident response
- Production health monitoring

---

### S7 — Product & DX Lead
Drives product strategy, API design, developer onboarding, and documentation quality. Synthesizes user feedback and coordinates feature releases.

**Key Responsibilities:**
- Product strategy & roadmap
- API design & documentation
- Developer experience
- Feature release coordination

---

### S8 — Economics & Governance Lead
Internal operative seat for tokenomics, DAO governance, incentives, abuse resistance, and long-term economic sustainability.

**Key Responsibilities:**
- Tokenomics modeling & simulation
- DAO governance framework
- Treasury management policy
- Economic sustainability analysis

---

## External Specialist Mandates

### EX-L — EU FinReg Counsel (Critical)
Provides legal interpretation of EU financial regulations (MiCA, PSD2, GDPR, DLT Regulation), compliance sign-off, and contract review.

### EX-P — Privacy Engineer (Critical)
Designs GDPR-compliant architecture, conducts privacy impact assessments, and ensures privacy-by-design principles.

### EX-C — Crypto & PQC Reviewer (Critical)
External veto owner for cryptography, key management, and PQC changes.

### EX-M — Mechanism Designer / Economics Auditor (Critical)
External veto owner for fee, reward, and mechanism changes.

---

## Governance Gates

SSID uses 6 critical gates to control major decisions:

| Gate | Owner | Approval Required For |
|---|---|---|
| **Crypto** | EX-C | Cryptography, key management, PQC |
| **Regulatory** | EX-L | Compliance policies, legal classification, external claims |
| **Privacy** | EX-P | Data handling changes, GDPR implications |
| **Product** | S7 | Feature launches, API changes, docs scope |
| **Operations** | S6 | Infrastructure, runtime, ports, deploy strategy |
| **Evidence** | S5 | Audit trail changes, evidence, WORM |

---

## Operational Status

**Binding baseline:**
- 8 operative seats
- 4 external veto mandates
- fixed repo and gate assignment
- fail-closed release logic
- workspace-only operative execution

**Hard runtime rule:**
- `C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\...` is the only operative zone
- `C:\Users\bibel\Documents\Github\...` is reserved canonical / mirror zone and is not used by AI for operative work

---

## How We Work

### Decision-Making
- **Default:** seat/gate authority per the canonical RACI matrix
- **Gate-Based:** crypto, regulatory, privacy, product, evidence, and operations are fail-closed
- **Escalation:** unresolved disputes go to S1; external veto owners remain authoritative in their domains

### Transparency
- All decisions documented in audit trails
- Quarterly governance reports (public)
- Monthly regulatory & security updates (stakeholders)
- Real-time Truth Gate validation

### Collaboration
- Weekly governance syncs (Monday 10:00 UTC)
- Daily standups for active Phase 6-10 work (Streams 0-1)
- Monthly external specialist check-ins
- Emergency council activation (4-hour response for critical issues)

---

## Contact & More Information

For detailed role responsibilities, gate ownership, and collaboration rules, see:
- **Internal:** `SSID/16_codex/SEAT_RESPONSIBILITIES.md`
- **Internal:** `SSID/16_codex/ORGANIGRAMM_8SEATS_CURRENT.md`
- **Internal:** `SSID/16_codex/governance/WORKSPACE_RUNTIME_BOUNDARY.md`

For product-related questions, contact S7 (Product & DX Lead).  
For security or compliance questions, contact S3 (Security & Compliance Lead).  
For technical protocol questions, contact S2 (Core Protocol Lead).

---

## Documentation Record

**Created:** 2026-04-16  
**Version:** 2.0  
**Status:** Operative governance baseline  
**Next Review:** on gate/status change
