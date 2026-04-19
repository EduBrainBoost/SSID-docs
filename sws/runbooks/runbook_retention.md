# Runbook — SWS Retention

Scope: scheduled execution of the 72h-source retention policy.

## What it does

The `retention_scheduler` module deletes `storage_path` targets referenced by
`source_manifest.json` files whose `retention_expires_at <= now` and whose
`retention_class` is `72h_source` (V1 hard rule) or any class past its TTL.

## Invocation

```
# Dry run — report only
python -m core.sws.retention_scheduler \
  --manifest-root /mnt/sws_jobs \
  --dry-run

# Live run
python -m core.sws.retention_scheduler \
  --manifest-root /mnt/sws_jobs
```

Output is JSON: `{ts, total, deleted:[...], kept:[...], errors:[...]}`.

## Schedule

### Linux/macOS — cron
```
*/15 * * * * /usr/bin/python -m core.sws.retention_scheduler --manifest-root /mnt/sws_jobs >> /var/log/sws_retention.log 2>&1
```

### Windows — Task Scheduler
- Trigger: every 15 minutes, starting at system start, indefinitely.
- Action: `python.exe -m core.sws.retention_scheduler --manifest-root C:/Users/bibel/SSID-Workspace/SSID-Arbeitsbereich/sws_jobs`
- Run whether user is logged on or not. Run with highest privileges = NO (read/delete on workspace is enough).

## Alerts

Alert if:
- `errors` array length > 0 for more than 2 consecutive runs.
- `deleted` + `kept` is 0 for > 6 hours (the pipeline may be idle; verify).
- `deleted` for a single run exceeds a baseline (e.g. > 100) — could indicate mass-ingest spike.

## Incident

If you suspect a wrong deletion:
1. Check the corresponding `source_manifest.json` — it MUST still exist (invariant).
2. Inspect `ingested_at` vs `retention_expires_at` — is the math correct?
3. If the deletion was premature, confirm the system clock. `timedatectl status` / `w32tm /query /status`.
4. File a governance incident record in the audit log:
   `retention_purge_review` event_type with the job_id.

## Tuning

- To keep sources longer, a Governor sets `retention_class` to `7d_derivative` or higher at ingest time. This requires RBAC action `retention.extend` and is logged.
- V1 does NOT allow per-job purge suppression via scheduler config — changes go through manifest edits (append-only superseding manifest), not scheduler flags.
