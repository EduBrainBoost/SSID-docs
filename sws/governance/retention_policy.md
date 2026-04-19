# SWS Retention Policy

Enforced by `SSID-EMS/portal/backend/core/sws/retention_scheduler.py`.

## Retention Classes

| Class | Age | Applies to |
|---|---|---|
| `72h_source` | **72 hours** | raw ingested source media (V1 MUST) |
| `7d_derivative` | 7 days | intermediate artifacts tied to a discarded attempt |
| `30d_evidence` | 30 days | wave close reports, gate reports, job_events.jsonl |
| `audit_permanent` | ~ permanent | rights_decisions.jsonl, audit_log.jsonl (hash-chained) |

## V1 Hard Rule

- Every `source_manifest.json` MUST have `retention_class = "72h_source"` and
  `retention_expires_at = ingested_at + 72h`.
- The `ingest` stage writes these fields by construction.
- The retention scheduler (cron / systemd timer) deletes `storage_path` targets where `retention_expires_at <= now`.
- Deletions must NOT remove the `source_manifest.json` itself — the manifest remains as evidence that ingest occurred, even after the media is gone.

## Scheduler Invocation

```
python -m core.sws.retention_scheduler --manifest-root <sws_jobs_path>
# Optional:
python -m core.sws.retention_scheduler --manifest-root <path> --dry-run
```

Returns a JSON summary: `{ts, total, deleted, kept, errors, dry_run}`.

## Cron Slot (V1.5 target)

- Linux/macOS: cron at `*/15 * * * *` (15-minute cadence)
- Windows Task Scheduler: equivalent 15-minute trigger
- Runbook: `SSID-docs/sws/runbooks/runbook_retention.md` (LANE_F deliverable)

## Override Path (Governor only)

- RBAC action `retention.extend` allows a Governor to bump `retention_expires_at` on a specific `source_manifest.json`, recorded in the audit log.
- RBAC action `retention.purge` allows an immediate force-delete; recorded with justification in the audit log.

## Failure Semantics

- If `storage_path` is missing at deletion time, the scheduler records it under `kept` with marker `(already absent)`.
- Filesystem errors are captured in `errors[]` — the scheduler continues with the next target.
- The scheduler never touches paths outside `manifest_root`. Path-traversal protection is inherent because it reads the path from a manifest inside the root.
