# SSID Technical Positioning

## Architecture Principles

### Non-Custodial Model
SSID operates on a non-custodial principle where:
- **KYC/AML Data**: Held exclusively by the Provider (not SSID)
- **Cryptographic Keys**: Managed by the end user, never held by SSID
- **Data Privacy**: Compliance with GDPR, no on-chain PII storage

### Hash-Only On-Chain Representation
- **PII Exclusion**: No personally identifiable information stored on-chain
- **Proof Mechanism**: Cryptographic hashes (SHA3-256) represent KYC compliance status
- **Verification**: Hash-based verification enables privacy-preserving proof validation

### Proof-Based Identity System
- **DID (Decentralized Identifier)**: W3C-compliant identifier for each user
- **VC (Verifiable Credential)**: Cryptographically signed claims from trusted providers
- **VP (Verifiable Presentation)**: User-constructed proofs for selective disclosure

## Current Operational Status

### Controlled Pilot Mode

**Scope Limitation**
- 1 product path (Identity Verification)
- 1 provider (EU KYC/AML-certified)
- 1 verification class (Standard Compliance)

**Validation Gates**
- All public claims subject to Legal review (EX-L mandate)
- Product feature claims require Product Gate PASS (S7 responsibility)
- 3 core flows validated after Product Gate PASS

**Timeline**
- Controlled Pilot target close: 2026-04-22
- Public Production launch: Conditional on all 6 gates PASS plus separate S1 release
  - Crypto Gate (EX-C accountable; S4/S2 execute)
  - Legal/Regulatory Gate (EX-L accountable; S3 executes)
  - Privacy Gate (EX-P accountable; S3 executes)
  - Product Gate (S7 accountable)
  - Operations Gate (S6 accountable)
  - Evidence Gate (S5 accountable)

## Core Flows (Validated)

### Flow 1: Initial KYC Verification
1. User registers with DID
2. Provider performs KYC/AML verification
3. Provider issues VC (KYC attestation)
4. Hash of VC stored on-chain (zero PII)
5. User receives VP for selective disclosure

### Flow 2: Compliance Proof Generation
1. User constructs VP from stored VC
2. VP proves KYC compliance without exposing PII
3. Third-party validates VP signature
4. On-chain hash confirms provider attestation

### Flow 3: Provider Re-issuance
1. Provider updates KYC status (e.g., post-expiry revalidation)
2. New VC issued with updated claims
3. New hash stored on-chain
4. Previous credentials remain valid for historical audit

## Compliance & Governance

### Legal Boundaries
All claims in documentation, positioning materials, or marketing must pass legal review per Legal Boundary Memo from EX-L. No exceptions for:
- Technical positioning claims
- Feature descriptions
- Regulatory compliance statements
- Integration guidance

### Product Authority
Product feature claims owned by S7 (Product Lead). Product Gate must PASS before:
- Feature documentation
- Integration guides
- Provider selection guidelines
- Service level claims

### Data Governance
- Non-custodial principle enforced at all layers
- Hash-only storage non-negotiable (encrypted on-chain)
- Provider isolation maintained (no cross-provider key sharing)
- Audit trails immutable (append-only event logs)

## Security & Cryptography

### Standard Algorithms
- **Key Exchange**: Kyber (post-quantum resistant)
- **Digital Signatures**: Dilithium (post-quantum resistant)
- **Hashing**: SHA3-256 (immutable proof anchors)
- **TLS**: mTLS for service-to-service authentication

### Non-Custodial Security
- User key recovery via BIP39/SLIP39 mnemonics
- Hardware wallet support (Ledger, Trezor)
- No backup keys held by SSID
- User-initiated key rotation

## Exclusions & Not Covered

### Out of Scope for Pilot
- Multi-provider federation (single provider only)
- Automated policy enforcement (manual review gates)
- Real-time fraud detection (batch post-analysis only)
- On-chain governance (centralized during pilot)

### Future Enhancements (Post-Pilot)
- Multi-provider attestation aggregation
- DAO-governed provider selection
- Zero-knowledge compliance proofs
- Cross-chain identity portability

## References

- Legal Boundary Memo: [External Legal Counsel mandate]
- Product Gate Charter: [S7 Product Leadership]
- Crypto Gate Audit: [EX-C Cryptography Review]
- Privacy Impact Assessment: [EX-P Privacy Mandate]
- Operations Readiness: [S1 Operations Lead]

**Status**: Controlled Pilot Mode
**Last Updated**: 2026-04-18
**Authority**: S1, S2, S3, S5, S6, S7, EX-C, EX-L, EX-P
