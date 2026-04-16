# SWS V1 Operator Quickstart Runbook

## 1. Introduction: What Is a SWS Analysis Job?

A **SWS (Semantic Web Service) Analysis Job** is an asynchronous, multi-stage content processing pipeline that:

1. **Ingests** media files or URLs (video, audio, documents, images)
2. **Performs Rights Assessment** (copyright, licensing, usage rights)
3. **Executes Parallel Analysis** (video analysis, audio analysis, transcript generation, OCR, external hooks)
4. **Generates Blueprints** (semantic artifacts: scene descriptions, entity extractions, intent models)
5. **Publishes Results** (APIs, storage, webhook deliveries)

### Real-World Scenario

**Example:** You receive a 2-hour video of a corporate training session:

- **Input:** `https://s3.example.com/training/q1-onboarding.mp4` (1.8 GB)
- **Job ID:** `job-7d3a2b9f8c1e4k2m`
- **Expected Processing Time:** 12–18 minutes (depending on resolution, audio tracks)
- **Output:** Scene keyframes, speaker diarization, transcript with timestamps, visual entity catalog, compliance metadata
- **Rights:** Licensed for internal use (R1 classification), watermarked blueprints

---

## 2. Job Lifecycle: State Diagram

### ASCII State Diagram

```
                              CREATED
                                 ↓
                            [CREATED]
                          (Payload received,
                           validation queued)
                                 ↓
                          RIGHTS_CHECK
                                 ↓
                      ┌───────────┴────────────┐
                      │                        │
                   PASS                      FAIL
                      │                        │
                      ↓                        ↓
                  INGEST                  FAILED
                      │              (R3/R4: denied)
         ┌────────────┴────────────┐
         │                         │
      PASS                       FAIL
         │                         │
         ↓                         ↓
     ANALYZING              FAILED
         │            (E-INGEST-*)
    ┌────┼────┬───────┬────────┐
    ↓    ↓    ↓       ↓        ↓
   [Video] [Audio] [Transcript] [OCR] [Hooks]
    │    │    │       │        │
    └────┼────┴───────┴────────┘
         ↓
    ANALYZED
    (all workers done)
         ↓
    BLUEPRINT_READY
    (semantic models built)
         ↓
    QA_PENDING
         ↓
    QA_COMPLETE
    (manual or automated QA pass)
         ↓
    PUBLISH_READY
         ↓
    PUBLISHED
    (results delivered)
```

### State Details

| State | Duration | Action | Next State |
|-------|----------|--------|-----------|
| `CREATED` | <1s | Validate payload, allocate worker | `RIGHTS_CHECK` |
| `RIGHTS_CHECK` | 2–5s | Fetch metadata, classify rights (R0–R4) | `INGEST` or `FAILED` |
| `INGEST` | 30s–2m | Download/stage content, extract metadata | `ANALYZING` or `FAILED` |
| `ANALYZING` | 5–15m | Run 5 parallel workers (video, audio, transcript, OCR, hooks) | `ANALYZED` |
| `ANALYZED` | <1s | Aggregate worker outputs | `BLUEPRINT_READY` |
| `BLUEPRINT_READY` | <1s | Generate semantic models, index | `QA_PENDING` |
| `QA_PENDING` | 1–30m | Await manual/automated QA review | `QA_COMPLETE` |
| `QA_COMPLETE` | <1s | Mark results verified | `PUBLISH_READY` |
| `PUBLISH_READY` | <1s | Prepare delivery artifacts | `PUBLISHED` |
| `PUBLISHED` | <1s | Deliver to APIs, webhooks, storage | (terminal) |

### Failure Terminal States

- **`FAILED`** – Hard error, no recovery path (E-INGEST-*, R3/R4 denied, corrupt input)

---

## 3. Common Error Patterns

### E-INGEST-* Errors

**E-INGEST-DOWNLOAD_TIMEOUT**
- **Trigger:** Content URL unreachable after 3 retries
- **Scenario:** `https://example.com/archive/2019/video.mp4` returns 404 or 503
- **Fix:**
  ```bash
  ssid-sws show-job job-7d3a2b9f8c1e4k2m
  # Check "error_detail.url" field — is it still valid?
  # Retry with corrected URL:
  ssid-sws retry-job job-7d3a2b9f8c1e4k2m \
    --source-url "https://example.com/archive/2019/video-corrected.mp4"
  ```

**E-INGEST-FILE_TOO_LARGE**
- **Trigger:** Media exceeds storage quota (default: 5 GB per job)
- **Scenario:** 4K multi-angle video recording, 8.2 GB
- **Fix:**
  ```bash
  # Create new job with pre-processing:
  ssid-sws analyze-file local-video.mp4 \
    --transcode-preset "h264_720p" \
    --audio-channels 2
  ```

**E-INGEST-UNSUPPORTED_CODEC**
- **Trigger:** Video codec not in whitelist (H.264, H.265, VP9 OK; ProRes, Cineform denied)
- **Scenario:** Input file is ProRes 422 HQ
- **Fix:**
  ```bash
  ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4
  ssid-sws analyze-file output.mp4
  ```

### E-RIGHTS-* Errors

**E-RIGHTS-DENIED_R3**
- **Trigger:** Content classified R3 (rights unknown, commercial use restricted)
- **Scenario:** Academic paper, unclear licensing
- **Outcome:** Job moves to `FAILED`, blueprint not published
- **Resolution:** Contact rights holder, request R2 re-classification, retry

**E-RIGHTS-DENIED_R4**
- **Trigger:** Content flagged R4 (no rights, all-rights-reserved, NDA)
- **Scenario:** Client confidential presentation, watermarked "Internal Use Only"
- **Outcome:** Job rejected at rights gate, no processing
- **Resolution:** Operator must obtain explicit usage agreement; no technical workaround

### E-MEDIA-* Errors

**E-MEDIA-VIDEO_CORRUPTION_DETECTED**
- **Trigger:** Video decoder fails on 3+ frames during analysis
- **Scenario:** Partial download, corrupted MP4 header
- **Fix:**
  ```bash
  # Re-download and validate checksum:
  ssid-sws retry-job job-7d3a2b9f8c1e4k2m \
    --validate-checksum-before-ingest
  ```

**E-MEDIA-AUDIO_EXTRACTION_FAILED**
- **Trigger:** Audio stream unreadable (damaged, encrypted, unsupported codec)
- **Scenario:** DTS audio in MKV container
- **Outcome:** Audio worker fails, blueprint incomplete
- **Workaround:** Re-transcode audio to AAC, restart job

**E-MEDIA-NO_DETECTABLE_SPEECH**
- **Trigger:** Transcript worker finds <5% speech confidence across entire media
- **Scenario:** Pure instrumental music, ambient recording, white noise
- **Outcome:** Transcript worker succeeds with empty result; blueprint marks transcript as `null`
- **Expected Behavior:** Not an error — job completes normally

---

## 4. Rights Gate Decisions: R0–R4 Classification

### Decision Tree

```
Content Rights Assessment
    ↓
Does copyright holder explicitly allow processing?
    ├─ YES → Is commercial use allowed?
    │   ├─ YES, no restrictions → R0 (full rights)
    │   └─ NO, internal/research only → R1 (limited commercial)
    │
    └─ NO → Is licensing information available?
        ├─ YES, can infer intent → R2 (inferred)
        ├─ UNCLEAR → R3 (unknown, restricted)
        └─ NO RIGHTS / NDA / CONFIDENTIAL → R4 (denied)
```

### Classification Examples

**R0: Full Rights**
- Public domain video (pre-1928, US Government works)
- Creative Commons CC-BY or CC-0
- Media with explicit written permission from rights holder
- **Result:** No watermark, blueprint published to all APIs

**R1: Limited Commercial**
- CC-BY-NC (personal, research, educational use only)
- Internal corporate training content
- Licensed for non-commercial derivative use
- **Result:** Blueprint watermarked with "LIMITED COMMERCIAL USE", accessible to internal APIs only

**R2: Inferred Rights**
- Academic paper with standard publication license (assumed reuse OK for research)
- Old archived content with institutional repository (assumed open)
- **Result:** Blueprint marked with confidence level (0.65–0.95); published with disclaimer

**R3: Unknown / Restricted**
- No metadata, unclear licensing
- Content from third-party archive without explicit permission
- Orphan works (copyright holder unknown)
- **Result:** Blueprint generated but **NOT PUBLISHED**; marked for manual review

**R4: Denied / No Rights**
- Explicitly marked "All Rights Reserved", "Do Not Distribute", "Confidential"
- NDA-protected content
- Content flagged by rights database (DMCA, takedown)
- **Result:** Job rejected at RIGHTS_CHECK; no processing occurs

### Operator Override (Emergency)

In rare cases, operator can force R2 classification with justification:

```bash
ssid-sws analyze-url https://example.com/archive/doc.pdf \
  --force-rights-classification "R2" \
  --override-reason "Internal archival assessment, low commercial value"
```

**Note:** All overrides are logged for audit compliance.

---

## 5. Audit Trail Queries

### Query Recent Job Events

```bash
# Show last 20 jobs
ssid-sws list-jobs --limit 20 --sort created_desc

# Show job details
ssid-sws show-job job-7d3a2b9f8c1e4k2m

# Sample output:
# {
#   "job_id": "job-7d3a2b9f8c1e4k2m",
#   "created_at": "2026-04-16T08:15:23Z",
#   "state": "PUBLISHED",
#   "source_url": "https://s3.example.com/training/q1-onboarding.mp4",
#   "rights_classification": "R1",
#   "duration_seconds": 7200,
#   "file_size_bytes": 1876234567,
#   "timeline": [
#     { "event": "CREATED", "timestamp": "2026-04-16T08:15:23Z" },
#     { "event": "RIGHTS_CHECK", "timestamp": "2026-04-16T08:15:25Z", "result": "PASS" },
#     { "event": "INGEST_START", "timestamp": "2026-04-16T08:15:30Z" },
#     { "event": "INGEST_COMPLETE", "timestamp": "2026-04-16T08:17:45Z" },
#     { "event": "ANALYZING_START", "timestamp": "2026-04-16T08:17:46Z" },
#     { "event": "WORKER_VIDEO_COMPLETE", "timestamp": "2026-04-16T08:28:10Z" },
#     { "event": "WORKER_AUDIO_COMPLETE", "timestamp": "2026-04-16T08:32:05Z" },
#     { "event": "WORKER_TRANSCRIPT_COMPLETE", "timestamp": "2026-04-16T08:29:55Z" },
#     { "event": "WORKER_OCR_COMPLETE", "timestamp": "2026-04-16T08:26:30Z" },
#     { "event": "ANALYZING_COMPLETE", "timestamp": "2026-04-16T08:32:10Z" },
#     { "event": "BLUEPRINT_READY", "timestamp": "2026-04-16T08:32:15Z" },
#     { "event": "QA_COMPLETE", "timestamp": "2026-04-16T08:32:20Z" },
#     { "event": "PUBLISHED", "timestamp": "2026-04-16T08:32:25Z" }
#   ],
#   "workers": {
#     "video_analysis": { "status": "COMPLETE", "duration_ms": 10324 },
#     "audio_analysis": { "status": "COMPLETE", "duration_ms": 14435 },
#     "transcript": { "status": "COMPLETE", "duration_ms": 11109 },
#     "ocr": { "status": "COMPLETE", "duration_ms": 8544 },
#     "hooks": { "status": "COMPLETE", "duration_ms": 5200 }
#   },
#   "blueprints": {
#     "scenes": 127,
#     "entities": 456,
#     "intents": 23,
#     "transcript_length": 18347,
#     "confidence_avg": 0.87
#   }
# }
```

### Filter by Time Range

```bash
# Jobs in last 24 hours
ssid-sws list-jobs --since "2026-04-15T00:00:00Z" --limit 100

# Jobs from specific time window
ssid-sws list-jobs \
  --since "2026-04-16T08:00:00Z" \
  --until "2026-04-16T10:00:00Z"
```

### Filter by State

```bash
# All failed jobs
ssid-sws list-jobs --state FAILED --limit 50

# All currently analyzing
ssid-sws list-jobs --state ANALYZING --limit 20

# All pending QA
ssid-sws list-jobs --state QA_PENDING --limit 30
```

### Export Events for Compliance

```bash
# Export audit trail as CSV
ssid-sws export-artifacts job-7d3a2b9f8c1e4k2m \
  --artifact-type "audit_timeline" \
  --format csv \
  --output job-audit.csv

# Export with signature
ssid-sws export-artifacts job-7d3a2b9f8c1e4k2m \
  --artifact-type "audit_timeline" \
  --format json \
  --with-signature \
  --output job-audit-signed.json
```

---

## 6. Recovery Scenarios

### Scenario 1: Job Stuck in ANALYZING (Worker Timeout)

**Symptom:** Job in ANALYZING state for >20 minutes, no progress

**Investigation:**
```bash
ssid-sws show-job job-7d3a2b9f8c1e4k2m | grep -A 10 "workers"

# Output shows:
# "video_analysis": { "status": "RUNNING", "started_at": "...", "duration_ms": 1200000 }
# (20+ minutes)
```

**Root Cause:** Video worker hung on scene detection (likely high-resolution or long duration)

**Fix:**
```bash
# Option 1: Cancel and retry with reduced quality
ssid-sws cancel-job job-7d3a2b9f8c1e4k2m
ssid-sws retry-job job-7d3a2b9f8c1e4k2m \
  --video-quality-preset "medium" \
  --scene-detection-sample-rate 2.0

# Option 2: Force completion (accept partial results)
ssid-sws force-state job-7d3a2b9f8c1e4k2m \
  --target-state "ANALYZED" \
  --skip-incomplete-workers "video_analysis"
  --reason "Timeout recovery, accept partial blueprint"
```

### Scenario 2: INGEST Fails Due to 403 Forbidden

**Symptom:** Job fails at INGEST with `E-INGEST-DOWNLOAD_FORBIDDEN`

**Scenario:** S3 bucket access restricted, wrong AWS credentials in job config

**Investigation:**
```bash
ssid-sws show-job job-7d3a2b9f8c1e4k2m | grep -A 5 "error_detail"

# Output:
# "error_detail": {
#   "code": "E-INGEST-DOWNLOAD_FORBIDDEN",
#   "http_status": 403,
#   "url": "https://s3.us-west-2.amazonaws.com/corporate-archive/file.mp4"
# }
```

**Fix:**
```bash
# Verify S3 permissions
aws s3 ls s3://corporate-archive/file.mp4

# If missing, update bucket policy or use presigned URL
aws s3 presign s3://corporate-archive/file.mp4 --expires-in 3600

# Retry with presigned URL
ssid-sws retry-job job-7d3a2b9f8c1e4k2m \
  --source-url "https://s3.us-west-2.amazonaws.com/corporate-archive/file.mp4?X-Amz-Algorithm=..."
```

### Scenario 3: Rights Classification Wrong (R3 Instead of R1)

**Symptom:** Job marked R3 (restricted), blueprint not published, but content should be R1 (internal)

**Investigation:**
```bash
ssid-sws show-job job-7d3a2b9f8c1e4k2m | grep "rights"

# Output:
# "rights_classification": "R3",
# "rights_confidence": 0.52,
# "rights_notes": "No explicit license metadata found"
```

**Root Cause:** Metadata missing or misinterpreted

**Fix:**
```bash
# Operator override with documented justification
ssid-sws update-job job-7d3a2b9f8c1e4k2m \
  --rights-classification "R1" \
  --operator-justification "Internal training content, employee-only distribution, licensed under corporate usage policy"

# Republish blueprint
ssid-sws republish-job job-7d3a2b9f8c1e4k2m \
  --target-state "PUBLISHED"
```

### Scenario 4: OCR Worker Fails (Unsupported Language)

**Symptom:** Job completes analysis, but OCR worker fails to extract text

**Investigation:**
```bash
ssid-sws show-job job-7d3a2b9f8c1e4k2m | grep -A 3 "ocr"

# Output:
# "ocr": { "status": "FAILED", "error": "E-MEDIA-UNSUPPORTED_LANGUAGE", "language_detected": "ja" }
```

**Root Cause:** Document in Japanese, OCR engine not configured for CJK

**Fix:**
```bash
# Retry with explicit language specification
ssid-sws retry-job job-7d3a2b9f8c1e4k2m \
  --ocr-languages "ja,en" \
  --skip-previous-workers "video_analysis,audio_analysis,transcript"

# Or accept incomplete blueprint
ssid-sws force-state job-7d3a2b9f8c1e4k2m \
  --target-state "BLUEPRINT_READY" \
  --skip-incomplete-workers "ocr" \
  --reason "OCR unsupported for Japanese; blueprint complete without text extraction"
```

### Scenario 5: Webhook Delivery Failed at Publish

**Symptom:** Job reaches PUBLISHED state, but external webhook receives 500 error

**Investigation:**
```bash
ssid-sws show-job job-7d3a2b9f8c1e4k2m | grep -A 5 "hooks"

# Output:
# "hooks": {
#   "status": "FAILED",
#   "webhook_url": "https://client-api.example.com/sws/notify",
#   "http_status": 500,
#   "retry_count": 3,
#   "last_error": "Internal Server Error"
# }
```

**Root Cause:** Webhook endpoint down or misconfigured

**Fix:**
```bash
# Option 1: Manually retry webhook
ssid-sws retry-webhook job-7d3a2b9f8c1e4k2m \
  --webhook-url "https://client-api.example.com/sws/notify" \
  --retry-count 5 \
  --timeout-seconds 30

# Option 2: Change webhook URL
ssid-sws update-job job-7d3a2b9f8c1e4k2m \
  --webhook-url "https://client-api.example.com/sws/notify-v2"

# Option 3: Fallback to API polling
# (Client must poll GET /sws/jobs/{job_id}/blueprints instead)
```

---

## 7. CLI Reference

### analyze-url

```bash
ssid-sws analyze-url "https://example.com/content.mp4" [OPTIONS]

Options:
  --rights-assumption {R0,R1,R2,R3,R4}     Override automatic classification (default: auto-detect)
  --video-quality-preset {low,medium,high} Processing resolution (default: high)
  --timeout-seconds INT                    Maximum processing time (default: 1800)
  --webhook-url STRING                     Delivery webhook
  --webhook-retry-count INT                Retries on webhook failure (default: 3)
  --ocr-languages STRING                   Comma-separated language codes (default: en)
  --skip-workers STRING                    Comma-separated worker names to skip
  --wait                                    Block until completion
  --output-format {json,yaml}              Result format (default: json)

Example:
  ssid-sws analyze-url "https://s3.example.com/video.mp4" \
    --rights-assumption R1 \
    --video-quality-preset medium \
    --webhook-url "https://api.example.com/notify" \
    --wait
```

### analyze-file

```bash
ssid-sws analyze-file LOCAL_PATH [OPTIONS]

Options:
  --transcode-preset {h264_720p,h264_1080p,h265_1080p} Pre-processing codec (default: none)
  --audio-channels {1,2,6}                 Target audio channels (default: original)
  --rights-assumption {R0,R1,R2,R3,R4}     Rights classification (default: R2)
  [all options from analyze-url]

Example:
  ssid-sws analyze-file "./training-video.mov" \
    --transcode-preset h264_720p \
    --audio-channels 2 \
    --wait
```

### show-job

```bash
ssid-sws show-job JOB_ID [OPTIONS]

Options:
  --include-timeline               Show full event timeline
  --include-worker-details         Show worker performance metrics
  --include-blueprints             Show blueprint statistics
  --output-format {json,yaml,text} Result format (default: json)

Example:
  ssid-sws show-job job-7d3a2b9f8c1e4k2m --include-timeline --output-format yaml
```

### retry-job

```bash
ssid-sws retry-job JOB_ID [OPTIONS]

Options:
  --source-url STRING                      New source URL
  --rights-classification {R0,R1,R2,R3,R4} New rights
  --skip-previous-workers STRING           Don't re-run these workers
  --video-quality-preset STRING            Reduced quality settings
  --force-restart                          Restart from CREATED state
  --reason STRING                          Justification log message

Example:
  ssid-sws retry-job job-7d3a2b9f8c1e4k2m \
    --video-quality-preset medium \
    --skip-previous-workers "ocr" \
    --reason "Recovery from timeout"
```

### export-artifacts

```bash
ssid-sws export-artifacts JOB_ID [OPTIONS]

Options:
  --artifact-type {scenes,entities,intents,transcript,ocr,audit_timeline,all} Default: all
  --format {json,csv,markdown}             Output format (default: json)
  --output FILE_PATH                       Save to file
  --with-signature                         Include cryptographic signature
  --include-raw-data                       Include unprocessed worker output

Example:
  ssid-sws export-artifacts job-7d3a2b9f8c1e4k2m \
    --artifact-type scenes \
    --format csv \
    --output scenes.csv

  ssid-sws export-artifacts job-7d3a2b9f8c1e4k2m \
    --artifact-type audit_timeline \
    --format json \
    --with-signature \
    --output audit.json
```

### list-jobs

```bash
ssid-sws list-jobs [OPTIONS]

Options:
  --limit INT                              Page size (default: 20)
  --offset INT                             Pagination offset
  --state {CREATED,ANALYZING,PUBLISHED,FAILED} Filter by state
  --since ISO8601                          Start time
  --until ISO8601                          End time
  --sort {created_asc,created_desc,modified_asc,modified_desc} Sort order
  --output-format {json,yaml,table}        Display format (default: table)

Example:
  ssid-sws list-jobs --state FAILED --limit 50 --output-format table
  ssid-sws list-jobs --since "2026-04-16T00:00:00Z" --sort created_desc
```

---

## 8. FAQ

### Q1: How long does a typical analysis job take?

**A:** 5–20 minutes depending on media type and length:
- **Short video (5–10 min):** 6–10 minutes
- **Long video (1–3 hours):** 12–20 minutes
- **Audio-only:** 8–15 minutes (faster than video)
- **Document/images:** 2–8 minutes
- **Bottleneck:** Video analysis (frame-by-frame processing)

### Q2: Can I cancel a job mid-processing?

**A:** Yes, with caveats:
```bash
ssid-sws cancel-job job-7d3a2b9f8c1e4k2m
```
- If job is in `ANALYZING`, running workers are terminated
- Blueprint is discarded; no results available
- Use only in emergency scenarios
- Job state transitions to `CANCELLED` (terminal)

### Q3: What's the maximum file size?

**A:** Default quota is **5 GB per job**. Workarounds:
- Transcode to lower quality (see analyze-file options)
- Split into multiple jobs
- Request quota increase via support

### Q4: Are results cached?

**A:** No. Each job runs independently. If you re-analyze the same content, it will be processed again.
- **Rationale:** Rights classifications may change, quality presets differ
- **Mitigation:** Store blueprint exports locally for reference

### Q5: Can I modify a blueprint after publishing?

**A:** No. Blueprints are immutable once `PUBLISHED`.
- **Workaround:** Create a new job with corrected content or updated rights classification
- **For minor fixes:** Use `update-job` to change metadata (e.g., rights classification), then `republish-job`

### Q6: What if a webhook delivery fails?

**A:** Job completes and enters `PUBLISHED` state; webhook delivery retries 3 times automatically.
- After 3 failures, job remains `PUBLISHED` but webhook not delivered
- **Resolution:** Use `retry-webhook` or configure fallback polling (client queries API)

### Q7: How do I handle content in non-English languages?

**A:** Specify OCR and transcript languages:
```bash
ssid-sws analyze-url "https://example.com/video-fr.mp4" \
  --ocr-languages "fr,en" \
  --transcript-language "fr"
```
Supported: en, es, fr, de, ja, zh-Simplified, zh-Traditional, ar, ru, ko, pt, it

### Q8: What rights classification should I use for academic papers?

**A:** Default to `R2` (inferred):
```bash
ssid-sws analyze-url "https://arxiv.org/pdf/2104.05427.pdf" \
  --rights-assumption R2 \
  --reason "Academic publication with standard reuse license"
```
If copyright holder unknown, system auto-assigns R2 with confidence 0.75–0.85.

### Q9: Can multiple users access the same job?

**A:** Yes. Job is accessible via API with appropriate auth tokens. Blueprints inherit parent job's rights classification.

### Q10: How do I audit who accessed my blueprints?

**A:** Export audit timeline:
```bash
ssid-sws export-artifacts job-7d3a2b9f8c1e4k2m \
  --artifact-type audit_timeline \
  --with-signature \
  --format json \
  --output audit-full.json
```
Timeline includes: job creation, all state transitions, worker completion times, webhook deliveries, access logs (if enabled).

---

## 9. Contact & Escalation

### Support Tiers

**Tier 1: Self-Service (First 30 min)**
- Consult this runbook
- Check job status via CLI
- Retry job with adjusted parameters
- Export audit trail

**Tier 2: Operator Team (30–120 min)**
- SSH into worker nodes: `ssh operator@sws-worker-01.example.com`
- Check logs: `docker logs sws-worker-xxx`
- Restart worker: `docker restart sws-worker-xxx`
- **Contact:** ops-team@example.com or #sws-operators Slack channel

**Tier 3: Engineering (>2 hours or data loss risk)**
- Engage SWS platform team
- Database recovery required
- Code-level debugging
- **Contact:** sws-eng@example.com (severity "P1" or "P2" only)

### Escalation Checklist

Before escalating, provide:
1. Job ID (e.g., `job-7d3a2b9f8c1e4k2m`)
2. Error code from `show-job` output
3. Timeline: When did job enter error state?
4. Reproduction steps (if applicable)
5. Audit export: `ssid-sws export-artifacts JOB_ID --artifact-type audit_timeline`

### Emergency Contact

**Critical Issues (Service Down, Data Corruption, Security):**
- **Slack:** @sws-oncall (24/7 rotation)
- **Phone:** +1-555-SWS-HELP (press 1 for platform)
- **PagerDuty:** [sws-incidents](https://example.pagerduty.com/incidents)

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| **Blueprint** | Semantic artifact collection: scenes, entities, intents, transcript, OCR results |
| **Scene** | Keyframe + metadata extracted at 2 fps from video |
| **Entity** | Person, object, location, event detected in blueprint |
| **Intent** | Inferred semantic purpose (e.g., "explain_concept", "customer_testimonial") |
| **Worker** | Parallel job: video_analysis, audio_analysis, transcript, ocr, hooks |
| **Rights Classification** | R0–R4 rating of content usage permissions (R0=full, R4=denied) |
| **Watermark** | Visible/invisible marker on restricted (R1–R3) blueprints |
| **Webhook** | External HTTP endpoint notified on job completion |
| **Presigned URL** | Temporary S3 URL with embedded credentials (expires 1 hour default) |
| **Transcode** | Re-encode video to standard codec/quality for compatibility |
| **DPI** | Dots per inch; OCR quality metric for text extraction |
| **Confidence Score** | 0.0–1.0 metric: likelihood of correct extraction/classification |
| **Terminal State** | Job state with no further transitions (PUBLISHED, FAILED, CANCELLED) |
| **Audit Trail** | Chronological log of job events, state changes, access |
| **Force State** | Operator override to advance job to specific state (bypass normal flow) |
| **Presigned URL** | Temporary S3 URL with embedded credentials (expires 1 hour default) |

---

## Appendix: Command Cheat Sheet

```bash
# Create new job from URL
ssid-sws analyze-url "URL" --wait

# Create new job from local file
ssid-sws analyze-file "PATH" --wait

# Check job status
ssid-sws show-job JOB_ID

# Retry failed job
ssid-sws retry-job JOB_ID --reason "reason"

# List all jobs (last 24h)
ssid-sws list-jobs --since "2026-04-15T00:00:00Z"

# Export blueprint results
ssid-sws export-artifacts JOB_ID --artifact-type all --format json --output results.json

# Export audit trail
ssid-sws export-artifacts JOB_ID --artifact-type audit_timeline --with-signature --output audit.json

# Force job to specific state (emergency only)
ssid-sws force-state JOB_ID --target-state STATE --reason "reason"

# Retry webhook delivery
ssid-sws retry-webhook JOB_ID --webhook-url "URL"

# List failed jobs
ssid-sws list-jobs --state FAILED

# List jobs in QA review
ssid-sws list-jobs --state QA_PENDING
```

---

**Last Updated:** 2026-04-16  
**Version:** 1.0  
**Owner:** SWS Operations  
**Status:** Production Ready
