# SSID-docs — Repo-Regeln

## REPO-IDENTITAET
- Repo-Name: SSID-docs
- Kanonisches Original (read-only Referenz): C:\Users\bibel\Documents\Github\SSID-docs
- Arbeitsstand (dieses Repo): C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID-docs
- Primaerer Branch: main
- Arbeits-Branches: develop, feature/*, fix/*
- Dieses Repo nutzt ausschliesslich Workspace-Ports (4331).

## WRITE-SCOPE
Nur innerhalb dieses Repos schreiben.
Dokumentation muss den aktuellen Stand der Quell-Repos (SSID, SSID-EMS, SSID-open-core,
SSID-orchestrator) widerspiegeln — API-Referenzen immer mit Source of Truth abgleichen.

## VERBOTENE PFADE
- Andere Repos (SSID, SSID-EMS, SSID-open-core, SSID-orchestrator)
- .git/ direkt beschreiben
- Globale .ssid-system/ Dateien ohne L0-Freigabe

## STACK
- Astro 5.x + Starlight (statische Site-Generierung)
- MDX (Markdown mit JSX-Erweiterungen)
- pnpm (Package Manager, Version in package.json packageManager)
- I18N (Mehrsprachigkeit — Vollstaendigkeit aller Sprachversionen pruefen)

## PORTS
| Service      | Local (C) | Workspace (G) |
|--------------|-----------|---------------|
| Docusaurus   | 3002      | 3102          |
| SSID-docs    | 4321      | 4331          |

Keine anderen Ports belegen. Port-Guard ist aktiv.

## QUALITAETSSICHERUNG
- MDX-Syntax vor jedem Merge pruefen
- I18N-Vollstaendigkeit sicherstellen (alle Sprachversionen aktuell)
- Interne Links auf Integritaet pruefen
- API-Referenzdocs mit Quell-Repos synchronisieren

## SCOPE-DISZIPLIN
- Nur das tun, was explizit beauftragt ist. Nicht "vorarbeiten" oder "mitliefern".
- Wenn der Auftrag "nur Baseline" sagt, keine Content-Expansion starten.
- Im Zweifel den engeren Scope waehlen.
- Scope-Erweiterung nur mit expliziter User-Freigabe.

## VERIFY-PFLICHT
Kein Commit und keine Fertig-Meldung ohne:
1. pnpm build PASS
2. pnpm test PASS
3. Dev-Server auf Workspace-Port 4331 gestartet
4. Route-Sweep aller neuen/geaenderten Seiten (HTTP 200)
5. CSP im HTML-Output geprueft (wenn konfiguriert)
Build allein ist NICHT ausreichend. Runtime-Verify ist Pflicht.

## STARLIGHT-REGELN
- Aside-Komponente: nur type="note", "tip", "caution", "danger"
- NICHT erlaubt: "important", "warning", "info", "success"
- Build schlaegt bei ungueltigen Aside-Typen fehl.

## REGULATORISCHE SPRACHE
- Kein "bonus multiplier" → "token-preference adjustment" oder "conversion incentive offset"
- Kein "fair-growth" → "fair-distribution"
- Kein "returned to user" (impliziert vorherige Custody) → "verbleibt beim User"
- Kein "investment", "returns", "profit", "guaranteed"
- Token = utility/governance ONLY. Developer = Code Publisher, NOT Operator.
- Stablecoin-Referenzen als "(hypothetisch, nicht geplant)" markieren.

## SAFE-FIX
SAFE-FIX ist permanent aktiv (NON-INTERACTIVE, SHA256-geloggt).
Alle Schreibvorgaenge werden im Evidence-Verzeichnis protokolliert.
