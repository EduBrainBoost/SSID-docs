---
# ADR-0008: EMS Live API Binding fuer Identity/Fee/Compliance Flows

**Status:** Accepted
**Datum:** 2026-04-05
**Autoren:** Auto-Swarm Production Hardening

## Kontext

EMS-Frontend-Komponenten (IdentityDashboard, FeeRouterStatus) waren statische Stubs ohne Live-API-Anbindung. Backend-Router fuer identity/compliance/fees fehlten.

## Entscheidung

- Backend: 3 FastAPI-Router unter portal/backend/routers/ (identity, compliance_status, fee_routing)
- Frontend: Next.js App-Router-Seiten /identity und /fees mit Live-Fetch + graceful degradation
- API-Prefix: /api/v1/ fuer alle neuen Endpoints
- Non-custodial: alle Requests/Responses nur SHA3-256-Hashes, kein PII

## Konsequenzen

- EMS ist jetzt Visibility-Layer fuer alle produktiven Flows
- Live-API erfordert laufende Backend-Services (Port G: 8100)
- Graceful degradation: Komponenten zeigen Defaults wenn API nicht erreichbar
- CORS: VITE_API_URL env-var fuer Frontend-Konfiguration
