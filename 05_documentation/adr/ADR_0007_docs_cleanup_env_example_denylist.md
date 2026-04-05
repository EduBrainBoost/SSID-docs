# ADR-0007: SSID-docs Cleanup -- .env.example + denylist-gate Ausnahme

## Status
Accepted

## Datum
2026-04-05

## Autoren
Auto-Swarm (78_docs_adr Agent)

## Kontext

Im Rahmen des Auto-Swarm-Laufs 2026-04-05 wurden folgende Aenderungen in SSID-docs vorgenommen:

1. 8 Duplikat-Dateien mit `(1)`-Suffix (Explorer/OneDrive-Sync-Artefakte) geloescht
2. `.env.example` als Dokumentationsartefakt hinzugefuegt
3. `denylist-gate` CI-Workflow um Ausnahme fuer `.env.example` und `.env.sample` erweitert

Die Aenderung am CI-Workflow (`denylist-gate`) loest die ADR-Pflicht gemaess
ADR-0001 (Integrator Merge Checks) aus.

## Entscheidung

- Duplikate werden geloescht (kein inhaltlicher Verlust, reine Sync-Artefakte)
- `.env.example` ist eine Dokumentationsdatei (kein Secret), daher erlaubt
- `denylist-gate` Pattern `\.env\.` bleibt aktiv fuer echte Secrets;
  `.env.example` und `.env.sample` werden via `ALLOWED_SUFFIXES` ausgenommen

## Konsequenzen

- CI `denylist-gate` ist jetzt toleranter gegenueber Beispiel-Env-Dateien
- Zukuenftige `.env.example` Dateien erfordern keine CI-Anpassung mehr
- `.env.production`, `.env.local` etc. bleiben weiterhin verboten
- Kein Sicherheitsrisiko: `.env.example` enthaelt ausschliesslich Platzhalter,
  keine realen Credentials

## Alternativen

1. **Keine Ausnahme, `.env.example` umbenennen** -- Abgelehnt, da `.env.example`
   ein weit verbreiteter Konventionsname ist und Entwicklern sofort signalisiert,
   welche Umgebungsvariablen benoetigt werden.
2. **denylist-gate komplett deaktivieren** -- Abgelehnt, da der Gate echte
   Secret-Leaks verhindert und nur minimal angepasst werden muss.
