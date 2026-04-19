# Runbook — SWS Analysis Failure

Scope: failures in stages `video_analysis`, `audio_analysis`, `transcript`, `ocr`, `narrative_hook`, `blueprint_compile`.

## Symptoms

- `attempt_manifest.status == "failed"` with `stage_trace[-1].stage` in the set above.
- Error codes:
  - `VIDEO_ANALYSIS_EXCEPTION`
  - `AUDIO_ANALYSIS_EXCEPTION`
  - `TRANSCRIPT_EXCEPTION`
  - `OCR_EXCEPTION`
  - `NARRATIVE_HOOK_EXCEPTION`
  - `BLUEPRINT_COMPILE_EXCEPTION`
  - `MISSING_UPSTREAM` (blueprint_compile without shot_timeline / source_manifest)
  - `NO_SOURCE_MANIFEST` (any stage called before ingest completed)

## Triage

1. `cat <workdir>/attempt_manifest.json` — identify `error_code`, `error_message`.
2. Inspect upstream artifacts. For a stage that failed, check that all its inputs are present and shape-valid:
   - video_analysis / audio_analysis / transcript / ocr: `source_manifest.json`
   - narrative_hook: `transcript_master.json` (stage `skip`s if missing)
   - blueprint_compile: `shot_timeline.json` and `source_manifest.json`

## Per-stage response

### video_analysis
- Most frequent cause: `scenedetect` binary missing. `which scenedetect` — install PySceneDetect if absent.
- Falls back to single-shot timeline; not a hard failure unless an exception bubbles.

### audio_analysis
- librosa missing → fallback empty structure (no failure).
- Unreadable audio container → `AUDIO_ANALYSIS_EXCEPTION` with librosa stack trace.
- Re-run after installing the correct codec (`ffmpeg -codecs | grep <codec>`).

### transcript
- Whisper model weights not yet downloaded on first run → `TRANSCRIPT_EXCEPTION` from faster-whisper.
- Pre-warm: `python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu')"`.

### ocr
- pytesseract needs the tesseract binary. `which tesseract`.
- On Windows set `TESSDATA_PREFIX` or install via Chocolatey.

### narrative_hook
- If `transcript_master.json` is missing the stage marks itself `SKIPPED`, not failed.
- A real failure means an exception in the heuristic code: escalate LANE_B.

### blueprint_compile
- Input shape mismatch: run the schema validator on the upstream artifacts:
  `python SSID-open-core/sws/validators/sws_schema_validator.py`.
- If schemas are green but compile fails → code bug, LANE_B ticket.

## Retry policy

- Transient (network, disk): retry via a fresh `attempt_id` (orchestrator emits automatically up to `RetryPolicy.max_attempts`).
- Deterministic (missing binary, shape error): do NOT retry; fix the environment or input, then submit a new job.

## Preventive

- Run the schema validator in CI. Nightly.
- Keep Whisper/Tesseract binaries prefetched in the container image.
- Watchdog alert on `stage_trace` containing > 1 consecutive `SKIPPED`.
