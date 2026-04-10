# SSID-docs IA Normalization Report

**Date:** 2026-03-23
**Branch:** fix/ssid-docs-baseline-sot-ia-csp-lock

## Aenderungen

### Sidebar-Korrekturen (2)

| Aenderung | Begruendung |
|-----------|-------------|
| `tooling/local-stack` in Sidebar eingefuegt | Datei existiert, war nicht navigierbar |
| `research/permissionless-crypto-assets-2026-03` in Project-Sektion eingefuegt | Datei existiert, war nicht navigierbar |

### Inhaltliche Korrekturen (3)

| Datei | Aenderung | Begruendung |
|-------|-----------|-------------|
| `architecture/matrix.mdx` | 24 Root-Namen auf kanonische Liste aktualisiert | Veralteter Draft-Satz stimmte nicht mit SoT ueberein |
| `tooling/mission-control.mdx` | EMS-Akronym korrigiert: "Evidence Management System" → "External Management System" | SoT-Definition: EMS = user's private vault |
| `CLAUDE.md` | Stack korrigiert: "Docusaurus" → "Astro 5.x + Starlight" | Faktisch falsch |

### Config-Aenderung (1)

| Datei | Aenderung | Begruendung |
|-------|-----------|-------------|
| `astro.config.mjs` | CSP + Referrer-Policy via Starlight head config hinzugefuegt | Medium-Fund schliessen |

## Sidebar-Ergebnis

| Sektion | Vorher | Nachher | Delta |
|---------|--------|---------|-------|
| Overview | 1 | 1 | 0 |
| Architecture | 4 | 4 | 0 |
| Governance | 5 | 5 | 0 |
| Compliance | 4 | 4 | 0 |
| Tooling | 6 | 7 | +1 (local-stack) |
| Token | 2 | 2 | 0 |
| FAQ | 2 | 2 | 0 |
| Project | 5 | 6 | +1 (research) |
| **Gesamt** | **30** (8 Sektionen) | **32** (8 Sektionen) | **+2** |

## Dopplungen
Keine.

## Sackgassen
Keine. Alle 32 Sidebar-Eintraege verweisen auf existierende Dateien.

## EMS/SSID-Vermischung
Korrigiert in tooling/mission-control.mdx. EMS ist jetzt konsistent als "External Management System" definiert.

## Keine neuen Seiten erstellt
Dieser Lauf hat keine neuen Content-Seiten erstellt. Nur bestehende Seiten korrigiert und in die Navigation eingebunden.
