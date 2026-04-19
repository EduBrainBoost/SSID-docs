# Runbook — SWS Rebuild Failure

Scope: failures in `rebuild_spine` stages (`replacement_plan`, `timeline_build`, `render`).

## Symptoms

- `attempt_manifest.status == "failed"` for a rebuild job (mode=`rebuild`).
- Error codes:
  - `NO_BLUEPRINT` (replacement_plan saw no rebuild_blueprint.json)
  - `MISSING_UPSTREAM` (timeline_build saw no blueprint or no plan)
  - `NO_TIMELINE` (render saw no rebuild_timeline.json)
  - `REPLACEMENT_PLAN_EXCEPTION`
  - `TIMELINE_BUILD_EXCEPTION`
  - `RENDER_EXCEPTION`

## Triage

1. Locate the source analyze workdir referenced by `input_ref` in the rebuild's `job_manifest.json`.
2. Confirm `rebuild_blueprint.json` exists and is schema-valid.
3. Check rebuild-attempt artifacts present so far: `ls <rebuild_workdir>`.

## Per-error response

### NO_BLUEPRINT
- The passed `--job-workdir` does not contain `rebuild_blueprint.json`.
- Fix: point to an attempt workdir that has completed blueprint_compile. Re-run rebuild_spine with correct path.

### MISSING_UPSTREAM in timeline_build
- `replacement_plan.json` was not produced. Inspect the previous stage's result.
- If replacement_plan truly failed, fix that first; rebuild stages are strictly sequential.

### NO_TIMELINE in render
- `rebuild_timeline.json` was not produced. Re-run timeline_build in isolation and validate output against `rebuild_timeline.schema.json`.

### Stage EXCEPTION codes
- Read `error_message`. Common root causes:
  - missing/corrupt blueprint JSON (fixed via re-analyze)
  - disk full
  - PermissionError on the workdir (mounted read-only)

### Render returns status `skipped_no_renderer`
- Not a failure. Means FFmpeg is absent; `render_output_manifest` is written with placeholder content.
- Install FFmpeg on the rebuild worker, then re-run rebuild_spine.

## Policy reminder

- `allow_1to1_copy` is **always false**. If a replacement_ref somehow points at the original `source_manifest.storage_path`, that is a **hard governance incident**; file under `EXTERNAL_HARD_BLOCK` and pause the rebuild lane.
- Deterministic render means: given the same timeline + same asset refs, the output hash must match. If it doesn't, the render engine is non-deterministic — open a LANE_C ticket.

## Preventive

- Nightly: run the WAVE_003 gate runner on a known-good fixture and compare render hashes.
- Alert on `stage_trace` containing `render` with `status_skipped_no_renderer` > 1% of rebuilds.
