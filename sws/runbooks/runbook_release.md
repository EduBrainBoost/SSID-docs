# Runbook — SWS Release

Scope: promoting a SWS version from the workspace to a deployable state.

## Prerequisites

- All 6 wave close reports present under `SSID/sws/evidence/`:
  `WAVE_001/wave_close_report.md` … `WAVE_006/wave_close_report.md`.
- `python SSID/sws/planning/gate_runner.py` returns 0 (Foundation).
- `python SSID/sws/planning/gate_runner_wave002.py` returns 0 (Analyze).
- `python SSID/sws/planning/gate_runner_wave003.py` returns 0 (Rebuild).
- `python SSID/sws/planning/gate_runner_wave004.py` returns 0 (Operatorization).
- `python SSID/sws/planning/gate_runner_wave005.py` returns 0 (Governance).
- `python SSID/sws/planning/gate_runner_wave006.py` returns 0 (Deploy).

## Steps

### 1. Tag

```
TAG="sws-v1.0-$(date +%Y%m%d)"
git -C SSID-EMS tag "$TAG"
git -C SSID-orchestrator tag "$TAG"
git -C SSID-open-core tag "$TAG"
git -C SSID-docs tag "$TAG"
git -C SSID tag "$TAG"
```

### 2. Freeze schemas

Copy the 14 V1 + V1.5 JSON schemas from `SSID-open-core/sws/schemas/` to an
immutable release bundle:

```
SSID-docs/sws/releases/$TAG/schemas/
```

with a `SHA256SUMS` file. These are the contract consumers must target.

### 3. Build container images (if present)

`docker-compose.sws.yml` entries for:
- `sws_backend` (SSID-EMS FastAPI)
- `sws_orchestrator` (CLI worker image)
- `sws_frontend` (Next.js / SWS UI)
- `sws_metrics` (Prometheus exporter; V1.5 optional)

### 4. Deploy local

```
docker compose -f SSID-EMS/portal/docker-compose.sws.yml up -d
```

Health:
```
curl http://127.0.0.1:8100/health
curl http://127.0.0.1:3100/sws/jobs
```

### 5. Smoke test

```
python -m sws.pipeline.analyze_spine --file ./samples/fixture.mp4 --rights R0 --workdir-base ./sws_jobs
python -m sws.pipeline.rebuild_spine --job-workdir ./sws_jobs/<job>/<att> --rights R0 --workdir-base ./sws_rebuilds
```

Confirm:
- both exits with code 0
- `render_output_manifest.status` in `{"succeeded","skipped_no_renderer"}`
- `audit_log.jsonl` verify_chain = OK

### 6. Publish docs

Regenerate `SSID-docs` site; confirm new pages under `/sws/*`.

## Rollback

Revert tags and `docker compose down`:

```
docker compose -f SSID-EMS/portal/docker-compose.sws.yml down
for repo in SSID-EMS SSID-orchestrator SSID-open-core SSID-docs SSID; do
  git -C "$repo" tag -d "$TAG"
done
```

Do not touch `audit_log.jsonl`, `rights_decisions.jsonl`, or any `wave_events.jsonl`. They are append-only permanent evidence.

## Known External Hard Block

- `EXTERNAL_HARD_BLOCK_1_team_engine_missing`: release uses script-driven pseudo-teams fallback per Recovery Runbook §4. Not release-blocking for V1.0.
