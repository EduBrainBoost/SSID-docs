---
# ADR-0009: Compliance Gate -- Fail-Closed Runtime Enforcement

**Status:** Accepted
**Datum:** 2026-04-05
**Autoren:** Auto-Swarm Production Hardening

## Kontext

Compliance-Anforderungen (MiCA/eIDAS2/AMLD6/GDPR) waren nur in YAML-Mappings dokumentiert, ohne ausfuehrbare technische Enforcement-Mechanismen.

## Entscheidung

- ComplianceGate-Klasse (23_compliance/runtime/compliance_gate.py) mit 4 Runtime-Checks
- Fail-closed: WARN und REVIEW_REQUIRED zaehlen NICHT als PASS
- Jurisdiction Runtime: unbekannte Jurisdiktionen werden blockiert (fail-closed)
- Evidence: jede Compliance-Entscheidung erzeugt strukturierten ComplianceCheck-Record
- 45 Unit-Tests (alle PASS)

## Konsequenzen

- MiCA Art.66: yield/security/redemption Claims werden zur Runtime blockiert
- GDPR Art.25: PII-Keys in Payloads triggern FAIL
- AMLD6: KYC-Threshold-Pruefung (EUR 1000) ist Runtime-enforced
- eIDAS2: LoA-Pruefung gegen Identity-Score ist Runtime-enforced
- Keine permissiven Bypasses ohne Evidence
