# SOCIAL WORKFLOW SYSTEM (SWS) — FOUNDATION SPEC v1.0

Status: Draft for canonical adoption  
Scope: SSID-style foundation specification for the Social Workflow System  
Depends on: Hauptspezifikation „Expertenstruktur und Zielarchitektur für das Social Workflow System“, Ergänzungsdokument „SWS Architektur-Ergänzung & Gap-Schließung v1.0"

---

## 1. Zweck

SWS ist das deterministische Social-Content-Intelligence-Subsystem im SSID-Ökosystem.

SWS zerlegt Fremd- oder Eigenvideos in reproduzierbare Strukturartefakte, kompiliert daraus Blueprints und nutzt diese Blueprints, um mit eigenen oder lizenzierten Assets neue Inhalte zu erzeugen.

SWS ist **kein Asset-Klon-System**. Es arbeitet auf Struktur-, Timing-, Hook-, CTA-, Caption-, Motion- und Stil-Fingerprint-Ebene. Fremdassets dürfen analysiert, aber ohne Freigabe nicht wiederverwendet werden.

---

## 2. Nicht verhandelbare Invarianten

1. **Determinismus vor Kreativität**  
   Alle nicht-generativen Stages müssen bei identischem Input und identischer Konfiguration identische Outputs erzeugen.

2. **Additive Writes only**  
   Kein kanonisches Artefakt wird destruktiv überschrieben. Statusänderungen werden event-sourced oder als versionierte Snapshots gespeichert.

3. **JOB-LOCK / Isolation**  
   Jeder Job läuft in vollständig isoliertem Kontext. Cross-Job-Dateizugriffe sind verboten. Zulässig sind nur ID-basierte Referenzen auf Library-Artefakte.

4. **Rights-first**  
   Kein Rebuild, kein Publish-Pack und kein Library-Write ohne erfolgreiches Rights-/Compliance-Gate.

5. **Asset-Provenance Pflicht**  
   Jeder im Rebuild verwendete Asset-Ref benötigt Herkunft, Lizenzstatus und Freigabestatus.

6. **Auditierbarkeit**  
   Jede Rechte-, QA-, Compliance-, Publish- und Policy-Entscheidung muss append-only protokolliert werden.

7. **SoT/Impl-Trennung**  
   SWS-Artefakte folgen SSID-Hybrid: `chart.yaml` beschreibt Capability und Governance, `manifest.yaml` beschreibt konkrete Implementierung.

---

## 3. Betriebsmodi

| Modus | Zweck | Fremdasset-Regel |
|---|---|---|
| ANALYZE | Zerlegung, Fingerprint, Blueprint | Analyse erlaubt gemäß Rights Class |
| REBUILD | Strukturtreuer Neuaufbau mit eigenen/lizenzierten Assets | keine Fremdasset-Wiederverwendung ohne Freigabe |
| CREATE | Neuer Content aus bestehender Blueprint-Library | nur eigene/lizenziert freigegebene Assets |
| QA | Similarity-, Compliance-, Quality-Prüfung | read-only |
| PUBLISH_PREP | Exportbundle, Metadaten, Scheduling-Artefakte | read-only auf Final-Artefakten |

---

## 4. Layer-Modell L0–L5

| Layer | Name | Verantwortung |
|---|---|---|
| L5 | Governance & Compliance | Rights Gate, Policy, Audit, DSGVO, RBAC, Freigaben |
| L4 | Orchestration & Operations | DAGs, Queue, Retry, DLQ, Batch, Monitoring Hooks |
| L3 | Intelligence & Production | Analyse-/Rebuild-Logik, Prompting, Script, Blueprint, Varianten |
| L2 | Media Processing | Video/Audio/OCR/ASR/Fingerprint/Timeline/Render |
| L1 | Ingest & Normalization | URL/Upload, Hashing, Metadaten, Format-Normalisierung |
| L0 | Storage & Infrastructure | Postgres, Object Storage, Vector/Search, Audit Store, Auth, Secrets |

### Zugriffsregeln

- Jede Schicht ruft ausschließlich die direkt darunterliegende Schicht auf.
- L5 darf alle Schichten lesen, aber nur L4 steuern.
- Schreibzugriffe auf L0 laufen ausschließlich über definierte Repository Interfaces.
- L2-Module sind zustandslos.

---

## 5. Kanonische Shards

| Shard | Zweck |
|---|---|
| `sws-intake` | URL/File Intake, Rights-Vorprüfung, Hashing |
| `sws-media-analyzer` | Shot, Audio, Transcript, OCR |
| `sws-fingerprint-compiler` | Hook, Narrative, Style, Thumbnail, Caption Patterns |
| `sws-blueprint-compiler` | Aggregation aller Analyseartefakte zu `rebuild_blueprint.json` |
| `sws-replacement-engine` | Brand-/Asset-Mapping, Script Reconstruction |
| `sws-render-engine` | Timeline Builder, FFmpeg-Render |
| `sws-qa-engine` | Similarity, Compliance, Render-Readiness |
| `sws-asset-registry` | Asset-Provenance, Lizenzstatus, Brand Assets |
| `sws-blueprint-library` | Suchbare Blueprint-Bibliothek |
| `sws-publish-packager` | Exportbundle je Plattform |
| `sws-daily-studio` | Blueprint-basierte Tagesproduktion |

### Pflicht je Shard

- `chart.yaml`
- `manifest.yaml`
- Contract/Schemas
- Tests
- Evidence Strategy
- Registry Entry
- Observability Hooks

---

## 6. Job- und Run-Modell

### 6.1 Korrektur der Additiv-Regel

Ein mutierendes `job_manifest.json` ist **nicht SSID-konform**, wenn es überschrieben wird.

Deshalb gilt:

- `job_manifest.json` = initialer unveränderlicher Job-Header
- `job_events.jsonl` = append-only Ereignisstrom für Status, Stage-Fortschritt, Fehler, Entscheidungen
- `job_state_view.json` = optionale materialisierte Sicht, jederzeit aus `job_manifest.json + job_events.jsonl` rekonstruierbar; nicht kanonisch
- `attempt_manifest.json` je Retry-Run innerhalb des Jobs

### 6.2 IDs

- `job_id` = logische Business-Entität
- `attempt_id` = konkreter technischer Lauf eines Jobs
- `blueprint_id` = Library-Artefakt
- `asset_id` = referenzierbares Asset

### 6.3 Statusautomat

`CREATED → RIGHTS_CHECK → INGEST → ANALYZING → ANALYZED → REBUILD_PENDING → REBUILDING → REBUILT → QA_PENDING → QA_COMPLETE → PUBLISH_READY → PUBLISHED`

Zusätzlich:

- jeder Status darf nach `FAILED` übergehen
- `FAILED → RETRY_PENDING → new attempt_id`
- abgeschlossene Attempts bleiben unveränderlich

---

## 7. Rechte- und Risikomodell

| Rights Class | Bedeutung | Erlaubte Modi |
|---|---|---|
| R0_INTERNAL | eigenes Material | ANALYZE, REBUILD, CREATE, PUBLISH_PREP |
| R1_LICENSED | lizenziertes Material | gemäß Lizenz, standardmäßig alle außer verbotene Reuse-Fälle |
| R2_ANALYZE_ONLY | Drittmaterial nur Analyse | ANALYZE, QA |
| R3_HIGH_RISK | unklar/heikel | nur nach Governor Review |
| R4_BLOCKED | unzulässig | kein Processing außer minimaler Dokumentation |

### Verbindliche Regel

- Library-Write nur bei freigegebenem Compliance-Status
- Publish-Pack blockiert bei `R3/R4`
- Rebuild blockiert bei `R2/R3/R4`, sofern keine ausschließlich eigenen/lizenzierten Zielassets und kein verletzter Policy-Fall vorliegen

---

## 8. Kanonische Artefakte

### Analyse

- `source_manifest.json`
- `rights_manifest.json`
- `media_technical.json`
- `transcript_master.json`
- `shot_timeline.json`
- `caption_layers.json`
- `audio_map.json`
- `beat_map.json`
- `hook_fingerprint.json`
- `visual_fingerprint.json`
- `style_fingerprint.json`
- `thumbnail_fingerprint.json` (optional V1.0 SHOULD)
- `rebuild_blueprint.json`

### Rebuild

- `replacement_plan.json`
- `script_blueprint.json`
- `brand_profile.json`
- `locale_variants.json`
- `rebuild_timeline.json`

### QA / Publish

- `qa_similarity.json`
- `compliance_report.json`
- `publish_bundle.json`
- `performance_signal.json` (V2)

### Contract-Invarianten je Artefakt

Pflichtfelder:

- `schema_version`
- `job_id`
- `attempt_id` (außer Library-Artefakte ohne Attempt-Bezug)
- `created_at_utc`
- `producer_module`
- `input_refs[]`
- `output_hash`
- `status`

---

## 9. Artifact Layout

```text
/jobs/{job_id}/
  job_manifest.json
  job_events.jsonl
  attempts/
    /{attempt_id}/
      attempt_manifest.json
      source/
      artifacts/
      rebuild/
      qa/
      publish/
      logs/
```

Regeln:

- kein Cross-Job-Pfadzugriff
- kein Überschreiben abgeschlossener Attempt-Artefakte
- Versionierung über neue Attempts oder neue versionspezifische Unterordner

---

## 10. RBAC

| Rolle | Analyze | Rebuild | Library Read | Library Write | QA Approve | Publish | Admin |
|---|---:|---:|---:|---:|---:|---:|---:|
| viewer | - | - | ✓ | - | - | - | - |
| operator | ✓ | ✓ | ✓ | - | - | - | - |
| producer | ✓ | ✓ | ✓ | ✓ | - | - | - |
| reviewer | ✓ | - | ✓ | - | ✓ | - | - |
| publisher | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| governor | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | partial |
| admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Zusatzregeln:

- Vier-Augen-Prinzip für QA-Freigaben
- Blueprint-Library-Schreibzugriff nur bei `compliance_report = APPROVED`
- Publish nur bei gültigem `publish_bundle.json` und `QA_COMPLETE`

---

## 11. Retry, Fehler, DLQ

### Fehlerklassen

- `E-RIGHTS-*` nicht retryable
- `E-INGEST-*` retryable
- `E-MEDIA-*` meist nicht retryable
- `E-ANALYZE-*` retryable begrenzt
- `E-LLM-*` retryable
- `E-RENDER-*` retryable begrenzt
- `E-QA-*` nicht retryable ohne menschliche Intervention
- `E-STORAGE-*` retryable
- `E-POLICY-*` nicht retryable

### DLQ-Regeln

- erschöpftes Retry-Budget → DLQ-Eintrag
- tägliche Operator-Sichtung
- Policy/Rights-Fälle direkt an Governor
- Re-Submission erzeugt neuen `attempt_id`

---

## 12. Observability

Pflicht:

- OpenTelemetry-Spans je Job und Stage
- strukturierte JSON-Logs je Attempt
- Prometheus-Metriken für Jobstatus, Dauern, Fehler, DLQ, Blueprint-Reuse, Tokenverbrauch

SLA-Größen gemäß Ergänzungsdokument gelten als Baseline ab V1.5.

---

## 13. DSGVO / Retention

- Quellvideo: automatische Löschung nach max. 72h
- PII-flagged Transcript-Segmente: 30 Tage
- Analyseartefakte ohne PII: 12 Monate
- Rebuild-Assets: bis zur expliziten Löschung
- Audit-Logs: 7 Jahre, nicht manuell löschbar

Langzeitspeicher speichert keine Klartext-Quell-URL, sondern nur Hash/abgeleitete Metadaten.

---

## 14. Repo-Zuordnung

| Repo | Verantwortung |
|---|---|
| `SSID-EMS` | Browser-App, Queue, Review, Blueprint Viewer, Rebuild UI |
| `SSID-orchestrator` | DAGs, Queue, Worker, Retry, DLQ, Scheduling |
| `SSID-open-core` | Schemas, Contracts, Analyzer/Compiler-Libs, Timeline Builder |
| `SSID-docs` | Architektur, Runbooks, Policies, ADRs |
| `SSID` | Governance, Audit-Standards, zentrale Compliance/SoT-Regeln |

### Empfohlene kanonische Doku-Pfade

- `SSID-docs/sws/architecture/SOCIAL_WORKFLOW_SYSTEM_FOUNDATION_SPEC_v1.0.md`
- `SSID-docs/sws/architecture/SWS_Architektur_Ergaenzung_v1.0.md`
- `SSID-docs/sws/roadmap/SWS_V1_BUILD_SPEC_v1.0.md`

---

## 15. Foundation Gates

Ein SWS-Shard gilt nur als foundations-ready, wenn erfüllt:

1. Contract vorhanden und schema-validierbar
2. `chart.yaml` + `manifest.yaml` vorhanden
3. Tests vorhanden
4. Observability instrumentiert
5. Rights/Compliance-Einstieg definiert
6. Artifact Output dokumentiert
7. Registry-Entry vorhanden
8. Evidence-Strategie dokumentiert

---

## 16. Offene Erweiterungen ab V2/V3

- Daily Content Studio
- Performance Feedback Loop
- semantische Blueprint-Suche
- Multi-Locale Production
- automatisiertes Variant Testing
- API-basierter Plattform-Metrikimport

