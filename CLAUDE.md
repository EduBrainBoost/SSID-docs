# SSID-docs — Repo-Regeln

## REPO-IDENTITAET
- Repo-Name: SSID-docs
- Repo-Pfad: C:\Users\bibel\SSID-Workspace\Github\SSID-docs
- Primaerer Branch: main
- Arbeits-Branches: develop, feature/*, fix/*

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

## SAFE-FIX
SAFE-FIX ist permanent aktiv (NON-INTERACTIVE, SHA256-geloggt).
Alle Schreibvorgaenge werden im Evidence-Verzeichnis protokolliert.
