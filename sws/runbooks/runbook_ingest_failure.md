# Runbook — SWS Ingest Failure

Scope: `ingest` stage failures in `analyze_spine`.

## Symptoms

- `attempt_manifest.json.status == "failed"`
- `stage_trace[1].stage == "ingest"` with `error_code` one of:
  - `INGEST_FILE_MISSING`
  - `INGEST_DOWNLOAD_FAILED`
  - `INGEST_UNKNOWN_KIND`
  - `INGEST_EXCEPTION`

## Quick triage

1. `cat <workdir>/attempt_manifest.json` — read `error_code`, `error_message`.
2. `tail <workdir>/job_events.jsonl` — confirm failure sequence.

## Per-error response

### INGEST_FILE_MISSING
- The provided `input_ref` path does not exist. Often an operator typo.
- Fix: correct the path and re-submit; do not retry the same attempt.

### INGEST_DOWNLOAD_FAILED
- `yt-dlp` or `curl` missing, URL unreachable, or site rejected the request.
- Check PATH: `which yt-dlp && which curl`.
- Check URL manually in a browser.
- If yt-dlp outdated: `pip install -U yt-dlp`.
- Retry with a different mirror; 2nd attempt is independent (`attempt_id` changes).

### INGEST_UNKNOWN_KIND
- Pipeline received an `input_kind` other than `url` or `file_upload`. This is a coding error upstream.
- Escalate: LANE_B ticket with the raw job_manifest.

### INGEST_EXCEPTION
- Catch-all for unexpected exceptions. Read `error_message` for details.
- Most common: disk full at `workdir_base`. `df -h` on the workdir mount.

## Preventive

- Monitor disk usage on `SWS_JOBS_ROOT` — alert at 80%.
- Keep `yt-dlp` fresh (weekly).
- Add a watchdog to detect attempts stuck in `running` status > 30 minutes.
