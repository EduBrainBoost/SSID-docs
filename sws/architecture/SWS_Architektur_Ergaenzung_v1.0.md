# Social Workflow System — Architektur-Ergänzung & Gap-Schließung

**Version:** 1.0  
**Status:** Kanonisch  
**Ergänzt:** Expertenstruktur und Zielarchitektur für das Social Workflow System  
**Scope:** Alle in der Hauptspezifikation fehlenden oder unvollständigen Architekturabschnitte

---

## Inhalt

1. [Zweck und Abgrenzung](#1-zweck-und-abgrenzung)
2. [SWS Layer-Modell L0–L5](#2-sws-layer-modell-l0l5)
3. [Job-Isolation-Protokoll (JOB-LOCK)](#3-job-isolation-protokoll-job-lock)
4. [Idempotenz-Vertrag](#4-idempotenz-vertrag)
5. [Fehlende Artefakt-Schemas](#5-fehlende-artefakt-schemas)
   - 5.1 job_manifest.json
   - 5.2 rebuild_blueprint.json (vollständiges Feldschema)
   - 5.3 brand_profile.json
   - 5.4 platform_policy.json
   - 5.5 niche_registry.json
   - 5.6 performance_signal.json
   - 5.7 locale_variants.json
6. [Error-Handling, Retry-Policy und Dead Letter Queue](#6-error-handling-retry-policy-und-dead-letter-queue)
7. [Auth- und RBAC-Modell](#7-auth--und-rbac-modell)
8. [Data-Retention-Policy (DSGVO)](#8-data-retention-policy-dsgvo)
9. [Audit-Log-Schema](#9-audit-log-schema)
10. [V1-Scope-Neukalibration](#10-v1-scope-neukalibration)
11. [Analytics-Feedback-Loop](#11-analytics-feedback-loop)
12. [Observability-Stack](#12-observability-stack)
13. [Testing-Strategie](#13-testing-strategie)
14. [Deployment-Architektur](#14-deployment-architektur)

---

## 1. Zweck und Abgrenzung

Dieses Dokument ist ein kanonisches Ergänzungsdokument zur Hauptspezifikation *„Expertenstruktur und Zielarchitektur für das Social Workflow System"*. Es schließt alle im Review identifizierten Lücken und macht keine bestehenden Definitionen ungültig. Im Konfliktfall gilt die explizitere Definition dieses Dokuments.

Nicht Gegenstand dieses Dokuments: Rollenprofile, Pipeline-Beschreibungen und Browser-App-Screens, die bereits in der Hauptspezifikation hinreichend beschrieben sind.

---

## 2. SWS Layer-Modell L0–L5

Das Social Workflow System folgt einem sechsstufigen Layer-Modell analog zur SSID-Architektur. Jede Schicht hat exklusiv definierten Zugriff auf die darunterliegenden Schichten.

```
L5  Governance & Compliance
    Governor-Rolle, Rights-Gate, Compliance-QA, Audit-Logging,
    DSGVO-Enforcement, Platform-Policy-Management

L4  Orchestration & Operations
    SSID-orchestrator, Job-Queue, DAG-Ausführung, Retry-Logic,
    Dead Letter Queue, Batch-Scheduling, Monitoring-Hooks

L3  Intelligence & Production
    Analyse-Agenten, Rebuild-Agenten, Prompt-Engineer,
    Script-Reconstruction, Voice/Image/Video-Production,
    Blueprint-Compiler, Variant-Generator

L2  Media Processing
    Video-Analyzer, Audio-Analyzer, Transcript-Engine,
    OCR-Engine, Narrative-Engine, Style-Fingerprint-Engine,
    Asset-Replacement-Engine, Timeline-Builder, Render-Engine

L1  Ingest & Normalization
    URL-Intake-Gateway, Media-Ingestor, Metadata-Extractor,
    Format-Normalisierung, Hashing, Rights-Manifest-Erstellung

L0  Storage & Infrastructure
    Object Storage (Media), Postgres (Metadaten),
    Vector-Index (Blueprint-Suche), Audit-Log-Store,
    Secret-Management, Auth-Service
```

### Zugriffsregeln

- Jede Schicht darf ausschließlich die direkt darunterliegende Schicht aufrufen.
- L5 darf jede Schicht lesen, aber nur L4 steuern.
- Kein Modul in L1–L4 darf direkt auf L0-Stores schreiben; Schreibzugriff läuft ausschließlich über definierte Repository-Interfaces.
- L2-Module sind zustandslos. Sie empfangen einen Job-Kontext und schreiben Artefakte; sie halten keinen Prozess-State im Speicher zwischen zwei Stages.

---

## 3. Job-Isolation-Protokoll (JOB-LOCK)

Jeder Analyse- oder Production-Job läuft in einem vollständig isolierten Kontext. Dieses Protokoll ist das SWS-Äquivalent zu SSID SESSION-ISOLATION.

### Prinzip

Ein Job ist die atomare Arbeitseinheit des SWS. Kein Artefakt, kein Prozess-State und keine Konfiguration eines Jobs beeinflusst einen anderen Job. Cross-Job-Zugriff ist verboten außer über explizite Blueprint-Library-Referenzen.

### Job-Kontext-Struktur

```
/jobs/{job_id}/
  job_manifest.json          ← Pflicht: wird bei Job-Start erzeugt
  source/                    ← heruntergeladenes oder hochgeladenes Medium
  artifacts/                 ← alle Analyse-Artefakte
    source_manifest.json
    rights_manifest.json
    media_technical.json
    transcript_master.json
    shot_timeline.json
    caption_layers.json
    audio_map.json
    beat_map.json
    hook_fingerprint.json
    visual_fingerprint.json
    style_fingerprint.json
    rebuild_blueprint.json
  rebuild/                   ← Rebuild-Outputs
    replacement_plan.json
    script_blueprint.json
    prompt_pack/
    voice_pack/
    image_pack/
    rebuild_timeline.json
  qa/                        ← QA-Outputs
    qa_similarity.json
    compliance_report.json
  publish/                   ← Export-Outputs
    publish_bundle.json
  logs/                      ← Job-spezifisches Logging
    pipeline.log
    audit.log
```

### JOB-LOCK-Regeln

1. **Keine direkten Pfad-Referenzen** über Job-Grenzen hinweg. Blueprints aus der Bibliothek werden ausschließlich per `blueprint_id` referenziert, nicht per Dateipfad.
2. **Schreiboperationen sind additiv.** Bestehende Artefakte eines Jobs werden nicht überschrieben; bei Bedarf wird ein neuer Artefakt-Versionsordner (`artifacts_v2/`) angelegt.
3. **Job-State ist unveränderlich** sobald der Status `COMPLETED` oder `FAILED` erreicht ist.
4. **Parallele Jobs desselben Quell-URLs** sind zulässig und produzieren unabhängige Job-Verzeichnisse.

### Job-Status-Automat

```
CREATED → RIGHTS_CHECK → INGEST → ANALYZING → ANALYZED
       → REBUILD_PENDING → REBUILDING → REBUILT
       → QA_PENDING → QA_COMPLETE → PUBLISH_READY
       → PUBLISHED

Jeder Status kann zu FAILED übergehen.
FAILED → RETRY_PENDING (bei konfigurierbarem Retry-Budget)
RETRY_PENDING → CREATED (neuer Job-Start, gleiches job_id, inkrementierter attempt_count)
```

---

## 4. Idempotenz-Vertrag

Alle SWS-Pipelines sind deterministisch und idempotent.

**Definition:** Das erneute Ausführen eines Jobs mit identischem Input und identischer Konfiguration produziert byte-identische Artefakt-Inhalte (bei gleichem Modell-Checkpoint) oder strukturell äquivalente Inhalte (bei generativen Modellen mit fixiertem Seed).

### Anforderungen je Stage

| Pipeline-Stage | Idempotenz-Anforderung |
|---|---|
| Ingest / Hashing | Byte-identisch — Hash muss konstant sein |
| Shot/Scene Detection | Deterministisch — gleicher Algorithmus, gleiche Parameter |
| ASR / Transcript | Modell-deterministisch bei fixiertem Checkpoint und Seed |
| OCR | Deterministisch bei gleicher Engine-Version |
| Blueprint Compiler | Vollständig deterministisch — reine Aggregationsfunktion |
| Script Reconstruction | LLM-Seed wird im job_manifest gespeichert und bei Re-Run gesetzt |
| Render | Byte-identisch bei gleicher ffmpeg-Version und gleichem Timeline-Plan |
| Generative Assets (Bild, Voice) | Strukturell äquivalent — Seed wird gespeichert, nicht byte-identisch |

### Seed-Verwaltung

Jeder generative Schritt speichert seinen Seed in `job_manifest.json` unter `generation_seeds`. Bei Re-Run wird dieser Seed geladen, um Reproduzierbarkeit zu gewährleisten.

---

## 5. Fehlende Artefakt-Schemas

Alle Schemas sind in JSON Schema Draft-07 beschrieben und als Contracts verbindlich.

---

### 5.1 job_manifest.json

Übergeordnetes Job-Container-Artefakt. Wird bei Job-Start erstellt und kontinuierlich aktualisiert.

```json
{
  "job_id": "string (UUID v4)",
  "job_type": "ANALYZE | REBUILD | ANALYZE_AND_REBUILD | DAILY_CONTENT",
  "status": "CREATED | RIGHTS_CHECK | INGEST | ANALYZING | ANALYZED | REBUILD_PENDING | REBUILDING | REBUILT | QA_PENDING | QA_COMPLETE | PUBLISH_READY | PUBLISHED | FAILED",
  "attempt_count": "integer (default: 1)",
  "created_at": "ISO 8601 timestamp",
  "updated_at": "ISO 8601 timestamp",
  "completed_at": "ISO 8601 timestamp | null",
  "source": {
    "type": "URL | FILE_UPLOAD",
    "value": "string (URL oder Dateipfad)",
    "platform": "YOUTUBE | TIKTOK | INSTAGRAM | UPLOAD | OTHER",
    "sha256_hash": "string"
  },
  "config": {
    "brand_profile_id": "string | null",
    "niche_id": "string | null",
    "target_platforms": ["TIKTOK", "YOUTUBE_SHORTS", "IG_REELS"],
    "locale_primary": "de | en | es | ...",
    "locale_variants": ["de", "en"],
    "quality_preset": "DRAFT | STANDARD | PREMIUM"
  },
  "generation_seeds": {
    "script_reconstruction": "integer | null",
    "voice_generation": "integer | null",
    "image_generation": "integer | null"
  },
  "pipeline_stages": {
    "rights_check": { "status": "PENDING | RUNNING | DONE | SKIPPED | FAILED", "completed_at": "timestamp | null", "error": "string | null" },
    "ingest": { "status": "...", "completed_at": null, "error": null },
    "video_analysis": { "status": "...", "completed_at": null, "error": null },
    "audio_analysis": { "status": "...", "completed_at": null, "error": null },
    "transcript": { "status": "...", "completed_at": null, "error": null },
    "ocr": { "status": "...", "completed_at": null, "error": null },
    "narrative": { "status": "...", "completed_at": null, "error": null },
    "style_fingerprint": { "status": "...", "completed_at": null, "error": null },
    "blueprint_compile": { "status": "...", "completed_at": null, "error": null },
    "script_reconstruction": { "status": "...", "completed_at": null, "error": null },
    "asset_replacement": { "status": "...", "completed_at": null, "error": null },
    "render": { "status": "...", "completed_at": null, "error": null },
    "qa_similarity": { "status": "...", "completed_at": null, "error": null },
    "qa_compliance": { "status": "...", "completed_at": null, "error": null },
    "publish_bundle": { "status": "...", "completed_at": null, "error": null }
  },
  "artifacts": {
    "source_manifest": "path | null",
    "rights_manifest": "path | null",
    "rebuild_blueprint": "path | null",
    "qa_similarity": "path | null",
    "compliance_report": "path | null",
    "publish_bundle": "path | null"
  },
  "error": {
    "stage": "string | null",
    "code": "string | null",
    "message": "string | null",
    "retryable": "boolean"
  }
}
```

---

### 5.2 rebuild_blueprint.json (vollständiges Feldschema)

Der zentrale Contract des gesamten Systems. Jedes Rebuild-Modul arbeitet ausschließlich auf Basis dieses Artefakts.

```json
{
  "blueprint_id": "string (UUID v4)",
  "blueprint_version": "semver string (z.B. 1.0.0)",
  "created_from_job_id": "string (UUID v4)",
  "created_at": "ISO 8601 timestamp",
  "source_ref": {
    "platform": "YOUTUBE | TIKTOK | INSTAGRAM | UPLOAD",
    "url_hash": "SHA-256 des Quell-URLs (kein Klartext aus DSGVO-Gründen)",
    "channel_category": "string | null",
    "niche_tags": ["string"]
  },
  "technical": {
    "duration_seconds": "float",
    "fps": "float",
    "resolution": { "width": "integer", "height": "integer" },
    "aspect_ratio": "9:16 | 16:9 | 1:1 | 4:5",
    "audio_channels": "integer",
    "audio_sample_rate": "integer"
  },
  "structure": {
    "total_shots": "integer",
    "avg_shot_duration_seconds": "float",
    "shot_pattern": ["float"],
    "segments": [
      {
        "segment_id": "integer",
        "label": "HOOK | PROBLEM | AGITATION | SOLUTION | PROOF | CTA | OUTRO",
        "start_seconds": "float",
        "end_seconds": "float",
        "duration_seconds": "float",
        "function": "string (Beschreibung der dramaturgischen Aufgabe)"
      }
    ]
  },
  "hook": {
    "hook_type": "PATTERN_INTERRUPT | BOLD_CLAIM | PROBLEM_OPEN | TEASE | QUESTION | STORY",
    "window_start_seconds": "float",
    "window_end_seconds": "float",
    "trigger_mechanism": "string",
    "retention_value": "LOW | MEDIUM | HIGH"
  },
  "cta": {
    "instances": [
      {
        "cta_type": "SUBSCRIBE | FOLLOW | COMMENT | LIKE | LINK | PRODUCT | SOFT",
        "position_seconds": "float",
        "form": "VERBAL | CAPTION | OVERLAY | COMBINED",
        "text_template": "string | null"
      }
    ]
  },
  "audio": {
    "speech_ratio": "float (0–1)",
    "music_present": "boolean",
    "music_genre_tags": ["string"],
    "bpm": "float | null",
    "energy_profile": ["float"],
    "drop_positions_seconds": ["float"],
    "loudness_lufs": "float | null"
  },
  "visual": {
    "color_palette": ["hex string"],
    "dominant_mood": "ENERGETIC | CALM | DRAMATIC | PLAYFUL | PROFESSIONAL | DARK",
    "framing_primary": "CLOSE_UP | MEDIUM | WIDE | OVERHEAD | POV",
    "motion_cadence": "FAST | MEDIUM | SLOW",
    "broll_ratio": "float (0–1)",
    "text_overlay_density": "LOW | MEDIUM | HIGH",
    "meme_overlay_present": "boolean"
  },
  "caption_pattern": {
    "style": "WORD_BY_WORD | PHRASE | FULL_LINE | NONE",
    "entry_timing_offset_ms": "float",
    "exit_timing_offset_ms": "float",
    "position": "BOTTOM | CENTER | TOP",
    "font_class": "BOLD_CAPS | SANS_REGULAR | HANDWRITTEN | OTHER"
  },
  "thumbnail": {
    "layout_type": "FACE_TEXT | PRODUCT_TEXT | PURE_GRAPHIC | SPLIT_SCREEN",
    "text_block_count": "integer",
    "emotion_primary": "SHOCKED | HAPPY | SERIOUS | CURIOUS | ANGRY | NEUTRAL",
    "contrast_level": "LOW | MEDIUM | HIGH",
    "complexity": "SIMPLE | MODERATE | COMPLEX"
  },
  "rebuild_slots": [
    {
      "slot_id": "string",
      "slot_type": "SCRIPT_SEGMENT | VOICE_TAKE | IMAGE_INSERT | BROLL_CLIP | MUSIC_BED | CAPTION_BLOCK | OVERLAY_GRAPHIC",
      "segment_ref": "string (Verweis auf segments[].segment_id)",
      "start_seconds": "float",
      "end_seconds": "float",
      "content_constraints": "string (Beschreibung was hier inhaltlich hingehört)",
      "asset_ref": "null (leer, wird bei Replacement befüllt)"
    }
  ],
  "quality_signals": {
    "estimated_retention_score": "float (0–1, intern kalkuliert)",
    "hook_strength": "LOW | MEDIUM | HIGH",
    "structure_completeness": "float (0–1, Anteil befüllter Pflicht-Segmente)"
  },
  "library_metadata": {
    "blueprint_tags": ["string"],
    "niche_id": "string | null",
    "platform_fit": ["TIKTOK", "YOUTUBE_SHORTS", "IG_REELS"],
    "reuse_count": "integer (wird bei jedem Rebuild inkrementiert)",
    "last_used_at": "ISO 8601 timestamp | null"
  }
}
```

---

### 5.3 brand_profile.json

Kanonisches Marken-Artefakt. Wird beim Asset-Replacement und bei der Script-Reconstruction geladen.

```json
{
  "brand_id": "string (UUID v4)",
  "brand_name": "string",
  "version": "semver string",
  "created_at": "ISO 8601 timestamp",
  "updated_at": "ISO 8601 timestamp",
  "identity": {
    "tone_of_voice": "AUTHORITATIVE | FRIENDLY | HUMOROUS | INSPIRING | EDUCATIONAL",
    "formality_level": "INFORMAL | SEMI_FORMAL | FORMAL",
    "primary_language": "de | en | es | ...",
    "forbidden_terms": ["string"],
    "brand_keywords": ["string"],
    "usp_statements": ["string"]
  },
  "visual": {
    "primary_colors": ["hex string"],
    "secondary_colors": ["hex string"],
    "font_primary": "string",
    "font_secondary": "string | null",
    "logo_asset_id": "string | null",
    "brand_overlay_asset_id": "string | null"
  },
  "audio": {
    "jingle_asset_id": "string | null",
    "preferred_music_genres": ["string"],
    "forbidden_music_genres": ["string"],
    "voice_profile": {
      "gender": "MALE | FEMALE | NEUTRAL",
      "age_range": "YOUNG | MIDDLE | SENIOR",
      "accent": "string | null",
      "tts_model_id": "string | null",
      "voice_sample_asset_id": "string | null"
    }
  },
  "channels": {
    "tiktok_handle": "string | null",
    "youtube_channel_id": "string | null",
    "instagram_handle": "string | null"
  },
  "cta_defaults": {
    "primary_cta_text": "string",
    "secondary_cta_text": "string | null",
    "link_in_bio_url": "string | null"
  }
}
```

---

### 5.4 platform_policy.json

Technische und regulatorische Vorgaben je Plattform. Wird vom Compliance-Layer und beim Rendering geladen.

```json
{
  "policy_version": "semver string",
  "updated_at": "ISO 8601 timestamp",
  "platforms": {
    "TIKTOK": {
      "max_duration_seconds": 600,
      "min_duration_seconds": 1,
      "recommended_duration_seconds": [15, 30, 60],
      "aspect_ratio_primary": "9:16",
      "aspect_ratio_supported": ["9:16", "1:1"],
      "resolution_min": { "width": 540, "height": 960 },
      "resolution_recommended": { "width": 1080, "height": 1920 },
      "caption_auto_available": true,
      "max_hashtags": 30,
      "max_title_chars": 2200,
      "music_policy": "LICENSED_VIA_PLATFORM_OR_ORIGINAL_ONLY",
      "watermark_forbidden": true,
      "copyright_claim_risk": "HIGH"
    },
    "YOUTUBE_SHORTS": {
      "max_duration_seconds": 180,
      "min_duration_seconds": 1,
      "recommended_duration_seconds": [30, 60],
      "aspect_ratio_primary": "9:16",
      "aspect_ratio_supported": ["9:16"],
      "resolution_recommended": { "width": 1080, "height": 1920 },
      "caption_auto_available": true,
      "max_title_chars": 100,
      "max_description_chars": 5000,
      "music_policy": "YOUTUBE_AUDIO_LIBRARY_OR_ORIGINAL",
      "copyright_claim_risk": "HIGH"
    },
    "IG_REELS": {
      "max_duration_seconds": 540,
      "min_duration_seconds": 3,
      "recommended_duration_seconds": [15, 30, 60, 90],
      "aspect_ratio_primary": "9:16",
      "aspect_ratio_supported": ["9:16", "4:5", "1:1"],
      "resolution_recommended": { "width": 1080, "height": 1920 },
      "caption_auto_available": true,
      "max_caption_chars": 2200,
      "max_hashtags": 30,
      "music_policy": "LICENSED_VIA_META_OR_ORIGINAL",
      "copyright_claim_risk": "MEDIUM"
    }
  }
}
```

---

### 5.5 niche_registry.json

Kuratierte Nischen-Taxonomie des Content-Strategy-Leads.

```json
{
  "registry_version": "semver string",
  "updated_at": "ISO 8601 timestamp",
  "niches": [
    {
      "niche_id": "string (slug, z.B. finance-personal-de)",
      "label": "string",
      "language": "de | en | ...",
      "target_platforms": ["TIKTOK", "YOUTUBE_SHORTS"],
      "audience_profile": {
        "age_range": "18-24 | 25-34 | 35-44 | 45+",
        "pain_points": ["string"],
        "aspirations": ["string"]
      },
      "hook_pattern_ids": ["string"],
      "cta_pattern_ids": ["string"],
      "forbidden_topics": ["string"],
      "top_performing_blueprint_ids": ["string"]
    }
  ]
}
```

---

### 5.6 performance_signal.json

Rückkanal von Plattform-Metriken in die Blueprint-Bibliothek. Ermöglicht datengetriebene Blueprint-Verbesserung.

```json
{
  "signal_id": "string (UUID v4)",
  "blueprint_id": "string",
  "job_id": "string",
  "platform": "TIKTOK | YOUTUBE_SHORTS | IG_REELS",
  "published_at": "ISO 8601 timestamp",
  "measured_at": "ISO 8601 timestamp",
  "metrics": {
    "views": "integer | null",
    "watch_time_seconds_avg": "float | null",
    "retention_rate_pct": "float | null",
    "completion_rate_pct": "float | null",
    "like_rate_pct": "float | null",
    "comment_rate_pct": "float | null",
    "share_rate_pct": "float | null",
    "follow_rate_pct": "float | null",
    "ctr_pct": "float | null"
  },
  "performance_tier": "TOP | AVERAGE | BELOW_AVERAGE | FLOP",
  "signal_notes": "string | null"
}
```

---

### 5.7 locale_variants.json

Verwaltung mehrsprachiger Skript- und Caption-Varianten je Rebuild-Job.

```json
{
  "job_id": "string",
  "primary_locale": "de",
  "variants": [
    {
      "locale": "en",
      "script_asset_id": "string | null",
      "caption_asset_id": "string | null",
      "voice_asset_id": "string | null",
      "translation_method": "HUMAN | LLM | HYBRID",
      "review_status": "PENDING | APPROVED | REJECTED",
      "reviewed_by": "string | null",
      "reviewed_at": "ISO 8601 timestamp | null"
    }
  ]
}
```

---

## 6. Error-Handling, Retry-Policy und Dead Letter Queue

### Fehler-Kategorien

| Code-Präfix | Kategorie | Retryable | Eskalation |
|---|---|---|---|
| `E-RIGHTS-*` | Rights-Check-Fehler | Nein | Governor |
| `E-INGEST-*` | Download/Upload-Fehler | Ja (3x) | Operator |
| `E-MEDIA-*` | Medienformat-Fehler | Nein | Operator |
| `E-ANALYZE-*` | Analyse-Stage-Fehler | Ja (2x) | Operator |
| `E-LLM-*` | LLM-API-Fehler | Ja (3x) | Auto-Retry |
| `E-RENDER-*` | Render-Fehler | Ja (2x) | Operator |
| `E-QA-*` | QA-Fehler (Similarity/Compliance) | Nein | Compliance-Rolle |
| `E-STORAGE-*` | Storage-Fehler | Ja (5x) | Infrastructure |
| `E-POLICY-*` | Platform-Policy-Verletzung | Nein | Compliance-Rolle |

### Retry-Policy

```
Standard-Retry-Strategie: Exponential Backoff
  Basis-Wartezeit:  5 Sekunden
  Multiplikator:    2x je Attempt
  Maximale Wartezeit: 300 Sekunden
  Max. Attempts:    Per Fehler-Kategorie (siehe oben)

Bei Überschreitung des Retry-Budgets:
  1. Job-Status → FAILED
  2. Eintrag in Dead Letter Queue
  3. Notification an zuständige Rolle (gemäß Eskalations-Mapping)
  4. Audit-Log-Eintrag (Stage, Fehler-Code, Attempt-Count)
```

### Dead Letter Queue (DLQ)

Die DLQ ist ein persistenter Store für Jobs, die ihr Retry-Budget erschöpft haben.

```json
{
  "dlq_entry_id": "string (UUID v4)",
  "job_id": "string",
  "failed_stage": "string",
  "error_code": "string",
  "error_message": "string",
  "attempt_count": "integer",
  "first_failed_at": "ISO 8601 timestamp",
  "last_failed_at": "ISO 8601 timestamp",
  "assigned_to": "string | null",
  "resolution_status": "OPEN | IN_REVIEW | RESOLVED | DISCARDED",
  "resolution_notes": "string | null"
}
```

**DLQ-Verarbeitungsregeln:**

- DLQ-Einträge werden täglich um 08:00 Uhr dem Workflow App Operator gemeldet.
- Einträge mit `E-RIGHTS-*` oder `E-POLICY-*` werden dem Governor eskaliert.
- Einträge älter als 30 Tage ohne Resolution werden automatisch auf `DISCARDED` gesetzt und archiviert.
- Manuelle Re-Submission aus der DLQ erzeugt einen neuen Job mit `source_dlq_entry_id`-Referenz.

### Atomare Stage-Isolation

Schlägt eine Pipeline-Stage fehl, bleiben alle bereits erfolgreich abgeschlossenen Stages und ihre Artefakte erhalten. Ein Retry startet ausschließlich die fehlgeschlagene Stage und alle abhängigen Folgestages. Abgeschlossene Stages werden nicht neu ausgeführt.

---

## 7. Auth- und RBAC-Modell

### Rollen und Berechtigungen

| Rolle | Analyse starten | Rebuild starten | Blueprint-Lib lesen | Blueprint-Lib schreiben | QA freigeben | Veröffentlichen | Admin |
|---|---|---|---|---|---|---|---|
| `viewer` | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| `operator` | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| `producer` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| `reviewer` | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ |
| `publisher` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| `governor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Teilweise |
| `admin` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Authentifizierung

- Primäre Authentifizierung: SSO über SSID-Identity-Service (OIDC/OAuth2).
- API-Zugriff: JWT mit 1-Stunden-Ablaufzeit und Refresh-Token.
- CLI-Zugriff: API-Key mit konfigurierbarem Scope, rotierbar über Admin-Panel.
- Service-to-Service (interne Module): mTLS mit kurzlebigen Zertifikaten.

### Besondere Freigabe-Regeln

1. **QA-Freigabe** erfordert mindestens `reviewer`-Rolle und darf nicht von derselben Person erteilt werden, die den Rebuild-Job gestartet hat (Vier-Augen-Prinzip).
2. **Blueprint-Library-Schreibzugriff** ist an die Pflicht-Bedingung geknüpft, dass `compliance_report.json` den Status `APPROVED` trägt.
3. **Veröffentlichung** erfordert gültige `publish_bundle.json` und den Status `QA_COMPLETE` im `job_manifest.json`.

---

## 8. Data-Retention-Policy (DSGVO)

### Grundsätze

Das SWS verarbeitet Fremdmaterial (Videos Dritter) sowie potenziell personenbezogene Daten (Transkripte, Gesichter in Thumbnails). Die folgenden Regeln sind verbindlich und gelten zusätzlich zu den Governance-Regeln der Hauptspezifikation.

### Datenkategorien und Aufbewahrungsfristen

| Datenkategorie | Speicherort | Aufbewahrungsfrist | Lösch-Trigger |
|---|---|---|---|
| Quell-Video (Fremdinhalt) | Object Storage `/jobs/{id}/source/` | 72 Stunden nach Job-Abschluss | Automatisch |
| Analyse-Artefakte (kein PII) | Object Storage `/jobs/{id}/artifacts/` | 12 Monate | Manuell oder nach Ablauf |
| Rebuild-Assets (eigene Inhalte) | Object Storage `/jobs/{id}/rebuild/` | Unbegrenzt bis zur expliziten Löschung | Manuell |
| Publish-Bundles | Object Storage `/jobs/{id}/publish/` | 24 Monate | Manuell |
| Transkripte mit Personendaten | Sonderkennzeichnung in `transcript_master.json` | 30 Tage | Automatisch |
| Audit-Logs | Dedizierter Audit-Store | 7 Jahre | Nicht manuell löschbar |
| `job_manifest.json` | Postgres | 24 Monate | Manuell nach Ablauf |
| Performance-Signals | Postgres | 36 Monate | Automatisch nach Ablauf |

### Pflichten bei Quell-Video-Verarbeitung

1. Das Quell-Video wird **ausschließlich** für die Laufzeit des Analyse-Jobs im System gehalten.
2. Nach Abschluss des Analyse-Schritts oder spätestens 72 Stunden nach Ingest wird das Quell-Video automatisch gelöscht.
3. Der `source_manifest.json`-Eintrag enthält ausschließlich den SHA-256-Hash des Videos sowie nicht-personenbezogene Metadaten; keine Quell-URL im Klartext im Langzeitspeicher.
4. Transkript-Segmente, die Eigennamen oder biographische Informationen enthalten, werden als `pii_flagged: true` markiert und nach 30 Tagen automatisch gelöscht.

### Löschanfragen (Right to Erasure)

Löschanfragen für Jobs, die Inhalte Dritter betreffen, werden über die Governor-Rolle bearbeitet. Audit-Logs sind von Löschanfragen ausgenommen (Aufbewahrungspflicht).

---

## 9. Audit-Log-Schema

Jede Freigabe-, Compliance- und Rechte-Entscheidung wird im Audit-Log unveränderlich gespeichert.

```json
{
  "audit_id": "string (UUID v4)",
  "timestamp": "ISO 8601 timestamp",
  "actor_id": "string (User-ID oder Service-ID)",
  "actor_role": "string",
  "action": "RIGHTS_APPROVED | RIGHTS_REJECTED | QA_APPROVED | QA_REJECTED | COMPLIANCE_CLEARED | COMPLIANCE_FLAGGED | BLUEPRINT_PUBLISHED | JOB_STARTED | JOB_CANCELLED | PUBLISH_EXECUTED | POLICY_UPDATED | USER_ROLE_CHANGED",
  "job_id": "string | null",
  "blueprint_id": "string | null",
  "resource_type": "JOB | BLUEPRINT | POLICY | USER | PUBLISH_BUNDLE",
  "resource_id": "string",
  "decision": "APPROVED | REJECTED | FLAGGED | EXECUTED | CANCELLED",
  "rationale": "string | null",
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL | null",
  "platform_context": "TIKTOK | YOUTUBE_SHORTS | IG_REELS | ALL | null",
  "metadata": "object (erweiterbare Key-Value-Struktur für stage-spezifische Zusatzinfos)"
}
```

### Audit-Log-Invarianten

- Audit-Log-Einträge sind **append-only**. Kein Eintrag darf nach seiner Erstellung modifiziert oder gelöscht werden.
- Jede Schreiboperation im Audit-Store erzeugt einen kryptographischen Hashchain-Eintrag, der spätere Manipulation nachweisbar macht.
- Der Audit-Store ist physisch vom Applikations-Store getrennt und nicht über die Standard-API erreichbar.
- Zugriff auf den Audit-Store ist ausschließlich der `governor`- und `admin`-Rolle vorbehalten, und ausschließlich lesend.

---

## 10. V1-Scope-Neukalibration

Die Hauptspezifikation listet Daily Content Studio und Similarity QA als V1-MUST. Beide sind infrastrukturell zu komplex für eine initiale V1. Die folgende Einteilung ersetzt die MUST/SHOULD-Liste der Hauptspezifikation.

### V1.0 — Funktionsfähige Analyse-Pipeline (MVP)

**MUST:**
- URL- und File-Upload-Ingest
- Rights-Gate (manuell konfigurierbarer Policy-Check)
- Video/Audio/Text-Decomposition (Shot, Transcript, Audio-Map)
- OCR- und Caption-Layer-Extraktion
- Hook- und CTA-Fingerprint
- Blueprint-Compiler (vollständige `rebuild_blueprint.json`)
- Browser-App: New Analysis Job, Job Queue, Blueprint Viewer
- CLI: `analyze-url`, `analyze-file`, `build-blueprint`
- Job-Isolation-Protokoll (JOB-LOCK)
- RBAC-Grundmodell (operator, producer, governor)
- Audit-Log für Rights- und Compliance-Entscheidungen
- Automatische Quell-Video-Löschung nach 72 Stunden

**SHOULD:**
- Style-Fingerprint-Engine (visuell)
- Thumbnail-Fingerprint
- Basis-Compliance-Report (Risikostufe, keine automatische Claim-Erkennung)
- Blueprint-Library mit Suche (Volltextsuche, kein Vector-Index)

**NOT V1:**
- Daily Content Studio
- Similarity QA
- Variant-Generator
- Render-Engine (Timeline-Plan wird erstellt, Rendering manuell)
- Publish-Bundle-Automation

---

### V1.5 — Rebuild und QA-Basis

**MUST:**
- Script Reconstruction (LLM-basiert)
- Asset-Replacement-Workflow
- Timeline-Builder (deterministischer Plan)
- Render-Engine (ffmpeg-basiert)
- Similarity QA (strukturelle Metriken: Dauer, Shot-Count, Caption-Timing)
- Compliance-Report (automatische Watermark- und Copyright-Signale)
- Browser-App: Rebuild Studio, QA Console
- Publish-Bundle-Erzeugung
- Brand-Profile-Verwaltung

**SHOULD:**
- Voice-Production (TTS-Integration)
- Image-Generation-Integration
- Variant-Generator (A/B für Hook und CTA)

---

### V2.0 — Daily Content Operations und Analytics

**MUST:**
- Daily Content Studio (Blueprint-basierte Produktion ohne Fremdvideo)
- Performance-Signal-Integration (Plattform-Metriken → Blueprint-Bibliothek)
- Analytics-Feedback-Loop (Performance Intelligence Analyst)
- Vector-Index für semantische Blueprint-Suche
- Multi-Locale-Support (locale_variants.json)
- Batch-Analyse (mehrere URLs parallel)
- Full Observability-Stack

**SHOULD:**
- Video-Generationsmodell-Integration (Runway, Kling)
- Nischen-Registry mit automatischer Blueprint-Zuordnung
- A/B/C-Variant-Testing mit automatisierter Auswertung

---

## 11. Analytics-Feedback-Loop

### Neue Rolle: Performance Intelligence Analyst

Diese Rolle war in der Hauptspezifikation nicht vorgesehen, ist aber für den skalierten Betrieb essenziell.

**Verantwortlichkeiten:**
- Importiert Plattform-Metriken (Views, Retention, CTR) für veröffentlichte Inhalte.
- Generiert `performance_signal.json` je Blueprint und Platform.
- Klassifiziert Blueprints nach Performance-Tier (TOP / AVERAGE / BELOW_AVERAGE / FLOP).
- Pflegt `blueprint.library_metadata.reuse_count` und `top_performing_blueprint_ids` in der Nischen-Registry.
- Liefert wöchentliche Signal-Reports an Content-Strategy-Lead.

**Output:**
- `performance_signal.json` (Schema: siehe Abschnitt 5.6)
- Wöchentlicher `performance_summary_report.json` pro Nische

### Feedback-Loop-Architektur

```
Publish → Platform → Metriken-Import (manuell V2 / API V3)
    ↓
performance_signal.json erzeugen
    ↓
Blueprint-Library aktualisieren (reuse_count, performance_tier)
    ↓
Nichen-Registry: top_performing_blueprint_ids aktualisieren
    ↓
Daily Content Studio priorisiert TOP-Blueprints
```

### Platform-Metriken-Import (V2.0)

In V2.0 erfolgt der Import manuell über einen CSV-Upload im Operations-Panel. Eine direkte API-Integration mit TikTok Creator Marketplace API, YouTube Data API und Instagram Graph API ist für V3.0 vorgesehen.

---

## 12. Observability-Stack

### Telemetrie-Ebenen

**Traces (OpenTelemetry):**
- Jeder Job erzeugt einen übergeordneten Trace-Span.
- Jede Pipeline-Stage erzeugt einen Kind-Span mit Stage-Name, Job-ID, Dauer und Status.
- LLM-Aufrufe werden als eigene Spans erfasst (Model, Token-Count, Latency).
- Render-Aufrufe werden mit Dauer und Output-Dateigröße instrumentiert.

**Metriken (Prometheus-Format):**

```
sws_job_total{status="completed|failed|retried", job_type="analyze|rebuild|daily"}
sws_job_duration_seconds{stage="ingest|video|audio|transcript|ocr|narrative|blueprint|render|qa"}
sws_pipeline_stage_errors_total{stage="...", error_code="..."}
sws_blueprint_library_size_total
sws_blueprint_reuse_total{niche_id="..."}
sws_dlq_size_total
sws_render_output_bytes_total
sws_llm_tokens_total{model="...", stage="..."}
```

**Logs (strukturiertes JSON-Logging):**
- Jede Pipeline-Stage schreibt strukturierte Logs in `jobs/{id}/logs/pipeline.log`.
- Log-Level: ERROR, WARN, INFO, DEBUG (konfigurierbar per Stage).
- Zentrales Log-Aggregat (SSID-orchestrator) indiziert alle Job-Logs.

### SLA-Targets (V1.5)

| Stage | Target-Dauer | Alert-Schwelle |
|---|---|---|
| Ingest (1080p, 60 Sek.) | < 60 Sek. | > 120 Sek. |
| Video-Analyse | < 90 Sek. | > 180 Sek. |
| Audio-Analyse + Transcript | < 120 Sek. | > 240 Sek. |
| Blueprint-Compile | < 10 Sek. | > 30 Sek. |
| Render (60 Sek. Output) | < 180 Sek. | > 360 Sek. |
| Gesamter Analyse-Job | < 8 Min. | > 15 Min. |

---

## 13. Testing-Strategie

### Teststufen

**Unit-Tests (pytest):**
- Jedes Analyse-Modul (Video-Analyzer, Audio-Analyzer, etc.) hat eigene Unit-Tests.
- Alle JSON-Schema-Validierungen werden als parametrisierte Tests ausgeführt.
- Blueprint-Compiler: Property-Based Testing mit randomisierten Eingabe-Artefakten.

**Golden-File-Tests:**
- Für jeden Analyse-Typ wird ein Referenz-Video mit bekannten Eigenschaften als Testfixture gepflegt.
- Der Golden-File-Test vergleicht die erzeugte Artefakt-Struktur (nicht Asset-Inhalte) gegen ein versioniertes Referenz-JSON.
- Abweichungen vom Referenz-JSON erfordern explizite Genehmigung (Äquivalent zu SAFE-FIX: keine unangekündigten Strukturänderungen).

**Integration-Tests:**
- Analyse-zu-Blueprint-Roundtrip mit Minimal-Testvideo (synthetisch generiert, lizenzfrei).
- Blueprint-zu-Rebuild-Roundtrip mit Brand-Profile-Fixture.
- Similarity-QA-Pipeline: prüft, ob strukturelle Metriken innerhalb der definierten Toleranzen liegen.

**UI-Tests (Playwright):**
- Kritische Flows: New Analysis Job, Job Queue Status-Updates, Blueprint Viewer, QA-Freigabe.
- Smoke-Tests bei jedem Deploy.

### Test-Datenanforderungen

- Alle Testvideos sind synthetisch generiert oder lizenzfrei (CC0).
- Keine echten Drittanbieter-URLs in automatisierten Tests (Mock-Ingestor für CI).
- Transcript-Fixtures enthalten keine realen Personennamen.

### CI-Integration

```
Bei jedem Pull Request:
  → Unit-Tests (alle Module)
  → Schema-Validierung (alle Artefakt-Schemas gegen Draft-07)
  → Golden-File-Tests (Analyse-Pipeline)

Bei Merge in main:
  → Integration-Tests (Roundtrip)
  → UI Smoke-Tests (Playwright)
  → Performance-Regression-Test (Stage-Dauer gegen SLA-Targets)

Bei Release-Tag:
  → Vollständige Test-Suite inkl. End-to-End-Pipeline
  → Compliance-Report-Validierung
```

---

## 14. Deployment-Architektur

### Containerisierung

Jedes SWS-Modul wird als eigenständiger Docker-Container betrieben. Module mit hohem GPU-Bedarf (Transcript-Engine, Style-Fingerprint-Engine, Render-Engine) werden auf GPU-fähigen Nodes geplant.

```
sws-gateway          ← URL-Intake, Auth, Rate-Limiting
sws-rights-gate      ← Rights-Check, Policy-Anwendung
sws-ingestor         ← Download, Upload-Handler, ffmpeg
sws-video-analyzer   ← PySceneDetect, OpenCV (CPU/GPU)
sws-audio-analyzer   ← librosa, Stem-Separation (CPU/GPU)
sws-transcript       ← WhisperX (GPU)
sws-ocr              ← OCR-Engine (CPU)
sws-narrative        ← Narrative/Hook-Engine, LLM-Client (CPU)
sws-style-fp         ← Style-Fingerprint (GPU optional)
sws-blueprint        ← Blueprint-Compiler (CPU, zustandslos)
sws-script           ← Script-Reconstruction LLM-Client (CPU)
sws-render           ← ffmpeg Render-Engine (CPU/GPU)
sws-qa               ← Similarity + Compliance QA (CPU)
sws-publisher        ← Publish-Bundle-Generator (CPU)
sws-worker           ← SSID-orchestrator Job-Executor
sws-api              ← REST API (FastAPI)
sws-app              ← Browser-App (SSID-EMS, served via nginx)
```

### Umgebungen

| Umgebung | Zweck | Datenisolation |
|---|---|---|
| `dev` | Lokale Entwicklung | Vollständig isoliert, Mock-Ingestor |
| `staging` | Integration und QA | Eigene DB, kein Zugriff auf Produktiv-Blueprint-Library |
| `prod` | Produktionsbetrieb | Strikt isoliert, Audit-Log aktiv |

### Kapazitätsplanung (V1.0-Baseline)

- Gleichzeitige Jobs: 5 (skalierbar auf 20 durch zusätzliche Worker-Instanzen)
- GPU-Nodes: mindestens 1 (Transcript-Engine), empfohlen 2 (+ Style-Fingerprint)
- Object Storage: 500 GB initial, autoskalierend
- Postgres: 50 GB initial, Standard-Replikation

### Secret-Management

Alle API-Keys (LLM-Provider, Platform-APIs, TTS-Services) werden ausschließlich über einen Secret-Store (Vault-kompatibel) injiziert. Keine Secrets in Umgebungsvariablen oder Konfigurationsdateien im Repository.

---

*Dokumentende. Dieses Dokument ist kanonisch und wird im SSID-docs-Repository unter `/sws/architecture/SWS_Architektur_Ergaenzung_v1.0.md` gepflegt.*
