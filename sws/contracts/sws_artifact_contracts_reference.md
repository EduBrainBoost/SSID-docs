# SWS Artifact Contracts Reference

**Document Version:** 1.0  
**Last Updated:** 2026-04-16  
**Scope:** SSID-open-core SWS (Streaming Workflow System) artifact specifications  
**Primary Consumer:** Schema validators, artifact producers, retention policy enforcement

---

## Overview

This reference defines immutable contracts for all 13 artifacts in the SWS data pipeline. Each contract specifies:
- **Purpose:** Why this artifact exists
- **Producer Shard:** Which SSID-open-core shard generates it
- **Mandatory Fields:** Required properties with types
- **Retention Policy:** Lifecycle and deletion rules
- **Immutability Rules:** When/how artifact can be written
- **Example JSON:** Reference structure

All schemas are managed in `SSID-open-core/schemas/sws/`.

---

## 1. job_manifest.json

**Purpose:** Immutable job metadata. Single source of truth for job identity, timing, and resource allocation.

**Producer Shard:** `06_data_pipeline/shards/01_orchestration`

**Mandatory Fields:**

```
job_id: string (UUID v4, immutable)
job_name: string (max 255 chars, no special chars except -, _)
job_version: string (semantic versioning: major.minor.patch)
created_at: ISO8601 timestamp (UTC, set at creation, never modified)
created_by: string (user email or service account identifier)
job_status: enum (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
input_manifest_ref: string (path to source_manifest.json SHA256)
resource_allocation: object {
  cpu_cores: integer (1-128)
  memory_gb: integer (1-1024)
  max_duration_seconds: integer (60-3600)
  gpu_required: boolean
}
retry_policy: object {
  max_retries: integer (0-10)
  backoff_multiplier: number (1.0-5.0)
  initial_delay_ms: integer (100-10000)
}
tags: array of strings (max 50, max 50 chars each)
```

**Retention Policy:**
- Keep indefinitely
- Archive to cold storage after 90 days if job_status = COMPLETED
- Delete after 2 years from creation_at

**Immutability Rules:**
- Write ONCE at job creation
- Status field can be updated via state transitions (PENDING → RUNNING → COMPLETED/FAILED)
- No other fields can be modified after creation
- Hash-verify before status write: calculate SHA256 of current state, append status change, recalculate, log both

**Example:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_name": "video_intake_20260416_batch_001",
  "job_version": "2.1.0",
  "created_at": "2026-04-16T10:30:45.123Z",
  "created_by": "intake-service@ssid.internal",
  "job_status": "RUNNING",
  "input_manifest_ref": "sha256:abc123def456...",
  "resource_allocation": {
    "cpu_cores": 8,
    "memory_gb": 32,
    "max_duration_seconds": 1800,
    "gpu_required": true
  },
  "retry_policy": {
    "max_retries": 3,
    "backoff_multiplier": 2.0,
    "initial_delay_ms": 1000
  },
  "tags": ["batch_intake", "video_stream", "priority_high"]
}
```

**Schema Link:** `SSID-open-core/schemas/sws/job_manifest.json`

---

## 2. job_events.jsonl

**Purpose:** Append-only event log. Records every state change, error, milestone, and decision in the job pipeline.

**Producer Shard:** `06_data_pipeline/shards/02_event_logging`

**Mandatory Fields (per line):**

```
event_id: string (UUID v4, unique per job)
job_id: string (reference to job_manifest.job_id)
timestamp: ISO8601 timestamp (UTC)
event_type: enum (STATE_CHANGE, ERROR, MILESTONE, DECISION, METRIC, RETRY, CHECKPOINT)
event_level: enum (INFO, WARNING, ERROR, CRITICAL)
actor: string (service/user identifier)
details: object (variable structure based on event_type)
  - STATE_CHANGE: { previous_state, new_state, reason }
  - ERROR: { error_code, error_message, stack_trace (optional), recovery_action }
  - MILESTONE: { milestone_name, duration_ms, memory_peak_mb }
  - METRIC: { metric_name, metric_value, unit }
  - RETRY: { attempt_number, previous_error_code, delay_ms }
context_metadata: object {
  request_id: string (trace ID for distributed tracing)
  source_component: string (shard/module name)
  user_region: string (optional, geo-location)
}
```

**Retention Policy:**
- Append ONLY, never delete or modify
- Keep for 7 years minimum (legal/audit requirement)
- Query via line-range read (no full-file loads for performance)
- Compress to gzip after 6 months inactivity

**Immutability Rules:**
- Append-only JSONL format (one event per line)
- No line edits after write
- Sequential event_id ordering (descending timestamp for log search)
- Validate event_type enum before append

**Example (single line):**

```json
{"event_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6", "job_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2026-04-16T10:30:46.234Z", "event_type": "STATE_CHANGE", "event_level": "INFO", "actor": "orchestrator-core", "details": {"previous_state": "PENDING", "new_state": "RUNNING", "reason": "all_dependencies_satisfied"}, "context_metadata": {"request_id": "trace-abc-123", "source_component": "06_data_pipeline/shards/02_event_logging", "user_region": "eu-central-1"}}
```

**Schema Link:** `SSID-open-core/schemas/sws/job_events.jsonl`

---

## 3. attempt_manifest.json

**Purpose:** Immutable metadata for each retry attempt. One per retry; enables deterministic replay and failure forensics.

**Producer Shard:** `06_data_pipeline/shards/03_retry_management`

**Mandatory Fields:**

```
attempt_id: string (UUID v4, unique per job × attempt)
job_id: string (reference to job_manifest.job_id)
attempt_number: integer (1-10, monotonic)
started_at: ISO8601 timestamp (UTC)
completed_at: ISO8601 timestamp (UTC, null if in-progress)
attempt_status: enum (RUNNING, SUCCEEDED, FAILED, SKIPPED)
parent_attempt_id: string (ref to previous attempt_id if retry, null if first)
error_code: string (null if SUCCEEDED, ISO8601 error code if FAILED)
error_message: string (max 500 chars, null if SUCCEEDED)
checkpoint_token: string (opaque token for resumption from last checkpoint)
resources_consumed: object {
  cpu_hours: number (decimal)
  memory_gb_hours: number (decimal)
  gpu_hours: number (decimal)
  cost_usd: number (decimal, estimated)
}
shard_chain: array of strings (ordered list of shards executed in this attempt)
```

**Retention Policy:**
- Keep for 3 years (incident forensics)
- Archive after 6 months if attempt_status = SUCCEEDED
- Delete checkpoints (checkpoint_token) after 30 days

**Immutability Rules:**
- Write ONCE per attempt
- Status can transition: RUNNING → SUCCEEDED/FAILED/SKIPPED
- error_code and error_message immutable once set
- Resources consumed locked after attempt completion
- Hash-verify before state transition (FAILED → next attempt)

**Example:**

```json
{
  "attempt_id": "f9e8d7c6-b5a4-4321-9876-543210fedcba",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "attempt_number": 2,
  "started_at": "2026-04-16T10:31:00.000Z",
  "completed_at": "2026-04-16T10:35:30.000Z",
  "attempt_status": "SUCCEEDED",
  "parent_attempt_id": "a1a1a1a1-b2b2-b2b2-c3c3-c3c3c3c3c3c3",
  "error_code": null,
  "error_message": null,
  "checkpoint_token": "ckpt_2026041610_attempt2_seg7",
  "resources_consumed": {
    "cpu_hours": 0.125,
    "memory_gb_hours": 2.5,
    "gpu_hours": 0.075,
    "cost_usd": 3.45
  },
  "shard_chain": [
    "06_data_pipeline/shards/01_orchestration",
    "06_data_pipeline/shards/04_source_validation",
    "06_data_pipeline/shards/05_transcoding"
  ]
}
```

**Schema Link:** `SSID-open-core/schemas/sws/attempt_manifest.json`

---

## 4. source_manifest.json

**Purpose:** Input metadata. Describes origin, integrity, and access lineage for all raw source data.

**Producer Shard:** `06_data_pipeline/shards/04_source_validation`

**Mandatory Fields:**

```
source_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
source_type: enum (VIDEO, AUDIO, DOCUMENT, IMAGE, ARCHIVE, STREAM, API_PAYLOAD)
source_location: object {
  protocol: enum (S3, GCS, BLOB, HTTP, IPFS, LOCAL)
  bucket_region: string (AWS region or null for non-S3)
  path: string (immutable full path)
  url: string (optional, immutable)
}
file_metadata: object {
  filename: string (immutable original filename)
  file_size_bytes: integer (immutable)
  mime_type: string (immutable, RFC 2045)
  encoding: string (optional, e.g., UTF-8)
}
integrity_check: object {
  sha256_hash: string (immutable, hex format)
  md5_hash: string (optional legacy, immutable)
  crc32: integer (optional, immutable)
}
provenance: object {
  uploaded_at: ISO8601 timestamp (UTC, immutable)
  uploaded_by: string (user email or service, immutable)
  original_format: string (immutable, describes input format)
  access_token_scopes: array of strings (e.g., ["read:video", "read:metadata"])
}
retention_classification: enum (TRANSIENT, TEMPORARY, ARCHIVE, PERMANENT, REGULATORY)
```

**Retention Policy:**
- Keep for duration of job + 90 days
- TRANSIENT: delete after 24 hours
- TEMPORARY: delete after 30 days
- ARCHIVE: keep indefinitely
- PERMANENT: keep indefinitely + comply with regulatory hold
- REGULATORY: minimum 7 years

**Immutability Rules:**
- All fields immutable after creation
- No modifications to paths, hashes, or timestamps
- Access logs appended separately (not in this artifact)

**Example:**

```json
{
  "source_id": "src-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_type": "VIDEO",
  "source_location": {
    "protocol": "S3",
    "bucket_region": "eu-central-1",
    "path": "s3://ssid-intake-eu/video/batch_001/sample_video.mp4",
    "url": null
  },
  "file_metadata": {
    "filename": "sample_video.mp4",
    "file_size_bytes": 5368709120,
    "mime_type": "video/mp4",
    "encoding": null
  },
  "integrity_check": {
    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
    "crc32": 2144863456
  },
  "provenance": {
    "uploaded_at": "2026-04-16T10:30:00.000Z",
    "uploaded_by": "intake-operator@ssid.internal",
    "original_format": "H.264/AAC video stream",
    "access_token_scopes": ["read:video", "read:metadata"]
  },
  "retention_classification": "TEMPORARY"
}
```

**Schema Link:** `SSID-open-core/schemas/sws/source_manifest.json`

---

## 5. rights_manifest.json

**Purpose:** Usage rights, licensing, and policy references. Enables compliance and enforcement across pipelines.

**Producer Shard:** `07_governance_legal/shards/01_rights_management`

**Mandatory Fields:**

```
rights_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
source_id: string (reference to source_manifest.source_id)
rights_framework: enum (CC0, CC_BY, CC_BY_SA, CC_BY_NC, PROPRIETARY, PUBLIC_DOMAIN, COPYRIGHTED_WITH_LICENSE)
rights_level: enum (R0_PUBLIC, R1_LICENSED, R2_RESTRICTED, R3_CONFIDENTIAL, R4_REGULATORY_HOLD)
licensor_entity: string (company/person name, immutable)
license_url: string (immutable, link to full license text)
jurisdiction: string (ISO 3166-1 alpha-2 country code, immutable)
applicable_regulations: array of strings (e.g., ["GDPR", "CCPA", "DGA"])
usage_restrictions: object {
  commercial_use_allowed: boolean (immutable)
  derivative_works_allowed: boolean (immutable)
  redistribution_allowed: boolean (immutable)
  attribution_required: boolean (immutable)
  time_limit_days: integer or null (immutable, null = no expiry)
  geographic_restrictions: array of strings (e.g., ["EU", "DE"], null = none)
}
policy_references: array of strings (e.g., ["compliance/data_minimization", "governance/fair_use"])
enforcement_action: enum (ALLOW, REQUIRE_APPROVAL, BLOCK, REQUIRE_ANONYMIZATION)
approval_log: array of objects {
  approver: string (user/service)
  approval_at: ISO8601 timestamp
  decision: enum (APPROVED, DENIED, CONDITIONAL)
  conditions: string (optional, max 500 chars)
}
```

**Retention Policy:**
- Keep indefinitely (legal/compliance requirement)
- Approval logs must be immutable and timestamped
- Regulatory holds: keep minimum 7 years after workflow completion

**Immutability Rules:**
- Framework, level, licensor, license_url immutable after creation
- Usage restrictions immutable after creation
- Approval log append-only
- No modifications to restrictions or licenses; create new rights_manifest if terms change

**Example:**

```json
{
  "rights_id": "rights-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_id": "src-20260416-0001",
  "rights_framework": "CC_BY_SA",
  "rights_level": "R1_LICENSED",
  "licensor_entity": "Creative Commons",
  "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
  "jurisdiction": "US",
  "applicable_regulations": ["GDPR", "CCPA"],
  "usage_restrictions": {
    "commercial_use_allowed": false,
    "derivative_works_allowed": true,
    "redistribution_allowed": true,
    "attribution_required": true,
    "time_limit_days": null,
    "geographic_restrictions": null
  },
  "policy_references": ["compliance/creative_commons_audit", "governance/external_content_policy"],
  "enforcement_action": "REQUIRE_APPROVAL",
  "approval_log": [
    {
      "approver": "legal-review@ssid.internal",
      "approval_at": "2026-04-16T10:32:00.000Z",
      "decision": "CONDITIONAL",
      "conditions": "Attribution must appear in all derived works; EU-only distribution"
    }
  ]
}
```

**Schema Link:** `SSID-open-core/schemas/sws/rights_manifest.json`

---

## 6. media_technical.json

**Purpose:** Codec, resolution, frame rate, bitrate, and technical specs for video/audio streams.

**Producer Shard:** `06_data_pipeline/shards/05_transcoding`

**Mandatory Fields:**

```
media_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
source_id: string (reference to source_manifest.source_id)
media_type: enum (VIDEO, AUDIO, SUBTITLE, MIXED)
video_specs: object (null if media_type != VIDEO/MIXED) {
  codec: enum (H264, H265, VP8, VP9, AV1, UNCOMPRESSED)
  codec_profile: string (e.g., "main", "high", null for variable)
  bitrate_kbps: integer (immutable, null if variable bitrate)
  frame_rate: number (fps, immutable, e.g., 23.976, 24, 25, 29.97, 30, 60)
  resolution: object {
    width_px: integer (immutable)
    height_px: integer (immutable)
  }
  pixel_format: string (e.g., "yuv420p", "rgb24", immutable)
  color_space: string (e.g., "bt709", "bt2020", immutable)
  hdr_mode: enum or null (SDR, HDR10, HLG, DOLBY_VISION)
  duration_seconds: number (immutable)
  field_order: enum (PROGRESSIVE, INTERLACED_TFF, INTERLACED_BFF)
}
audio_specs: object (null if media_type != AUDIO/MIXED) {
  codec: enum (AAC, OPUS, VORBIS, PCM, FLAC, ALAC, AC3, EAC3)
  sample_rate_hz: integer (immutable, e.g., 44100, 48000, 96000)
  bit_depth_bits: integer (16, 24, 32, immutable)
  channels: integer (1-8, immutable)
  channel_layout: string (e.g., "mono", "stereo", "5.1", "7.1")
  bitrate_kbps: integer or null (immutable)
  duration_seconds: number (immutable)
}
quality_metrics: object {
  estimated_quality_score: number (0.0-1.0, subjective)
  noise_level_db: number (optional, immutable)
  signal_to_noise_ratio_db: number (optional, immutable)
}
timestamps_recorded_at: ISO8601 timestamp (UTC, when specs were measured)
```

**Retention Policy:**
- Keep for duration of job + 6 months
- Archive technical logs after 1 year
- Delete quality_metrics if source expires

**Immutability Rules:**
- All codec, resolution, bitrate specs immutable after measurement
- Measured timestamp immutable
- Quality metrics appended only once; no recalculation

**Example:**

```json
{
  "media_id": "media-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_id": "src-20260416-0001",
  "media_type": "VIDEO",
  "video_specs": {
    "codec": "H264",
    "codec_profile": "high",
    "bitrate_kbps": 5000,
    "frame_rate": 29.97,
    "resolution": {
      "width_px": 1920,
      "height_px": 1080
    },
    "pixel_format": "yuv420p",
    "color_space": "bt709",
    "hdr_mode": null,
    "duration_seconds": 300.5,
    "field_order": "PROGRESSIVE"
  },
  "audio_specs": null,
  "quality_metrics": {
    "estimated_quality_score": 0.92,
    "noise_level_db": -40.5,
    "signal_to_noise_ratio_db": 45.2
  },
  "timestamps_recorded_at": "2026-04-16T10:33:00.000Z"
}
```

**Schema Link:** `SSID-open-core/schemas/sws/media_technical.json`

---

## 7. transcript_master.json

**Purpose:** Time-aligned transcription with confidence scores and speaker labels. Master record for all speech content.

**Producer Shard:** `06_data_pipeline/shards/06_transcription`

**Mandatory Fields:**

```
transcript_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
media_id: string (reference to media_technical.media_id)
language_code: string (ISO 639-1, immutable, e.g., "en", "de", "fr")
model_info: object {
  model_name: string (immutable, e.g., "openai/whisper-large")
  model_version: string (semantic version, immutable)
  transcription_engine: string (immutable, e.g., "openai", "google", "azure")
}
segments: array of objects (immutable, ordered by start_time) {
  segment_id: string (UUID v4, unique per transcript)
  start_seconds: number (immutable, offset from media start)
  end_seconds: number (immutable)
  speaker_label: string (optional, e.g., "Speaker-1", immutable)
  text: string (immutable, transcribed text)
  confidence: number (0.0-1.0, immutable, overall segment confidence)
  word_timestamps: array of objects (optional) {
    word: string (immutable)
    start_seconds: number (immutable)
    end_seconds: number (immutable)
    confidence: number (0.0-1.0, immutable)
  }
}
post_processing: object {
  punctuation_added: boolean (immutable)
  diarization_applied: boolean (immutable)
  language_detection_confidence: number (0.0-1.0, immutable)
  content_filter_applied: boolean (immutable)
}
quality_stats: object {
  total_duration_seconds: number (immutable)
  average_confidence: number (0.0-1.0, immutable)
  unique_speakers_detected: integer (immutable)
  untranscribable_segments_count: integer (immutable)
  untranscribable_duration_seconds: number (immutable)
}
generated_at: ISO8601 timestamp (UTC, immutable)
```

**Retention Policy:**
- Keep for job duration + 2 years
- Archive after 1 year if no active use
- PII redaction: apply separately (keep raw for 6 months, delete after redaction complete)

**Immutability Rules:**
- Segments array immutable (no edits to text, timestamps, or confidence after generation)
- Model info immutable (reproducibility)
- Generated timestamp immutable
- Create new transcript if reprocessing needed; don't modify original

**Example:**

```json
{
  "transcript_id": "trans-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "media_id": "media-20260416-0001",
  "language_code": "en",
  "model_info": {
    "model_name": "openai/whisper-large",
    "model_version": "3.1.0",
    "transcription_engine": "openai"
  },
  "segments": [
    {
      "segment_id": "seg-001",
      "start_seconds": 0.0,
      "end_seconds": 5.2,
      "speaker_label": "Speaker-1",
      "text": "Hello, this is a test recording.",
      "confidence": 0.98,
      "word_timestamps": [
        {"word": "Hello", "start_seconds": 0.0, "end_seconds": 0.5, "confidence": 0.99},
        {"word": "this", "start_seconds": 0.6, "end_seconds": 0.9, "confidence": 0.97},
        {"word": "is", "start_seconds": 1.0, "end_seconds": 1.2, "confidence": 0.98},
        {"word": "a", "start_seconds": 1.3, "end_seconds": 1.4, "confidence": 0.96},
        {"word": "test", "start_seconds": 1.5, "end_seconds": 2.0, "confidence": 0.99},
        {"word": "recording", "start_seconds": 2.1, "end_seconds": 3.0, "confidence": 0.98}
      ]
    }
  ],
  "post_processing": {
    "punctuation_added": true,
    "diarization_applied": true,
    "language_detection_confidence": 0.995,
    "content_filter_applied": false
  },
  "quality_stats": {
    "total_duration_seconds": 300.5,
    "average_confidence": 0.966,
    "unique_speakers_detected": 2,
    "untranscribable_segments_count": 1,
    "untranscribable_duration_seconds": 2.3
  },
  "generated_at": "2026-04-16T10:35:00.000Z"
}
```

**Schema Link:** `SSID-open-core/schemas/sws/transcript_master.json`

---

## 8. shot_timeline.json

**Purpose:** Frame-accurate shot boundaries, scene cuts, and visual transitions for video content.

**Producer Shard:** `06_data_pipeline/shards/07_scene_detection`

**Mandatory Fields:**

```
timeline_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
media_id: string (reference to media_technical.media_id)
detection_model: string (immutable, e.g., "scenedetect-5.0", "opencv-adaptive")
shots: array of objects (immutable, ordered by frame_start) {
  shot_id: string (UUID v4, unique per timeline)
  frame_start: integer (immutable, 0-indexed frame number from media start)
  frame_end: integer (immutable)
  timecode_start: string (immutable, HH:MM:SS.mmm format)
  timecode_end: string (immutable, HH:MM:SS.mmm format)
  shot_type: enum (STATIC, PAN, TILT, ZOOM, TRACKING, CUT, FADE, DISSOLVE, WIPE)
  transition_type: enum or null (CUT, FADE_IN, FADE_OUT, DISSOLVE, WIPE, NONE)
  transition_duration_frames: integer (immutable, 0 if CUT)
  scene_label: string (optional, max 100 chars, e.g., "office_meeting_room")
  brightness_avg: number (0.0-1.0, immutable, optional)
  shot_confidence: number (0.0-1.0, immutable, detection confidence)
}
timeline_stats: object {
  total_shots: integer (immutable)
  total_scenes: integer (immutable)
  average_shot_duration_frames: number (immutable)
  fastest_cut_frames: integer (immutable)
  slowest_transition_frames: integer (immutable)
}
generated_at: ISO8601 timestamp (UTC, immutable)
```

**Retention Policy:**
- Keep for job duration + 1 year
- Archive after 6 months if no active analysis
- Delete frame-level data after 2 years, keep shot-level summaries indefinitely

**Immutability Rules:**
- Shot array immutable (no edits to frame numbers, timecodes, transitions)
- Detection model immutable (reproducibility)
- Cannot add or remove shots; create new timeline for reprocessing
- Confidence scores immutable

**Example:**

```json
{
  "timeline_id": "shot-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "media_id": "media-20260416-0001",
  "detection_model": "scenedetect-5.0",
  "shots": [
    {
      "shot_id": "shot-seg-001",
      "frame_start": 0,
      "frame_end": 147,
      "timecode_start": "00:00:00.000",
      "timecode_end": "00:00:04.900",
      "shot_type": "STATIC",
      "transition_type": "CUT",
      "transition_duration_frames": 0,
      "scene_label": "office_exterior",
      "brightness_avg": 0.72,
      "shot_confidence": 0.97
    },
    {
      "shot_id": "shot-seg-002",
      "frame_start": 148,
      "frame_end": 299,
      "timecode_start": "00:00:04.917",
      "timecode_end": "00:00:09.967",
      "shot_type": "PAN",
      "transition_type": "DISSOLVE",
      "transition_duration_frames": 6,
      "scene_label": "office_interior",
      "brightness_avg": 0.68,
      "shot_confidence": 0.94
    }
  ],
  "timeline_stats": {
    "total_shots": 12,
    "total_scenes": 8,
    "average_shot_duration_frames": 149.5,
    "fastest_cut_frames": 0,
    "slowest_transition_frames": 24
  },
  "generated_at": "2026-04-16T10:36:00.000Z"
}
```

**Schema Link:** `SSID-open-core/schemas/sws/shot_timeline.json`

---

## 9. caption_layers.json

**Purpose:** OCR output, burned-in text, subtitles, and visual text extraction from all frames.

**Producer Shard:** `06_data_pipeline/shards/08_ocr_extraction`

**Mandatory Fields:**

```
caption_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
media_id: string (reference to media_technical.media_id)
ocr_engine: string (immutable, e.g., "tesseract-5.2", "google-vision", "paddleocr")
language_code: string (ISO 639-1, immutable)
text_layers: array of objects (immutable, ordered by z_order) {
  layer_id: string (UUID v4, unique per caption_id)
  layer_name: string (e.g., "subtitles", "burned_text", "graphics_text", immutable)
  z_order: integer (stacking order, immutable)
  segments: array of objects (immutable, ordered by frame_start) {
    segment_id: string (UUID v4)
    frame_start: integer (immutable)
    frame_end: integer (immutable)
    timecode_start: string (immutable, HH:MM:SS.mmm)
    timecode_end: string (immutable)
    text: string (immutable, extracted text)
    confidence: number (0.0-1.0, immutable)
    bounding_box: object (immutable) {
      x_normalized: number (0.0-1.0, left edge as % of width)
      y_normalized: number (0.0-1.0, top edge as % of height)
      width_normalized: number (0.0-1.0)
      height_normalized: number (0.0-1.0)
    }
    font_properties: object (optional, immutable) {
      font_size_estimated_px: integer (estimated from width/height)
      color_dominant_hex: string (e.g., "#FFFFFF")
      background_color_hex: string (e.g., "#000000")
    }
  }
}
quality_metrics: object {
  total_segments: integer (immutable)
  average_confidence: number (0.0-1.0, immutable)
  languages_detected: array of strings (immutable)
  total_text_pixels_scanned: integer (immutable)
}
generated_at: ISO8601 timestamp (UTC, immutable)
```

**Retention Policy:**
- Keep for job duration + 18 months
- Archive after 1 year; compress to optimize storage
- Delete bounding box data after 2 years, keep extracted text indefinitely

**Immutability Rules:**
- Text layers array immutable (no edits to text, confidence, bounding boxes)
- OCR engine immutable (reproducibility)
- Cannot add or remove layers; create new caption_id if reprocessing
- Segments ordered by timecode; no modifications allowed

**Example:**

```json
{
  "caption_id": "cap-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "media_id": "media-20260416-0001",
  "ocr_engine": "google-vision",
  "language_code": "en",
  "text_layers": [
    {
      "layer_id": "layer-subs-001",
      "layer_name": "subtitles",
      "z_order": 1,
      "segments": [
        {
          "segment_id": "cap-seg-001",
          "frame_start": 50,
          "frame_end": 200,
          "timecode_start": "00:00:01.667",
          "timecode_end": "00:00:06.667",
          "text": "Welcome to the presentation.",
          "confidence": 0.98,
          "bounding_box": {
            "x_normalized": 0.1,
            "y_normalized": 0.85,
            "width_normalized": 0.8,
            "height_normalized": 0.1
          },
          "font_properties": {
            "font_size_estimated_px": 48,
            "color_dominant_hex": "#FFFFFF",
            "background_color_hex": "#000000"
          }
        }
      ]
    }
  ],
  "quality_metrics": {
    "total_segments": 25,
    "average_confidence": 0.92,
    "languages_detected": ["en"],
    "total_text_pixels_scanned": 15728640
  },
  "generated_at": "2026-04-16T10:37:00.000Z"
}
```

**Schema Link:** `SSID-open-core/schemas/sws/caption_layers.json`

---

## 10. audio_map.json

**Purpose:** Per-channel audio analysis: silence detection, beat/rhythm, energy profiles, and silence gaps.

**Producer Shard:** `06_data_pipeline/shards/09_audio_analysis`

**Mandatory Fields:**

```
audio_map_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
media_id: string (reference to media_technical.media_id)
channels_analyzed: integer (immutable, 1-8)
analysis_engine: string (immutable, e.g., "librosa-0.10", "essentia-2.1")
sample_rate_hz: integer (immutable, copied from media_technical)
silence_detection: object {
  threshold_db: number (immutable, e.g., -40.0)
  min_duration_ms: integer (immutable, minimum silence segment)
  silence_segments: array of objects (immutable, ordered by start_time) {
    silence_id: string (UUID v4)
    start_seconds: number (immutable)
    end_seconds: number (immutable)
    duration_seconds: number (immutable)
    average_energy_db: number (immutable)
  }
  total_silence_seconds: number (immutable)
}
beat_detection: object {
  tempo_bpm: number (immutable, null if no beat detected)
  confidence: number (0.0-1.0, immutable)
  beat_frames: array of numbers (immutable, frame indices where beats occur)
  time_signature: string (immutable, optional, e.g., "4/4", "3/4")
}
energy_profile: object {
  time_window_ms: integer (immutable, e.g., 50)
  channels: array of objects (immutable, ordered by channel_number) {
    channel_number: integer (0-indexed)
    channel_label: string (e.g., "FL", "FR", "LFE")
    energy_samples: array of numbers (immutable, energy level per window)
    peak_energy_db: number (immutable)
    rms_energy_db: number (immutable)
  }
}
music_detection: object {
  music_present: boolean (immutable)
  confidence: number (0.0-1.0, immutable)
  segments: array of objects (immutable) {
    start_seconds: number (immutable)
    end_seconds: number (immutable)
    genre_prediction: string (optional, e.g., "pop", "classical", "electronic")
  }
}
speech_detection: object {
  speech_present: boolean (immutable)
  confidence: number (0.0-1.0, immutable)
  speech_segments: array of objects (immutable) {
    start_seconds: number (immutable)
    end_seconds: number (immutable)
    speaker_count_estimate: integer (immutable, 1-10)
  }
}
generated_at: ISO8601 timestamp (UTC, immutable)
```

**Retention Policy:**
- Keep for job duration + 1 year
- Archive energy profiles after 6 months
- Delete beat/tempo data after 2 years; keep silence and speech segments indefinitely

**Immutability Rules:**
- All detection segments immutable
- Energy samples and tempo immutable
- Cannot modify analysis results; create new audio_map for reprocessing
- Analysis engine must be recorded (reproducibility)

**Example:**

```json
{
  "audio_map_id": "amap-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "media_id": "media-20260416-0001",
  "channels_analyzed": 2,
  "analysis_engine": "librosa-0.10",
  "sample_rate_hz": 48000,
  "silence_detection": {
    "threshold_db": -40.0,
    "min_duration_ms": 500,
    "silence_segments": [
      {
        "silence_id": "sil-001",
        "start_seconds": 45.2,
        "end_seconds": 46.1,
        "duration_seconds": 0.9,
        "average_energy_db": -50.5
      }
    ],
    "total_silence_seconds": 12.3
  },
  "beat_detection": {
    "tempo_bpm": 120.5,
    "confidence": 0.87,
    "beat_frames": [1200, 1440, 1680, 1920],
    "time_signature": "4/4"
  },
  "energy_profile": {
    "time_window_ms": 50,
    "channels": [
      {
        "channel_number": 0,
        "channel_label": "FL",
        "energy_samples": [0.1, 0.15, 0.2, 0.18, 0.12],
        "peak_energy_db": -10.2,
        "rms_energy_db": -18.5
      },
      {
        "channel_number": 1,
        "channel_label": "FR",
        "energy_samples": [0.12, 0.18, 0.22, 0.16, 0.11],
        "peak_energy_db": -9.8,
        "rms_energy_db": -19.2
      }
    ]
  },
  "music_detection": {
    "music_present": true,
    "confidence": 0.92,
    "segments": [
      {
        "start_seconds": 0.0,
        "end_seconds": 120.0,
        "genre_prediction": "pop"
      }
    ]
  },
  "speech_detection": {
    "speech_present": true,
    "confidence": 0.88,
    "speech_segments": [
      {
        "start_seconds": 5.0,
        "end_seconds": 45.0,
        "speaker_count_estimate": 2
      }
    ]
  },
  "generated_at": "2026-04-16T10:38:00.000Z"
}
```

**Schema Link:** `SSID-open-core/schemas/sws/audio_map.json`

---

## 11. hook_fingerprint.json

**Purpose:** Engagement hooks (hooks are specific moments, cues, or CTAs designed to maximize viewer engagement), call-to-action markers, and action timestamps for content strategy.

**Producer Shard:** `06_data_pipeline/shards/10_engagement_analytics`

**Mandatory Fields:**

```
fingerprint_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
media_id: string (reference to media_technical.media_id)
hooks: array of objects (immutable, ordered by start_seconds) {
  hook_id: string (UUID v4)
  hook_type: enum (CLIFFHANGER, QUESTION, SURPRISE, EMOTIONAL_PEAK, HUMOR, CURIOSITY_GAP, ACTION_SEQUENCE, REVEAL, CTA)
  start_seconds: number (immutable)
  end_seconds: number (immutable)
  hook_strength: number (0.0-1.0, immutable, predicted engagement impact)
  hook_text: string (optional, immutable, associated text/transcript segment)
  context: string (optional, immutable, max 200 chars, description)
}
cta_markers: array of objects (immutable, ordered by timestamp) {
  cta_id: string (UUID v4)
  cta_type: enum (SUBSCRIBE, SHARE, COMMENT, LIKE, CLICK_LINK, PURCHASE, REGISTER, DOWNLOAD, FOLLOW)
  start_seconds: number (immutable)
  end_seconds: number (immutable)
  cta_text: string (optional, immutable)
  cta_url: string (optional, immutable, target URL or action identifier)
  prominence_score: number (0.0-1.0, immutable, expected visibility/effectiveness)
}
action_points: array of objects (immutable, ordered by frame_number) {
  action_id: string (UUID v4)
  frame_number: integer (immutable)
  action_type: enum (SCENE_CUT, TITLE_CARD, MUSIC_DROP, SOUND_EFFECT, VISUAL_EFFECT, TEXT_APPEARANCE, CHARACTER_ENTRY, OBJECT_REVEAL)
  impact_score: number (0.0-1.0, immutable, predicted viewer attention)
  audio_trigger: boolean (immutable, true if audio cue accompanies)
  visual_trigger: boolean (immutable, true if visual cue present)
}
timing_analysis: object {
  first_hook_seconds: number (immutable)
  hook_frequency_per_minute: number (immutable)
  cta_density_per_minute: number (immutable)
  optimal_break_points: array of numbers (immutable, timestamps suggested for multi-part viewing)
}
predicted_retention: object {
  drop_off_seconds: array of numbers (immutable, frame times where viewer retention is predicted to drop)
  recovery_points: array of numbers (immutable, frame times with high re-engagement potential)
  estimated_watch_time_percent: number (0.0-1.0, immutable, predicted % of total viewing)
}
generated_at: ISO8601 timestamp (UTC, immutable)
```

**Retention Policy:**
- Keep for job duration + 3 years (content strategy reference)
- Archive after 1 year; compress for efficient storage
- Delete predicted metrics after 2 years if superseded by actual performance data

**Immutability Rules:**
- All hooks, CTAs, and action points immutable
- Predictions immutable (for historical comparison)
- Cannot modify timing or impact scores; create new fingerprint for reanalysis
- IDs must be unique per artifact

**Example:**

```json
{
  "fingerprint_id": "hook-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "media_id": "media-20260416-0001",
  "hooks": [
    {
      "hook_id": "hook-seg-001",
      "hook_type": "QUESTION",
      "start_seconds": 10.0,
      "end_seconds": 15.5,
      "hook_strength": 0.85,
      "hook_text": "But wait, there's more...",
      "context": "Presenter introduces unexpected finding"
    },
    {
      "hook_id": "hook-seg-002",
      "hook_type": "EMOTIONAL_PEAK",
      "start_seconds": 45.0,
      "end_seconds": 52.0,
      "hook_strength": 0.92,
      "hook_text": null,
      "context": "Dramatic music crescendo with visual reveal"
    }
  ],
  "cta_markers": [
    {
      "cta_id": "cta-001",
      "cta_type": "SUBSCRIBE",
      "start_seconds": 250.0,
      "end_seconds": 260.0,
      "cta_text": "Subscribe for more content",
      "cta_url": "https://example.com/subscribe",
      "prominence_score": 0.88
    }
  ],
  "action_points": [
    {
      "action_id": "act-001",
      "frame_number": 300,
      "action_type": "SCENE_CUT",
      "impact_score": 0.75,
      "audio_trigger": true,
      "visual_trigger": true
    }
  ],
  "timing_analysis": {
    "first_hook_seconds": 10.0,
    "hook_frequency_per_minute": 1.8,
    "cta_density_per_minute": 0.3,
    "optimal_break_points": [75.0, 150.0, 225.0]
  },
  "predicted_retention": {
    "drop_off_seconds": [120.0, 200.0],
    "recovery_points": [130.0, 210.0],
    "estimated_watch_time_percent": 0.78
  },
  "generated_at": "2026-04-16T10:39:00.000Z"
}
```

**Schema Link:** `SSID-open-core/schemas/sws/hook_fingerprint.json`

---

## 12. visual_fingerprint.json

**Purpose:** Style, motion, color, and visual characteristics. Enables content matching, duplicate detection, and visual intelligence. **Status:** SHOULD v1 (planned, not yet required).

**Producer Shard:** `06_data_pipeline/shards/11_visual_intelligence` (future)

**Mandatory Fields (when implemented):**

```
visual_fp_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
media_id: string (reference to media_technical.media_id)
color_profile: object {
  dominant_colors: array of objects (immutable, top 5) {
    hex: string (e.g., "#FF5733")
    name: string (color name approximation)
    frequency_percent: number (0.0-100.0)
  }
  color_space: string (e.g., "srgb", "bt709")
  saturation_average: number (0.0-1.0, immutable)
  brightness_average: number (0.0-1.0, immutable)
}
motion_characteristics: object {
  motion_type: enum (STATIC, LOW_MOTION, MEDIUM_MOTION, HIGH_MOTION, FAST_CUT_HEAVY)
  motion_intensity_average: number (0.0-1.0, immutable)
  camera_movement: enum (NONE, PAN, TILT, ZOOM, TRACKING, HANDHELD, COMBINED)
  optical_flow_samples: array of numbers (immutable, motion vectors per frame region)
}
texture_analysis: object {
  dominant_texture: enum (SMOOTH, ROUGH, PATTERN, GRADIENT, NOISE)
  texture_complexity: number (0.0-1.0, immutable)
  edge_density: number (0.0-1.0, immutable)
}
contrast_profile: object {
  dynamic_range_ev: number (immutable, estimated exposure value range)
  shadow_detail: number (0.0-1.0, immutable, visibility in dark areas)
  highlight_detail: number (0.0-1.0, immutable, visibility in bright areas)
}
style_tags: array of strings (immutable, max 20, e.g., ["documentary", "cinematic", "animated", "vlog"])
similarity_hashes: object (immutable) {
  dhash: string (perceptual hash, 64-bit hex)
  phash: string (average hash, 64-bit hex)
  whash: string (wavelet hash, 64-bit hex)
}
generated_at: ISO8601 timestamp (UTC, immutable)
```

**Retention Policy:**
- Keep for job duration + indefinitely (deduplication/asset library)
- Hashes searchable for content matching

**Immutability Rules:**
- All hashes immutable
- Style tags immutable
- Cannot modify analysis results

**Example (placeholder v1):**

```json
{
  "visual_fp_id": "vfp-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "media_id": "media-20260416-0001",
  "color_profile": {
    "dominant_colors": [
      {"hex": "#1F1F1F", "name": "black", "frequency_percent": 35.2},
      {"hex": "#FFFFFF", "name": "white", "frequency_percent": 28.5},
      {"hex": "#4A90E2", "name": "blue", "frequency_percent": 18.3}
    ],
    "color_space": "srgb",
    "saturation_average": 0.42,
    "brightness_average": 0.58
  },
  "motion_characteristics": {
    "motion_type": "MEDIUM_MOTION",
    "motion_intensity_average": 0.35,
    "camera_movement": "PAN",
    "optical_flow_samples": [0.1, 0.12, 0.15, 0.13, 0.11]
  },
  "texture_analysis": {
    "dominant_texture": "SMOOTH",
    "texture_complexity": 0.38,
    "edge_density": 0.22
  },
  "contrast_profile": {
    "dynamic_range_ev": 8.5,
    "shadow_detail": 0.68,
    "highlight_detail": 0.72
  },
  "style_tags": ["cinematic", "corporate", "educational"],
  "similarity_hashes": {
    "dhash": "8f7e6d5c4b3a2918",
    "phash": "a1b2c3d4e5f67890",
    "whash": "f9e8d7c6b5a49382"
  },
  "generated_at": "2026-04-16T10:40:00.000Z"
}
```

**Schema Link:** `SSID-open-core/schemas/sws/visual_fingerprint.json` (TBD)

---

## 13. rebuild_blueprint.json

**Purpose:** Final composite blueprint. Aggregates all artifacts into a single, deterministic rebuild specification. Enables end-to-end reproducibility.

**Producer Shard:** `06_data_pipeline/shards/12_composition`

**Mandatory Fields:**

```
blueprint_id: string (UUID v4, immutable)
job_id: string (reference to job_manifest.job_id)
job_version: string (immutable, copied from job_manifest)
source_manifest_ref: string (immutable, SHA256 hash of source_manifest.json)
attempt_manifest_ref: string (immutable, SHA256 hash of final successful attempt_manifest.json)
rights_manifest_ref: string (immutable, SHA256 hash of rights_manifest.json)
media_technical_ref: string (immutable, SHA256 hash of media_technical.json)
transcript_master_ref: string (immutable, SHA256 hash of transcript_master.json)
shot_timeline_ref: string (immutable, SHA256 hash of shot_timeline.json)
caption_layers_ref: string (immutable, SHA256 hash of caption_layers.json)
audio_map_ref: string (immutable, SHA256 hash of audio_map.json)
hook_fingerprint_ref: string (immutable, SHA256 hash of hook_fingerprint.json)
visual_fingerprint_ref: string or null (immutable, SHA256 hash of visual_fingerprint.json; null if v1 not implemented)
manifest_chain: array of objects (immutable, ordered by creation time) {
  manifest_type: string (enum above)
  manifest_id: string (UUID from artifact)
  sha256: string (immutable hash)
  producer_shard: string (which shard created it)
  created_at: ISO8601 timestamp
}
integrity_verification: object {
  all_refs_valid: boolean (immutable, true if all hashes verified)
  validation_timestamp: ISO8601 timestamp (immutable)
  validator_service: string (immutable, e.g., "sws-blueprint-validator-v2")
}
rebuild_instructions: object {
  entry_point_shard: string (immutable, which shard to invoke first for rebuild)
  shard_execution_order: array of strings (immutable, canonical order for reproducibility)
  environment_requirements: object {
    min_memory_gb: integer (immutable)
    min_storage_gb: integer (immutable)
    required_tools: array of strings (immutable, e.g., ["ffmpeg-6.0", "openai-api", "tesseract-5.2"])
  }
  input_validation_checksum: string (immutable, final sha256 of all inputs combined)
}
lifecycle_metadata: object {
  created_at: ISO8601 timestamp (immutable)
  created_by: string (immutable, service identifier)
  expiration_date: ISO8601 timestamp (immutable, null = indefinite)
  immutable_until: ISO8601 timestamp (immutable, locks artifact from modification)
}
```

**Retention Policy:**
- Keep indefinitely (master record for reproducibility)
- Store in multiple redundant locations (primary + DR + archive)
- Cryptographically sign blueprint; verify before rebuild

**Immutability Rules:**
- FULLY IMMUTABLE after creation
- All hash refs locked; no modifications allowed
- Create new blueprint if any underlying artifact changes
- Blueprint cannot be deleted; only archived

**Example:**

```json
{
  "blueprint_id": "bp-20260416-0001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_version": "2.1.0",
  "source_manifest_ref": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "attempt_manifest_ref": "sha256:abc123def456789...",
  "rights_manifest_ref": "sha256:def456ghi789jkl...",
  "media_technical_ref": "sha256:ghi789jkl012mno...",
  "transcript_master_ref": "sha256:jkl012mno345pqr...",
  "shot_timeline_ref": "sha256:mno345pqr678stu...",
  "caption_layers_ref": "sha256:pqr678stu901vwx...",
  "audio_map_ref": "sha256:stu901vwx234yza...",
  "hook_fingerprint_ref": "sha256:vwx234yza567bcd...",
  "visual_fingerprint_ref": null,
  "manifest_chain": [
    {
      "manifest_type": "source_manifest",
      "manifest_id": "src-20260416-0001",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "producer_shard": "06_data_pipeline/shards/04_source_validation",
      "created_at": "2026-04-16T10:30:00.000Z"
    },
    {
      "manifest_type": "media_technical",
      "manifest_id": "media-20260416-0001",
      "sha256": "ghi789jkl012mno...",
      "producer_shard": "06_data_pipeline/shards/05_transcoding",
      "created_at": "2026-04-16T10:33:00.000Z"
    }
  ],
  "integrity_verification": {
    "all_refs_valid": true,
    "validation_timestamp": "2026-04-16T10:40:30.000Z",
    "validator_service": "sws-blueprint-validator-v2"
  },
  "rebuild_instructions": {
    "entry_point_shard": "06_data_pipeline/shards/01_orchestration",
    "shard_execution_order": [
      "06_data_pipeline/shards/01_orchestration",
      "06_data_pipeline/shards/04_source_validation",
      "06_data_pipeline/shards/05_transcoding",
      "06_data_pipeline/shards/06_transcription",
      "06_data_pipeline/shards/07_scene_detection",
      "06_data_pipeline/shards/08_ocr_extraction",
      "06_data_pipeline/shards/09_audio_analysis",
      "06_data_pipeline/shards/10_engagement_analytics"
    ],
    "environment_requirements": {
      "min_memory_gb": 64,
      "min_storage_gb": 500,
      "required_tools": ["ffmpeg-6.0", "openai-api-v1", "tesseract-5.2", "librosa-0.10", "google-vision-api"]
    },
    "input_validation_checksum": "sha256:combined_all_inputs_hash..."
  },
  "lifecycle_metadata": {
    "created_at": "2026-04-16T10:40:30.000Z",
    "created_by": "blueprint-composer@ssid.internal",
    "expiration_date": null,
    "immutable_until": "2099-12-31T23:59:59.000Z"
  }
}
```

**Schema Link:** `SSID-open-core/schemas/sws/rebuild_blueprint.json`

---

## Cross-Artifact Validation Rules

1. **Referential Integrity:** All artifact references (via job_id, source_id, media_id, etc.) must resolve to valid artifacts
2. **Timestamp Ordering:** All created_at timestamps must be sequential and monotonic
3. **Hash Verification:** Before any state transition (e.g., status change), recalculate SHA256 of prior state and verify against evidence log
4. **Immutability Enforcement:** Any attempt to modify a locked field triggers SAFE_FIX protocol verification
5. **Evidence Chain:** Every artifact mutation must be logged in job_events.jsonl with actor, timestamp, and reason

---

## Schema Files Location

All canonical schemas available at:

```
SSID-open-core/schemas/sws/
├── job_manifest.json
├── job_events.jsonl
├── attempt_manifest.json
├── source_manifest.json
├── rights_manifest.json
├── media_technical.json
├── transcript_master.json
├── shot_timeline.json
├── caption_layers.json
├── audio_map.json
├── hook_fingerprint.json
├── visual_fingerprint.json
├── rebuild_blueprint.json
└── _validation.json  (meta-schema for validator tools)
```

---

## Versioning & Updates

- **Version 1.0:** 2026-04-16 — Initial release; all 13 artifacts defined
- **Updates:** Changes to schema published via RFC process; artifacts retain backward compatibility
- **Validation Tooling:** `sws-blueprint-validator` CLI tool validates artifact compliance

---

**Document prepared by:** SWS Artifact Contracts Working Group  
**Stakeholders:** Data Pipeline Team, Governance & Legal, Content Strategy, Engineering  
**Next Review:** 2026-07-16
