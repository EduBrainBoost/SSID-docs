# SOCIAL WORKFLOW SYSTEM (SWS) — V1 BUILD SPEC v1.0

Status: Build specification  
Scope: implementierbarer V1-Rollout im SSID-Stil  
Depends on: `SOCIAL_WORKFLOW_SYSTEM_FOUNDATION_SPEC_v1.0.md`

---

## 1. Ziel von V1

V1 liefert eine produktionsnahe, aber bewusst geschnittene Analyseplattform.

V1 baut **kein vollständiges Daily Content Studio** und **kein vollautomatisches Rendering-/Publishing-Ökosystem**.  
V1 muss stattdessen zuverlässig folgende Kernleistung erbringen:

- Video/URL sicher entgegennehmen
- Rechte klassifizieren
- Video/Audio/Text/Captions deterministisch analysieren
- Blueprint erzeugen
- Ergebnisse im EMS sichtbar machen
- Auditierbar speichern

---

## 2. V1 Scope

### MUST

1. URL- und File-Upload-Ingest
2. Rights Gate mit manueller Policy-Konfiguration
3. Format-Normalisierung via ffmpeg/ffprobe
4. Shot/Scene Detection
5. Audio Map + Basissignal-Analyse
6. Transcript mit Timestamps
7. OCR/Caption Layer Extraction
8. Hook-/CTA-Fingerprint
9. `rebuild_blueprint.json` Compiler
10. JOB-LOCK + Attempt-Modell
11. RBAC-Grundmodell (`operator`, `producer`, `governor`)
12. Audit-Log für Rights-/Compliance-Entscheidungen
13. Browser-App: `New Analysis Job`, `Job Queue`, `Blueprint Viewer`
14. CLI: `analyze-url`, `analyze-file`, `build-blueprint`
15. automatische Löschung des Quellvideos nach 72h

### SHOULD

1. Visual Style Fingerprint V1
2. Thumbnail Fingerprint V1
3. Blueprint-Library mit Volltextsuche
4. Basis-Compliance-Report

### NOT V1

1. Daily Content Studio
2. Similarity QA
3. Variant Generator
4. automatisches Final Rendering
5. automatisiertes Publish Bundle
6. Plattform-Metrikimport
7. semantischer Vector Index

---

## 3. V1 Deliverables nach Repo

## 3.1 `SSID-open-core`

### Pflicht

- JSON Schemas:
  - `job_manifest.schema.json`
  - `attempt_manifest.schema.json`
  - `source_manifest.schema.json`
  - `rights_manifest.schema.json`
  - `media_technical.schema.json`
  - `transcript_master.schema.json`
  - `shot_timeline.schema.json`
  - `caption_layers.schema.json`
  - `audio_map.schema.json`
  - `hook_fingerprint.schema.json`
  - `rebuild_blueprint.schema.json`
- Python Library Modules:
  - intake models
  - artifact repositories interfaces
  - shot analyzer
  - transcript adapter interface
  - OCR adapter interface
  - hook/CTA fingerprint compiler
  - blueprint compiler
- validator package für Schema- und Contract-Checks
- Golden fixture loader für Tests

### Acceptance

- alle Schemas Draft-07 validierbar
- blueprint compiler liefert bei Fixture-Inputs deterministische JSON-Outputs
- kein Modul schreibt direkt in produktive Stores ohne Repository Interface

## 3.2 `SSID-orchestrator`

### Pflicht

- Job DAG `analyze_url`
- Job DAG `analyze_file`
- Stage Executor für:
  - rights_check
  - ingest
  - video_analysis
  - audio_analysis
  - transcript
  - ocr
  - narrative_hook
  - blueprint_compile
- Retry Engine
- DLQ Baseline
- `job_events.jsonl` writer
- Trace/Metric hooks

### Acceptance

- jeder Stage-Wechsel erzeugt Event-Log
- Retry erzeugt neuen `attempt_id`
- DLQ-Eintrag bei erschöpftem Budget
- abgeschlossene Stage wird beim Retry nicht erneut ausgeführt

## 3.3 `SSID-EMS`

### Pflicht

- Screen: `New Analysis Job`
- Screen: `Job Queue`
- Screen: `Blueprint Viewer`
- RBAC-basierte Sichtsteuerung
- Job Detail View:
  - Status
  - Attempts
  - Artefaktliste
  - Rights Status
  - Fehleranzeige

### Acceptance

- Jobstart via URL oder Upload
- Live-Statusanzeige je Stage
- Blueprint JSON und strukturierte Visualisierung verfügbar
- governor sieht Rights-/Compliance-Entscheidungen

## 3.4 `SSID-docs`

### Pflicht

- Foundation Spec
- Ergänzungsdokument
- V1 Build Spec
- Operator Runbook
- Rights Gate Policy Guide
- Artifact Contracts Guide

### Acceptance

- alle Runbooks referenzieren kanonische Artefakte und States
- keine widersprüchlichen Statusmodelle zwischen Docs und Runtime

## 3.5 `SSID`

### Pflicht

- zentrale Governance-Referenz für SWS Rights/Compliance/Audit
- Policy-Verankerung für Audit-Store, Retention, Rollen
- ggf. zentrales Rego/Policy-Contract für Rights Classes

### Acceptance

- SWS kann zentrale Policy konsumieren, ohne eigene Schatten-Governance aufzubauen

---

## 4. Shard-Reihenfolge für V1

### Wave 1 — Contracts & Docs

- SWS Foundation Spec
- V1 Build Spec
- Schemas in `SSID-open-core`
- Doku in `SSID-docs`
- zentrale Policy-Anbindung in `SSID`

### Wave 2 — Analyzer Core

- Ingest
- Shot detection
- Transcript adapter
- OCR adapter
- Hook/CTA fingerprint
- Blueprint compiler

### Wave 3 — Orchestration

- DAGs
- Event logging
- Retry/DLQ
- Observability baseline

### Wave 4 — EMS UI

- New Analysis Job
- Queue
- Blueprint Viewer
- Role-based views

### Wave 5 — Hardening

- Golden tests
- integration tests
- Playwright smoke
- retention enforcement
- SLA measurement

---

## 5. Canonical CLI v1

```bash
sws analyze-url <url>
sws analyze-file <path>
sws build-blueprint <job_id>
sws show-job <job_id>
sws retry-job <job_id>
sws export-artifacts <job_id>
```

### CLI-Regeln

- kein stilles Überschreiben von Artefakten
- jeder Kommando-Lauf schreibt Attempt- und Event-Spuren
- Fehlercode-Mapping muss konsistent zur Runtime sein

---

## 6. Artefakt-Minimum je erfolgreichem V1-Analysejob

Pflichtoutputs:

- `job_manifest.json`
- `job_events.jsonl`
- `attempt_manifest.json`
- `source_manifest.json`
- `rights_manifest.json`
- `media_technical.json`
- `transcript_master.json`
- `shot_timeline.json`
- `caption_layers.json`
- `audio_map.json`
- `hook_fingerprint.json`
- `rebuild_blueprint.json`

Optional V1 SHOULD:

- `visual_fingerprint.json`
- `thumbnail_fingerprint.json`
- `compliance_report.json`

---

## 7. V1 Gates

## G1 Contract Gate

PASS wenn:

- alle Pflichtschemas vorhanden
- Draft-07-Validierung grün

## G2 Analyzer Gate

PASS wenn:

- Fixture-Video in Shot/Transcript/OCR/Audio/Hook-Artefakte zerlegt wird
- deterministische Re-Run-Stabilität gegeben ist

## G3 Blueprint Gate

PASS wenn:

- `rebuild_blueprint.json` aus Pflichtinputs erzeugt wird
- Segmentstruktur, Hook und CTA vorhanden sind

## G4 Orchestration Gate

PASS wenn:

- Job-State korrekt fortschreitet
- Retry/DLQ funktionieren
- Event-Log append-only geschrieben wird

## G5 EMS Gate

PASS wenn:

- User Job starten, verfolgen und Blueprint einsehen kann
- RBAC-Beschränkungen greifen

## G6 Retention/Audit Gate

PASS wenn:

- Quellvideo-Löschung automatisiert ist
- Audit-Events append-only geschrieben werden

---

## 8. Teststrategie V1

### Unit

- Schema validation
- Analyzer module tests
- blueprint compiler deterministic tests

### Golden Tests

- synthetische/lizenzfreie Referenzvideos
- versionierte Referenz-JSONs
- Abweichung nur per expliziter Freigabe

### Integration

- analyze_url/file → blueprint roundtrip
- retry and DLQ flow
- retention worker deletes source after TTL

### UI

- Job anlegen
- Queue Status beobachten
- Blueprint öffnen

---

## 9. Runtime/Infra Baseline V1

- 1 API service
- 1 orchestrator worker
- 1 ingest/analyzer worker pool
- 1 transcript-capable node (GPU empfohlen, CPU fallback erlaubt für V1 Testbetrieb)
- Postgres für Job/Metadata
- Object Storage für Media/Artefakte
- separater Audit Store

Secrets ausschließlich via Secret Store / mounted secret files / short-lived service credentials. Keine Repo-Secrets.

---

## 10. Ausschlusskriterien

V1 ist nicht abgeschlossen, wenn eines der folgenden Probleme besteht:

- Job-Retry überschreibt Artefakte früherer Attempts
- Klartext-Quell-URL wird dauerhaft gespeichert
- Rights Gate ist optional statt blockierend
- Blueprint Compiler erzeugt nicht-deterministische Pflichtfelder
- EMS zeigt Jobstatus nur pauschal statt stage-basiert
- kein Audit-Eintrag für Rights-/Compliance-Entscheidungen

---

## 11. Abschlusskriterium V1

V1 gilt als erreicht, wenn:

1. ein URL- oder File-Job erfolgreich gestartet werden kann
2. der Job deterministisch bis `ANALYZED` läuft
3. alle Pflichtartefakte erzeugt und schema-validiert werden
4. `rebuild_blueprint.json` erzeugt wird
5. EMS den Job und Blueprint sichtbar macht
6. Audit/Retention/RBAC baseline aktiv ist
7. Golden- und Integration-Tests grün sind

